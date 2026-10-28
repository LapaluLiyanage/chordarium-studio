"""Style templates (spec 6.4). All shipped styles are *starter templates* to be refined with musicians."""
from __future__ import annotations

from dataclasses import dataclass, field
from functools import lru_cache
from importlib import resources

import yaml


@dataclass(frozen=True)
class Style:
    id: str
    name: str
    time_signatures: list[tuple[int, int]]
    tempo_range: tuple[int, int]
    defaults: dict[str, dict]
    patterns: dict[str, list[str]]
    grids: dict[str, dict[str, dict[str, str]]] = field(default_factory=dict)
    starter: bool = True


@lru_cache(maxsize=1)
def load_styles() -> dict[str, Style]:
    out: dict[str, Style] = {}
    for f in sorted(resources.files(__package__).iterdir(), key=lambda p: p.name):
        if not f.name.endswith(".yaml"):
            continue
        d = yaml.safe_load(f.read_text(encoding="utf-8"))
        out[d["id"]] = Style(
            id=d["id"], name=d["name"],
            time_signatures=[tuple(t) for t in d["time_signatures"]],
            tempo_range=tuple(d["tempo_range"]), defaults=d["defaults"], patterns=d["patterns"],
            grids={k: {str(n): rows for n, rows in v.items()} for k, v in d.get("grids", {}).items()},
            starter=d.get("starter", True),
        )
    return out


def get_style(style_id: str) -> Style:
    try:
        return load_styles()[style_id]
    except KeyError:
        raise KeyError(f"unknown style {style_id!r}; available: {', '.join(load_styles())}") from None
