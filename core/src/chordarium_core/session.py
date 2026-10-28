"""Session state: song, plans, parts, undo/redo, persistence."""
from __future__ import annotations

import json
import random
import uuid
from pathlib import Path
from typing import Callable

from chordarium_engine.arrange import PlanError, build_part, default_plan, default_seed, validate_plan
from chordarium_engine.generators.common import section_ticks
from chordarium_engine.midi_export import export_part, export_section, export_song, part_filename
from chordarium_engine.models import ArrangementPlan, Part, PartSpec, Song
from chordarium_engine.parser.sheet import parse_sheet
from chordarium_engine.styles import get_style

MAX_HISTORY = 100


class SessionError(ValueError):
    pass


def suggest_style(song: Song) -> str:
    if song.time_signature == (6, 8):
        return "baila_6_8"
    return "sinhala_ballad" if song.language == "si" else "pop_4_4"


class Session:
    def __init__(self, session_id: str | None = None):
        self.id = session_id or "s_" + uuid.uuid4().hex[:8]
        self.song: Song | None = None
        self.plans: dict[str, ArrangementPlan] = {}
        self.parts: dict[str, Part] = {}
        self.selected_section_id: str | None = None
        self.undo_stack: list[str] = []
        self.redo_stack: list[str] = []
        self.listeners: list[Callable[[str, dict], None]] = []

    # ---- events / snapshots ----
    def emit(self, event: str, payload: dict | None = None) -> None:
        for fn in list(self.listeners):
            fn(event, payload or {})

    def snapshot(self) -> dict:
        return {"id": self.id, "song": self.song.model_dump(mode="json") if self.song else None,
                "plans": {k: v.model_dump(mode="json") for k, v in self.plans.items()},
                "parts": {k: v.model_dump(mode="json") for k, v in self.parts.items()},
                "selected_section_id": self.selected_section_id}

    def restore(self, snap: dict) -> None:
        self.id = snap.get("id", self.id)
        self.song = Song.model_validate(snap["song"]) if snap.get("song") else None
        self.plans = {k: ArrangementPlan.model_validate(v) for k, v in snap.get("plans", {}).items()}
        self.parts = {k: Part.model_validate(v) for k, v in snap.get("parts", {}).items()}
        self.selected_section_id = snap.get("selected_section_id")

    def _checkpoint(self) -> None:
        self.undo_stack.append(json.dumps(self.snapshot()))
        del self.undo_stack[:-MAX_HISTORY]
        self.redo_stack.clear()

    def undo(self) -> bool:
        if not self.undo_stack:
            return False
        self.redo_stack.append(json.dumps(self.snapshot()))
        self.restore(json.loads(self.undo_stack.pop()))
        self.emit("session.updated")
        return True

    def redo(self) -> bool:
        if not self.redo_stack:
            return False
        self.undo_stack.append(json.dumps(self.snapshot()))
        self.restore(json.loads(self.redo_stack.pop()))
        self.emit("session.updated")
        return True

    def save(self, home: Path) -> Path:
        d = home / "sessions"
        d.mkdir(parents=True, exist_ok=True)
        f = d / f"{self.id}.json"
        tmp = f.with_suffix(".tmp")
        tmp.write_text(json.dumps(self.snapshot()), encoding="utf-8")
        tmp.replace(f)
        return f

    @classmethod
    def load(cls, path: Path) -> "Session":
        s = cls()
        s.restore(json.loads(path.read_text(encoding="utf-8")))
        return s

    # ---- helpers ----
    def require_song(self) -> Song:
        if self.song is None:
            raise SessionError("No song loaded. Paste a chord sheet first.")
        return self.song

    def find_section(self, ref: str | None):
        song = self.require_song()
        ref = ref or self.selected_section_id or (song.sections[0].id if song.sections else None)
        for s in song.sections:
            if ref and ref.lower() in (s.id.lower(), s.name.lower()):
                return s
        raise SessionError(f"Section {ref!r} not found. Available: {', '.join(s.name for s in song.sections) or 'none'}")

    def part_for(self, section_id: str, role: str) -> Part:
        p = self.parts.get(f"part_{section_id}_{role}")
        if p is None:
            raise SessionError(f"No {role} part in {section_id}. Arrange the section first.")
        return p

    # ---- song ----
    def load_sheet(self, text: str, title: str | None = None) -> Song:
        self._checkpoint()
        self.song = parse_sheet(text, title)
        self.plans, self.parts = {}, {}
        self.selected_section_id = self.song.sections[0].id if self.song.sections else None
        self.emit("session.updated")
        return self.song

    def patch_song(self, patch: dict) -> Song:
        song = self.require_song()
        self._checkpoint()
        old_bars = {s.id: s.bars for s in song.sections}
        merged = {**song.model_dump(mode="json"), **patch}
        new = Song.model_validate(merged)
        new.warnings = song.warnings
        self.song = new
        live = {s.id for s in new.sections}
        for pid in [p for p, part in self.parts.items() if part.section_id not in live]:
            del self.parts[pid]
        self.plans = {k: v for k, v in self.plans.items() if k in live}
        for sec in new.sections:
            if sec.id in self.plans and (old_bars.get(sec.id) != sec.bars or "time_signature" in patch):
                self._regenerate_section(sec.id)
        if self.selected_section_id not in live:
            self.selected_section_id = new.sections[0].id if new.sections else None
        self.emit("session.updated")
        return new

    def _regenerate_section(self, section_id: str) -> None:
        plan = self.plans[section_id]
        style = get_style(plan.style)
        for spec in plan.parts:
            old = self.parts.get(f"part_{section_id}_{spec.role}")
            if old is not None and old.locked:
                continue
            seed = old.seed if old else (spec.seed if spec.seed is not None else default_seed(section_id, spec.role))
            self.parts[f"part_{section_id}_{spec.role}"] = build_part(self.song, section_id, spec, style, plan.dynamics, seed)  # type: ignore[arg-type]

    # ---- arrangement ----
    def arrange(self, section_ids: list[str] | None, plan: ArrangementPlan | None = None,
                style: str | None = None, dynamics: str = "medium") -> list[Part]:
        song = self.require_song()
        sections = [self.find_section(s) for s in section_ids] if section_ids else [self.find_section(None)]
        self._checkpoint()
        out: list[Part] = []
        for sec in sections:
            p = plan.model_copy(update={"section_id": sec.id}, deep=True) if plan else \
                default_plan(sec.id, style or suggest_style(song), dynamics)  # type: ignore[arg-type]
            errors = validate_plan(p, song)
            if errors:
                self.undo_stack.pop()
                raise PlanError(errors)
            style_obj = get_style(p.style)
            kept: list[PartSpec] = []
            for spec in p.parts:
                existing = self.parts.get(f"part_{sec.id}_{spec.role}")
                if existing is not None and existing.locked:
                    kept.append(existing.spec)
                    out.append(existing)
                    continue
                seed = spec.seed if spec.seed is not None else default_seed(sec.id, spec.role)
                part = build_part(song, sec.id, spec, style_obj, p.dynamics, seed)
                self.parts[part.id] = part
                kept.append(spec)
                out.append(part)
            self.plans[sec.id] = p.model_copy(update={"parts": kept})
        self.selected_section_id = sections[-1].id
        self.emit("session.updated")
        return out

    def edit_part(self, section_id: str, role: str, changes: dict) -> Part:
        sec = self.find_section(section_id)
        part = self.part_for(sec.id, role)
        if part.locked:
            raise SessionError(f"{role.title()} is locked. Unlock to change it.")
        forbidden = set(changes) & {"role", "locked"}
        if forbidden:
            raise SessionError(f"Cannot change {', '.join(sorted(forbidden))} with edit_part.")
        plan = self.plans[sec.id]
        spec = PartSpec.model_validate({**part.spec.model_dump(), **changes})
        if spec.pattern not in get_style(plan.style).patterns[role]:
            raise PlanError([f"{role}: pattern {spec.pattern!r} not in {get_style(plan.style).patterns[role]}"])
        self._checkpoint()
        seed = int(changes["seed"]) if changes.get("seed") is not None else part.seed
        new = build_part(self.song, sec.id, spec, get_style(plan.style), plan.dynamics, seed)  # type: ignore[arg-type]
        self.parts[new.id] = new
        plan.parts = [spec if p.role == role else p for p in plan.parts]
        self.emit("part.updated", {"part_id": new.id})
        return new

    def regenerate_part(self, section_id: str, role: str, seed: int | None = None) -> Part:
        part = self.part_for(self.find_section(section_id).id, role)
        return self.edit_part(part.section_id, role, {"seed": seed if seed is not None else random.randrange(1, 2**31)})

    def set_lock(self, section_id: str, role: str, locked: bool) -> Part:
        part = self.part_for(self.find_section(section_id).id, role)
        self._checkpoint()
        part.locked = locked
        part.spec.locked = locked
        self.emit("part.updated", {"part_id": part.id})
        return part

    def clear_part(self, section_id: str, role: str) -> None:
        part = self.part_for(self.find_section(section_id).id, role)
        if part.locked:
            raise SessionError(f"{role.title()} is locked. Unlock to change it.")
        self._checkpoint()
        del self.parts[part.id]
        plan = self.plans[part.section_id]
        plan.parts = [p for p in plan.parts if p.role != role] or plan.parts
        self.emit("session.updated")

    # ---- export ----
    def export(self, scope: str, ids: list[str] | None, out_dir: Path) -> list[str]:
        song = self.require_song()
        out_dir.mkdir(parents=True, exist_ok=True)
        paths: list[Path] = []
        if scope == "part":
            if not ids:
                raise SessionError("Give the part ids to export.")
            for pid in ids:
                part = self.parts.get(pid)
                if part is None:
                    raise SessionError(f"Part {pid!r} not found.")
                name = part_filename(song.section(part.section_id).name, part.role)
                paths.append(export_part(song, part, out_dir / name))
        elif scope == "section":
            for ref in (ids or [self.find_section(None).id]):
                sec = self.find_section(ref)
                parts = [p for p in self.parts.values() if p.section_id == sec.id]
                if not parts:
                    raise SessionError(f"{sec.name} has no parts yet. Arrange it first.")
                paths.append(export_section(song, parts, out_dir / part_filename(sec.name, "All").replace("_All", "")))
        elif scope == "song":
            by_sec = {s.id: [p for p in self.parts.values() if p.section_id == s.id] for s in song.sections}
            if not any(by_sec.values()):
                raise SessionError("Nothing arranged yet.")
            paths.append(export_song(song, by_sec, out_dir / f"{song.title.replace(' ', '') or 'Song'}.mid"))
        else:
            raise SessionError("scope must be part, section or song")
        return [str(p) for p in paths]

    # ---- summaries ----
    @staticmethod
    def part_summary(p: Part) -> dict:
        pitches = [n.pitch for n in p.notes]
        return {"id": p.id, "section_id": p.section_id, "role": p.role, "pattern": p.spec.pattern,
                "notes": len(p.notes), "range": [min(pitches), max(pitches)] if pitches else None,
                "seed": p.seed, "locked": p.locked, "density": p.spec.density, "velocity": list(p.spec.velocity)}

    def summary(self) -> dict:
        if self.song is None:
            return {"id": self.id, "song": None, "parts": [], "plans": {}}
        s = self.song
        return {"id": self.id, "selected_section_id": self.selected_section_id,
                "song": {"title": s.title, "key": s.key, "mode": s.mode, "tempo_bpm": s.tempo_bpm,
                         "time_signature": list(s.time_signature), "language": s.language, "warnings": s.warnings,
                         "sections": [{"id": x.id, "name": x.name, "kind": x.kind, "bars": len(x.bars),
                                       "ticks": section_ticks(x),
                                       "chords": [[c.symbol for c in b.chords] for b in x.bars]} for x in s.sections]},
                "plans": {k: v.model_dump(mode="json") for k, v in self.plans.items()},
                "parts": [self.part_summary(p) for p in self.parts.values()]}
