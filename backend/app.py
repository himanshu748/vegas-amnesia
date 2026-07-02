"""Vegas Amnesia — FastAPI backend (deployed as a Hugging Face Docker Space)."""
import logging
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from backend import config
from backend.services import cognee_client

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(message)s")

app = FastAPI(title="Vegas Amnesia", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=config.ALLOWED_ORIGINS,
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/api/health")
async def health() -> dict:
    return {
        "status": "ok",
        "cognee_configured": bool(config.COGNEE_API_KEY),
        "llm_backend": config.LLM_BACKEND,
    }


@app.get("/api/debug/cognee-log")
async def cognee_log() -> dict:
    """Raw lifecycle-call log for the in-game debug overlay (backtick key)."""
    return {"calls": cognee_client.CALL_LOG[-100:]}


from backend.routers import game, memory, session  # noqa: E402

app.include_router(session.router)
app.include_router(game.router)
app.include_router(memory.router)

# Single-service deploy: serve the static frontend from the same origin
# (HF Spaces runs just this container). Vercel remains optional per PRD.
_FRONTEND = Path(__file__).resolve().parents[1] / "frontend"
if _FRONTEND.is_dir():
    app.mount("/", StaticFiles(directory=_FRONTEND, html=True), name="frontend")
