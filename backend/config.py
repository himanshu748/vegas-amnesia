"""Central config — everything comes from env vars (HF Spaces secrets in prod)."""
import os

COGNEE_API_KEY = os.environ.get("COGNEE_API_KEY", "")
COGNEE_BASE_URL = os.environ.get("COGNEE_BASE_URL", "https://api.cognee.ai").rstrip("/")

LLM_BACKEND = os.environ.get("LLM_BACKEND", "hf")  # "hf" | "anthropic"
HF_TOKEN = os.environ.get("HF_TOKEN", "")
HF_MODEL = os.environ.get("HF_MODEL", "Qwen/Qwen2.5-72B-Instruct")
ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")
ANTHROPIC_MODEL = os.environ.get("ANTHROPIC_MODEL", "claude-sonnet-5")

# Optional access gate: when set, /api/session/start requires this code in the
# X-Access-Code header (judges get it in the submission). Empty = open.
ACCESS_CODE = os.environ.get("ACCESS_CODE", "")
# Cap concurrent sessions so public traffic can't run up the Cognee tenant.
MAX_SESSIONS = int(os.environ.get("MAX_SESSIONS", "40"))

ALLOWED_ORIGINS = [
    o.strip()
    for o in os.environ.get(
        "ALLOWED_ORIGINS", "http://localhost:3000,http://127.0.0.1:3000"
    ).split(",")
    if o.strip()
]
