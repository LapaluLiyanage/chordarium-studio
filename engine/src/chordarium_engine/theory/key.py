"""Key detection: Krumhansl-Schmuckler correlation over beat-weighted chord tones."""
from __future__ import annotations

from math import sqrt

from ..parser.chords import Chord

_MAJOR = [6.35, 2.23, 3.48, 2.33, 4.38, 4.09, 2.52, 5.19, 2.39, 3.66, 2.29, 2.88]
_MINOR = [6.33, 2.68, 3.52, 5.38, 2.60, 3.53, 2.54, 4.75, 3.98, 2.69, 3.34, 3.17]
_MAJOR_NAMES = ["C", "Db", "D", "Eb", "E", "F", "F#", "G", "Ab", "A", "Bb", "B"]
_MINOR_NAMES = ["C", "C#", "D", "Eb", "E", "F", "F#", "G", "G#", "A", "Bb", "B"]


def _corr(a: list[float], b: list[float]) -> float:
    ma, mb = sum(a) / 12, sum(b) / 12
    num = sum((x - ma) * (y - mb) for x, y in zip(a, b))
    den = sqrt(sum((x - ma) ** 2 for x in a) * sum((y - mb) ** 2 for y in b))
    return num / den if den else 0.0


def detect_key(chords: list[tuple[Chord, float]]) -> tuple[str, str, float]:
    """Return (tonic name, 'major'|'minor', confidence 0..1) for (chord, beats) pairs."""
    hist = [0.0] * 12
    for chord, beats in chords:
        for i, pc in enumerate(chord.pitch_classes):
            hist[pc] += beats * (1.5 if i == 0 else 1.0)
    if not any(hist):
        return "C", "major", 0.0
    scored: list[tuple[float, int, str]] = []
    for tonic in range(12):
        rot = hist[tonic:] + hist[:tonic]
        scored.append((_corr(rot, _MAJOR), tonic, "major"))
        scored.append((_corr(rot, _MINOR), tonic, "minor"))
    scored.sort(reverse=True)
    best, second = scored[0], scored[1]
    conf = max(0.0, min(1.0, best[0] * 0.5 + (best[0] - second[0])))
    name = (_MAJOR_NAMES if best[2] == "major" else _MINOR_NAMES)[best[1]]
    return name, best[2], round(conf, 3)
