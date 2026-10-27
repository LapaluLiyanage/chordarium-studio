"""Pydantic data models (spec section 6). Timing unit: ticks, PPQ = 480."""
from __future__ import annotations

import warnings
from typing import Literal

from pydantic import BaseModel, Field, field_validator, model_validator

# The spec names a PartSpec field "register"; pydantic warns it shadows a BaseModel attribute.
warnings.filterwarnings("ignore", message='Field name "register"')

PPQ = 480

SectionKind = Literal[
    "intro", "verse", "pre_chorus", "chorus", "bridge", "interlude", "solo", "outro", "other"
]
Role = Literal["piano", "bass", "pad", "drums"]
Register = Literal["low", "mid_low", "mid", "mid_high", "high"]
Fills = Literal["none", "end_of_section", "every_4_bars"]
Mode = Literal["major", "minor"]

# MIDI channel map used by print-to-tracks (1-based).
ROLE_CHANNEL: dict[str, int] = {"piano": 1, "bass": 2, "pad": 3, "drums": 10}


class ChordSlot(BaseModel):
    symbol: str
    beats: float = Field(gt=0)


class Bar(BaseModel):
    chords: list[ChordSlot] = Field(min_length=1)


class Section(BaseModel):
    id: str
    name: str
    kind: SectionKind = "other"
    bars: list[Bar] = Field(default_factory=list)
    lyrics: list[str | None] | None = None


class Song(BaseModel):
    id: str = "song_01"
    title: str = "Untitled"
    key: str | None = None
    mode: Mode = "major"
    tempo_bpm: float = Field(default=90, gt=0)
    time_signature: tuple[int, int] = (4, 4)
    capo: int = Field(default=0, ge=0, le=12)
    language: Literal["en", "si"] = "en"
    sections: list[Section] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)

    def section(self, section_id: str) -> Section:
        for s in self.sections:
            if s.id == section_id:
                return s
        raise KeyError(section_id)


class PartSpec(BaseModel):
    role: Role
    pattern: str
    density: float = Field(default=0.5, ge=0, le=1)
    velocity: tuple[int, int] = (50, 80)
    register: Register = "mid"
    instrument: str | None = None
    fills: Fills = "none"
    seed: int | None = None
    locked: bool = False
    variation: float = Field(default=0.0, ge=0, le=1)

    @field_validator("velocity")
    @classmethod
    def _velocity_range(cls, v: tuple[int, int]) -> tuple[int, int]:
        lo, hi = v
        if not (1 <= lo <= 127 and 1 <= hi <= 127):
            raise ValueError("velocity values must be within 1..127")
        if lo > hi:
            raise ValueError("velocity min must be <= max")
        return v


class ArrangementPlan(BaseModel):
    section_id: str
    style: str
    feel: str = "straight"
    dynamics: Literal["soft", "medium", "loud"] = "medium"
    parts: list[PartSpec] = Field(min_length=1)
    notes: str = ""

    @model_validator(mode="after")
    def _unique_roles(self) -> "ArrangementPlan":
        roles = [p.role for p in self.parts]
        if len(roles) != len(set(roles)):
            raise ValueError("each role may appear only once per plan")
        return self


class NoteEvent(BaseModel):
    pitch: int = Field(ge=0, le=127)
    start: int = Field(ge=0)
    duration: int = Field(gt=0)
    velocity: int = Field(ge=1, le=127)


class CCEvent(BaseModel):
    cc: int = Field(ge=0, le=127)
    start: int = Field(ge=0)
    value: int = Field(ge=0, le=127)


class Part(BaseModel):
    id: str
    section_id: str
    role: Role
    channel: int
    spec: PartSpec
    seed: int
    locked: bool = False
    notes: list[NoteEvent] = Field(default_factory=list)
    ccs: list[CCEvent] = Field(default_factory=list)
