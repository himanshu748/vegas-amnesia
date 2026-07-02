"""In-memory session state (hackathon scope: single process, no persistence).

Each session gets its own Cognee dataset, so demo runs never pollute each
other. The session also keeps a snapshot of graph node/edge ids so every
response can carry an incremental `graph_delta` for the frontend to animate.
"""
from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class Session:
    id: str
    dataset: str
    started_at: float
    current_location: str
    # fact_id -> {"text", "data_id", "source_type", "source_ref"}
    discovered: dict[str, dict] = field(default_factory=dict)
    forgotten: set[str] = field(default_factory=set)
    inspected_hotspots: set[str] = field(default_factory=set)
    # per-character conversation history: [{"role", "content"}, ...]
    conversations: dict[str, list[dict]] = field(default_factory=dict)
    # characters whose unlock_condition has fired (e.g. Lou's confession)
    unlocked: set[str] = field(default_factory=set)
    memify_runs: int = 0
    # graph snapshot for delta computation
    seen_node_ids: set[str] = field(default_factory=set)
    seen_edge_ids: set[str] = field(default_factory=set)
    # nodes that first appeared during a memify run — rendered as inferences
    inference_node_ids: set[str] = field(default_factory=set)

    @property
    def active_fact_ids(self) -> set[str]:
        return set(self.discovered) - self.forgotten


_SESSIONS: dict[str, Session] = {}


def create_session(start_location: str) -> Session:
    sid = uuid.uuid4().hex[:12]
    session = Session(
        id=sid,
        dataset=f"vegas_{sid}",
        started_at=time.time(),
        current_location=start_location,
    )
    _SESSIONS[sid] = session
    return session


def get_session(session_id: str) -> Optional[Session]:
    return _SESSIONS.get(session_id)


def drop_session(session_id: str) -> Optional[Session]:
    return _SESSIONS.pop(session_id, None)


def graph_delta(session: Session, graph: dict) -> dict:
    """Diff a fresh graph snapshot against what this session has already seen,
    update the snapshot, and return only the changes (added/removed nodes and
    edges) so the frontend animates increments instead of re-rendering.
    """
    node_ids = {str(n.get("id")) for n in graph.get("nodes", [])}
    edge_ids = {
        f"{e.get('source')}->{e.get('target')}:{e.get('label')}"
        for e in graph.get("edges", [])
    }

    added_nodes = [n for n in graph.get("nodes", []) if str(n.get("id")) not in session.seen_node_ids]
    removed_node_ids = sorted(session.seen_node_ids - node_ids)
    added_edges = [
        e
        for e in graph.get("edges", [])
        if f"{e.get('source')}->{e.get('target')}:{e.get('label')}" not in session.seen_edge_ids
    ]
    removed_edge_ids = sorted(session.seen_edge_ids - edge_ids)

    session.seen_node_ids = node_ids
    session.seen_edge_ids = edge_ids

    return {
        "added_nodes": added_nodes,
        "added_edges": added_edges,
        "removed_node_ids": removed_node_ids,
        "removed_edge_ids": removed_edge_ids,
    }
