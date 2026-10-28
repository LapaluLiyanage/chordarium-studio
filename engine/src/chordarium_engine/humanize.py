"""Seeded humanization: timing and velocity jitter (spec 7.4)."""
from __future__ import annotations

import random

from .models import NoteEvent

GRID_DRUMS = {36, 37, 38}  # kick, rim, snare


def humanize(notes: list[NoteEvent], rng: random.Random, velocity: tuple[int, int], total_ticks: int,
             *, is_drums: bool = False, density: float = 0.5, timing: int = 8, vel_jitter: int = 6) -> list[NoteEvent]:
    out: list[NoteEvent] = []
    lo, hi = velocity
    for n in notes:
        start = n.start
        if not (is_drums and density < 0.3 and n.pitch in GRID_DRUMS):
            start += rng.randint(-timing, timing)
        start = max(0, start)
        if start >= total_ticks:
            continue
        end = min(total_ticks, max(start + 1, n.start + n.duration))
        vel = max(lo, min(hi, n.velocity + rng.randint(-vel_jitter, vel_jitter)))
        out.append(NoteEvent(pitch=n.pitch, start=start, duration=end - start, velocity=vel))
    return out
