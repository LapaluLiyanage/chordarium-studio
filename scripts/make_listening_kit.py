"""M7 listening-test kit: export blinded arrangements (one MIDI per fixture section x style) in random order,
plus an answer key and a rating form. Human-made references are dropped into --refs and blinded the same way.

    python scripts/make_listening_kit.py --out kit --refs refs_dir --seed 1
"""
import argparse
import csv
import random
import shutil
from pathlib import Path

from chordarium_engine.arrange import arrange_section, default_plan
from chordarium_engine.midi_export import export_section
from chordarium_engine.parser.sheet import parse_sheet

SHEETS = Path(__file__).resolve().parent.parent / "engine" / "tests" / "fixtures" / "sheets"


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="kit")
    ap.add_argument("--refs", default=None, help="folder of human-made .mid references")
    ap.add_argument("--count", type=int, default=10)
    ap.add_argument("--style", default="pop_4_4")
    ap.add_argument("--seed", type=int, default=1)
    a = ap.parse_args()
    out = Path(a.out); out.mkdir(parents=True, exist_ok=True)
    items: list[tuple[str, Path, str]] = []  # (kind, file, label)
    for sheet in sorted(SHEETS.glob("*.txt")):
        song = parse_sheet(sheet.read_text(encoding="utf-8"), title=sheet.stem)
        for sec in song.sections:
            parts = arrange_section(song, default_plan(sec.id, a.style, "soft"))
            f = out / f"_tmp_{sheet.stem}_{sec.id}.mid"
            export_section(song, parts, f)
            items.append(("studio", f, f"{sheet.stem}/{sec.name}"))
    items = items[: a.count]
    if a.refs:
        items += [("human", p, p.stem) for p in sorted(Path(a.refs).glob("*.mid"))]
    random.Random(a.seed).shuffle(items)
    with open(out / "answer_key.csv", "w", newline="") as key, open(out / "rating_form.csv", "w", newline="") as form:
        k, r = csv.writer(key), csv.writer(form)
        k.writerow(["clip", "source", "label"]); r.writerow(["clip", "musicality_1_5", "naturalness_1_5", "would_use_1_5", "ai_or_human_guess", "comments"])
        for i, (kind, f, label) in enumerate(items, 1):
            name = f"clip_{i:02d}.mid"; shutil.copy(f, out / name)
            k.writerow([name, kind, label]); r.writerow([name, "", "", "", "", ""])
    for f in out.glob("_tmp_*.mid"):
        f.unlink()
    print(f"{len(items)} blinded clips in {out}")


if __name__ == "__main__":
    main()
