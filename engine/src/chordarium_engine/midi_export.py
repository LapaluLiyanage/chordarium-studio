"""MIDI export with mido (spec 7.5). Type-1 file, PPQ 480, one track per part."""
from __future__ import annotations

import re
from pathlib import Path

import mido

from .generators.common import section_ticks
from .models import PPQ, ROLE_CHANNEL, Part, Song

_ORDER = {"note_off": 0, "control_change": 1, "note_on": 2}


def _track(name: str, events: list[tuple[int, mido.Message]]) -> mido.MidiTrack:
    tr = mido.MidiTrack()
    tr.append(mido.MetaMessage("track_name", name=name, time=0))
    last = 0
    for tick, msg in sorted(events, key=lambda e: (e[0], _ORDER[e[1].type])):
        tr.append(msg.copy(time=tick - last))
        last = tick
    tr.append(mido.MetaMessage("end_of_track", time=0))
    return tr


def _part_events(part: Part, offset: int = 0) -> list[tuple[int, mido.Message]]:
    ch = ROLE_CHANNEL[part.role] - 1
    ev: list[tuple[int, mido.Message]] = []
    for n in part.notes:
        ev.append((offset + n.start, mido.Message("note_on", channel=ch, note=n.pitch, velocity=n.velocity)))
        ev.append((offset + n.start + n.duration, mido.Message("note_off", channel=ch, note=n.pitch, velocity=0)))
    for c in part.ccs:
        ev.append((offset + c.start, mido.Message("control_change", channel=ch, control=c.cc, value=c.value)))
    return ev


def _tempo_track(song: Song) -> mido.MidiTrack:
    tr = mido.MidiTrack()
    tr.append(mido.MetaMessage("track_name", name=song.title, time=0))
    tr.append(mido.MetaMessage("time_signature", numerator=song.time_signature[0],
                               denominator=song.time_signature[1], time=0))
    tr.append(mido.MetaMessage("set_tempo", tempo=mido.bpm2tempo(song.tempo_bpm), time=0))
    tr.append(mido.MetaMessage("end_of_track", time=0))
    return tr


def write_parts(song: Song, tracks: dict[str, list[tuple[int, mido.Message]]], path: str | Path) -> Path:
    mid = mido.MidiFile(type=1, ticks_per_beat=PPQ)
    mid.tracks.append(_tempo_track(song))
    for name, ev in tracks.items():
        mid.tracks.append(_track(name, ev))
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    mid.save(path)
    return path


def export_part(song: Song, part: Part, path: str | Path) -> Path:
    return write_parts(song, {part.role.title(): _part_events(part)}, path)


def export_section(song: Song, parts: list[Part], path: str | Path) -> Path:
    return write_parts(song, {p.role.title(): _part_events(p) for p in parts}, path)


def export_song(song: Song, parts_by_section: dict[str, list[Part]], path: str | Path) -> Path:
    tracks: dict[str, list[tuple[int, mido.Message]]] = {}
    offset = 0
    for sec in song.sections:
        for p in parts_by_section.get(sec.id, []):
            tracks.setdefault(p.role.title(), []).extend(_part_events(p, offset))
        offset += section_ticks(sec)
    return write_parts(song, tracks, path)


def safe_name(text: str) -> str:
    return re.sub(r"[^A-Za-z0-9඀-෿_-]+", "", text) or "Part"


def part_filename(section_name: str, role: str) -> str:
    return f"{safe_name(section_name)}_{role.title()}.mid"
