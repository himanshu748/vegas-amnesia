"""Game-logic glue between the routers, the story files, and Cognee.

Every discovery flows through here: ground-truth fact ids -> remember() ->
session bookkeeping -> fresh graph snapshot -> incremental graph_delta.
"""
from __future__ import annotations

from backend.models.facts import load_ground_truth
from backend.models.world import load_world
from backend.services import cognee_client
from backend.services.session_store import Session, graph_delta


async def remember_facts(session: Session, fact_ids: list[str]) -> list[dict]:
    """Ingest newly discovered ground-truth facts into the session's dataset.
    Already-discovered ids are skipped (re-inspecting evidence is free).
    Returns the fact records that were newly remembered.
    """
    truth = load_ground_truth()
    new_ids = [fid for fid in fact_ids if fid not in session.discovered]
    payloads = []
    for fid in new_ids:
        fact = truth.fact_by_id(fid)
        if fact is not None:
            payloads.append({"id": fid, "text": fact.text})

    if not payloads:
        return []

    result = await cognee_client.remember(payloads, session.dataset)
    remembered = []
    for entry in result["remembered"]:
        fact = truth.fact_by_id(entry["fact_id"])
        record = {
            "fact_id": entry["fact_id"],
            "text": entry["text"],
            "data_id": entry["data_id"],
            "source_type": fact.source.type if fact else "evidence",
            "source_ref": fact.source.ref if fact else "unknown",
            "is_red_herring": bool(fact and fact.is_red_herring),
            "time_hint": fact.time_hint if fact else None,
        }
        session.discovered[entry["fact_id"]] = record
        session.forgotten.discard(entry["fact_id"])  # re-discovery revives it
        remembered.append(record)
    return remembered


async def fresh_graph_delta(session: Session) -> tuple[dict, dict]:
    """(full graph in Cytoscape form, incremental delta) for the session."""
    graph = await cognee_client.get_graph(session.dataset)
    delta = graph_delta(session, graph)
    return to_cytoscape(graph, session), format_delta(delta, session)


def node_type(node: dict, session: Session) -> str:
    if str(node.get("id")) in session.inference_node_ids:
        return "inference"
    return "memory"


def to_cytoscape(graph: dict, session: Session) -> dict:
    """Cognee's {nodes, edges} -> Cytoscape.js elements JSON."""
    nodes = [
        {
            "data": {
                "id": str(n.get("id")),
                "label": n.get("label") or n.get("name") or str(n.get("id"))[:8],
                "type": node_type(n, session),
                "properties": n.get("properties") or {},
            }
        }
        for n in graph.get("nodes", [])
    ]
    edges = [
        {
            "data": {
                "id": f"{e.get('source')}->{e.get('target')}:{e.get('label')}",
                "source": str(e.get("source")),
                "target": str(e.get("target")),
                "label": e.get("label") or "",
            }
        }
        for e in graph.get("edges", [])
    ]
    return {"nodes": nodes, "edges": edges}


def format_delta(delta: dict, session: Session) -> dict:
    return {
        "added_nodes": [
            {
                "data": {
                    "id": str(n.get("id")),
                    "label": n.get("label") or n.get("name") or str(n.get("id"))[:8],
                    "type": node_type(n, session),
                }
            }
            for n in delta["added_nodes"]
        ],
        "added_edges": [
            {
                "data": {
                    "id": f"{e.get('source')}->{e.get('target')}:{e.get('label')}",
                    "source": str(e.get("source")),
                    "target": str(e.get("target")),
                    "label": e.get("label") or "",
                }
            }
            for e in delta["added_edges"]
        ],
        "removed_node_ids": delta["removed_node_ids"],
        "removed_edge_ids": delta["removed_edge_ids"],
    }


def hud_counts(session: Session) -> dict:
    """Lifecycle usage counters for the HUD (reinforces API usage to judges)."""
    return {
        "memories": len(session.active_fact_ids),
        "inferences": len(session.inference_node_ids),
        "forgotten": len(session.forgotten),
        "memify_runs": session.memify_runs,
    }


def public_state(session: Session) -> dict:
    world = load_world()
    return {
        "session_id": session.id,
        "dataset": session.dataset,
        "started_at": session.started_at,
        "current_location": session.current_location,
        "locations": [
            {"id": l.id, "name": l.name, "character": l.character}
            for l in world.locations
        ],
        "discovered_facts": [
            {**rec, "forgotten": fid in session.forgotten}
            for fid, rec in session.discovered.items()
        ],
        "inspected_hotspots": sorted(session.inspected_hotspots),
        "hud": hud_counts(session),
    }
