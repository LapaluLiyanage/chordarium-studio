"""M7 parse-accuracy benchmark. Each sheet in the folder may have a sibling <name>.expected.json with the
expected chord symbols per section ({"Section": [["G"], ["Em", "C"]]}); reports bar-level accuracy.

    python scripts/parse_benchmark.py engine/tests/fixtures/sheets
"""
import json
import sys
import time
from pathlib import Path

from chordarium_engine.parser.sheet import parse_sheet

total = ok = 0
t0 = time.perf_counter()
for sheet in sorted(Path(sys.argv[1]).glob("*.txt")):
    exp_file = sheet.with_suffix(".expected.json")
    song = parse_sheet(sheet.read_text(encoding="utf-8"))
    if not exp_file.exists():
        print(f"{sheet.name}: parsed {sum(len(s.bars) for s in song.sections)} bars (no expected file)")
        continue
    exp = json.loads(exp_file.read_text())
    for sec in song.sections:
        want = exp.get(sec.name, [])
        for i, bar in enumerate(sec.bars):
            total += 1
            ok += i < len(want) and [c.symbol for c in bar.chords] == want[i]
print(f"bar accuracy: {ok}/{total}" + (f" = {ok/total:.1%}" if total else "") + f"  in {time.perf_counter()-t0:.2f}s")
