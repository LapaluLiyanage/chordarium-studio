# Chordarium Studio — End-to-End Build Specification

> **For Claude Code.** Put this file at the repo root as `CLAUDE.md` (or keep the name and reference it from `CLAUDE.md`).
> Work **milestone by milestone** (section 14). Do not start a milestone until the previous milestone's acceptance criteria pass.
> UI details live in `CHORDARIUM_STUDIO_UI.md`. Read both before writing code.

---

## 1. Product summary

Chordarium Studio is a **VST3 plugin + local companion service** that turns a **chord sheet** and a **plain-language brief** into a **multi-track MIDI arrangement** (piano, bass, pad, drums) inside a DAW. Cubase 15 is the launch DAW.

Example brief: *"Add the first chorus on grand piano, soft, with a bass line, harmony pad and light drums."*

Core principles:

1. **AI plans, rules write notes.** The language model only produces a small JSON *arrangement plan*. Deterministic rule-based generators turn the plan into exact, playable MIDI. This keeps output musical, editable, cheap, and works with small free models.
2. **Plugin-first, not DAW-API-first.** Cubase's MIDI Remote API cannot create tracks or load plugins. So the plugin hosts instruments itself, previews parts, and hands MIDI to Cubase by drag-and-drop or "print to tracks". The MIDI Remote script is only used for extras (transport, markers).
3. **Bring your own AI.** No developer-paid API key. Supported providers:
   - MCP clients: **Claude Desktop, Claude Code, LM Studio** (they call our MCP tools)
   - **Ollama** (local) and **OpenAI-compatible free-tier keys** (Gemini, Groq, OpenRouter, Mistral) via an in-plugin chat panel
   - **Rules only** (no AI) as a guaranteed fallback
4. **Sinhala + English** chord sheets are first-class.

Out of scope for the core: live audio-to-MIDI from non-MIDI keyboards. That is a later **add-on** (section 18).

---

## 2. Non-negotiable rules for Claude Code

- **Git authorship:** every commit is authored as **Lapalu Liyanage** only.
  - Run once: `git config user.name "Lapalu Liyanage"` and `git config user.email "lapaluliyanage@gmail.com"`.
  - **Never** add `Co-Authored-By:` lines, "Generated with Claude Code" footers, or any Claude/session trailers to commit messages.
  - Use Conventional Commits: `feat(engine): add bass root-fifth pattern`.
- **Never commit secrets.** API keys live only in the OS user config dir (section 9.4). Add `.env*`, `*.key`, `token` to `.gitignore`.
- **Localhost only.** Every server binds to `127.0.0.1`, never `0.0.0.0`. All local calls carry the shared token (section 9.4).
- **Tests first for the engine.** Each generator and the parser get unit tests before integration.
- **Small PRs per milestone task.** Keep `main` buildable.
- **Ask before** adding a dependency with a non-permissive licence (GPL/AGPL) or any paid SDK.
- **Verify, don't assume:** where this spec marks something **[VERIFY]**, check the current official docs before implementing, and record the finding in `docs/decisions/`.

---

## 3. Development environment (target machine)

- Windows 11, 16 GB RAM, NVIDIA MX550 (laptop). Keep the plugin light: no GPU needs, no heavy ML in the core path.
- **C++:** Visual Studio 2022 (Desktop C++ workload), CMake ≥ 3.25, Ninja.
- **JUCE 8** fetched with CMake `FetchContent` (pin a release tag). **[VERIFY]** current JUCE licence terms (JUCE 8 is dual-licensed; confirm the free tier fits a student/indie product) and the Steinberg VST3 SDK licence.
- **Python 3.11+** managed with **uv**.
- **Node 20 LTS** + **pnpm** for the UI.
- **loopMIDI** (virtual MIDI ports on Windows).
- **Cubase 15** for testing; **pluginval** for plugin validation.
- Optional for AI testing: Claude Desktop, LM Studio, Ollama.

---

## 4. Architecture

```
┌──────────────────────────── User's computer ─────────────────────────────┐
│                                                                          │
│  Claude Desktop / Claude Code / LM Studio                                │
│        │ MCP (stdio)                                                     │
│        ▼                                                                 │
│  chordarium-mcp  (thin MCP adapter, Python)                              │
│        │ HTTP + token                                                    │
│        ▼                                                                 │
│  chordarium-core  (Python service, 127.0.0.1:47811)  ◀── Ollama / BYOK   │
│   • session state (song, plan, parts)        AI provider client          │
│   • chord sheet parser   • arrangement engine (rules → MIDI)             │
│   • tool-calling loop for in-plugin chat     • MIDI file export          │
│   • MIDI out to loopMIDI ("Chordarium Remote") for Cubase transport      │
│        │ WebSocket + token                                               │
│        ▼                                                                 │
│  Chordarium Studio VST3 (JUCE 8, inside Cubase)                          │
│   • WebView UI (React)   • preview playback synced to host transport     │
│   • built-in GM sounds   • hosted VST3 instruments per part role         │
│   • MIDI output (print to tracks)   • drag MIDI files into Cubase        │
│        │                                                                 │
│        ▼                                                                 │
│  Cubase 15  ◀── MIDI Remote script (listens on "Chordarium Remote" port) │
└──────────────────────────────────────────────────────────────────────────┘
```

