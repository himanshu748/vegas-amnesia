"""Session lifecycle — each session owns a fresh Cognee dataset."""
from __future__ import annotations

import logging

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from backend.models.world import load_world
from backend.services import cognee_client, game, session_store

log = logging.getLogger("session")
router = APIRouter(prefix="/api/session", tags=["session"])


class SessionRef(BaseModel):
    session_id: str


@router.post("/start")
async def start_session() -> dict:
    world = load_world()
    session = session_store.create_session(world.start_location)
    log.info("session %s started, dataset=%s", session.id, session.dataset)
    return {"state": game.public_state(session)}


@router.post("/reset")
async def reset_session(body: SessionRef) -> dict:
    """Drop the old session and its Cognee dataset, hand back a fresh one."""
    old = session_store.drop_session(body.session_id)
    if old is not None:
        try:
            await cognee_client.delete_dataset(old.dataset)
        except Exception as exc:  # cleanup is best-effort; never block a reset
            log.warning("dataset cleanup for %s failed: %s", old.dataset, exc)
    world = load_world()
    session = session_store.create_session(world.start_location)
    return {"state": game.public_state(session)}


def require_session(session_id: str) -> session_store.Session:
    session = session_store.get_session(session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="unknown session_id")
    return session
