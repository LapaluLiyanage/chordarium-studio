"""Section label dictionary (EN + SI).

The Sinhala dictionary is intentionally empty: fill it in with the words you use on
your chord sheets (do not guess). Keys are matched lowercase with spaces/hyphens removed.
Use ``register_labels({"<word>": "chorus"})`` or edit SINHALA_LABELS directly.
"""
from __future__ import annotations

import re

ENGLISH_LABELS: dict[str, str] = {
    "intro": "intro", "introduction": "intro",
    "verse": "verse", "v": "verse",
    "prechorus": "pre_chorus", "pre": "pre_chorus",
    "chorus": "chorus", "refrain": "chorus", "hook": "chorus", "c": "chorus",
    "bridge": "bridge", "middle8": "bridge",
    "interlude": "interlude", "instrumental": "interlude", "break": "interlude",
    "solo": "solo",
    "outro": "outro", "ending": "outro", "coda": "outro",
}

SINHALA_LABELS: dict[str, str] = {}  # TODO(Lapalu): fill with real Sinhala section words

_CANONICAL = {"intro": "Intro", "verse": "Verse", "pre_chorus": "Pre-Chorus", "chorus": "Chorus",
              "bridge": "Bridge", "interlude": "Interlude", "solo": "Solo", "outro": "Outro"}


def register_labels(extra: dict[str, str]) -> None:
    SINHALA_LABELS.update({_norm(k): v for k, v in extra.items()})


def _norm(label: str) -> str:
    return re.sub(r"[\s\-_]+", "", label.strip().lower())


def lookup(label: str) -> str | None:
    key = _norm(label)
    return SINHALA_LABELS.get(key) or ENGLISH_LABELS.get(key)


def canonical_name(kind: str, raw: str) -> str:
    return _CANONICAL.get(kind, raw.strip().title() or "Section")
