"""Every fixture sheet must parse and arrange in every starter style without error."""
from pathlib import Path

import pytest
from chordarium_engine.arrange import arrange_section, default_plan
from chordarium_engine.parser.sheet import parse_sheet
from chordarium_engine.styles import load_styles

SHEETS = sorted((Path(__file__).parent / "fixtures" / "sheets").glob("*.txt"))


@pytest.mark.parametrize("path", SHEETS, ids=lambda p: p.stem)
def test_sheet_parses(path):
    song = parse_sheet(path.read_text(encoding="utf-8"), title=path.stem)
    assert song.sections and all(s.bars for s in song.sections)
    assert song.key


@pytest.mark.parametrize("path", SHEETS, ids=lambda p: p.stem)
def test_every_style_arranges(path):
    song = parse_sheet(path.read_text(encoding="utf-8"), title=path.stem)
    for style_id in load_styles():
        for sec in song.sections:
            parts = arrange_section(song, default_plan(sec.id, style_id))
            assert {p.role for p in parts} == {"piano", "bass", "pad", "drums"}
            assert all(p.notes for p in parts if p.role in ("piano", "bass", "drums"))
