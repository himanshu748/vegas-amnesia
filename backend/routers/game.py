"""Gameplay endpoints: state, locations, evidence, dialogue, solve."""
from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from backend.models.facts import load_ground_truth
from backend.models.world import load_world
from backend.routers.session import require_session
from backend.services import cognee_client, game
from backend.services.solve import evaluate_solve

router = APIRouter(prefix="/api", tags=["game"])


class LocationEnter(BaseModel):
    session_id: str
    location_id: str


class EvidenceInspect(BaseModel):
    session_id: str
    location_id: str
    hotspot_id: str


class CharacterTalk(BaseModel):
    session_id: str
    character_id: str
    message: str


class SolveRequest(BaseModel):
    session_id: str


@router.get("/game/state")
async def game_state(session_id: str) -> dict:
    session = require_session(session_id)
    return {"state": game.public_state(session)}


@router.post("/location/enter")
async def enter_location(body: LocationEnter) -> dict:
    session = require_session(body.session_id)
    location = load_world().location(body.location_id)
    if location is None:
        raise HTTPException(status_code=404, detail="unknown location")
    session.current_location = location.id
    return {
        "location": {
            "id": location.id,
            "name": location.name,
            "description": location.description,
            "character": location.character,
            "hotspots": [
                {
                    "id": h.id,
                    "name": h.name,
                    "inspected": h.id in session.inspected_hotspots,
                }
                for h in location.hotspots
            ],
        }
    }


@router.post("/evidence/inspect")
async def inspect_evidence(body: EvidenceInspect) -> dict:
    session = require_session(body.session_id)
    hotspot = load_world().hotspot(body.location_id, body.hotspot_id)
    if hotspot is None:
        raise HTTPException(status_code=404, detail="unknown hotspot")

    session.inspected_hotspots.add(hotspot.id)
    remembered = await game.remember_facts(session, hotspot.facts)
    graph, delta = (None, None)
    if remembered:
        _, delta = await game.fresh_graph_delta(session)

    return {
        "hotspot": {"id": hotspot.id, "name": hotspot.name, "description": hotspot.description},
        "facts": remembered,
        "graph_delta": delta,
        "hud": game.hud_counts(session),
    }


@router.post("/character/talk")
async def talk_to_character(body: CharacterTalk) -> dict:
    """M3 placeholder dialogue: each exchange reveals the character's next
    unknown fact with a canned line. M6 swaps this for LLM-generated dialogue
    with persona + graph-aware context; the revelation/remember flow is final.
    """
    session = require_session(body.session_id)
    character = load_world().character(body.character_id)
    if character is None:
        raise HTTPException(status_code=404, detail="unknown character")

    history = session.conversations.setdefault(character.id, [])
    history.append({"role": "player", "content": body.message})

    truth = load_ground_truth()
    revealed_ids: list[str] = []

    # Lucky Lou's special arc: he lies until confronted with the receipt.
    if character.unlock_condition and character.id not in session.unlocked:
        required = set(character.unlock_condition.requires_facts)
        if required <= session.active_fact_ids:
            session.unlocked.add(character.id)

    if character.id == "lucky_lou" and character.id not in session.unlocked:
        candidates = character.knows_facts  # the lie (f08)
    else:
        candidates = character.knows_facts + character.confesses_facts

    for fid in candidates:
        if fid not in session.discovered:
            revealed_ids = [fid]
            break

    remembered = await game.remember_facts(session, revealed_ids)
    delta = None
    if remembered:
        _, delta = await game.fresh_graph_delta(session)

    if remembered:
        line = f"{character.name}: \"{remembered[0]['text']}\""
    else:
        line = f"{character.name} has nothing new to add. (LLM dialogue lands in M6.)"
    history.append({"role": "character", "content": line})

    return {
        "character": {"id": character.id, "name": character.name},
        "line": line,
        "facts": remembered,
        "graph_delta": delta,
        "hud": game.hud_counts(session),
    }


@router.post("/game/solve")
async def solve(body: SolveRequest) -> dict:
    session = require_session(body.session_id)
    truth = load_ground_truth()
    result = evaluate_solve(
        truth,
        remembered_ids=set(session.discovered),
        forgotten_ids=session.forgotten,
    )
    # HAL answers the final question from its actual Cognee memory — shown on
    # the ending screen next to the reconstructed timeline.
    try:
        recall_answer = await cognee_client.recall(truth.final_question, session.dataset)
    except Exception as exc:
        recall_answer = {"error": str(exc)}
    return {
        "result": result.model_dump(),
        "final_question": truth.final_question,
        "hal_answer": recall_answer,
        "hud": game.hud_counts(session),
    }
