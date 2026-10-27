"""Chord sheet -> Song (spec 7.2). Auto-detects and mixes the four supported formats."""
from __future__ import annotations

import re

from ..models import Bar, ChordSlot, Section, Song
from ..theory.key import detect_key
from . import labels
from .chords import ChordParseError, is_no_chord, parse_chord

_META_RE = re.compile(r"^\s*(title|key|tempo|bpm|time|capo)\s*[:=]\s*(.+?)\s*$", re.I)
_KEY_RE = re.compile(r"^([A-G][#b]?)\s*(m|min|minor|major|maj)?$", re.I)
_BEATS_RE = re.compile(r"^(.+?)\((\d+(?:\.\d+)?)\)$")
_BRACKET_RE = re.compile(r"\[([^\]]*)\]")
_SINHALA_RE = re.compile(r"[඀-෿]")


def _beats_per_bar(ts: tuple[int, int]) -> float:
    num, den = ts
    return num * 4 / den if den != 4 else float(num)


def _norm_symbol(token: str, loc: str, warnings: list[str]) -> str | None:
    """Canonical symbol, 'N.C.', '%' or None when token is not a chord."""
    if token == "%":
        return "%"
    if is_no_chord(token):
        return "N.C."
    local: list[str] = []
    try:
        chord = parse_chord(token, local)
    except ChordParseError:
        return None
    warnings.extend(f"{loc}: {w}" for w in local)
    return chord.symbol


def _split_header(line: str) -> tuple[str, str | None, str, str] | None:
    """Return (kind, number, raw_label, rest_of_line) if line is a section header."""
    s = line.strip()
    if not s or len(s) > 60:
        return None
    wrapped = re.match(r"^[\[(]([^\[\]()]+)[\])]\s*(.*)$", s)
    if wrapped:
        head, rest = wrapped.group(1), wrapped.group(2)
    else:
        m = re.match(r"^(.*?)(?:\s*[:–]\s*|\s+-\s+|\s*-$)(.*)$", s)
        head, rest = (m.group(1), m.group(2)) if m else (s, "")
    head = head.strip().rstrip(":")
    nm = re.match(r"^(.*?)\s*(\d+)?$", head)
    raw, num = nm.group(1), nm.group(2)
    kind = labels.lookup(raw)
    if kind is None:
        return None
    return kind, num, raw, rest.strip()


def _parse_cell(cell: str, bar_beats: float, loc: str, warnings: list[str]) -> list[ChordSlot] | None:
    tokens = cell.split()
    if not tokens:
        return []
    parsed: list[tuple[str, float | None]] = []
    for t in tokens:
        beats = None
        m = _BEATS_RE.match(t)
        if m and _norm_symbol(m.group(1), loc, []) is not None:
            t, beats = m.group(1), float(m.group(2))
        sym = _norm_symbol(t, loc, warnings)
        if sym is None:
            return None
        parsed.append((sym, beats))
    fixed = sum(b for _, b in parsed if b)
    free = [i for i, (_, b) in enumerate(parsed) if not b]
    share = (bar_beats - fixed) / len(free) if free else 0
    if free and share <= 0:
        warnings.append(f"{loc}: explicit beats exceed the bar; split evenly")
        fixed, share, parsed = 0, bar_beats / len(parsed), [(s, None) for s, _ in parsed]
    return [ChordSlot(symbol=s, beats=b or share) for s, b in parsed]


def _bars_from_chords(syms: list[str], bar_beats: float, loc: str, warnings: list[str]) -> list[list[ChordSlot]]:
    if len(syms) > 4:
        warnings.append(f"{loc}: no bar lines, assumed 2 chords per bar; confirm in chord grid")
        step = 2
    else:
        warnings.append(f"{loc}: no bar lines, assumed 1 chord per bar; confirm in chord grid")
        step = 1
    bars = []
    for i in range(0, len(syms), step):
        group = syms[i:i + step]
        bars.append([ChordSlot(symbol=s, beats=bar_beats / len(group)) for s in group])
    return bars


