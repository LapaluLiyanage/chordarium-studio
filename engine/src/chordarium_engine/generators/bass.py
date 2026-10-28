from __future__ import annotations

from ..models import NoteEvent, PartSpec, Section
from ..styles import Style
from ..theory.voicing import REGISTER_RANGES
from .common import Generated, timeline, vel


def _root_in_range(pc: int, lo: int, hi: int) -> int:
    p = lo + (pc - lo) % 12
    return p


def generate(section: Section, spec: PartSpec, style: Style, seed: int,
             time_signature: tuple[int, int] = (4, 4), dynamics: str = "medium") -> Generated:
    lo, hi = REGISTER_RANGES[spec.register]
    slots, total = timeline(section)
    notes: list[NoteEvent] = []

    def add(p: int, s: int, d: int, acc: float) -> None:
        if 0 <= s < total and d > 0:
            notes.append(NoteEvent(pitch=p, start=s, duration=min(d, total - s), velocity=vel(spec, acc)))

    for slot in slots:
        c = slot.chord
        if c is None:
            continue
        root = _root_in_range(c.bass if c.bass is not None else c.root, lo, hi)
        fifth = root + 7 if root + 7 <= hi else root - 5
        octave = root + 12 if root + 12 <= hi else (root - 12 if root - 12 >= lo else root)
        s, d = slot.start, slot.duration
        gap = 10
        pat = spec.pattern
        if pat == "root":
            add(root, s, d - gap, 1.0)
        elif pat == "root_fifth":
            half = max(120, (d // 2) // 120 * 120) if d >= 480 else d
            add(root, s, half - gap, 1.0)
            if half < d:
                add(fifth, s + half, d - half - gap, 0.75)
        elif pat == "root_octave":
            step = 240 if spec.density >= 0.5 else 480
            t, i = s, 0
            while t < s + d:
                add(root if i % 2 == 0 else octave, t, min(step, s + d - t) - gap, 1.0 if i == 0 else 0.7)
                t += step
                i += 1
        elif pat == "walking_lite":
            nxt = next((x for x in slots[slot.index + 1:slot.index + 2] if x.chord is not None), None)
            if nxt is not None and d >= 480:
                target = _root_in_range(nxt.chord.bass if nxt.chord.bass is not None else nxt.chord.root, lo, hi)
                approach = target - 1 if abs((target - 1) - root) <= abs((target + 1) - root) else target + 1
                approach = min(max(approach, lo), hi)
                add(root, s, d - 240 - gap, 1.0)
                add(approach, s + d - 240, 240 - gap, 0.7)
            else:
                add(root, s, d - gap, 1.0)
        else:
            raise ValueError(f"unknown bass pattern {pat!r}")
    return notes, []
