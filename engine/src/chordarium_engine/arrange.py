"""Plan -> Parts. Deterministic: same song + plan + seeds give identical notes."""
from __future__ import annotations

import random
import zlib

from .generators import bass, drums, pad, piano
from .generators.common import section_ticks
from .humanize import humanize
from .models import ROLE_CHANNEL, ArrangementPlan, Part, PartSpec, Song
from .styles import Style, get_style

GENERATORS = {"piano": piano.generate, "bass": bass.generate, "pad": pad.generate, "drums": drums.generate}
DYNAMIC_SHIFT = {"soft": -10, "medium": 0, "loud": 20}


class PlanError(ValueError):
    def __init__(self, errors: list[str]):
        super().__init__("; ".join(errors))
        self.errors = errors


def default_seed(section_id: str, role: str) -> int:
    return zlib.crc32(f"{section_id}:{role}".encode())


def default_plan(section_id: str, style_id: str, dynamics: str = "medium", roles: list[str] | None = None) -> ArrangementPlan:
    style = get_style(style_id)
    shift = DYNAMIC_SHIFT[dynamics]
    parts = []
    for role, d in style.defaults.items():
        if roles and role not in roles:
            continue
        lo, hi = d["velocity"]
        parts.append(PartSpec(role=role, pattern=d["pattern"], density=d["density"],
                              velocity=(max(1, min(127, lo + shift)), max(1, min(127, hi + shift))),
                              register=d.get("register", "mid"), fills=d.get("fills", "none")))
    return ArrangementPlan(section_id=section_id, style=style_id, dynamics=dynamics, parts=parts)


def validate_plan(plan: ArrangementPlan, song: Song) -> list[str]:
    errors: list[str] = []
    try:
        style = get_style(plan.style)
    except KeyError as e:
        return [str(e)]
    if plan.section_id not in {s.id for s in song.sections}:
        errors.append(f"unknown section_id {plan.section_id!r}")
    for p in plan.parts:
        if p.pattern not in style.patterns.get(p.role, []):
            errors.append(f"{p.role}: pattern {p.pattern!r} not in {style.patterns.get(p.role, [])}")
    return errors


def build_part(song: Song, section_id: str, spec: PartSpec, style: Style, dynamics: str, seed: int) -> Part:
    section = song.section(section_id)
    total = section_ticks(section)
    notes, ccs = GENERATORS[spec.role](section, spec, style, seed, song.time_signature, dynamics)
    notes = humanize(notes, random.Random(seed ^ 0x5EED), spec.velocity, total,
                     is_drums=spec.role == "drums", density=spec.density)
    notes.sort(key=lambda n: (n.start, n.pitch))
    return Part(id=f"part_{section_id}_{spec.role}", section_id=section_id, role=spec.role,
                channel=ROLE_CHANNEL[spec.role], spec=spec, seed=seed, locked=spec.locked, notes=notes, ccs=ccs)


def arrange_section(song: Song, plan: ArrangementPlan) -> list[Part]:
    errors = validate_plan(plan, song)
    if errors:
        raise PlanError(errors)
    style = get_style(plan.style)
    return [build_part(song, plan.section_id, p, style, plan.dynamics,
                       p.seed if p.seed is not None else default_seed(plan.section_id, p.role))
            for p in plan.parts]
