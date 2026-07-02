"""Gameplay endpoints: state, locations, evidence, dialogue, solve."""
from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

import logging

from backend.models.facts import load_ground_truth
from backend.models.world import load_world
from backend.routers.session import require_session
from backend.services import cognee_client, game, llm
from backend.services.solve import evaluate_solve

log = logging.getLogger("game")
router = APIRouter(prefix="/api", tags=["game"])


async def generate_line(session, character, truth, message, history,
                        reveal_text, lie_mode) -> str:
    """LLM line with persona + graph context; scripted fallback on any failure."""
    if llm.available():
        try:
            known = [
                (f.text, fid in session.discovered)
                for fid in character.knows_facts + character.confesses_facts
                if (f := truth.fact_by_id(fid))
            ]
            player_facts = [
                rec["text"] for fid, rec in session.discovered.items()
                if fid in session.active_fact_ids
            ]
            debunks = [
                character.debunk_hints[rh] for rh in character.debunks
                if rh in session.active_fact_ids and rh in character.debunk_hints
            ]
            system = llm.build_dialogue_system(
                character, known, player_facts, reveal_text, lie_mode, debunks)
            messages = [
                {"role": "user" if m["role"] == "player" else "assistant", "content": m["content"]}
                for m in history[-8:]
            ]
            return await llm.chat(system, messages)
        except Exception as exc:
            log.warning("LLM dialogue failed, using scripted line: %s", exc)
    if reveal_text:
        return f"{reveal_text}"
    return "Look, I've told you everything I remember. Try someone else — or that graph of yours."


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
    """Fact reveals stay deterministic (scripted arc, reliable demo); the
    spoken line is LLM-generated with persona + graph-aware context, falling
    back to scripted lines when no LLM key is configured.
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

    lie_mode = character.id == "lucky_lou" and character.id not in session.unlocked
    candidates = character.knows_facts if lie_mode else (
        character.knows_facts + character.confesses_facts
    )

    for fid in candidates:
        if fid not in session.discovered:
            revealed_ids = [fid]
            break

    reveal_text = None
    if revealed_ids:
        fact = truth.fact_by_id(revealed_ids[0])
        reveal_text = fact.text if fact else None

    line = await generate_line(session, character, truth, body.message,
                               history, reveal_text, lie_mode)

    remembered = await game.remember_facts(session, revealed_ids)
    delta = None
    if remembered:
        _, delta = await game.fresh_graph_delta(session)

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
