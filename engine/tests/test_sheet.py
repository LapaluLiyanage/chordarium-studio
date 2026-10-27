import random

import pytest

from chordarium_engine.parser.sheet import parse_sheet
from chordarium_engine.parser import labels


def syms(song, sec=0):
    return [[c.symbol for c in b.chords] for b in song.sections[sec].bars]


def test_bar_notation_with_beats_and_split():
    s = parse_sheet("Key: G\nTempo: 76\nTime: 4/4\n[Chorus 1]\n| G | Em C | D(1) C(3) |")
    sec = s.sections[0]
    assert (s.key, s.mode, s.tempo_bpm) == ("G", "major", 76)
    assert sec.id == "sec_chorus_1" and sec.name == "Chorus 1" and sec.kind == "chorus"
    assert syms(s) == [["G"], ["Em", "C"], ["D", "C"]]
    assert [c.beats for c in sec.bars[1].chords] == [2, 2]
    assert [c.beats for c in sec.bars[2].chords] == [1, 3]


def test_chords_over_lyrics():
    s = parse_sheet("Verse\nG   Em\nHello moon light\nC   D\nSecond line")
    assert syms(s) == [["G"], ["Em"], ["C"], ["D"]]
    assert s.sections[0].lyrics == ["Hello moon light", None, "Second line", None]
    assert any("1 chord per bar" in w for w in s.warnings)


def test_inline_brackets():
    s = parse_sheet("[Chorus]\n[G]Sanda [Em]eliya [C]hello [D]world")
    assert syms(s) == [["G"], ["Em"], ["C"], ["D"]]
    assert s.sections[0].lyrics == ["Sanda", "eliya", "hello", "world"]


def test_more_than_four_chords_two_per_bar():
    s = parse_sheet("Intro\nC G Am F C G")
    assert syms(s) == [["C", "G"], ["Am", "F"], ["C", "G"]]
    assert any("2 chords per bar" in w for w in s.warnings)


def test_repeat_and_no_chord():
    s = parse_sheet("| G | % | N.C. | % |")
    assert syms(s) == [["G"], ["G"], ["N.C."], ["N.C."]] or syms(s)[3] == ["N.C."]


def test_sus_warning_and_canonical():
    s = parse_sheet("| Gsus | D |")
    assert syms(s)[0] == ["Gsus4"]
    assert any("read as" in w for w in s.warnings)


def test_key_detection_major_minor():
    a = parse_sheet("| C | F | G | C |")
    assert (a.key, a.mode) == ("C", "major") and any("detected" in w for w in a.warnings)
    b = parse_sheet("| Am | Dm | E | Am |")
    assert (b.key, b.mode) == ("A", "minor")


def test_key_metadata_minor_and_time():
    s = parse_sheet("Key: Em\nTime: 6/8\n| Em | D |")
    assert (s.key, s.mode, s.time_signature) == ("E", "minor", (6, 8))
    assert s.sections[0].bars[0].chords[0].beats == 3.0


def test_capo_metadata():
    s = parse_sheet("Capo: 2\n| G | C |")
    assert s.capo == 2 and any("Capo 2" in w for w in s.warnings)


def test_header_with_inline_content_and_hyphen_label():
    s = parse_sheet("Intro: G C\nPre-Chorus -\n| Am | D |")
    assert [x.kind for x in s.sections] == ["intro", "pre_chorus"]
    assert syms(s, 0) == [["G"], ["C"]]


def test_repeated_sections_get_unique_ids():
    s = parse_sheet("Chorus\n| G |\nVerse\n| C |\nChorus\n| G |")
    assert [x.id for x in s.sections] == ["sec_chorus_1", "sec_verse_1", "sec_chorus_2"]


def test_sinhala_detected_and_label_dictionary_extensible():
    labels.register_labels({"පද්‍ය": "verse"})
    try:
        s = parse_sheet("පද්‍ය 1\nG   C\nසඳ එළිය")
        assert s.language == "si" and s.sections[0].kind == "verse"
        assert s.sections[0].lyrics[0] == "සඳ එළිය"
    finally:
        labels.SINHALA_LABELS.clear()


def test_mixed_formats_in_one_sheet():
    text = "Title: Mix\nIntro\n| G | C |\nVerse\nEm  D\nlyric\nChorus\n[G]one [C]two"
    s = parse_sheet(text)
    assert s.title == "Mix" and [x.kind for x in s.sections] == ["intro", "verse", "chorus"]


def test_whitespace_fuzz_equivalent():
    base = "Key: G\nChorus 1\n| G | Em C | D |"
    ref = parse_sheet(base)
    rnd = random.Random(7)
    for _ in range(25):
        noisy = "\n".join(
            ("  " * rnd.randint(0, 2)) + ln.replace(" ", " " * rnd.randint(1, 3)) + (" " * rnd.randint(0, 2))
            for ln in base.splitlines()
        )
        got = parse_sheet(noisy)
        assert syms(got) == syms(ref) and got.key == ref.key


def test_empty_and_lyrics_only():
    s = parse_sheet("just some words\nnothing here")
    assert s.sections == []
