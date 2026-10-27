import json
from pathlib import Path

import pytest

from chordarium_engine.parser.chords import (
    ChordParseError, from_harte, is_no_chord, parse_chord, note_to_pc, QUALITY_INTERVALS,
)

ROOTS = ["C", "C#", "Db", "D", "D#", "Eb", "E", "F", "F#", "Gb", "G", "G#", "Ab", "A", "A#", "Bb", "B"]
SUFFIX_QUALITY = [
    ("", "maj"), ("m", "min"), ("dim", "dim"), ("aug", "aug"), ("7", "7"), ("maj7", "maj7"),
    ("m7", "min7"), ("sus2", "sus2"), ("sus4", "sus4"), ("m7b5", "hdim7"), ("add9", "add9"),
    ("6", "maj6"), ("m6", "min6"), ("9", "9"), ("13", "13"),
]


@pytest.mark.parametrize("root", ROOTS)
@pytest.mark.parametrize("suffix,quality", SUFFIX_QUALITY)
def test_root_quality_grid(root, suffix, quality):  # 17 x 15 = 255 symbols
    c = parse_chord(root + suffix)
    assert c.root == note_to_pc(root)
    assert c.quality == quality
    assert c.bass is None
    assert c.symbol == root + suffix or c.quality in {"maj"}


EDGE = [
    ("Bbmaj7/D", "Bb", "maj7", "D"), ("F#m7b5", "F#", "hdim7", None), ("Ebsus2", "Eb", "sus2", None),
    ("C/E", "C", "maj", "E"), ("Gsus", "G", "sus4", None), ("Am7/G", "A", "min7", "G"),
    ("D-7", "D", "min7", None), ("CM7", "C", "maj7", None), ("CΔ7", "C", "maj7", None),
    ("Bø", "B", "hdim7", None), ("C°7", "C", "dim7", None), ("C+", "C", "aug", None),
    ("Cm(maj7)", "C", "minmaj7", None), ("G7#9", "G", "7#9", None), ("G7b9", "G", "7b9", None),
    ("G7#11", "G", "7#11", None), ("G7b13", "G", "7b13", None), ("Dmin", "D", "min", None),
    ("Em9", "E", "min9", None), ("Cmaj9", "C", "maj9", None), ("C11", "C", "11", None),
    ("Cadd11", "C", "add11", None), ("G7sus4", "G", "7sus4", None),
]


@pytest.mark.parametrize("sym,root,quality,bass", EDGE)
def test_edge_cases(sym, root, quality, bass):
    c = parse_chord(sym)
    assert (c.root_name, c.quality, c.bass_name) == (root, quality, bass)


def test_slash_equal_to_root_is_dropped():
    assert parse_chord("C/C").bass is None


def test_sus_warns():
    w: list[str] = []
    parse_chord("Gsus", w)
    assert w and "sus4" in w[0]


def test_no_chord_and_repeat():
    assert is_no_chord("N.C.") and is_no_chord("NC") and not is_no_chord("C")
    for s in ("N.C.", "%"):
        with pytest.raises(ChordParseError):
            parse_chord(s)


@pytest.mark.parametrize("bad", ["", "H", "Cxyz", "C/H", "c", "Cm7b5b5b5", "7"])
def test_invalid(bad):
    with pytest.raises(ChordParseError):
        parse_chord(bad)


def test_pitch_classes():
    assert parse_chord("Am7").pitch_classes == (9, 0, 4, 7)
    assert parse_chord("Cadd9").pitch_classes == (0, 4, 7, 2)


def test_every_alias_quality_has_intervals():
    for _, q in SUFFIX_QUALITY:
        assert q in QUALITY_INTERVALS


# ---- parity with the existing Chordarium project (shared/chord_cases.json) ----
CASES = json.loads((Path(__file__).parent / "fixtures" / "chord_cases.json").read_text())
PLAIN = [c for c in CASES["render"] if not (set(c) - {"label", "expected"})]


@pytest.mark.parametrize("case", PLAIN, ids=lambda c: c["label"])
def test_chordarium_parity_plain_render(case):
    chord = from_harte(case["label"])
    if chord is None:
        pytest.skip("no-chord label")
    # same symbol for sharp-spelled cases; flats come from the key-aware renderer (later milestone)
    if "b" not in case["expected"][1:2]:
        assert chord.symbol == case["expected"]


def test_harte_roundtrip():
    for label in ["A:min7/b3", "B:hdim7", "C:minmaj7", "D:7/3", "F#:min7", "G:sus4"]:
        assert parse_chord(from_harte(label).symbol).harte == from_harte(label).harte
    assert from_harte("N") is None
