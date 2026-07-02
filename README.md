---
title: Vegas Amnesia
emoji: 🎰
colorFrom: pink
colorTo: purple
sdk: docker
app_port: 7860
pinned: false
---

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
| `memify` | `POST /api/v1/cognify` re-run with a custom inference-extraction prompt¹ + derived inferences remembered as new memory items | "Consolidate Memories" button → inferred nodes/edges render purple with a 💡 animation |
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

# run everything (API + game UI on the same origin):
.venv/bin/uvicorn backend.app:app --reload --port 8000
# → open http://localhost:8000
```

## Architecture

```
 browser (vanilla JS + Cytoscape.js)
   │  clicks evidence / talks to characters / consolidate / forget / Ask-HAL
   ▼
 FastAPI (HF Docker Space, serves the static frontend too)
   │  session_store: session ←→ its own Cognee dataset (+ graph-delta snapshots)
   │  game.py: ground-truth fact reveals, solve scoring   llm.py: dialogue (HF/Anthropic)
   ▼
 Cognee Cloud tenant  —  remember / recall(search) / memify(cognify+prompt) / forget
   └─ GET /datasets/{id}/graph  →  Cytoscape deltas animated in the memory panel
```

## Deploy

**Hugging Face Docker Space (single service — API + UI):**
1. Create a Docker Space, point it at this repo (`backend/Dockerfile`, build context = repo root).
2. Space secrets: `COGNEE_API_KEY`, `COGNEE_BASE_URL` (your tenant URL), `HF_TOKEN`,
   `ALLOWED_ORIGINS` (add your Vercel domain if you split the frontend out).
3. Optional split per PRD: deploy `frontend/` to Vercel as a static site and open it
   with `?api=https://<your-space>.hf.space`.

## 2-minute demo script

1. **0:00 boot** — "MEMORY CORRUPTED" screen; empty graph. "I'm HAL-9001. My memory
   was wiped. Priya arrives at noon."
2. **0:15 remember** — Hotel Suite: click the safe note + ice bucket → fact chips,
   cyan nodes pop into the graph, HUD counts tick.
3. **0:40 recall** — Ask HAL: *"Where is Priya's engagement ring?"* → answer + amber
   citation pulse on source nodes.
4. **1:00 memify** — hit CONSOLIDATE → purple inferred nodes + dashed edges appear
   ("the real ring never left the safe").
5. **1:20 forget** — inspect the lipstick napkin (red herring), Rosa debunks it,
   right-click → FORGET → nodes fade out, forgotten counter ticks.
6. **1:40 solve** — SOLVE THE NIGHT → ending screen: verdict, reconstructed timeline
   with citations, HAL's final answer. Backtick shows the raw lifecycle call log.

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
