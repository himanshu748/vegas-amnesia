"""Provider-agnostic LLM for character dialogue.

Backends (env LLM_BACKEND): "hf" (HuggingFace Inference API, OpenAI-compatible
router, default) or "anthropic". If no key is configured or the call fails,
callers fall back to scripted lines — the game never blocks on an LLM.
"""
from __future__ import annotations

import logging
from pathlib import Path

import httpx

from backend import config

log = logging.getLogger("llm")

PROMPTS_DIR = Path(__file__).resolve().parents[1] / "prompts"
DIALOGUE_TEMPLATE = (PROMPTS_DIR / "dialogue.txt").read_text()

HF_ROUTER_URL = "https://router.huggingface.co/v1/chat/completions"
ANTHROPIC_URL = "https://api.anthropic.com/v1/messages"


def available() -> bool:
    if config.LLM_BACKEND == "anthropic":
        return bool(config.ANTHROPIC_API_KEY)
    return bool(config.HF_TOKEN)


async def chat(system: str, messages: list[dict], max_tokens: int = 300) -> str:
    """messages: [{"role": "user"|"assistant", "content": str}, ...]"""
    async with httpx.AsyncClient(timeout=60) as client:
        if config.LLM_BACKEND == "anthropic":
            resp = await client.post(
                ANTHROPIC_URL,
                headers={
                    "x-api-key": config.ANTHROPIC_API_KEY,
                    "anthropic-version": "2023-06-01",
                },
                json={
                    "model": config.ANTHROPIC_MODEL,
                    "max_tokens": max_tokens,
                    "system": system,
                    "messages": messages,
                },
            )
            resp.raise_for_status()
            return resp.json()["content"][0]["text"].strip()

        resp = await client.post(
            HF_ROUTER_URL,
            headers={"Authorization": f"Bearer {config.HF_TOKEN}"},
            json={
                "model": config.HF_MODEL,
                "max_tokens": max_tokens,
                "messages": [{"role": "system", "content": system}, *messages],
            },
        )
        resp.raise_for_status()
        return resp.json()["choices"][0]["message"]["content"].strip()


def build_dialogue_system(
    character,
    known_facts: list[tuple[str, bool]],
    player_facts: list[str],
    reveal_text: str | None,
    lie_mode: bool,
    debunks: list[str],
) -> str:
    """known_facts: [(fact_text, player_already_knows)]"""
    known = "\n".join(
        f"- {text}" + ("  [the player already knows this]" if known else "")
        for text, known in known_facts
    ) or "- (nothing relevant)"
    player = "\n".join(f"- {t}" for t in player_facts) or "- (their graph is empty — they know nothing yet)"

    if lie_mode:
        reveal = (
            "THIS TURN: the player hasn't caught you yet, so stick to your lie — "
            f"deliver it convincingly: \"{reveal_text}\""
        )
    elif reveal_text:
        reveal = (
            "THIS TURN: work this revelation naturally into your reply "
            f"(keep its meaning exact): \"{reveal_text}\""
        )
    else:
        reveal = (
            "THIS TURN: you have nothing new to reveal — riff in character on "
            "what's already known, or nudge them toward another lead."
        )

    debunk = ""
    if debunks:
        debunk = "IF ASKED about these false leads the player is carrying, set them straight:\n" + "\n".join(
            f"- {d}" for d in debunks
        )

    return DIALOGUE_TEMPLATE.format(
        name=character.name,
        name_upper=character.name.upper(),
        role=character.role,
        persona=character.persona,
        known_facts=known,
        player_facts=player,
        reveal_instruction=reveal,
        debunk_instruction=debunk,
    )
