"""World model + loader (story/world.json) — locations, hotspots, characters."""
from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Optional

from pydantic import BaseModel, Field

WORLD_PATH = Path(__file__).resolve().parents[2] / "story" / "world.json"


class Hotspot(BaseModel):
    id: str
    name: str
    description: str
    facts: list[str] = Field(default_factory=list)


class Location(BaseModel):
    id: str
    name: str
    description: str
    character: Optional[str] = None
    hotspots: list[Hotspot]


class UnlockCondition(BaseModel):
    requires_facts: list[str]
    grants: str


class Character(BaseModel):
    id: str
    name: str
    role: str
    location: str
    persona: str
    knows_facts: list[str] = Field(default_factory=list)
    confesses_facts: list[str] = Field(default_factory=list)
    debunks: list[str] = Field(default_factory=list)
    debunk_hints: dict[str, str] = Field(default_factory=dict)
    unlock_condition: Optional[UnlockCondition] = None


class World(BaseModel):
    start_location: str
    locations: list[Location]
    characters: list[Character]

    def location(self, location_id: str) -> Optional[Location]:
        return next((l for l in self.locations if l.id == location_id), None)

    def character(self, character_id: str) -> Optional[Character]:
        return next((c for c in self.characters if c.id == character_id), None)

    def hotspot(self, location_id: str, hotspot_id: str) -> Optional[Hotspot]:
        loc = self.location(location_id)
        if loc is None:
            return None
        return next((h for h in loc.hotspots if h.id == hotspot_id), None)


@lru_cache(maxsize=1)
def load_world() -> World:
    return World(**json.loads(WORLD_PATH.read_text()))
