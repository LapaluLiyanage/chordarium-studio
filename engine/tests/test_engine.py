import itertools
import random

import mido
import pytest
from hypothesis import given, settings, strategies as st

from chordarium_engine.arrange import PlanError, arrange_section, default_plan, validate_plan
from chordarium_engine.cli import main as cli_main
from chordarium_engine.generators.common import section_ticks
from chordarium_engine.humanize import humanize
from chordarium_engine.midi_export import export_part, export_section, export_song, part_filename
from chordarium_engine.models import ArrangementPlan, NoteEvent, PartSpec, Song
from chordarium_engine.parser.chords import parse_chord
from chordarium_engine.parser.sheet import parse_sheet
from chordarium_engine.styles import get_style, load_styles
from chordarium_engine.theory.voicing import (
    REGISTER_RANGES, choose_voicing, shift_register, voicings, voicing_cost,
)

SHEET = "Key: G\nTempo: 76\n[Chorus 1]\n| G | Em C | D | G |\n[Verse 1]\n| Em | C | G | D |"
DRUM_PITCHES = {36, 37, 38, 42, 44, 45, 46, 49, 50, 51}


def song(ts="4/4", sheet=SHEET):
    return parse_sheet(f"Time: {ts}\n" + sheet)


# ---------- theory ----------
@pytest.mark.parametrize("reg", REGISTER_RANGES)
@pytest.mark.parametrize("sym", ["C", "Am7", "G7", "Bdim", "F#m7b5", "C13", "Dsus4", "Gadd9", "C11", "Caug"])
def test_voicings_in_register_and_contain_chord_tones(reg, sym):
    c = parse_chord(sym)
    lo, hi = REGISTER_RANGES[reg]
    vs = voicings(c, reg)
    assert vs
    for v in vs:
        assert all(lo <= n <= hi for n in v) and list(v) == sorted(v)
        assert {n % 12 for n in v} <= set(c.pitch_classes)
        assert c.root in {n % 12 for n in v}


def test_voice_leading_prefers_small_movement_and_is_deterministic():
    prev = choose_voicing(parse_chord("C"), "mid", None)
    a = choose_voicing(parse_chord("F"), "mid", prev)
    assert a == choose_voicing(parse_chord("F"), "mid", prev)
    assert sum(abs(x - y) for x, y in zip(a, prev)) <= 8


def test_parallel_octave_penalised():
    base = voicing_cost((48, 60), (47, 59), "mid")
    assert base > 20


def test_shift_register_clamps():
    assert shift_register("high", 1) == "high" and shift_register("low", -1) == "low"
    assert shift_register("mid", 1) == "mid_high"


# ---------- styles / plans ----------
def test_six_starter_styles():
    assert set(load_styles()) == {"pop_4_4", "sinhala_ballad", "baila_6_8", "gospel_ballad", "lofi", "bollywood_pop"}
    with pytest.raises(KeyError):
        get_style("nope")


def test_default_plan_validates_and_dynamics_shift():
    s = song()
    soft = default_plan("sec_chorus_1", "sinhala_ballad", "soft")
    loud = default_plan("sec_chorus_1", "sinhala_ballad", "loud")
    assert soft.parts[0].velocity[1] < loud.parts[0].velocity[1]
    assert validate_plan(soft, s) == []


def test_invalid_plan_rejected():
    s = song()
    bad = ArrangementPlan(section_id="sec_chorus_1", style="pop_4_4",
                          parts=[PartSpec(role="bass", pattern="nonsense")])
    assert validate_plan(bad, s)
    with pytest.raises(PlanError):
        arrange_section(s, bad)
    assert validate_plan(bad.model_copy(update={"style": "x"}), s)
    assert validate_plan(bad.model_copy(update={"section_id": "zzz"}), s)


# ---------- generators: every pattern x style x time signature ----------
CASES = [(sid, role, pat) for sid, stl in load_styles().items() for role, pats in stl.patterns.items() for pat in pats]


