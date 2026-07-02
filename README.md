# Vegas Amnesia 🎰🧠

A detective game where **you are an AI agent that woke up with a wiped memory**.
Explore Vegas, collect evidence, interrogate characters, and reconstruct last
night — every discovery flows through **Cognee Cloud's full memory lifecycle**
(`remember → recall → memify → forget`), visualized as a live memory graph that
IS the game UI.

Built for the **WeMakeDevs × Cognee "The Hangover Part AI" hackathon — Cognee
Cloud track**.

> **AI-assistant disclosure:** built with Claude Code (as required by hackathon rules).

## Memory lifecycle usage (for the judges)

| Lifecycle op | Cognee Cloud endpoint (verified live via `scripts/smoke_test.py`) | In-game mechanic |
|---|---|---|
| `remember` | `POST /api/v1/remember` (multipart, auto-cognifies; one data item per fact, named by fact id) | Inspecting evidence / character revelations → facts ingested, nodes pop into the graph |
| `recall` | `POST /api/v1/recall` with `includeReferences` (+ `/search` for typed queries) | "Ask HAL" free-text questions + the final "Solve the Night" check, with graph-node citations |
| `memify` | `POST /api/v1/cognify` re-run with a custom inference-extraction prompt¹ | "Consolidate Memories" button → inferred nodes/edges render purple with a 💡 animation |
| `forget` | `POST /api/v1/forget` with `dataId` (dedicated unified-deletion endpoint) | Right-click a node → prune red herrings; node fades out |

¹ Our Cognee Cloud tenant doesn't expose `/api/v1/memify`, so per the closest-equivalent rule we
implement memify as a `cognify` re-run whose `customPrompt` extracts *inferred* temporal/causal/
contradiction relationships across already-remembered facts (see `MEMIFY_PROMPT` in
`backend/services/cognee_client.py`).

Every call is timed and logged (`backend/services/cognee_client.py:CALL_LOG`);
press <kbd>`</kbd> in-game for the raw lifecycle-call debug overlay.
Each game session gets its own Cognee dataset, so demo runs never pollute each other.

## Stack

- **Backend** — Python 3.11 / FastAPI, deployed as a Hugging Face Docker Space
- **Frontend** — vanilla JS + Cytoscape.js, deployed on Vercel (static)
- **Memory** — Cognee Cloud REST API (all calls wrapped in `backend/services/cognee_client.py`)
- **Dialogue LLM** — HuggingFace Inference API (Qwen2.5-72B) or Anthropic, env-selected

## Run locally

```bash
cp .env.example .env          # fill in COGNEE_API_KEY (+ HF_TOKEN for dialogue)
python -m venv .venv && .venv/bin/pip install -r backend/requirements.txt

# M1 gate — verify all four lifecycle ops against Cognee Cloud:
.venv/bin/python scripts/smoke_test.py

# run the API:
.venv/bin/uvicorn backend.app:app --reload --port 8000
```

## Repo layout

```
backend/            FastAPI app
  services/         cognee_client.py (ALL Cognee calls), llm.py, sessions
  routers/          session / game / memory endpoints
  prompts/          character + fact-extraction prompts
story/              ground_truth.json — the ~20-fact true timeline + red herrings
frontend/           vanilla JS + Cytoscape.js (assets/manifest.json for art drops)
scripts/            smoke_test.py — Cognee Cloud lifecycle verification
docs/               architecture diagram, 2-min demo script
```

*(Architecture diagram + demo script land in M8.)*
