"""Voicing generation and voice leading (spec 7.3)."""
from __future__ import annotations

import itertools
import random

from ..parser.chords import Chord

REGISTER_RANGES: dict[str, tuple[int, int]] = {
    "low": (28, 52), "mid_low": (40, 60), "mid": (48, 72), "mid_high": (55, 79), "high": (64, 88),
}
REGISTER_ORDER = ["low", "mid_low", "mid", "mid_high", "high"]


def chord_tone_pcs(chord: Chord) -> list[int]:
    """Up to four pitch classes, root first. Drops the 5th, then the top extension."""
    iv = list(chord.intervals)
    while len(iv) > 4:
        fifths = [i for i in iv if i % 12 == 7]
        iv.remove(fifths[0]) if fifths else iv.pop()
    return [(chord.root + i) % 12 for i in iv]


def voicings(chord: Chord, register: str, max_span: int = 17) -> list[tuple[int, ...]]:
    """All sorted voicings (closed and open, every inversion) inside the register."""
    lo, hi = REGISTER_RANGES[register]
    options = [[p for p in range(lo, hi + 1) if p % 12 == pc] for pc in chord_tone_pcs(chord)]
    found: set[tuple[int, ...]] = set()
    for combo in itertools.product(*options):
        if len(set(combo)) < len(combo):
            continue
        v = tuple(sorted(combo))
        if v[-1] - v[0] <= max_span:
            found.add(v)
    return sorted(found)


def voicing_cost(v: tuple[int, ...], prev: tuple[int, ...] | None, register: str) -> float:
    lo, hi = REGISTER_RANGES[register]
    if prev is None:
        return abs(sum(v) / len(v) - (lo + hi) / 2)
    cost = float(sum(abs(a - b) for a, b in zip(v, prev)) + 3 * abs(len(v) - len(prev)))
    top_move = v[-1] - prev[-1]
    if abs(top_move) > 4:
        cost += 2 * (abs(top_move) - 4)
    bass_move = v[0] - prev[0]
    prev_int, new_int = (prev[-1] - prev[0]) % 12, (v[-1] - v[0]) % 12
    if bass_move and top_move and (bass_move > 0) == (top_move > 0) and prev_int == new_int and prev_int in (0, 7):
        cost += 20  # parallel fifths / octaves between outer voices
    cost += 5 * sum(1 for n in v if n < lo)
    return cost


def choose_voicing(chord: Chord, register: str, prev: tuple[int, ...] | None,
                   rng: random.Random | None = None, variation: float = 0.0) -> tuple[int, ...]:
    cands = voicings(chord, register)
    scored = sorted((voicing_cost(v, prev, register), v) for v in cands)
    best = scored[0]
    if rng is not None and variation > 0 and rng.random() < variation:
        near = [v for c, v in scored if c <= best[0] + 2]
        return rng.choice(near)
    return best[1]


def shift_register(register: str, step: int) -> str:
    i = max(0, min(len(REGISTER_ORDER) - 1, REGISTER_ORDER.index(register) + step))
    return REGISTER_ORDER[i]