def parse_sheet(text: str, title: str | None = None) -> Song:
    warnings: list[str] = []
    song = Song(title=title or "Untitled")
    song.warnings = warnings  # keep one shared list (pydantic copies on init)
    song.language = "si" if _SINHALA_RE.search(text) else "en"
    key_meta: str | None = None
    sections: list[Section] = []
    kind_count: dict[str, int] = {}
    cur: Section | None = None
    cur_lyrics: list[str | None] = []

    def start_section(kind: str, raw: str, num: str | None) -> None:
        nonlocal cur, cur_lyrics
        finish()
        n = kind_count[kind] = kind_count.get(kind, 0) + 1
        name = labels.canonical_name(kind, raw) + (f" {num}" if num else "")
        cur = Section(id=f"sec_{kind}_{n}", name=name, kind=kind)  # type: ignore[arg-type]
        cur_lyrics = []

    def finish() -> None:
        if cur is not None and cur.bars:
            cur.lyrics = cur_lyrics if any(cur_lyrics) else None
            sections.append(cur)

    def add_bars(bars: list[list[ChordSlot]], lyrics: list[str | None]) -> None:
        nonlocal cur
        if cur is None:
            start_section("other", "Section", None)
            cur.name = "Section 1"  # type: ignore[union-attr]
        for b, ly in zip(bars, lyrics):
            cur.bars.append(Bar(chords=b))  # type: ignore[union-attr]
            cur_lyrics.append(ly)

    def resolve_repeats(bars: list[list[ChordSlot]]) -> list[list[ChordSlot]]:
        out = []
        for b in bars:
            if len(b) == 1 and b[0].symbol == "%":
                prev = out[-1] if out else (cur.bars[-1].chords if cur and cur.bars else None)
                if prev is None:
                    warnings.append("'%' with no previous bar ignored")
                    continue
                b = [s.model_copy() for s in prev]
            out.append(b)
        return out

    lines = text.splitlines()
    i = 0
    bar_beats = _beats_per_bar(song.time_signature)

    def apply_meta(k: str, v: str) -> None:
        nonlocal key_meta, bar_beats
        k = k.lower()
        if k == "title":
            song.title = title or v
        elif k == "key":
            key_meta = v
        elif k in ("tempo", "bpm"):
            try:
                song.tempo_bpm = float(re.sub(r"[^\d.]", "", v))
            except ValueError:
                warnings.append(f"Could not read tempo {v!r}")
        elif k == "time":
            m = re.match(r"^(\d+)\s*/\s*(\d+)$", v)
            if m:
                song.time_signature = (int(m.group(1)), int(m.group(2)))
                bar_beats = _beats_per_bar(song.time_signature)
            else:
                warnings.append(f"Could not read time signature {v!r}")
        elif k == "capo":
            try:
                song.capo = int(v)
                warnings.append(f"Capo {song.capo}: chords are shapes; sounding key is {song.capo} semitones higher")
            except ValueError:
                warnings.append(f"Could not read capo {v!r}")

    def handle(line: str, lineno: int, lookahead: list[str]) -> int:
        """Process one content line; return number of extra lines consumed."""
        loc = f"Line {lineno}"
        stripped = line.strip()
        if not stripped:
            return 0
        hdr = _split_header(stripped)
        if hdr:
            kind, num, raw, rest = hdr
            start_section(kind, raw, num)
            return handle(rest, lineno, lookahead) if rest else 0
        # bar notation
        if "|" in stripped:
            cells = [c.replace(":", " ") for c in stripped.split("|")]
            bars: list[list[ChordSlot]] = []
            ok = True
            for c in cells:
                slots = _parse_cell(c, bar_beats, loc, warnings)
                if slots is None:
                    ok = False
                    break
                if slots:
                    bars.append(slots)
            if ok and bars:
                bars = resolve_repeats(bars)
                add_bars(bars, [None] * len(bars))
                return 0
        # inline brackets
        groups = _BRACKET_RE.findall(stripped)
        if groups:
            syms = [_norm_symbol(g.strip(), loc, warnings) for g in groups]
            if all(s is not None for s in syms):
                parts = _BRACKET_RE.split(stripped)  # lead, chord, seg, chord, seg ...
                segs = [p.strip() or None for p in parts[2::2]]
                bars = _bars_from_chords(syms, bar_beats, loc, warnings)  # type: ignore[arg-type]
                step = 2 if len(syms) > 4 else 1
                lyr = []
                for j in range(0, len(syms), step):
                    joined = " ".join(s for s in segs[j:j + step] if s)
                    lyr.append(joined or None)
                bars = resolve_repeats(bars)
                add_bars(bars, lyr[: len(bars)])
                return 0
        # chords over lyrics (chord-only line)
        tokens = stripped.split()
        syms = [_norm_symbol(t, loc, warnings) for t in tokens]
        if tokens and all(s is not None for s in syms):
            bars = resolve_repeats(_bars_from_chords(syms, bar_beats, loc, warnings))  # type: ignore[arg-type]
            lyric = None
            consumed = 0
            if lookahead:
                nxt = lookahead[0].strip()
                if nxt and not _META_RE.match(nxt) and not _split_header(nxt) and "|" not in nxt \
                        and not all(_norm_symbol(t, loc, []) is not None for t in nxt.split()):
                    lyric, consumed = nxt, 1
            add_bars(bars, [lyric] + [None] * (len(bars) - 1))
            return consumed
        return 0  # plain lyric / unknown text

    while i < len(lines):
        raw = lines[i]
        m = _META_RE.match(raw)
        if m:
            apply_meta(m.group(1), m.group(2))
            i += 1
            continue
        i += 1 + handle(raw, i + 1, lines[i + 1:i + 2])
    finish()
    song.sections = sections

    if key_meta:
        km = _KEY_RE.match(key_meta.strip())
        if km:
            song.key = km.group(1)[0].upper() + km.group(1)[1:]
            song.mode = "minor" if (km.group(2) or "").lower() in ("m", "min", "minor") else "major"
        else:
            warnings.append(f"Could not read key {key_meta!r}")
    if song.key is None:
        pairs = []
        for s in sections:
            for b in s.bars:
                for c in b.chords:
                    if c.symbol != "N.C.":
                        pairs.append((parse_chord(c.symbol), c.beats))
        if pairs:
            tonic, mode, conf = detect_key(pairs)
            song.key, song.mode = tonic, mode  # type: ignore[assignment]
            warnings.append(f"Key not specified; detected {tonic} {mode} (confidence {conf:.2f})")
    return song