### 4.1 Responsibilities

| Component | Language | Owns |
| --- | --- | --- |
| `engine` | Python package | Parsing, music theory, plan validation, part generators, MIDI writing. Pure functions, no I/O. |
| `core` | Python (FastAPI + websockets) | Session state, REST/WS API, AI providers + tool loop, file export, MIDI Remote messages. The hub. |
| `mcp` | Python (official `mcp` SDK, FastMCP) | Exposes core features as MCP tools. Stateless; forwards to core. |
| `plugin` | C++ (JUCE 8) | Audio/MIDI, playback, instrument hosting, WebView host, drag-and-drop, state save. Thin: no music logic. |
| `ui` | TypeScript (React + Vite) | All screens. Runs inside the plugin WebView and in a browser (dev mode). |
| `cubase` | JavaScript (MIDI Remote API) | Maps CC messages from `Chordarium Remote` port to transport/markers. |

### 4.2 Process lifecycle

- The plugin starts `chordarium-core` if it is not running (bundled exe, section 16), then connects by WebSocket. If core is down, the UI shows a reconnect banner; preview of the last committed parts still works from plugin state.
- Claude Desktop starts `chordarium-mcp` via its config; `chordarium-mcp` connects to core over HTTP. If core is not running, MCP tools return a clear error: "Open Chordarium Studio in your DAW first."
- One core instance serves one active session. Multiple plugin instances: the first opened is "primary"; others show read-only state (MVP).

---

## 5. Repository layout

```
chordarium-studio/
├── CLAUDE.md                      # this spec (or pointer to it)
├── CHORDARIUM_STUDIO_UI.md
├── docs/
│   ├── decisions/                 # ADRs, [VERIFY] findings, spike results
│   └── user-guide/
├── engine/                        # Python package: chordarium_engine
│   ├── pyproject.toml
│   ├── src/chordarium_engine/
│   │   ├── models.py              # pydantic models (section 6)
│   │   ├── parser/                # chord sheet parsing
│   │   │   ├── chords.py          # chord symbol grammar
│   │   │   ├── sheet.py           # sheet → Song
│   │   │   └── labels.py          # section label dictionary (EN + SI)
│   │   ├── theory/                # pitch, chord tones, voicings, voice leading
│   │   ├── generators/            # piano.py bass.py pad.py drums.py common.py
│   │   ├── styles/                # *.yaml style templates
│   │   ├── humanize.py
│   │   ├── midi_export.py
│   │   └── cli.py
│   └── tests/
│       ├── fixtures/sheets/       # sample chord sheets (EN + SI)
│       └── golden/                # expected note lists (JSON)
├── core/                          # Python package: chordarium_core
│   ├── src/chordarium_core/
│   │   ├── app.py                 # FastAPI app + WS
│   │   ├── session.py
│   │   ├── tools.py               # single source of tool definitions
│   │   ├── ai/                    # providers/, prompts.py, loop.py, fallback.py
│   │   ├── remote.py              # MIDI out to loopMIDI
│   │   └── config.py
│   └── tests/
├── mcp/                           # Python package: chordarium_mcp
│   └── src/chordarium_mcp/server.py
├── plugin/                        # JUCE 8 VST3
│   ├── CMakeLists.txt
│   ├── Source/
│   │   ├── PluginProcessor.*      # audio + MIDI
│   │   ├── PluginEditor.*         # WebView host
│   │   ├── CoreConnection.*       # WebSocket client
│   │   ├── Playback.*             # note scheduling, transport sync
│   │   ├── BuiltInSynth.*         # GM SoundFont player
│   │   ├── PluginHost.*           # hosted VST3 per role
│   │   ├── MidiDrag.*             # external file drag
│   │   └── NativeBridge.*         # WebView native functions/events
│   └── Resources/                 # fonts, soundfont, ui bundle
├── ui/                            # React app (see UI spec)
├── cubase/
│   └── MIDI Remote/ChordariumStudio/Chordarium_Studio.js
├── installer/                     # Inno Setup script, PyInstaller specs
└── scripts/                       # dev helpers (run-all.ps1, build.ps1)
```

---

## 6. Data models (pydantic in `engine/models.py`; mirror as TS types in `ui/src/types.ts`)

