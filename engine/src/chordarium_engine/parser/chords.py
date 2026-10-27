"""Chord symbol grammar (spec 7.1).

Internal quality names follow the existing Chordarium project vocabulary
(`maj min dim aug min6 maj6 min7 minmaj7 maj7 7 dim7 hdim7 sus2 sus4`) and the
Harte-style key format ``ROOT:quality[/bass]`` (e.g. ``F#:min7``).  Studio
extensions (add9, 9, 11, 13, alterations) are added on top without renaming.
"""
from __future__ import annotations

import re
from dataclasses import dataclass

SHARPS = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]
FLATS = ["C", "Db", "D", "Eb", "E", "F", "Gb", "G", "Ab", "A", "Bb", "B"]
_NATURAL_PC = {"C": 0, "D": 2, "E": 4, "F": 5, "G": 7, "A": 9, "B": 11}


def note_to_pc(name: str) -> int:
    """Pitch class of a note name such as ``Bb`` or ``F#`` (accepts ``E#``/``Cb``)."""
    pc = _NATURAL_PC[name[0]]
    for ch in name[1:]:
        pc += 1 if ch == "#" else -1
    return pc % 12


# quality -> semitone intervals above the root (may exceed 12 for extensions)
QUALITY_INTERVALS: dict[str, tuple[int, ...]] = {
    "maj": (0, 4, 7), "min": (0, 3, 7), "dim": (0, 3, 6), "aug": (0, 4, 8),
    "min6": (0, 3, 7, 9), "maj6": (0, 4, 7, 9), "min7": (0, 3, 7, 10),
    "minmaj7": (0, 3, 7, 11), "maj7": (0, 4, 7, 11), "7": (0, 4, 7, 10),
    "dim7": (0, 3, 6, 9), "hdim7": (0, 3, 6, 10), "sus2": (0, 2, 7), "sus4": (0, 5, 7),
    "7sus4": (0, 5, 7, 10),
    "add9": (0, 4, 7, 14), "minadd9": (0, 3, 7, 14), "add11": (0, 4, 7, 17),
    "9": (0, 4, 7, 10, 14), "min9": (0, 3, 7, 10, 14), "maj9": (0, 4, 7, 11, 14),
    "11": (0, 4, 7, 10, 14, 17), "min11": (0, 3, 7, 10, 14, 17),
    "13": (0, 4, 7, 10, 14, 21), "min13": (0, 3, 7, 10, 14, 21),
    "7b9": (0, 4, 7, 10, 13), "7#9": (0, 4, 7, 10, 15), "7#11": (0, 4, 7, 10, 18),
    "7b13": (0, 4, 7, 10, 20), "7b5": (0, 4, 6, 10), "7#5": (0, 4, 8, 10),
}

# canonical symbol suffix per quality
QUALITY_SYMBOL: dict[str, str] = {
    "maj": "", "min": "m", "dim": "dim", "aug": "aug", "min6": "m6", "maj6": "6",
    "min7": "m7", "minmaj7": "mMaj7", "maj7": "maj7", "7": "7", "dim7": "dim7",
    "hdim7": "m7b5", "sus2": "sus2", "sus4": "sus4", "7sus4": "7sus4",
    "add9": "add9", "minadd9": "madd9", "add11": "add11", "9": "9", "min9": "m9",
    "maj9": "maj9", "11": "11", "min11": "m11", "13": "13", "min13": "m13",
    "7b9": "7b9", "7#9": "7#9", "7#11": "7#11", "7b13": "7b13", "7b5": "7b5", "7#5": "7#5",
}

# accepted input suffix -> quality
_ALIASES: dict[str, tuple[str, ...]] = {
    "maj": ("", "maj", "M", "major"),
    "min": ("m", "min", "-", "mi", "minor"),
    "dim": ("dim", "°", "o"),
    "aug": ("aug", "+"),
    "min6": ("m6", "min6", "-6"),
    "maj6": ("6", "maj6", "M6"),
    "min7": ("m7", "min7", "-7", "mi7"),
    "minmaj7": ("mMaj7", "mM7", "minmaj7", "m(maj7)", "mmaj7", "-maj7", "mMA7"),
    "maj7": ("maj7", "M7", "Maj7", "MAJ7", "Δ", "Δ7", "ma7"),
    "7": ("7", "dom7"),
    "dim7": ("dim7", "°7", "o7"),
    "hdim7": ("m7b5", "ø", "ø7", "min7b5", "-7b5", "m7-5"),
    "sus2": ("sus2",),
    "sus4": ("sus4",),
    "7sus4": ("7sus4", "7sus"),
    "add9": ("add9", "(add9)", "add2"),
    "minadd9": ("madd9", "m(add9)", "minadd9"),
    "add11": ("add11", "(add11)"),
    "9": ("9",),
    "min9": ("m9", "min9", "-9"),
    "maj9": ("maj9", "M9", "Maj9"),
    "11": ("11",),
    "min11": ("m11", "min11", "-11"),
    "13": ("13",),
    "min13": ("m13", "min13"),
    "7b9": ("7b9", "7-9"),
    "7#9": ("7#9", "7+9"),
    "7#11": ("7#11", "7+11"),
    "7b13": ("7b13", "7-13"),
    "7b5": ("7b5", "7-5"),
    "7#5": ("7#5", "7+5", "aug7", "+7"),
}
_SUFFIX_TO_QUALITY: dict[str, str] = {s: q for q, ss in _ALIASES.items() for s in ss}
_SUFFIX_TO_QUALITY["sus"] = "sus4"  # bare "sus" is read as sus4 (with a warning)

