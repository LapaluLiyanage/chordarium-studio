"""Rules-only fallback (spec 8.5): keyword -> change map."""
from __future__ import annotations

from ..session import Session, SessionError
from ..tools import ToolError

HELP = "Without an AI connected I can do: softer, louder, busier, simpler, add fill, remove a part."
ROLE_WORDS = {"piano": "piano", "keys": "piano", "bass": "bass", "pad": "pad", "drums": "drums", "drum": "drums"}
ORDER = ["low", "mid_low", "mid", "mid_high", "high"]


def _clamp(x: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, x))


def apply_rules(session: Session, message: str, section_id: str | None = None) -> tuple[str, list[dict]]:
    """Returns (reply, tool_events)."""
    text = message.lower()
    try:
        sec = session.find_section(section_id)
    except SessionError as e:
        return str(e), []
    parts = [p for p in session.parts.values() if p.section_id == sec.id]
    if not parts and any(k in text for k in ("arrange", "add", "make")):
        session.arrange([sec.id])
        parts = [p for p in session.parts.values() if p.section_id == sec.id]
        return f"Arranged {sec.name} with the style defaults.", [{"name": "arrange", "ok": True, "summary": f"Arranged {sec.name}"}]
    roles = {r for w, r in ROLE_WORDS.items() if w in text} or {p.role for p in parts}
    events: list[dict] = []

    def edit(role: str, changes: dict, label: str) -> None:
        try:
            session.edit_part(sec.id, role, changes)
            events.append({"name": "edit_part", "ok": True, "summary": f"{label} {role} · {sec.name}"})
        except (SessionError, ToolError) as e:
            events.append({"name": "edit_part", "ok": False, "summary": str(e)})

    def shift(delta_v: int, delta_d: float, label: str) -> None:
        for p in parts:
            if p.role in roles:
                lo, hi = p.spec.velocity
                edit(p.role, {"velocity": [int(_clamp(lo + delta_v, 1, 126)), int(_clamp(hi + delta_v, 2, 127))],
                              "density": round(_clamp(p.spec.density + delta_d, 0, 1), 2)}, label)

    if any(k in text for k in ("remove drums", "no drums", "remove the drums")):
        try:
            session.clear_part(sec.id, "drums")
            events.append({"name": "clear_part", "ok": True, "summary": f"Removed drums · {sec.name}"})
        except SessionError as e:
            return str(e), []
        return "Removed the drums.", events
    if "add fill" in text or "fill" in text:
        edit("drums", {"fills": "end_of_section"}, "Added fill to")
    elif any(k in text for k in ("soft", "gentle", "quiet")):
        shift(-15, -0.15, "Softened")
    elif any(k in text for k in ("loud", "powerful", "big")):
        shift(15, 0.15, "Strengthened")
    elif any(k in text for k in ("busier", "more movement")):
        shift(0, 0.25, "Busier")
    elif any(k in text for k in ("simpler", "less")):
        shift(0, -0.25, "Simplified")
    elif "higher" in text or "lower" in text:
        step = 1 if "higher" in text else -1
        for p in parts:
            if p.role in roles:
                edit(p.role, {"register": ORDER[int(_clamp(ORDER.index(p.spec.register) + step, 0, 4))]}, "Moved")
    else:
        return HELP, []
    ok = [e for e in events if e["ok"]]
    if not ok:
        return (events[0]["summary"] if events else HELP), events
    return f"Done — {len(ok)} change{'s' if len(ok) != 1 else ''} in {sec.name}.", events
