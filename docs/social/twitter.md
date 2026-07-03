# X / Twitter thread

Attach `docs/demo.mp4` (or the YouTube link) to tweet 1. Tag @cognee_ and @WeMakeDevs.

---

**1/**
I built a detective game where you play an AI that woke up with its memory wiped 🧠

Every clue you file becomes a node in a live 3D memory graph. Some clues are lies. You have to
*forget* them to win.

The twist: the whole thing runs on @cognee_'s memory lifecycle.

🎮 vegas-amnesia.vercel.app
🧵👇

**2/**
Meet HAL-9001. Your owner had a wild night in Vegas. His fiancée lands at noon. There's a
suspicious ring on his finger and you remember *nothing*.

Reconstruct the night before she arrives.

**3/**
Cognee has 4 memory ops. Most demos only use 2. So I made all four into game mechanics:

🗂 remember → file evidence, watch nodes appear
❓ recall → ask HAL anything, answers cite their sources
🧠 memify → "connect the dots", HAL infers new facts
🗑 forget → delete the lies from memory

**4/**
The witnesses are LLM-driven and react to what your graph already knows.

One of them lies to your face. But you filed the receipt that contradicts him — so the graph
catches it. That "gotcha" moment is the whole pitch: memory you can reason over.

**5/**
Stack:
• @cognee_ Cloud — one dataset per playthrough
• FastAPI backend, every lifecycle call timed + logged
• vanilla JS + three.js 3D force graph
• Qwen2.5-72B for dialogue
• art via @higgsfield_ai
• built with Claude Code

**6/**
Built for the @WeMakeDevs × @cognee_ "The Hangover Part AI" hackathon.

▶ Play free: vegas-amnesia.vercel.app
⭐ Code: github.com/himanshu748/vegas-amnesia

Would love your feedback 🎰🧠
