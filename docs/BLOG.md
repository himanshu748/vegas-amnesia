---
title: "Vegas Amnesia: I turned Cognee's memory lifecycle into a detective game"
published: true
tags: ai, knowledgegraph, gamedev, hackathon
cover_image: https://raw.githubusercontent.com/himanshu748/vegas-amnesia/main/docs/social/thumbnail.png
canonical_url: https://github.com/himanshu748/vegas-amnesia
---

*Built for the WeMakeDevs × Cognee "The Hangover Part AI" hackathon — Cognee Cloud track.*

**▶ Play it free: [vegas-amnesia.vercel.app](https://vegas-amnesia.vercel.app)  ·  ⭐ [Code on GitHub](https://github.com/himanshu748/vegas-amnesia)**

![Vegas Amnesia gameplay](https://raw.githubusercontent.com/himanshu748/vegas-amnesia/main/docs/media/demo.gif)

---

## The problem with most memory demos

When you give a developer a memory API, the demo almost always looks the same: `add()` some
documents, `search()` over them, print the answer. Two functions. It works, it's fine, and it
teaches you almost nothing about *why* graph-based memory is different from stuffing everything into
a context window.

Cognee actually has a **four-stage lifecycle** — `remember → recall → memify → forget` — and the
interesting parts are the two everyone skips. `memify` consolidates what you know into *new*
inferences. `forget` lets you *delete* a belief and watch the graph heal around it. Memory you can
reason over **and correct**.

So instead of writing another RAG demo, I asked: what if the memory lifecycle wasn't the plumbing —
what if it was the *game*?

## Meet HAL-9001

You play **HAL-9001**, a personal AI assistant (yes, HAL 9000's slightly more helpful successor).
Your owner Dev had a wild night in Vegas. At 6 AM your memory graph was corrupted. His fiancée Priya
lands at noon, there's a suspicious ring on his finger, and you remember **nothing**.

The screen boots to a "MEMORY CORRUPTED" terminal and an empty graph. Your job: reconstruct the
night, catch the lies, and answer the final question — *what happened, and where's the ring?* —
before noon.

Every location you explore, every clue you examine, every witness you interrogate feeds a **live 3D
memory graph** that you can pop open at any time. That graph isn't a visualization *of* the game
state. It **is** the game state — it's your Cognee dataset, rendered.

## The four mechanics = the four lifecycle ops

Here's the mapping I'm most proud of. Each Cognee operation is a verb the player performs:

| You do this in-game | Cognee Cloud call | What happens |
|---|---|---|
| 🗂 **File It** on a clue | `POST /api/v1/remember` | The fact is ingested + auto-cognified into graph nodes that pop into view |
| ❓ **Ask HAL** a question | `POST /api/v1/recall` | You get an answer *with citations* — the source nodes pulse amber in the graph |
| 🧠 **Connect the Dots** | `POST /api/v1/cognify` (inference prompt) | HAL derives new insights; purple inference nodes appear, wired to their premises |
| 🗑 **Forget** a lie | `POST /api/v1/forget` | The memory is deleted for real — nodes fade out and the graph re-settles |

Two design decisions made this click:

**1. Filing is a choice.** Inspecting a clue is free and instant. *Filing* it commits it to Cognee.
That matters because **not every clue is true** — I seeded five red herrings into the story (a
lipstick-stained napkin, a stray pawn ticket, a keycard for the wrong room). File a lie and it
poisons your memory; the only cure is `forget`. Suddenly `forget` isn't a button you press to show
off an API — it's how you *win*.

**2. The witnesses can see your graph.** Rosa the bartender, Lucky Lou the evasive pawnbroker, Rev.
Sonny the chapel officiant, and Chad the hungover best man are all **LLM-driven** (Qwen2.5-72B).
Their system prompt includes *what your memory graph currently contains*. So they react: "You
already know about the pawn shop? Then let me tell you this..."

And Lucky Lou **lies**. He claims Dev never came into his shop. But if you've filed the pawn receipt,
your graph now holds a fact that directly contradicts him — and the game can surface the
contradiction. That single moment, watching structured memory catch a liar, is the entire thesis of
graph-based agent memory in one interaction.

## How it's built

```
 browser — vanilla JS + three.js 3D force graph (zero framework)
   │  file evidence · interrogate · connect-the-dots · forget · Ask HAL
   ▼
 FastAPI (single container: API + static frontend)
   │  session ⇄ its own Cognee dataset · graph-delta snapshots · solve scoring
   │  llm.py — graph-aware character dialogue (Qwen2.5-72B via HF Inference)
   ▼
 Cognee Cloud — remember / recall / memify / forget
   └─ GET /datasets/{id}/graph → animated into the 3D memory panel
```

A few things I did specifically to use Cognee *deeply* rather than superficially:

- **One dataset per playthrough.** Each session mints a fresh `vegas_<id>` dataset, so two players
  (or two demo runs) never see each other's memories. Reset deletes the dataset.
- **Incremental graph deltas.** Every backend response carries a `graph_delta` (added/removed nodes
  and edges) so the front end animates *exactly* what changed instead of re-fetching the world.
- **Citations end to end.** Recall requests set `includeReferences`, and the final ending screen
  reconstructs the whole night as a timeline where every line cites the memory it came from.
- **The receipts.** Press backtick in-game and you get a live log of every Cognee call — operation,
  dataset, latency, status. Partly for debugging, mostly because I wanted the lifecycle usage to be
  *inspectable*, not just claimed.

### The bit that fought me

Cognee's `remember` endpoint is multipart and auto-cognifies, which is lovely — but the response's
`items` list is **cumulative** for the dataset, not just the thing you posted. My first version
happily mapped the wrong `data_id` to each fact, which quietly broke `forget`. The fix was to name
each data item by its fact id and resolve ids by name after ingest. Lesson: read what the API
*returns*, not what you assume it returns.

The other one: my tenant doesn't expose a dedicated `/memify`, so — per the "closest equivalent"
rule — I implemented consolidation as a `cognify` re-run with a custom inference-extraction prompt,
plus a derivation layer that remembers ground-truth inferences once their premises are all in memory.
That's how "connect the dots" reliably produces those purple insight nodes on demand.

## What I'd tell anyone building agent memory

The context-window arms race is the wrong frame for a lot of agent problems. What you often actually
want is memory you can **inspect, reason over, and correct** — add a belief, derive consequences,
and *retract* a belief when it turns out to be a lie, watching everything downstream update. That's
a knowledge graph, and building a game on top of Cognee made that concrete in a way a RAG script
never did.

## Try it

- 🎮 **Play:** [vegas-amnesia.vercel.app](https://vegas-amnesia.vercel.app)
- 🎬 **90-second demo:** [watch on YouTube](https://youtu.be/MM1nnQxJARo)
- ⭐ **Code + full README:** [github.com/himanshu748/vegas-amnesia](https://github.com/himanshu748/vegas-amnesia)

Built with Claude Code. Art generated with Higgsfield. Dialogue by Qwen2.5-72B. Memory — all of it —
by Cognee Cloud.

*🎲 The house always remembers.*
