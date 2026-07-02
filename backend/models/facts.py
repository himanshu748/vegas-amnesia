"""Fact model + ground-truth story loader (story/ground_truth.json)."""
from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Literal, Optional

from pydantic import BaseModel, Field

STORY_PATH = Path(__file__).resolve().parents[2] / "story" / "ground_truth.json"


class FactSource(BaseModel):
    type: Literal["evidence", "testimony", "inference"]
    ref: str


class Fact(BaseModel):
    id: str
    text: str
    source: FactSource
    entities: list[str] = Field(default_factory=list)
    time_hint: Optional[str] = None
    is_red_herring: bool = False
    key: bool = False
    status: Literal["remembered", "forgotten"] = "remembered"
    debunked_by: Optional[str] = None
    truth: Optional[str] = None


class DerivableFact(BaseModel):
    id: str
    text: str
    derived_from: list[str]


class GroundTruth(BaseModel):
    facts: list[Fact]
    red_herrings: list[Fact]
    derivable: list[DerivableFact]
    final_question: str
    solution_summary: str

    def fact_by_id(self, fact_id: str) -> Optional[Fact]:
        for fact in self.facts + self.red_herrings:
            if fact.id == fact_id:
                return fact
        return None

    @property
    def key_fact_ids(self) -> set[str]:
        return {f.id for f in self.facts if f.key}

    @property
    def red_herring_ids(self) -> set[str]:
        return {f.id for f in self.red_herrings}


@lru_cache(maxsize=1)
def load_ground_truth() -> GroundTruth:
    raw = json.loads(STORY_PATH.read_text())
    return GroundTruth(
        facts=[Fact(**f) for f in raw["facts"]],
        red_herrings=[Fact(**f) for f in raw["red_herrings"]],
        derivable=[DerivableFact(**d) for d in raw["derivable"]],
        final_question=raw["case"]["final_question"],
        solution_summary=raw["solution_summary"],
    )