Timing unit: **ticks, PPQ = 480**. Bars and beats derive from the time signature.

### 6.1 Song

```json
{
  "id": "song_01",
  "title": "Sanda Eliya",
  "key": "G",
  "mode": "major",
  "tempo_bpm": 76,
  "time_signature": [4, 4],
  "language": "si",
  "sections": [
    {
      "id": "sec_chorus_1",
      "name": "Chorus 1",
      "kind": "chorus",
      "bars": [
        { "chords": [ { "symbol": "G",  "beats": 4 } ] },
        { "chords": [ { "symbol": "Em", "beats": 2 }, { "symbol": "C", "beats": 2 } ] }
      ],
      "lyrics": ["optional lyric line per bar or null"]
    }
  ],
  "warnings": ["Bar 7: 'Gsus' read as Gsus4"]
}
```

Section `kind` enum: `intro | verse | pre_chorus | chorus | bridge | interlude | solo | outro | other`.

### 6.2 Arrangement plan (what the AI produces)

```json
{
  "section_id": "sec_chorus_1",
  "style": "sinhala_ballad",
  "feel": "straight",
  "dynamics": "soft",
  "parts": [
    { "role": "piano", "pattern": "arpeggio_up", "density": 0.4, "velocity": [40, 60], "register": "mid", "instrument": "grand_piano" },
    { "role": "bass",  "pattern": "root_fifth",  "density": 0.5, "velocity": [55, 70], "register": "low", "instrument": "finger_bass" },
    { "role": "pad",   "pattern": "sustain",     "density": 0.2, "velocity": [35, 50], "register": "mid_high", "instrument": "warm_pad" },
    { "role": "drums", "pattern": "ballad_light","density": 0.3, "velocity": [45, 75], "fills": "end_of_section" }
  ],
  "notes": "free text the AI may add; ignored by generators"
}
```

Rules:

- `role` ∈ `piano | bass | pad | drums` (MVP). Unknown roles are rejected.
- `pattern` must be in the role's pattern list for the chosen style (`GET /styles`). Unknown pattern → validation error, AI is asked to fix it once, then rules pick the style default.
- `density` 0–1, `velocity` [min,max] within 1–127, `register` ∈ `low | mid_low | mid | mid_high | high`.
- Optional per part: `seed` (int), `locked` (bool), `variation` (0–1).

### 6.3 Part (generated output)

```json
{
  "id": "part_sec_chorus_1_piano",
  "section_id": "sec_chorus_1",
  "role": "piano",
  "channel": 1,
  "spec": { "...the PartSpec used...": true },
  "seed": 1234,
  "locked": false,
  "notes": [ { "pitch": 55, "start": 0, "duration": 900, "velocity": 52 } ]
}
```

MIDI channel map (for print-to-tracks): piano 1, bass 2, pad 3, drums 10.

### 6.4 Style template (`engine/styles/*.yaml`)

```yaml
id: sinhala_ballad
name: Sinhala Ballad
time_signatures: [[4,4], [6,8]]
tempo_range: [60, 90]
defaults:
  piano: { pattern: arpeggio_up, density: 0.4, velocity: [40, 62], register: mid }
  bass:  { pattern: root_fifth,  density: 0.5, velocity: [55, 72], register: low }
  pad:   { pattern: sustain,     density: 0.2, velocity: [35, 50], register: mid_high }
  drums: { pattern: ballad_light, density: 0.3, velocity: [45, 75] }
patterns:
  piano: [block, broken, arpeggio_up, arpeggio_updown, ballad_comp]
  bass:  [root, root_fifth, root_octave, walking_lite]
  pad:   [sustain, swell]
  drums: [ballad_light, pop_basic, half_time]
```

Ship starter styles: `pop_4_4`, `sinhala_ballad`, `baila_6_8`, `gospel_ballad`, `lofi`, `bollywood_pop`. Mark them **starter templates**; they will be refined with musicians (Fastunes) during evaluation.

---

## 7. Engine specification (`engine/`)

### 7.1 Chord symbol grammar (`parser/chords.py`)

