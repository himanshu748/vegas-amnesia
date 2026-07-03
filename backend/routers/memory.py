"""Memory lifecycle endpoints — the judge-facing surface: memify/forget/recall/graph."""
from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from backend.models.facts import load_ground_truth
from backend.routers.session import require_session
from backend.services import cognee_client, game

router = APIRouter(prefix="/api", tags=["memory"])


class MemifyRequest(BaseModel):
    session_id: str


class ForgetRequest(BaseModel):
    session_id: str
    fact_id: str


class RecallRequest(BaseModel):
    session_id: str
    query: str


@router.post("/memory/memify")
async def memify(body: MemifyRequest) -> dict:
    """Consolidate memories. Two layers:
    1. Cognee's cognify re-run with the inference-extraction prompt.
    2. Derivation: any ground-truth derivable inference whose premises are all
       in the player's active memory gets remembered as a new memory item.
    Nodes/edges appearing during this call render purple as inferences.
    """
    session = require_session(body.session_id)
    await cognee_client.memify(session.dataset)
    session.memify_runs += 1

    truth = load_ground_truth()
    derived = [
        {"id": d.id, "text": d.text}
        for d in truth.derivable
        if d.id not in session.discovered
        and set(d.derived_from) <= session.active_fact_ids
    ]
    new_inferences = []
    if derived:
        result = await cognee_client.remember(derived, session.dataset)
        for entry in result["remembered"]:
            derived_from = next(
                (d.derived_from for d in truth.derivable if d.id == entry["fact_id"]), [])
            record = {
                "fact_id": entry["fact_id"],
                "text": entry["text"],
                "data_id": entry["data_id"],
                "source_type": "inference",
                "source_ref": f"memify_run_{session.memify_runs}",
                "is_red_herring": False,
                "time_hint": None,
                "derived_from": derived_from,
            }
            session.discovered[entry["fact_id"]] = record
            new_inferences.append(record)
    graph, delta = await game.fresh_graph_delta(session)
    new_ids = {n["data"]["id"] for n in delta["added_nodes"]}
    session.inference_node_ids |= new_ids
    # re-tag the freshly added nodes now that they're known to be inferences
    for node in delta["added_nodes"]:
        node["data"]["type"] = "inference"
    for node in graph["nodes"]:
        if node["data"]["id"] in new_ids:
            node["data"]["type"] = "inference"
    return {
        "graph": graph,
        "graph_delta": delta,
        "inferences": new_inferences,
        "hud": game.hud_counts(session),
    }


@router.post("/memory/forget")
async def forget(body: ForgetRequest) -> dict:
    session = require_session(body.session_id)
    record = session.discovered.get(body.fact_id)
    if record is None:
        raise HTTPException(status_code=404, detail="fact not discovered in this session")
    if body.fact_id in session.forgotten:
        raise HTTPException(status_code=409, detail="fact already forgotten")

    await cognee_client.forget(
        session.dataset, data_id=record.get("data_id"), fact_id=body.fact_id
    )
    session.forgotten.add(body.fact_id)
    _, delta = await game.fresh_graph_delta(session)
    return {"forgotten": body.fact_id, "graph_delta": delta, "hud": game.hud_counts(session)}


@router.post("/memory/recall")
async def recall(body: RecallRequest) -> dict:
    """Ask HAL: free-text recall over the session's memory, with graph-node
    citations (nodes whose labels appear in the answer get pulse-highlighted)."""
    session = require_session(body.session_id)
    answer = await cognee_client.recall(body.query, session.dataset)

    answer_text = str(answer).lower()
    graph = await cognee_client.get_graph(session.dataset)
    cited = [
        str(n.get("id"))
        for n in graph.get("nodes", [])
        if (label := str(n.get("label") or n.get("name") or "")).strip()
        and len(label) > 3
        and label.lower() in answer_text
    ]
    return {"answer": answer, "cited_node_ids": cited, "hud": game.hud_counts(session)}


@router.get("/graph")
async def full_graph(session_id: str) -> dict:
    session = require_session(session_id)
    graph, delta = await game.fresh_graph_delta(session)
    return {"graph": graph, "graph_delta": delta, "hud": game.hud_counts(session)}
