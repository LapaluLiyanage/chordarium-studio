from __future__ import annotations

import argparse
import sys
from pathlib import Path

from .arrange import PlanError, arrange_section, default_plan
from .midi_export import export_section
from .parser.sheet import parse_sheet
from .styles import load_styles


def _read(path: str) -> str:
    return Path(path).read_text(encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="chordarium-studio")
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("parse", help="print Song JSON")
    p.add_argument("sheet")
    a = sub.add_parser("arrange", help="arrange one section to a MIDI file")
    a.add_argument("sheet")
    a.add_argument("--section", required=True, help="section name or id, e.g. 'Chorus 1'")
    a.add_argument("--style", default="pop_4_4")
    a.add_argument("--dynamics", choices=["soft", "medium", "loud"], default="medium")
    a.add_argument("--out", required=True)
    sub.add_parser("styles", help="list styles and patterns")
    args = ap.parse_args(argv)

    if args.cmd == "styles":
        for s in load_styles().values():
            print(f"{s.id}  ({s.name}, starter template)")
            for role, pats in s.patterns.items():
                print(f"  {role}: {', '.join(pats)}")
        return 0

    song = parse_sheet(_read(args.sheet))
    if args.cmd == "parse":
        print(song.model_dump_json(indent=2))
        return 0

    key = args.section.strip().lower()
    sec = next((s for s in song.sections if key in (s.id.lower(), s.name.lower())), None)
    if sec is None:
        print(f"Section {args.section!r} not found. Available: {', '.join(s.name for s in song.sections)}", file=sys.stderr)
        return 2
    try:
        parts = arrange_section(song, default_plan(sec.id, args.style, args.dynamics))
    except (PlanError, KeyError) as e:
        print(f"error: {e}", file=sys.stderr)
        return 2
    export_section(song, parts, args.out)
    print(f"Wrote {args.out}: {', '.join(f'{p.role}={len(p.notes)} notes' for p in parts)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