- Root: `[A-G]` + optional `#` or `b`.
- Quality/extensions (case-sensitive where it matters): `m`, `min`, `-`, `maj`, `M`, `maj7`, `M7`, `7`, `m7`, `mMaj7`, `dim`, `°`, `dim7`, `m7b5`, `ø`, `aug`, `+`, `sus2`, `sus4`, `sus` (→ sus4), `add9`, `add11`, `6`, `m6`, `9`, `m9`, `maj9`, `11`, `13`, `7b9`, `7#9`, `7#11`, `7b13`.
- Slash bass: `/[A-G][#b]?`.
- Also accept `N.C.` (no chord) and `%` (repeat previous bar).
- Output: root pitch class, bass pitch class, interval set, canonical symbol.
- **Reuse Chordarium's vocabulary** (repo `LapaluLiyanage/Chordarium`, `server/theory/chord.py` and `client/src/theory/chord.ts`): 12 roots (sharp spelling `C C# D D# E F F# G G# A A# B`, flats accepted) × qualities `maj, min, dim, aug, min6, maj6, min7, minmaj7, maj7, 7, dim7, hdim7 (m7b5), sus2, sus4`; the recognizer's 144 templates use 12 of these (`maj min 7 maj7 min7 dim dim7 hdim7 aug sus2 sus4 min6`). Internal key format is `ROOT:quality` (e.g. `F#:min7`) plus optional bass. Clone the repo read-only to `../chordarium` and port the chord-parsing tests (`shared/chord_cases.json`) so both projects agree; Studio adds the extensions above (`add9`, `9`, `11`, `13`, alterations) on top without renaming existing qualities.
- Tests: ≥ 150 symbols incl. edge cases (`Bbmaj7/D`, `F#m7b5`, `Ebsus2`, `C/E`).

### 7.2 Sheet parser (`parser/sheet.py`)

Supported input formats (auto-detect, can mix):

1. **Chords over lyrics:** a chord-only line followed by a lyric line (Sinhala or English).
2. **Inline brackets:** `[G]Sanda [Em]eliya`.
3. **Bar notation:** `| G | Em C | D |` (each `|...|` is one bar; multiple chords split the bar evenly unless beats given like `Em(2) C(2)`).
4. **Section headers:** lines like `[Chorus]`, `Chorus 1:`, `VERSE`, `Intro -`, plus a configurable **Sinhala label dictionary** in `labels.py` (empty entries that Lapalu fills; do not invent Sinhala words).
5. Metadata lines: `Key: G`, `Tempo: 76`, `Time: 6/8`, `Capo: 2`.

Bar inference without bar lines: default **1 chord = 1 bar**; if a line has more than 4 chords, assume 2 beats each. Always add a `warnings` entry when inferring, so the UI can ask the user to confirm in the chord grid.

Key detection if missing: score major/minor keys by chord-root fit (Krumhansl-style weights on chord tones); return best key + confidence.

Photo/PDF input (v1, not MVP): PDF text via `pypdf`; images via OCR (**[VERIFY]** Tesseract `sin` language support and quality; if poor, MVP accepts text only and photo import is marked beta).

### 7.3 Theory (`theory/`)

- Pitch helpers, chord tones from interval sets, scale degrees.
- **Voicing generator:** for a chord, produce candidate voicings (3–5 notes) within a register range, closed and open, all inversions.
- **Voice leading:** choose the candidate minimizing `Σ|movement|` vs the previous voicing, with penalties for: top voice jumps > 4 semitones, parallel fifths/octaves between outer voices, notes below the register floor. Deterministic given seed.
- Register ranges (MIDI): low 28–52, mid_low 40–60, mid 48–72, mid_high 55–79, high 64–88.

### 7.4 Generators (`generators/`)

All generators: `generate(section, spec, style, seed) -> list[NoteEvent]`. Deterministic for the same inputs + seed. Density 0–1 scales note count (e.g., arpeggio subdivision 8ths at ≥0.5, quarters below).

- **Piano:** `block` (chord on beat 1, held), `broken` (bass note then upper voicing), `arpeggio_up`, `arpeggio_updown`, `ballad_comp` (beats 1 and 3 with anticipation). Uses voice leading.
- **Bass:** `root`, `root_fifth`, `root_octave`, `walking_lite` (chromatic/diatonic approach note on the last 8th before chord change). Slash chords use the slash bass.
- **Pad:** `sustain` (whole chord duration, smooth voicing, legato overlap 20 ticks), `swell` (velocity ramp across the bar using CC11 expression events).
- **Drums:** 16-step grids (12-step for 6/8) per pattern in the style YAML, GM map: kick 36, snare 38, rim 37, closed hat 42, pedal hat 44, open hat 46, crash 49, ride 51, low tom 45, high tom 50. `fills`: `none | end_of_section | every_4_bars`. Crash on bar 1 of chorus when dynamics ≥ medium.
- **Humanize (`humanize.py`):** timing jitter ±8 ticks (not on drums kick/snare grid at density < 0.3), velocity jitter ±6, clamp to spec velocity range. Seeded.

### 7.5 MIDI export (`midi_export.py`)

- Use `mido` (MIT). Type-1 MIDI file, PPQ 480, tempo + time signature meta, one track per part, track names `Piano`, `Bass`, `Pad`, `Drums`.
- Export modes: per part (one file each, for drag-and-drop), per section (all parts), whole song.
- Files go to `%APPDATA%/ChordariumStudio/exports/<session>/` with readable names: `Chorus1_Piano.mid`.