@pytest.mark.parametrize("ts", ["4/4", "6/8", "3/4"])
@pytest.mark.parametrize("sid,role,pat", CASES)
def test_every_pattern_generates_valid_notes(sid, role, pat, ts):
    s = song(ts)
    sec = s.sections[0]
    total = section_ticks(sec)
    plan = ArrangementPlan(section_id=sec.id, style=sid, dynamics="medium", parts=[
        PartSpec(role=role, pattern=pat, density=0.6, velocity=(40, 90), register="mid" if role != "bass" else "low",
                 fills="end_of_section" if role == "drums" else "none")])
    (part,) = arrange_section(s, plan)
    assert part.notes, "pattern produced no notes"
    for n in part.notes:
        assert 0 <= n.start < total and n.start + n.duration <= total
        assert 40 <= n.velocity <= 90
        if role == "drums":
            assert n.pitch in DRUM_PITCHES
    if role != "drums":
        lo, hi = REGISTER_RANGES["mid" if role != "bass" else "low"]
        assert all(lo <= n.pitch <= hi for n in part.notes)
    again = arrange_section(s, plan)[0]
    assert again.notes == part.notes  # determinism


def test_seed_changes_humanization_but_not_structure():
    s = song()
    p1 = default_plan("sec_chorus_1", "pop_4_4")
    p2 = p1.model_copy(deep=True)
    for p in p2.parts:
        p.seed = 999
    a, b = arrange_section(s, p1), arrange_section(s, p2)
    assert [len(x.notes) for x in a] == [len(x.notes) for x in b]
    assert [x.notes for x in a] != [x.notes for x in b]


def test_swell_emits_cc11_and_sustain_overlap():
    s = song()
    sec = s.sections[0]
    mk = lambda pat: ArrangementPlan(section_id=sec.id, style="pop_4_4", parts=[
        PartSpec(role="pad", pattern=pat, velocity=(40, 70), register="mid_high")])
    swell = arrange_section(s, mk("swell"))[0]
    assert swell.ccs and all(c.cc == 11 for c in swell.ccs)
    sus = arrange_section(s, mk("sustain"))[0]
    assert not sus.ccs


def test_drums_crash_on_chorus_and_fill_and_density_thinning():
    s = song()
    sec = s.sections[0]
    def run(density, fills, dyn="medium", sid=None):
        return arrange_section(s, ArrangementPlan(section_id=sid or sec.id, style="pop_4_4", dynamics=dyn, parts=[
            PartSpec(role="drums", pattern="pop_basic", density=density, velocity=(40, 100), fills=fills)]))[0]
    assert any(n.pitch == 49 for n in run(0.5, "none").notes)
    assert not any(n.pitch == 49 for n in run(0.5, "none", "soft").notes)
    assert not any(n.pitch == 49 for n in run(0.5, "none", sid=s.sections[1].id).notes)  # verse
    assert any(n.pitch in (45, 50) for n in run(0.5, "end_of_section").notes)
    assert len(run(0.1, "none").notes) < len(run(0.9, "none").notes)
    assert any(n.pitch in (45, 50) for n in run(0.5, "every_4_bars").notes)


def test_no_chord_slots_are_rests():
    s = parse_sheet("| G | N.C. | C | N.C. |")
    plan = default_plan(s.sections[0].id, "pop_4_4")
    for part in arrange_section(s, plan):
        if part.role != "drums":
            assert all(not (1920 + 16 <= n.start < 3840 - 16) for n in part.notes)


def test_slash_chord_bass_uses_slash_note():
    s = parse_sheet("| C/E |")
    plan = ArrangementPlan(section_id=s.sections[0].id, style="pop_4_4", parts=[
        PartSpec(role="bass", pattern="root", register="low", velocity=(60, 60))])
    n = arrange_section(s, plan)[0].notes[0]
    assert n.pitch % 12 == 4


def test_bass_walking_lite_approach_note():
    s = parse_sheet("| C | G |")
    plan = ArrangementPlan(section_id=s.sections[0].id, style="pop_4_4", parts=[
        PartSpec(role="bass", pattern="walking_lite", register="low", velocity=(60, 90))])
    notes = arrange_section(s, plan)[0].notes
    approach = [n for n in notes if 1600 <= n.start < 1800]
    assert approach and abs(approach[0].pitch % 12 - 7) == 1


@settings(max_examples=40, deadline=None)
@given(chords=st.lists(st.sampled_from(["C", "Am", "F", "G7", "Dm7", "Bdim", "Esus4", "Cmaj7", "A7b9", "G/B", "N.C."]),
                       min_size=1, max_size=8),
       density=st.floats(0, 1), seed=st.integers(0, 10_000),
       ts=st.sampled_from(["4/4", "6/8", "3/4"]), style=st.sampled_from(sorted(load_styles())))
