from __future__ import annotations

import random

from ..models import NoteEvent, PartSpec, Section
from ..styles import Style
from ..theory.voicing import choose_voicing
from .common import Generated, timeline, vel


def generate(section: Section, spec: PartSpec, style: Style, seed: int,
             time_signature: tuple[int, int] = (4, 4), dynamics: str = "medium") -> Generated:
    rng = random.Random(seed)
    slots, total = timeline(section)
    notes: list[NoteEvent] = []
    prev: tuple[int, ...] | None = None
    sub = 240 if spec.density >= 0.5 else 480

    def add(p: int, s: int, d: int, acc: float) -> None:
        if s < total and d > 0:
            notes.append(NoteEvent(pitch=p, start=max(0, s), duration=min(d, total - max(0, s)), velocity=vel(spec, acc)))

    for slot in slots:
        if slot.chord is None:
            prev = None
            continue
        v = choose_voicing(slot.chord, spec.register, prev, rng, spec.variation)
        prev = v
        s, d = slot.start, slot.duration
        pat = spec.pattern
        if pat == "block":
            for p in v:
                add(p, s, d, 1.0)
        elif pat == "broken":
            add(v[0], s, max(STEPMIN, d // 2), 1.0)
            off = min(480, d // 2)
            for p in v[1:]:
                add(p, s + off, d - off, 0.7)
        elif pat in ("arpeggio_up", "arpeggio_updown"):
            seq = list(v) if pat == "arpeggio_up" else list(v) + list(v[-2:0:-1])
            t, i = s, 0
            while t < s + d:
                dur = min(sub, s + d - t)
                add(seq[i % len(seq)], t, dur, 1.0 if i == 0 else 0.65)
                t += sub
                i += 1
        elif pat == "ballad_comp":
            ant = 240 if slot.index > 0 and spec.density >= 0.4 else 0
            hits = [(s - ant, 1.0)]
            if d >= 1440:
                hits.append((s + 960, 0.7))
            for k, (t, acc) in enumerate(hits):
                end = (hits[k + 1][0] if k + 1 < len(hits) else s + d)
                for p in v:
                    add(p, t, end - t, acc)
        else:
            raise ValueError(f"unknown piano pattern {pat!r}")
    return notes, []


STEPMIN = 120