### 7.6 CLI (`cli.py`)

```
chordarium-studio parse sheet.txt              # prints Song JSON
chordarium-studio arrange sheet.txt --section "Chorus 1" --style sinhala_ballad --out out.mid
chordarium-studio styles                        # lists styles + patterns
```

---

## 8. AI layer (`core/ai/`)

### 8.1 Provider interface

```python
class Provider(Protocol):
    name: str
    async def chat(self, messages: list[dict], tools: list[dict]) -> ChatResult: ...
    async def health(self) -> ProviderHealth: ...
```

Implementations:

- `OpenAICompatibleProvider(base_url, api_key, model)` — covers **Ollama** (`http://127.0.0.1:11434/v1`), **LM Studio** server (`http://127.0.0.1:1234/v1`), **Gemini**, **Groq**, **OpenRouter**, **Mistral** (each via their OpenAI-compatible endpoint). **[VERIFY]** each base URL and tool-calling support at implementation time; keep URLs in config, not code.
- `RulesOnlyProvider` — no network; maps keywords to plan edits (section 8.5).
- MCP clients (Claude Desktop/Code, LM Studio MCP) do **not** go through this layer: they call MCP tools directly and act as the planner themselves.

### 8.2 Tool definitions — single source of truth

Define tools once in `core/tools.py` (name, description, JSON schema, handler). Generate:
- the **MCP tool list** (`mcp` package imports them),
- the **OpenAI function-calling schema** for in-plugin chat,
so both paths behave identically.

### 8.3 System prompt (in-plugin chat; also used as MCP server instructions)

```
You are the arranging assistant inside Chordarium Studio, a music plugin.
You never write MIDI notes yourself. You call tools.
To arrange, call get_session to read the song, then call arrange with a plan
that follows the plan schema exactly. Use only styles and patterns returned by
list_styles. Keep velocities musical: soft 35-65, medium 55-90, loud 80-115.
For edits ("busier bass", "remove drums in bar 4"), call edit_part or
regenerate_part on the affected part only, and never touch locked parts.
If the request is unclear, ask one short question.
Reply to the user in one or two sentences after tools finish.
```

### 8.4 Loop + validation (`loop.py`)

- Max 6 tool calls per user message. Timeout 60 s per provider call.
- Validate every plan with pydantic. On error: send the validation message back once ("fix these fields"). Second failure → apply style defaults and tell the user "I used the style's default for X".
- Small local models: if the provider reports no tool support, switch to **JSON mode**: ask for the plan JSON only, parse, validate, apply.

### 8.5 Rules-only fallback (`fallback.py`)

Keyword → change map, applied to the selected section/part:

| Phrase contains | Change |
| --- | --- |
| soft, gentle, quiet | velocity −15, density −0.15 |
| loud, powerful, big | velocity +15, density +0.15 |
| busier, more movement | density +0.25 |
| simpler, less | density −0.25 |
| remove/no drums | mute drums part |
| add fill | drums.fills = end_of_section |
| higher / lower | register up / down one step |

Unknown phrases → reply: "Without an AI connected I can do: softer, louder, busier, simpler, add fill, remove a part."

---

## 9. Core service (`core/`)

FastAPI on `127.0.0.1:47811` (configurable). JSON everywhere.

### 9.1 REST

| Method & path | Purpose |
| --- | --- |
| `GET /health` | `{status, version, provider, cubase_remote: bool}` |
| `GET /session` | Song + plans + parts summary |
| `POST /song/parse` | `{text, title?}` → Song (+ warnings); replaces session song |
| `PATCH /song` | Edit chords/sections from the chord grid |
| `GET /styles` | Styles and patterns |
| `POST /arrange` | `{section_ids, plan?}` → parts (plan optional: style defaults) |
| `POST /parts/{id}/edit` | Partial PartSpec changes → regenerated part |
| `POST /parts/{id}/regenerate` | New seed |
| `POST /parts/{id}/lock` | `{locked: bool}` |
| `POST /export` | `{scope: part|section|song, ids}` → file paths |
| `POST /chat` | `{message}` → streams assistant reply + tool events (in-plugin chat) |
| `GET/PUT /config` | Provider settings (keys stored outside repo) |
| `POST /remote/{action}` | `play | stop | record | to_start | add_marker` → MIDI Remote |

### 9.2 WebSocket `/ws`

Server → client events: `session.updated`, `part.updated`, `chat.delta`, `chat.tool`, `chat.done`, `provider.status`, `error`.
Client → server: `hello {client: "plugin"|"ui", token}`, `preview.request {section_id}`.

### 9.3 Session persistence

- Session JSON saved to `%APPDATA%/ChordariumStudio/sessions/<id>.json` on every change (debounced 500 ms).
- The plugin stores the **session id + a full snapshot** in its DAW state (`getStateInformation`) so a Cubase project reopens with the same song and parts even if the core lost its file.

