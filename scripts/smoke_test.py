"""M1 gate: verify all four lifecycle operations against Cognee Cloud.

Usage:
    cp .env.example .env   # fill in COGNEE_API_KEY (+ COGNEE_BASE_URL if tenant)
    python -m venv .venv && .venv/bin/pip install -r backend/requirements.txt
    .venv/bin/python scripts/smoke_test.py

Exercises, in order: remember -> recall -> memify (graph diffed before/after)
-> forget (by data_id, graph diffed again) -> dataset cleanup. Prints a
pass/fail line per step and exits non-zero on any failure. Uses a throwaway
timestamped dataset so it never touches game data.
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
    {"id": "f01", "text": "Dev started the night at the Neon Mirage casino bar at 9 PM."},
    {"id": "f03", "text": "Bartender Rosa served Dev and a bachelor party group at the casino bar."},
    {"id": "f04", "text": "Dev won 8000 dollars playing blackjack at 11 PM."},
    {"id": "rh1", "text": "A lipstick-marked napkin was found in Dev's hotel suite."},
]


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

    # 1. remember — the red herring (rh1) goes in too so forget has a target.
    result = await cognee_client.remember(FACTS, dataset)
    ok = len(result["remembered"]) == 4 and not result["failed"]
    data_ids = {r["fact_id"]: r["data_id"] for r in result["remembered"]}
    failures += not step(
        "remember (4 facts)", ok and all(data_ids.values()),
        f"{len(result['remembered'])}/4 ingested, data_ids returned"
    )

    # 2. recall
    try:
        answer = await cognee_client.recall("How much did Dev win at blackjack?", dataset)
        text = str(answer)
        failures += not step("recall", "8,000" in text or "8000" in text, text[:120])
    except Exception as exc:
        failures += not step("recall", False, str(exc)[:200])

    # 3. memify (= cognify + inference prompt on this tenant) — diff the graph.
    try:
        before = await cognee_client.get_graph(dataset)
        await cognee_client.memify(dataset)
        after = await cognee_client.get_graph(dataset)
        detail = (
            f"nodes {len(before['nodes'])} -> {len(after['nodes'])}, "
            f"edges {len(before['edges'])} -> {len(after['edges'])}"
        )
        failures += not step("memify + graph diff", len(after["nodes"]) > 0, detail)
    except Exception as exc:
        failures += not step("memify + graph diff", False, str(exc)[:200])

    # 4. forget the red herring by the data_id remember returned.
    try:
        await cognee_client.forget(dataset, data_id=data_ids.get("rh1"))
        remaining = {i["name"] for i in await cognee_client.list_data_items(dataset)}
        failures += not step(
            "forget (red herring)", "rh1" not in remaining, f"remaining items: {sorted(remaining)}"
        )
    except Exception as exc:
        failures += not step("forget (red herring)", False, str(exc)[:200])

    # 5. cleanup
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
