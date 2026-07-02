"""Win-condition evaluation — pure functions, no I/O, unit-tested in M2.

The player wins when their memory graph covers enough KEY ground-truth facts
and they've pruned (or never trusted) the red herrings. The timeline for the
ending screen is every remembered true fact sorted by time_hint, each line
carrying its fact id so the frontend can cite graph nodes.
"""
from __future__ import annotations

from pydantic import BaseModel

from backend.models.facts import GroundTruth

# Tuned for drama, not punishment: 8/10 key facts, at most 1 live red herring.
KEY_FACT_THRESHOLD = 0.8
MAX_ACTIVE_RED_HERRINGS = 1


class SolveResult(BaseModel):
    won: bool
    key_facts_found: list[str]
    key_facts_missing: list[str]
    active_red_herrings: list[str]
    coverage: float
    timeline: list[dict]
    verdict: str


def evaluate_solve(
    truth: GroundTruth,
    remembered_ids: set[str],
    forgotten_ids: set[str],
) -> SolveResult:
    """remembered_ids/forgotten_ids are ground-truth fact ids the player has
    discovered / explicitly forgotten. A forgotten fact no longer counts for
    either coverage or red-herring contamination.
    """
    active = remembered_ids - forgotten_ids

    key_ids = truth.key_fact_ids
    found = sorted(active & key_ids)
    missing = sorted(key_ids - active)
    herrings = sorted(active & truth.red_herring_ids)
    coverage = len(found) / len(key_ids) if key_ids else 0.0

    won = coverage >= KEY_FACT_THRESHOLD and len(herrings) <= MAX_ACTIVE_RED_HERRINGS

    timeline = build_timeline(truth, active)

    if won:
        verdict = truth.solution_summary
    elif coverage < KEY_FACT_THRESHOLD:
        verdict = (
            f"Your reconstruction has gaps — {len(found)}/{len(key_ids)} key memories "
            "recovered. Keep investigating."
        )
    else:
        verdict = (
            "Your memory graph is contaminated: you're still holding onto "
            f"{len(herrings)} false lead(s). Forget what isn't true."
        )

    return SolveResult(
        won=won,
        key_facts_found=found,
        key_facts_missing=missing,
        active_red_herrings=herrings,
        coverage=round(coverage, 3),
        timeline=timeline,
        verdict=verdict,
    )


def build_timeline(truth: GroundTruth, active_ids: set[str]) -> list[dict]:
    """Remembered TRUE facts in chronological order for the ending screen."""
    entries = []
    for fact in truth.facts:
        if fact.id in active_ids:
            entries.append(
                {
                    "id": fact.id,
                    "time": fact.time_hint or "??:??",
                    "text": fact.text,
                    "source": fact.source.model_dump(),
                }
            )
    # The night runs 20:00 -> 12:00 next day: hours < 20 sort after hours >= 20.
    def night_order(entry: dict) -> tuple:
        time = entry["time"]
        if ":" not in time:
            return (2, 0, 0)
        hours, minutes = (int(p) for p in time.split(":"))
        return (0 if hours >= 20 else 1, hours, minutes)

    return sorted(entries, key=night_order)
