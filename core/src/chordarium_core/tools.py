"""Single source of truth for tools. The MCP server and the in-plugin chat both use these definitions."""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable

from chordarium_engine.arrange import PlanError
from chordarium_engine.models import ArrangementPlan
from chordarium_engine.styles import load_styles
from pydantic import ValidationError

from .remote import RemoteError, RemoteOut
from .session import Session, SessionError

ROLES = ["piano", "bass", "pad", "drums"]


class ToolError(Exception):
    """User-facing, recoverable error message (also fed back to the AI once to fix its input)."""


@dataclass
class ToolContext:
    session: Session
    remote: RemoteOut
    export_dir: Path


@dataclass(frozen=True)
class Tool:
    name: str
    description: str
    parameters: dict
    handler: Callable[[ToolContext, dict], Any]


def _obj(props: dict, required: list[str] | None = None) -> dict:
    return {"type": "object", "properties": props, "required": required or [], "additionalProperties": False}


PLAN_SCHEMA = {
    "type": "object", "description": "Arrangement plan (schema 6.2). Use only styles/patterns from list_styles.",
    "properties": {
        "section_id": {"type": "string"}, "style": {"type": "string"}, "feel": {"type": "string"},
        "dynamics": {"type": "string", "enum": ["soft", "medium", "loud"]},
        "parts": {"type": "array", "items": {"type": "object", "properties": {
            "role": {"type": "string", "enum": ROLES}, "pattern": {"type": "string"},
            "density": {"type": "number", "minimum": 0, "maximum": 1},
            "velocity": {"type": "array", "items": {"type": "integer"}, "minItems": 2, "maxItems": 2},
            "register": {"type": "string", "enum": ["low", "mid_low", "mid", "mid_high", "high"]},
            "instrument": {"type": "string"}, "fills": {"type": "string", "enum": ["none", "end_of_section", "every_4_bars"]},
            "seed": {"type": "integer"}, "variation": {"type": "number"}}, "required": ["role", "pattern"]}},
        "notes": {"type": "string"}},
    "required": ["style", "parts"],
}


def _wrap(fn: Callable[[ToolContext, dict], Any]) -> Callable[[ToolContext, dict], Any]:
    def run(ctx: ToolContext, args: dict) -> Any:
        try:
            return fn(ctx, args)
        except ToolError:
            raise
        except PlanError as e:
            raise ToolError("Fix these fields: " + "; ".join(e.errors)) from e
        except ValidationError as e:
            raise ToolError("Fix these fields: " + "; ".join(
                f"{'.'.join(str(x) for x in err['loc'])}: {err['msg']}" for err in e.errors())) from e
        except (SessionError, RemoteError, KeyError) as e:
            raise ToolError(str(e.args[0]) if isinstance(e, KeyError) else str(e)) from e
    return run


def _need(args: dict, *keys: str) -> None:
    for k in keys:
        if args.get(k) in (None, ""):
            raise ToolError(f"Missing required argument: {k}")


def get_session(ctx: ToolContext, args: dict) -> dict:
    return ctx.session.summary()


def load_chord_sheet(ctx: ToolContext, args: dict) -> dict:
    _need(args, "text")
    song = ctx.session.load_sheet(args["text"], args.get("title"))
    return {"title": song.title, "key": song.key, "mode": song.mode, "tempo_bpm": song.tempo_bpm,
            "time_signature": list(song.time_signature), "language": song.language,
            "sections": [{"id": s.id, "name": s.name, "bars": len(s.bars)} for s in song.sections],
            "warnings": song.warnings}


def list_styles(ctx: ToolContext, args: dict) -> dict:
    return {"styles": [{"id": s.id, "name": s.name, "time_signatures": [list(t) for t in s.time_signatures],
                        "tempo_range": list(s.tempo_range), "patterns": s.patterns,
                        "defaults": s.defaults} for s in load_styles().values()],
            "registers": ["low", "mid_low", "mid", "mid_high", "high"]}


def arrange(ctx: ToolContext, args: dict) -> dict:
    plan = ArrangementPlan.model_validate({"section_id": "-", **args["plan"]}) if args.get("plan") else None
    ids = args.get("section_ids") or ([plan.section_id] if plan and plan.section_id != "-" else None)
    parts = ctx.session.arrange(ids, plan, args.get("style"), args.get("dynamics", "medium"))
    return {"parts": [Session.part_summary(p) for p in parts]}