### 9.4 Config & secrets

- Config file: `%APPDATA%/ChordariumStudio/config.json` (provider, model, base URL, port).
- API keys: Windows Credential Manager via `keyring`; never in config JSON or logs.
- Local auth token: random 32 bytes generated on first run, stored in `%APPDATA%/ChordariumStudio/token`; required header `X-Chordarium-Token` (REST) and in WS `hello`.

### 9.5 MIDI Remote output (`remote.py`)

- `python-rtmidi` opens output port **"Chordarium Remote"** (created by the user in loopMIDI; the setup screen checks for it).
- Message map (channel 16, CC): 20 play, 21 stop, 22 record, 23 to start, 24 add marker. Value 127 = trigger.

---

## 10. MCP server (`mcp/`)

Built with the official Python `mcp` SDK (`FastMCP`), stdio transport. Server name `chordarium-studio`. Instructions = system prompt from 8.3.

Tools (all forward to core):

| Tool | Args | Returns |
| --- | --- | --- |
| `get_session` | — | Song summary (sections, bars, chords, key, tempo) + parts status |
| `load_chord_sheet` | `text`, `title?` | Parsed song + warnings |
| `list_styles` | — | Styles with allowed patterns per role |
| `arrange` | `section_ids[]`, `plan` (schema 6.2) | Parts summary (note counts, ranges) |
| `edit_part` | `section_id`, `role`, `changes` | Updated part summary |
| `regenerate_part` | `section_id`, `role`, `seed?` | Updated part summary |
| `set_part_lock` | `section_id`, `role`, `locked` | ok |
| `export_midi` | `scope`, `ids?` | File paths + instruction "drag from the plugin or import these files" |
| `transport` | `action` | ok / "Cubase link not set up" |

Claude Desktop config snippet for the user guide (Windows):

```json
{
  "mcpServers": {
    "chordarium-studio": {
      "command": "C:\\Program Files\\Chordarium Studio\\chordarium-mcp.exe"
    }
  }
}
```

LM Studio: same server added in its MCP settings. **[VERIFY]** current LM Studio `mcp.json` format.

---

## 11. Plugin (`plugin/`, JUCE 8)

### 11.1 Plugin type

- VST3 **instrument**, stereo out, **produces MIDI** (event output bus) for print-to-tracks.
- Name "Chordarium Studio", manufacturer "Chordarium", 4-char codes set once and never changed.
- **Spike S1 (M0) must confirm** Cubase 15 can route this plugin's MIDI output to other MIDI tracks. If not, fall back to drag-and-drop + "export to folder" only, and record it in `docs/decisions/`.

### 11.2 Playback (`Playback.*`)

- Receives parts (note lists) from core over WebSocket, converts ticks → host PPQ.
- **Synced mode:** follows `AudioPlayHead` position; section placed at a user-chosen bar (default: Cubase cycle/left locator if available, else bar 1).
- **Free mode:** loops the selected section with its own clock (for auditioning while Cubase is stopped).
- Per-role mute/solo/volume. All scheduling sample-accurate in `processBlock`, lock-free FIFO from message thread to audio thread. No allocation on the audio thread.

### 11.3 Sounds

- **Built-in:** a GM SoundFont player using **TinySoundFont** (MIT, single header) and a small permissively licensed GM SoundFont. **[VERIFY]** the SoundFont's licence allows redistribution (candidate: GeneralUser GS). Keep total size < 40 MB.
- **Hosted instruments (v1):** one slot per role. Use `AudioPluginFormatManager` + `KnownPluginList` (VST3 only), scan on demand in a background thread, show plugin UIs in separate windows. Save hosted plugin state inside our state chunk. Kontakt is the main test target.

### 11.4 Getting MIDI into Cubase (two paths)

1. **Drag-and-drop (MVP):** export the part to a temp `.mid`, then `DragAndDropContainer::performExternalDragDropOfFiles`. Because the UI is a WebView, the drag starts from a **native JUCE drag handle overlay** positioned over each part row (WebView reports row rects via a native event). **Spike S3** confirms Cubase accepts it.
2. **Print to tracks (v1):** plugin plays the section out of its MIDI output on channels 1/2/3/10; the user arms Cubase MIDI tracks whose input is "Chordarium Studio MIDI Out" filtered per channel and records. Provide a Cubase project template + track presets in `cubase/`.

### 11.5 WebView UI host (`PluginEditor.*`, `NativeBridge.*`)

