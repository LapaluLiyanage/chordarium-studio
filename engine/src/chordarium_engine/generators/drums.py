from __future__ import annotations

from ..models import NoteEvent, PartSpec, Section
from ..styles import Style
from .common import STEP, Generated, timeline, vel

GM = {"kick": 36, "snare": 38, "rim": 37, "hat": 42, "phat": 44, "ohat": 46, "crash": 49,
      "ride": 51, "ltom": 45, "htom": 50}
THIN = {"hat", "phat", "ohat", "ride"}  # voices thinned out by low density
FILL = ["snare", "snare", "htom", "ltom"]


def generate(section: Section, spec: PartSpec, style: Style, seed: int,
             time_signature: tuple[int, int] = (4, 4), dynamics: str = "medium") -> Generated:
    _, total = timeline(section)
    grids = style.grids.get(spec.pattern)
    if grids is None:
        raise ValueError(f"unknown drum pattern {spec.pattern!r}")
    notes: list[NoteEvent] = []
    hits: dict[int, dict[str, float]] = {}  # tick -> voice -> accent

    bar_start = 0
    nbars = len(section.bars)
    for bi, bar in enumerate(section.bars):
        bar_ticks = sum(round(c.beats * 480) for c in bar.chords)
        steps = bar_ticks // STEP
        grid = grids.get(str(steps)) or grids.get("16") or next(iter(grids.values()))
        for voice, row in grid.items():
            for st in range(steps):
                ch = row[st % len(row)]
                if ch == ".":
                    continue
                level = 0 if st % 4 == 0 else 1 if st % 2 == 0 else 2
                if voice in THIN and spec.density < (0.0, 0.25, 0.6)[level]:
                    continue
                hits.setdefault(bar_start + st * STEP, {})[voice] = 1.0 if ch == "x" else 0.6
        fill_here = (spec.fills == "end_of_section" and bi == nbars - 1) or \
                    (spec.fills == "every_4_bars" and (bi + 1) % 4 == 0)
        if fill_here and steps >= 4:
            for k, voice in enumerate(FILL):
                t = bar_start + (steps - 4 + k) * STEP
                hits[t] = {voice: 1.0}  # replaces the groove on those steps
        bar_start += bar_ticks

    if section.kind == "chorus" and dynamics in ("medium", "loud") and total > 0:
        hits.setdefault(0, {})["crash"] = 1.0

    for t in sorted(hits):
        for voice, acc in hits[t].items():
            base = 1.0 if voice in ("kick", "snare", "crash", "ltom", "htom") else 0.45
            notes.append(NoteEvent(pitch=GM[voice], start=t, duration=min(60, total - t),
                                   velocity=vel(spec, min(1.0, base * acc if voice not in ("kick", "snare") else acc))))
    return notes, []