def edit_part(ctx: ToolContext, args: dict) -> dict:
    _need(args, "role", "changes")
    return Session.part_summary(ctx.session.edit_part(args.get("section_id"), args["role"], args["changes"]))  # type: ignore[arg-type]


def regenerate_part(ctx: ToolContext, args: dict) -> dict:
    _need(args, "role")
    return Session.part_summary(ctx.session.regenerate_part(args.get("section_id"), args["role"], args.get("seed")))  # type: ignore[arg-type]


def set_part_lock(ctx: ToolContext, args: dict) -> dict:
    _need(args, "role")
    if "locked" not in args:
        raise ToolError("Missing required argument: locked")
    return Session.part_summary(ctx.session.set_lock(args.get("section_id"), args["role"], bool(args["locked"])))  # type: ignore[arg-type]


def export_midi(ctx: ToolContext, args: dict) -> dict:
    scope = args.get("scope", "section")
    out = ctx.export_dir / ctx.session.id
    files = ctx.session.export(scope, args.get("ids"), out)
    return {"files": files, "message": "Drag the parts from the plugin, or import these MIDI files into Cubase."}


def transport(ctx: ToolContext, args: dict) -> dict:
    _need(args, "action")
    ctx.remote.send(args["action"])
    return {"ok": True}


_SEC = {"section_id": {"type": "string", "description": "Section id or name; defaults to the selected section."}}
TOOLS: dict[str, Tool] = {t.name: t for t in [
    Tool("get_session", "Read the current song (sections, bars, chords, key, tempo) and the status of every part.",
         _obj({}), _wrap(get_session)),
    Tool("load_chord_sheet", "Parse a chord sheet (English or Sinhala; chords over lyrics, [G]inline, | bar | notation).",
         _obj({"text": {"type": "string"}, "title": {"type": "string"}}, ["text"]), _wrap(load_chord_sheet)),
    Tool("list_styles", "List styles with the allowed patterns per role. Use only these in plans.", _obj({}), _wrap(list_styles)),
    Tool("arrange", "Arrange one or more sections from a plan. Omit plan to use a style's defaults.",
         _obj({"section_ids": {"type": "array", "items": {"type": "string"}}, "plan": PLAN_SCHEMA,
               "style": {"type": "string"}, "dynamics": {"type": "string", "enum": ["soft", "medium", "loud"]}}),
         _wrap(arrange)),
    Tool("edit_part", "Change fields of one part (pattern, density, velocity, register, fills, variation, seed). Locked parts cannot change.",
         _obj({**_SEC, "role": {"type": "string", "enum": ROLES}, "changes": {"type": "object"}}, ["role", "changes"]),
         _wrap(edit_part)),
    Tool("regenerate_part", "Regenerate one part with a new seed.",
         _obj({**_SEC, "role": {"type": "string", "enum": ROLES}, "seed": {"type": "integer"}}, ["role"]), _wrap(regenerate_part)),
    Tool("set_part_lock", "Lock or unlock a part so it is never changed by later edits.",
         _obj({**_SEC, "role": {"type": "string", "enum": ROLES}, "locked": {"type": "boolean"}}, ["role", "locked"]),
         _wrap(set_part_lock)),
    Tool("export_midi", "Export MIDI files (scope part|section|song). For part scope ids are part ids.",
         _obj({"scope": {"type": "string", "enum": ["part", "section", "song"]},
               "ids": {"type": "array", "items": {"type": "string"}}}), _wrap(export_midi)),
    Tool("transport", "Control Cubase transport through the MIDI Remote link.",
         _obj({"action": {"type": "string", "enum": ["play", "stop", "record", "to_start", "add_marker"]}}, ["action"]),
         _wrap(transport)),
]}


def call_tool(ctx: ToolContext, name: str, args: dict | None) -> Any:
    tool = TOOLS.get(name)
    if tool is None:
        raise ToolError(f"Unknown tool {name!r}")
    return tool.handler(ctx, args or {})


def openai_schema() -> list[dict]:
    return [{"type": "function", "function": {"name": t.name, "description": t.description, "parameters": t.parameters}}
            for t in TOOLS.values()]


def mcp_specs() -> list[tuple[str, str, dict]]:
    return [(t.name, t.description, t.parameters) for t in TOOLS.values()]
