# LinkedIn post

Attach the YouTube link or `docs/demo.mp4`. Post the thumbnail if uploading the link as an image.

---

I spent this week turning an AI memory system into a video game — and it taught me more about
knowledge graphs than any tutorial could.

Meet **Vegas Amnesia** 🎰🧠

You play HAL-9001, a personal AI assistant whose memory was wiped after your owner's wild night in
Vegas. You have until noon to reconstruct what happened and find a missing ring.

Here's the idea I'm proud of: instead of *explaining* Cognee's memory lifecycle, I made it the
gameplay. Cognee Cloud has four core operations, and each one became a mechanic:

🗂 remember — file a clue, and it becomes a node in a live 3D memory graph
❓ recall — ask HAL a question, and the answer cites the exact memories it came from
🧠 memify — "connect the dots," and the system derives new inferences you never entered
🗑 forget — some evidence is a lie; you have to prune it from the graph to solve the case

The witnesses are LLM-driven and react to what your graph already knows. One of them lies — but if
you've filed the receipt that contradicts him, the graph catches the contradiction. That moment,
watching structured memory catch a lie, is exactly why graph-based memory matters for AI agents.

Built for the WeMakeDevs × Cognee "The Hangover Part AI" hackathon (Cognee Cloud track).

Tech: FastAPI + Cognee Cloud (one dataset per playthrough, every call timed and logged), a vanilla
JS front end with a three.js 3D force graph, Qwen2.5-72B for character dialogue, art generated with
Higgsfield, and the whole thing built with Claude Code.

▶ Play it free: https://vegas-amnesia.vercel.app
⭐ Code + write-up: https://github.com/himanshu748/vegas-amnesia

If you're building AI agents, the takeaway is simple: memory you can *reason over and correct* beats
a bigger context window. Would love your thoughts.

#AI #KnowledgeGraph #Cognee #LLM #GameDev #Hackathon #AIAgents #WeMakeDevs