- JUCE 8 `WebBrowserComponent` with native integration + resource provider serving the built UI bundle from binary data (no network needed). **[VERIFY]** exact JUCE 8 API names (`withNativeIntegrationEnabled`, `withResourceProvider`, `withNativeFunction`, event emitting) against the JUCE 8 docs and the JS helper shipped in `juce_gui_extra`.
- Windows WebView2 runtime: check at startup; if missing, show a native fallback message with the download link.
- Native functions exposed to JS: `getCoreConnection()` (port + token), `previewPlay(sectionId)`, `previewStop()`, `setRoleMix(role, {mute, solo, gain})`, `setSyncMode(mode)`, `openHostedPlugin(role)`, `scanPlugins()`, `assignPlugin(role, pluginId)`, `reportDragRects(rects)`, `getHostInfo()`.
- Native → JS events: `transport` (playing, ppq, bpm), `meter` (per role, 15 Hz max), `dragDone`, `pluginList`.
- Editor size: default 1100×720, resizable, min 900×600, remembers size.

### 11.6 State

`getStateInformation` writes JSON: version, session snapshot (song, plans, parts), mix, sync mode, hosted plugin descriptors + states (base64). `setStateInformation` restores and re-sends the snapshot to core.

### 11.7 Quality gates

- pluginval strictness level ≥ 5 passes.
- No audio-thread allocations or locks (verify with a debug allocation guard).
- CPU < 5 % on the target laptop with built-in sounds, 4 parts playing.

---

## 12. Cubase integration (`cubase/`)

### 12.1 MIDI Remote script

- Location (user install): `Documents\Steinberg\Cubase\MIDI Remote\Driver Scripts\Local\Chordarium\Studio\Chordarium_Studio.js`.
- Uses `midiremote_api_v1`: create driver ("Chordarium", "Studio"), one MIDI input bound to port **"Chordarium Remote"**, detection by port name.
- Bind CC 20–24 on channel 16 to transport start, stop, record, return to zero, add marker.
- **[VERIFY]** API calls against the API reference that ships with Cubase in the MIDI Remote folder; write the script against that, not from memory.
- Keep the script tiny and documented; it is optional (the product works without it).

### 12.2 Templates

- `cubase/templates/Chordarium_Studio_Starter.cpr` (created manually by Lapalu following a checklist in `docs/user-guide/cubase-setup.md`): one instrument track with Chordarium Studio, four MIDI tracks (Piano, Bass, Pad, Drums) with input = plugin MIDI out per channel, routed to the user's instruments.

---

## 13. UI

See `CHORDARIUM_STUDIO_UI.md`. Stack: React 18 + TypeScript + Vite + Tailwind CSS + Zustand. The UI talks to **core** over REST/WS and to the **plugin** through the JUCE native bridge. In browser dev mode, a mock bridge replaces native calls.

---

## 14. Milestones

Each milestone ends with: tests green, a short demo note in `docs/decisions/Mx-demo.md`, and a commit tagged `mx-done`.

### M0 — Feasibility spikes (gate for everything else)

| Spike | Pass condition |
| --- | --- |
| S1 VST3 MIDI out | A JUCE test instrument emits notes; a Cubase 15 MIDI track records them from the plugin's MIDI output |
| S2 WebView | JUCE 8 plugin loads a Vite-built React page from binary resources and calls one native function both ways |
| S3 External drag | Dragging a temp `.mid` from the plugin onto a Cubase track creates a MIDI part |
| S4 MIDI Remote | loopMIDI port "Chordarium Remote" + script: sending CC 20 starts Cubase playback |
| S5 MCP | A FastMCP hello-world server appears in Claude Desktop and its tool runs |
| S6 Local model | Ollama or LM Studio returns a valid tool call for a dummy tool on the target laptop |

Any failure → write the fallback decision before continuing.

### M1 — Engine (Python, no AI)

Tasks: models, chord grammar, sheet parser (4 formats), key detection, voicing + voice leading, 4 generators, humanize, MIDI export, CLI, 6 starter styles, fixtures (≥ 10 EN + ≥ 10 SI sheets provided by Lapalu).
Acceptance: `pytest` ≥ 90 % coverage on `engine`; `chordarium-studio arrange` produces a 4-track MIDI that opens in Cubase and sounds musically correct on 5 test songs (Lapalu listening check).

### M2 — Core service + MCP

Tasks: FastAPI app, session store, REST + WS, tool definitions, MCP server, config/token/keyring, export.
Acceptance: In Claude Desktop, "load this chord sheet and arrange the chorus as a soft ballad" produces parts in core and exported MIDI files; integration tests hit every endpoint.

### M3 — UI in browser dev mode

Tasks: all MVP screens from the UI spec against the real core and a mock plugin bridge; chord grid editing; part lanes with mini piano roll; chat panel wired to `/chat`.
Acceptance: full flow (paste sheet → fix chords → arrange → edit by chat → export) works in Chrome against core.

### M4 — Plugin MVP

