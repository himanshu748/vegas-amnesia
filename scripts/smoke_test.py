"""M1 gate: verify all four lifecycle operations against Cognee Cloud.

Usage:
    cp .env.example .env   # fill in COGNEE_API_KEY
    python -m venv .venv && .venv/bin/pip install -r backend/requirements.txt
    .venv/bin/python scripts/smoke_test.py

Exercises, in order: remember -> recall -> memify -> get_graph -> forget ->
dataset cleanup. Prints a pass/fail line per step and exits non-zero on any
failure. Uses a throwaway timestamped dataset so it never touches game data.
"""
import asyncio
import os
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

try:
    from dotenv import load_dotenv

    load_dotenv(Path(__file__).resolve().parents[1] / ".env")
except ImportError:
    pass

from backend.services import cognee_client  # noqa: E402

FACTS = [
    "Dev started the night at the Neon Mirage casino bar at 9 PM.",
    "Bartender Rosa served Dev and a bachelor party group at the casino bar.",
    "Dev won 8000 dollars playing blackjack at 11 PM.",
]

RED_HERRING = "A lipstick-marked napkin was found in Dev's hotel suite."


def step(name: str, ok: bool, detail: str = "") -> bool:
    print(f"  {'PASS' if ok else 'FAIL'}  {name}" + (f" — {detail}" if detail else ""))
    return ok


async def main() -> int:
    if not os.environ.get("COGNEE_API_KEY"):
        print("FAIL  COGNEE_API_KEY is not set (see .env.example)")
        return 1

    dataset = f"smoke_{int(time.time())}"
    print(f"Cognee Cloud smoke test — dataset '{dataset}' at "
          f"{os.environ.get('COGNEE_BASE_URL', 'https://api.cognee.ai')}\n")
    failures = 0

    # 1. remember — the red herring goes in too so forget has a real target.
    result = await cognee_client.remember(FACTS + [RED_HERRING], dataset)
    ok = len(result["remembered"]) == 4 and not result["failed"]
    failures += not step("remember (4 facts)", ok, f"{len(result['remembered'])}/4 ingested")

    # remember auto-cognifies; give the pipeline a moment before querying.
    await asyncio.sleep(10)

    # 2. recall
    try:
        answer = await cognee_client.recall("How much did Dev win at blackjack?", dataset)
        failures += not step("recall", bool(answer), str(answer)[:120])
    except Exception as exc:
        failures += not step("recall", False, str(exc)[:200])

    # 3. memify
    try:
        result = await cognee_client.memify(dataset)
        failures += not step("memify", True, str(result)[:120])
    except Exception as exc:
        failures += not step("memify", False, str(exc)[:200])

    # 4. graph snapshot
    try:
        graph = await cognee_client.get_graph(dataset)
        n, e = len(graph["nodes"]), len(graph["edges"])
        failures += not step("get_graph", n > 0, f"{n} nodes, {e} edges")
    except Exception as exc:
        failures += not step("get_graph", False, str(exc)[:200])

    # 5. forget the red herring
    try:
        await cognee_client.forget(dataset, fact_text=RED_HERRING)
        failures += not step("forget (red herring)", True)
    except Exception as exc:
        failures += not step("forget (red herring)", False, str(exc)[:200])

    # 6. cleanup
    try:
        deleted = await cognee_client.delete_dataset(dataset)
        failures += not step("delete_dataset (cleanup)", deleted)
    except Exception as exc:
        failures += not step("delete_dataset (cleanup)", False, str(exc)[:200])

    print(f"\n{'ALL LIFECYCLE CALLS VERIFIED' if not failures else f'{failures} step(s) failed'}")
    print("\nCall log:")
    for call in cognee_client.CALL_LOG:
        print(f"  {call['op']:<16} {call['ms']:>8.0f}ms  ok={call['ok']}  {call['detail']}")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
