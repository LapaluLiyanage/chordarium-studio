from __future__ import annotations

import random

from ..models import CCEvent, NoteEvent, PartSpec, Section
from ..styles import Style
from ..theory.voicing import choose_voicing
from .common import Generated, timeline, vel


def generate(section: Section, spec: PartSpec, style: Style, seed: int,
             time_signature: tuple[int, int] = (4, 4), dynamics: str = "medium") -> Generated:
    rng = random.Random(seed)
    slots, total = timeline(section)
    notes: list[NoteEvent] = []
    ccs: list[CCEvent] = []
    prev = None
    for slot in slots:
        if slot.chord is None:
            prev = None
            continue
        v = choose_voicing(slot.chord, spec.register, prev, rng, spec.variation)
        prev = v
        d = slot.duration + (0 if slot.last else 20)  # legato overlap
        d = min(d, total - slot.start)
        lo, hi = spec.velocity
        if spec.pattern == "sustain":
            for p in v:
                notes.append(NoteEvent(pitch=p, start=slot.start, duration=d, velocity=vel(spec, 0.7)))
        elif spec.pattern == "swell":
            for p in v:
                notes.append(NoteEvent(pitch=p, start=slot.start, duration=d, velocity=lo))
            n = 8
            for k in range(n + 1):
                value = round(40 + (hi + 20 - 40) * k / n)
                ccs.append(CCEvent(cc=11, start=slot.start + slot.duration * k // n - (1 if k == n else 0),
                                   value=max(0, min(127, value))))
        else:
            raise ValueError(f"unknown pad pattern {spec.pattern!r}")
    return notes, ccs