Tasks: JUCE project, WebView host + bridge, core auto-start + connection, playback (synced + free), built-in SoundFont sounds, mix controls, state save/restore, native drag handles.
Acceptance: In Cubase 15 the full flow works inside the plugin; parts preview in sync with Cubase transport; drag a part to a track; reopen project restores everything; pluginval passes.

### M5 — AI providers + in-plugin chat

Tasks: OpenAI-compatible provider, Ollama/LM Studio/BYOK presets, JSON-mode fallback, rules-only provider, provider setup screen, health checks.
Acceptance: the same 5 briefs produce valid plans with Claude (MCP), one local model, one free-tier key, and rules-only.

### M6 — Hosted instruments + Cubase link

Tasks: plugin scanning/hosting per role, Kontakt test, print-to-tracks, MIDI Remote script, template + setup guide.
Acceptance: Kontakt piano plays the piano part inside the plugin; print-to-tracks records 4 parts into 4 Cubase tracks in one pass; transport tool works from Claude.

### M7 — Evaluation + polish (research)

Tasks: listening test kit (export 10 arrangements + human-made references, randomized order, rating form), parse-accuracy benchmark, timing metrics, bug bash, accessibility pass.
Acceptance: metrics from the proposal recorded in `docs/evaluation/`.

### M8 — Packaging & beta

Tasks: PyInstaller one-file exes for `chordarium-core` and `chordarium-mcp`; Inno Setup installer (VST3 to `C:\Program Files\Common Files\VST3`, exes to `C:\Program Files\Chordarium Studio`, MIDI Remote script copy option, WebView2 check); in-app first-run checklist; crash-safe logs in `%APPDATA%/ChordariumStudio/logs`.
Acceptance: clean Windows VM install → plugin appears in Cubase → full flow works without Python/Node installed.

### M9 (later) — Keyboard Input add-on

See section 18. Separate feature flag and licence.

---

## 15. Testing strategy

- **Engine:** unit tests per function; golden tests (note lists as JSON) per generator × pattern × time signature; property tests (Hypothesis) — no note outside register, all notes inside section length, velocities within range, determinism with seed.
- **Parser:** fixture sheets with expected Song JSON; fuzz with random whitespace/casing.
- **Core:** pytest + httpx AsyncClient; WS tests; fake provider that returns scripted tool calls.
- **MCP:** run server in-process with the SDK test client.
- **UI:** Vitest + Testing Library for components; Playwright for the browser-mode flow.
- **Plugin:** pluginval; Catch2 unit tests for tick/PPQ conversion and FIFO; manual Cubase checklist in `docs/qa/cubase-checklist.md`.
- **CI:** GitHub Actions on `windows-latest`: Python tests, UI tests + build, plugin build (no Cubase in CI).

---

## 16. Packaging, install, update

- Versioning: SemVer, single `VERSION` file read by all components; plugin refuses a core with a different major version and shows "Please update".
- Core/MCP exes built with PyInstaller; sign later (out of scope for MVP).
- Uninstaller removes binaries, keeps `%APPDATA%` data unless the user ticks "remove my data".

---

## 17. Licensing & legal checklist (record answers in `docs/decisions/licensing.md`)

- JUCE 8 licence tier for distribution **[VERIFY]**.
- Steinberg VST3 SDK licence **[VERIFY]**.
- SoundFont redistribution licence **[VERIFY]**.
- Python deps: prefer MIT/BSD/Apache (mido, fastapi, pydantic, keyring, python-rtmidi — confirm each).
- Do not use the words "Cubase", "Kontakt" or "Copilot" in the product name or logo; "works with Cubase" is fine in descriptions.
- Chord sheets in fixtures/corpus: use songs Lapalu has rights to use for research, or public-domain/traditional songs; store provenance per fixture.

---

## 18. Later add-on: Keyboard Input (non-MIDI keyboards)

Not part of MVP. When started:

- New plugin input: mono/stereo audio sidechain/input bus.
- Pipeline: onset detection (spectral flux) → pitch detection (constant-Q + harmonic template matching) → **per-keyboard calibration** (record each key once, build NMF dictionary) → note on/off events → same playback/hosting path + optional "play-to-arrange".
- Prototype in Python first (sounddevice + loopMIDI), then port to C++.
- Targets: F1 ≥ 0.9 single notes, ≥ 0.8 chords; latency < 20 ms mid/high, < 50 ms low notes.

---

## 19. Definition of done (MVP)

- A user installs Chordarium Studio, opens Cubase 15, inserts the plugin, pastes a Sinhala or English chord sheet, fixes any flagged bars, types (or asks Claude/local model) "arrange chorus 1 as a soft ballad with piano, bass, pad and light drums", hears it in sync, edits it by chat, and drags the parts onto Cubase tracks — **in under five minutes, with no API key bought by anyone.**
