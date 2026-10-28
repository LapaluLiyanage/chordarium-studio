"""Shared helpers for part generators."""
from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache

from ..models import PPQ, CCEvent, NoteEvent, PartSpec, Section
from ..parser.chords import Chord, ChordParseError, is_no_chord, parse_chord

STEP = 120  # one 16th note
Generated = tuple[list[NoteEvent], list[CCEvent]]


@lru_cache(maxsize=1024)
def _chord(symbol: str) -> Chord | None:
    if is_no_chord(symbol):
        return None
    try:
        return parse_chord(symbol)
    except ChordParseError:
        return None


@dataclass(frozen=True)
class Slot:
    chord: Chord | None
    start: int
    duration: int
    bar: int
    bar_start: int
    bar_ticks: int
    index: int
    last: bool


def timeline(section: Section) -> tuple[list[Slot], int]:
    """Chord slots with absolute ticks, plus the section length in ticks."""
    slots: list[Slot] = []
    t = 0
    for bi, bar in enumerate(section.bars):
        bar_ticks = sum(round(c.beats * PPQ) for c in bar.chords)
        pos = t
        for c in bar.chords:
            d = round(c.beats * PPQ)
            slots.append(Slot(_chord(c.symbol), pos, d, bi, t, bar_ticks, len(slots), False))
            pos += d
        t += bar_ticks
    if slots:
        slots[-1] = Slot(**{**slots[-1].__dict__, "last": True})
    return slots, t


def section_ticks(section: Section) -> int:
    return timeline(section)[1]


def vel(spec: PartSpec, accent: float) -> int:
    lo, hi = spec.velocity
    return max(1, min(127, round(lo + (hi - lo) * accent)))