def test_property_all_roles(chords, density, seed, ts, style):
    s = parse_sheet(f"Time: {ts}\n| " + " | ".join(chords) + " |")
    sec = s.sections[0]
    total = section_ticks(sec)
    st_ = get_style(style)
    parts = [PartSpec(role=r, pattern=st_.patterns[r][seed % len(st_.patterns[r])], density=density,
                      velocity=(35, 110), register={"piano": "mid", "bass": "low", "pad": "mid_high", "drums": "mid"}[r],
                      seed=seed) for r in ("piano", "bass", "pad", "drums")]
    plan = ArrangementPlan(section_id=sec.id, style=style, parts=parts)
    out = arrange_section(s, plan)
    assert out == arrange_section(s, plan)
    for p in out:
        for n in p.notes:
            assert 0 <= n.start and n.start + n.duration <= total and 35 <= n.velocity <= 110
            if p.role != "drums":
                lo, hi = REGISTER_RANGES[p.spec.register]
                assert lo <= n.pitch <= hi


# ---------- humanize ----------
def test_humanize_bounds_and_grid_preservation():
    notes = [NoteEvent(pitch=36, start=480, duration=100, velocity=80), NoteEvent(pitch=42, start=480, duration=50, velocity=80),
             NoteEvent(pitch=60, start=0, duration=500, velocity=80)]
    out = humanize(notes, random.Random(1), (70, 90), 1000, is_drums=True, density=0.1)
    assert out[0].start == 480  # kick stays on grid at low density
    assert all(70 <= n.velocity <= 90 for n in out)
    assert all(n.start + n.duration <= 1000 for n in out)
    assert humanize(notes, random.Random(1), (70, 90), 1000) == humanize(notes, random.Random(1), (70, 90), 1000)
    assert humanize([NoteEvent(pitch=1, start=999, duration=5, velocity=50)], random.Random(0), (1, 127), 100) == []


# ---------- MIDI export ----------
def test_midi_roundtrip_section_part_song(tmp_path):
    s = song()
    parts = arrange_section(s, default_plan("sec_chorus_1", "sinhala_ballad"))
    f = export_section(s, parts, tmp_path / "Chorus1.mid")
    mid = mido.MidiFile(f)
    assert mid.type == 1 and mid.ticks_per_beat == 480
    names = [next((m.name for m in t if m.type == "track_name"), None) for t in mid.tracks]
    assert names[1:] == ["Piano", "Bass", "Pad", "Drums"]
    meta = [m for m in mid.tracks[0] if m.type in ("set_tempo", "time_signature")]
    assert {m.type for m in meta} == {"set_tempo", "time_signature"}
    assert round(mido.tempo2bpm(next(m.tempo for m in meta if m.type == "set_tempo"))) == 76
    drums = mid.tracks[4]
    assert {m.channel for m in drums if m.type == "note_on"} == {9}
    on = sum(1 for m in mid.tracks[1] if m.type == "note_on")
    assert on == len(parts[0].notes)
    one = export_part(s, parts[1], tmp_path / "x" / "bass.mid")
    assert len(mido.MidiFile(one).tracks) == 2
    full = export_song(s, {sec.id: arrange_section(s, default_plan(sec.id, "pop_4_4")) for sec in s.sections}, tmp_path / "song.mid")
    total = max(sum(m.time for m in t) for t in mido.MidiFile(full).tracks)
    assert total > section_ticks(s.sections[0])
    assert part_filename("Chorus 1", "piano") == "Chorus1_Piano.mid"


def test_swell_cc_written(tmp_path):
    s = song()
    plan = ArrangementPlan(section_id="sec_chorus_1", style="lofi", parts=[PartSpec(role="pad", pattern="swell", register="mid_high")])
    mid = mido.MidiFile(export_section(s, arrange_section(s, plan), tmp_path / "p.mid"))
    assert any(m.type == "control_change" and m.control == 11 and m.channel == 2 for m in mid.tracks[1])


# ---------- CLI ----------
def test_cli(tmp_path, capsys):
    sheet = tmp_path / "s.txt"
    sheet.write_text(SHEET, encoding="utf-8")
    out = tmp_path / "o.mid"
    assert cli_main(["parse", str(sheet)]) == 0 and "sec_chorus_1" in capsys.readouterr().out
    assert cli_main(["arrange", str(sheet), "--section", "Chorus 1", "--style", "sinhala_ballad", "--out", str(out)]) == 0
    assert out.exists() and "piano=" in capsys.readouterr().out
    assert cli_main(["arrange", str(sheet), "--section", "Nope", "--out", str(out)]) == 2
    assert cli_main(["arrange", str(sheet), "--section", "chorus 1", "--style", "zzz", "--out", str(out)]) == 2
    assert cli_main(["styles"]) == 0 and "sinhala_ballad" in capsys.readouterr().out