_SYMBOL_RE = re.compile(r"^(?P<root>[A-G][#b]?)(?P<suffix>[^/]*)(?:/(?P<bass>[A-G][#b]?))?$")
_NO_CHORD = {"N.C.", "N.C", "NC", "N/C", "N"}


class ChordParseError(ValueError):
    pass


@dataclass(frozen=True)
class Chord:
    root_name: str
    quality: str
    bass_name: str | None = None

    @property
    def root(self) -> int:
        return note_to_pc(self.root_name)

    @property
    def bass(self) -> int | None:
        return None if self.bass_name is None else note_to_pc(self.bass_name)

    @property
    def intervals(self) -> tuple[int, ...]:
        return QUALITY_INTERVALS[self.quality]

    @property
    def pitch_classes(self) -> tuple[int, ...]:
        return tuple((self.root + i) % 12 for i in self.intervals)

    @property
    def symbol(self) -> str:
        s = self.root_name + QUALITY_SYMBOL[self.quality]
        return s + ("/" + self.bass_name if self.bass_name else "")

    @property
    def harte(self) -> str:
        r = SHARPS[self.root]
        s = f"{r}:{self.quality}"
        if self.bass is not None and self.bass != self.root:
            s += f"/{SHARPS[self.bass]}"
        return s


def is_no_chord(symbol: str) -> bool:
    return symbol.strip() in _NO_CHORD


def parse_chord(symbol: str, warnings: list[str] | None = None) -> Chord:
    """Parse a chord symbol. Raises ChordParseError; ``N.C.`` is not a Chord."""
    sym = symbol.strip()
    if is_no_chord(sym) or sym == "%":
        raise ChordParseError(f"{symbol!r} is not a chord (no-chord / repeat marker)")
    m = _SYMBOL_RE.match(sym)
    if not m:
        raise ChordParseError(f"Cannot parse chord symbol {symbol!r}")
    suffix = m.group("suffix")
    quality = _SUFFIX_TO_QUALITY.get(suffix)
    if quality is None:
        raise ChordParseError(f"Unknown chord quality {suffix!r} in {symbol!r}")
    if suffix == "sus" and warnings is not None:
        warnings.append(f"'{sym}' read as {m.group('root')}sus4")
    bass = m.group("bass")
    if bass is not None and note_to_pc(bass) == note_to_pc(m.group("root")):
        bass = None
    return Chord(m.group("root"), quality, bass)


_HARTE_RE = re.compile(r"^(?P<root>[A-G][#b]?)(?::(?P<q>[^/]+))?(?:/(?P<bass>.+))?$")
_DEGREE = {"1": 0, "b2": 1, "2": 2, "b3": 3, "3": 4, "4": 5, "b5": 6, "5": 7,
           "#5": 8, "b6": 8, "6": 9, "bb7": 9, "b7": 10, "7": 11}


def from_harte(label: str) -> Chord | None:
    """Parse ``ROOT:quality[/bass]`` (bass may be a degree like ``b3``). ``N``/``X`` -> None."""
    label = label.strip()
    if label in ("", "N", "X"):
        return None
    m = _HARTE_RE.match(label)
    if not m:
        raise ChordParseError(f"Bad Harte label {label!r}")
    quality = m.group("q") or "maj"
    if quality not in QUALITY_INTERVALS:
        raise ChordParseError(f"Unknown quality {quality!r}")
    root = m.group("root")
    bass = m.group("bass")
    bass_name = None
    if bass:
        pc = (note_to_pc(root) + _DEGREE[bass]) % 12 if bass in _DEGREE else note_to_pc(bass)
        if pc != note_to_pc(root):
            bass_name = SHARPS[pc]
    return Chord(root, quality, bass_name)
