# Chordarium Studio — UI Specification

> **For Claude Code.** Read together with `CHORDARIUM_STUDIO_BUILD.md`. This file defines every screen, component, state and interaction of the plugin UI.
> **Brand rule:** Chordarium Studio uses the **existing Chordarium logo, colour theme and animations**, already extracted into the `brand/` folder. Do **not** invent a new brand. Section 1 lists exactly what to use.

---

## 1. Brand: the existing Chordarium identity (already extracted)

The brand was extracted from Lapalu's repo `LapaluLiyanage/Chordarium` (React 19 + GSAP). The ready-to-use pack is in **`brand/`** next to this file. Copy it to `ui/src/brand/` unchanged and build on it. **Do not redraw or recolour.**

| File | Contents |
| --- | --- |
| `brand/logo/chordarium-mark.svg` | The mark: a "C" ring with three beat dots (top dot amber, rest `currentColor`) |
| `brand/logo/chordarium-app-icon.svg` | Ink circle, cream ring, amber dot — plugin icon, installer, favicon |
| `brand/tokens.css` | Raw palette + Studio semantic tokens + `@font-face` (Archivo) |
| `brand/fonts/` | Archivo variable woff2 (latin, latin-ext, vietnamese) + TTFs |
| `brand/motion.ts` | GSAP presets: `flipIn`, `splashLogo`, `wordmarkIn`, `riseIn`, `letterBounce`, `pulseRing`, `bob` |
| `brand/BRAND.md` | Every value with its source file; items needing approval |

### 1.1 Palette (verbatim from Chordarium)

| Role | Value |
| --- | --- |
| Brand amber (primary accent, active chord, CTA) | `#f2913d` |
| Blue (focus ring, secondary accent) | `#6aa8e0` |
| Purple / green / coral / yellow | `#b48be0` / `#6fbf8b` / `#ee8577` / `#f2c14e` |
| Bass teal | `#4fc3c9` |
| Light: cream / sand / paper / ink | `#fbf5ea` / `#efe5d4` / `#fffdf8` / `#231d17` |
| Dark: bg / panel / line / chord chip | `#1f1a16` / `#2a241e` / `#3d352d` / `#342c25` |
| Text on dark / muted on dark | `#f6eee1` / `#b9ad9c` |

**Studio runs dark by default** (DAWs are dark): `--bg #1f1a16`, `--surface #2a241e`, `--border #3d352d`, `--text #f6eee1`, `--brand #f2913d` with `--on-brand #231d17`. Chordarium's native cream look ships as `data-theme="light"` (setting in 4.8). Components use **semantic tokens only**, never raw hex.

Song-section colours are the same as Chordarium: intro yellow, verse blue, chorus amber, bridge purple, interlude coral, outro green, other `#b9ad9c`. Reuse them for section tags in the chord grid and arrangement lanes.
Part-lane colours: piano = amber, bass = teal, pad = purple, drums = coral. Drums/lane choices are Studio-derived: verify each reaches **3:1** against `--surface` and flag in `BRAND.md` for Lapalu's approval.

### 1.2 Look and shape

- Chordarium's character: big condensed black type, pill buttons (`border-radius: 999px`, min-height 44 px, 800-weight 12 px, letter-spacing .05em), rounded dark cards (22–32 px), chips 10 px, bar cells 14 px, 2 px ink outlines in light mode, an amber hero panel with the logo "notch".
- Selected segmented/pill buttons invert (dark ↔ amber). Active structure block fills with its section colour; a looping block gets a 3 px cream ring.
- Chord symbols use Chordarium's **chord style**: Archivo weight 900, width 62 %, with a small quality, raised extension and teal slash-bass (`.cs`, `.cs-quality`, `.cs-ext`, `.cs-bass`). Low-confidence/AI-guessed chords get a dotted underline; guessed sections get a dashed border.
- The chord lane pattern is reused for the timeline: playhead fixed at 50 %, the chip track scrolls under it, chips 54 px high with 2 px transparent border, empty chip = dashed.
- Focus ring: `3px solid var(--blue)`, offset 2 px. Text selection: amber background.
- App icon and splash use the logo mark; wordmark "CHORDARIUM STUDIO" in the condensed black style.

### 1.3 Typography

- One family everywhere: **Archivo** (variable, bundled, works offline). Display/wordmark/chords: 900 weight, `font-stretch: 62%`, `font-variation-settings: 'wdth' 62`, uppercase for wordmark. UI text: 600–800 weight, normal width.
- Sinhala lyrics: **Noto Sans Sinhala** (OFL), bundle locally, fallback after Archivo (Chordarium has no Sinhala font).
- Scale: 11 / 12 / 13 / 15 / 18 / 24 / 32 px for UI; chords sized in `em`. Body 13 px. Line height 1.4.

### 1.4 Motion language (Chordarium, GSAP 3)

Use **GSAP** like Chordarium (add `gsap`; Lenis smooth-scroll is not needed in a plugin panel). Presets are in `brand/motion.ts`.

| Studio moment | Chordarium animation to reuse |
| --- | --- |
| Splash / app load | Logo spins in (`scale 0, rotation -180` → 1, 1 s, `back.out(1.6)`), wordmark letters rise (`yPercent 115`, stagger .055, `power4.out`). Cap total at 900 ms in Studio. |
| Active chord during playback | `flipIn`: rises with `rotateX -70 → 0`, 0.5 s `back.out(2)`, on every chord change; beat dots light amber |
| Panels / cards appear | `riseIn`: y 30 + fade, 0.8 s `power3.out` (use 0.4 s in Studio) |
| AI thinking | `pulseRing` on the Generate button + amber progress bar (scaleX, linear) like Chordarium's queue bar |
| Part generated | Notes draw in left to right (stagger ≤ 400 ms total) |
| Part regenerated | Cross-fade 200 ms |
| Section selected | Fill with section colour + 3 px cream ring, 150 ms |
| Hover on primary buttons | Magnetic follow (x 30 %, y 40 %), release `elastic.out(1,.4)` 0.7 s (pointer devices only) |
| Playing feedback | Optional floating-notes burst (0.9–1.4 s, `power2.out`), off by default |
| Drag part to DAW | Lift (scale 1.02 + shadow); ghost follows cursor |
| Errors / toasts | Slide + fade, `power3.out` |

**Not for the plugin:** custom cursor ring, scroll-progress bar, 3D chord wheel (three.js). They suit the website, not a DAW panel.

**Performance rules (UI runs inside a DAW):**
- Animate only `transform` and `opacity` (box-shadow pulse only on the single CTA, stop when idle).
- No idle loops; pause everything when the editor is hidden (`document.visibilityState`).
- Playhead and meters update via `requestAnimationFrame`, meters max 30 fps.
- Respect `prefers-reduced-motion` (Chordarium disables all animation under it): instant state changes or 100 ms fades.
- Target UI CPU < 3 % while playing.

### 1.5 Reuse, don't rewrite

Chordarium's `ChordSymbol`, `ChordLane`, `Logo` and `sections.ts` can be ported almost directly (React 19 + TS). Clone `LapaluLiyanage/Chordarium` read-only into `../chordarium` to copy them. Never modify that repo from this project. It is Lapalu's own code, so reuse is fine; confirm the licence of `@tombatossals/chords-db` before shipping chord diagrams.

---

## 2. Tech stack

- React 19 + TypeScript + Vite (same as Chordarium), Tailwind CSS optional (tokens wired as CSS variables from `brand/tokens.css`), Zustand (state), Radix UI primitives (accessible popovers, dialogs, sliders, tabs), lucide-react icons (or Chordarium's icon set if it uses another), **GSAP 3** (Chordarium's animation library; no Framer Motion).
- Build output: a single static bundle embedded into the JUCE plugin as binary resources (see build spec 11.5).
- Two runtime modes:
  - **Plugin mode:** native bridge from JUCE 8 (`window.__JUCE__` via the JS helper that ships with JUCE 8 — **[VERIFY]** exact API).
  - **Browser dev mode:** `pnpm dev` at `http://localhost:5173`, talks to the real core service, and a **mock bridge** (`src/bridge/mock.ts`) simulates transport, meters and playback.
- All core calls go through `src/api/core.ts` (REST + WebSocket, token header). All plugin calls go through `src/bridge/index.ts`. Components never call `fetch` or the bridge directly.

---

## 3. Window and layout

Default 1100×720, resizable, minimum 900×600. Layout scales with the window; panels collapse at narrow widths.

```
┌──────────────────────────────────────────────────────────────────────────────┐
│ [Chordarium logo] Studio   Song: Sanda Eliya ▾   G maj · 76 BPM · 4/4         │  Top bar (48px)
│                                   [AI: Claude ● ] [Cubase link ●] [⚙]        │
├───────────────┬──────────────────────────────────────────────┬───────────────┤
│ SONG          │ ARRANGEMENT                                  │ ASSISTANT     │
│ (260px)       │                                              │ (320px)       │
│ Sections      │  Intro │ Verse 1 │ Chorus 1 │ Verse 2 │ ...   │ chat messages │
│ ▸ Intro       │  ──────┼─────────┼──────────┼─────────┼────   │               │
│ ▸ Verse 1     │ Piano  ▒▒▒▒▒▒  ▒▒▒  ▒▒▒▒▒▒▒▒ ...      [⠿]    │               │
│ ● Chorus 1    │ Bass   ▬ ▬ ▬ ▬ ▬ ▬ ▬ ...                [⠿]    │ quick chips:  │
│ ▸ Verse 2     │ Pad    ━━━━━━━━━━━━━━ ...               [⠿]    │ [softer]      │
│               │ Drums  ·•·•·•·• ...                     [⠿]    │ [busier bass] │
│ Chord grid    │  chord ruler: | G | Em C | D | G |            │ [add fill]    │
│ (selected     │  ▲ playhead                                  │               │
│  section)     │                                              │ [type a brief]│
├───────────────┴──────────────────────────────────────────────┴───────────────┤
│ ▶ ■  Sync: Cubase ▾  Loop section ☐   Piano [M][S]▮  Bass [M][S]▮ ...  [Export]│  Bottom bar (56px)
└──────────────────────────────────────────────────────────────────────────────┘
```

- `[⠿]` = **native drag handle** for dragging the part into Cubase (rendered by JUCE over the WebView; the UI reserves the space and reports its rectangle via `reportDragRects`).
- Narrow widths (< 1000 px): Assistant panel collapses to an icon tab on the right edge; < 920 px: Song panel collapses to a drawer.

---

## 4. Screens

### 4.1 First-run setup (modal wizard, 4 steps)

1. **Welcome:** Chordarium logo animation, one line: "Turn a chord sheet into a full band arrangement."
2. **Choose your AI** (cards, can skip):
   - Claude Desktop / Claude Code (MCP) — shows the config snippet with a Copy button and a "Test connection" button.
   - LM Studio (MCP, local, free).
   - Ollama (local, free) — URL field prefilled `http://127.0.0.1:11434`, model dropdown after test.
   - Free-tier key (Gemini / Groq / OpenRouter / Mistral) — provider select + key field (masked) + model + Test. Note: "Your key stays on this computer."
   - No AI (rules only).
3. **Cubase link (optional):** checks for the loopMIDI port "Chordarium Remote" and the MIDI Remote script; shows step-by-step instructions with status ticks.
4. **Sounds:** "Built-in sounds" (default) or "Choose instruments" (opens Instruments screen).

Each step shows a status chip: ✓ ready / ! needs action / – skipped.

### 4.2 Song panel — import and chord grid

- **Empty state:** large drop zone with the Chordarium logo mark, text "Paste a chord sheet or drop a .txt / .pdf file", buttons **Paste** and **Open file**, plus "Try an example" (loads a bundled sample sheet).
- **Paste dialog:** monospace textarea (Sinhala font fallback), live preview on the right showing detected sections and chords as chips; **Import** button.
- **Section list:** name, bar count, status dot (not arranged / arranged / locked). Click selects; double-click renames; drag to reorder; right-click menu: duplicate, delete, mark as chorus/verse/…
- **Chord grid** (selected section): one cell per bar, chord chips inside (Chordarium chord-chip style). Click a chip to edit (autocomplete chord symbols, validated live). Cells with parser warnings show a warning outline and tooltip ("Inferred 1 bar per chord — check").
- Metadata row: Key (dropdown + "detected" badge with confidence), Tempo (number), Time signature (4/4, 3/4, 6/8, 12/8).

### 4.3 Arrangement view (centre)

- **Section header strip:** sections as blocks across the top, width proportional to bars. Selected section highlighted with brand glow.
- **Part lanes:** Piano, Bass, Pad, Drums, each with role colour, name, and controls on the left: Mute, Solo, Lock (padlock), Regenerate (↻), and a ⋯ menu (change pattern, change instrument, clear).
- **Mini piano roll** per lane: notes as rounded bars (velocity → opacity), drums as dots per GM row. Read-only in MVP; click a lane to open the Part inspector.
- **Chord ruler** under the section strip; **playhead** line in brand colour; current chord chip pulses on change (brand motion).
- **Generate controls:** when a section has no parts, show a centred card: style dropdown + "Arrange with defaults" button + "or describe it in the Assistant →".

### 4.4 Part inspector (right-side sheet over the Assistant, or popover)

Fields: Pattern (dropdown from style), Density (slider 0–100), Velocity range (dual slider), Register (segmented: Low · Mid-low · Mid · Mid-high · High), Instrument (built-in preset or hosted plugin), Variation (slider), Seed (number + dice button). Changes apply on release with a 300 ms debounce and animate the lane (cross-fade).

### 4.5 Assistant panel (chat)

- Header: provider chip (e.g., "Claude via MCP ●", "Ollama · qwen ●", "Rules only"). Clicking opens provider settings.
- **MCP mode note:** when the provider is an MCP client, the chat happens in Claude Desktop/LM Studio; this panel shows an **activity feed** of tool calls ("Claude arranged Chorus 1 — 4 parts") and a button "Open Claude Desktop" plus suggested prompts to copy.
- **In-plugin chat mode** (Ollama / free key / rules): message list, user bubble right, assistant left; tool events shown as compact rows ("↻ Regenerated Bass · Chorus 1"); streaming text; "Thinking" state uses the brand loading animation.
- Quick chips above the input (context-aware for the selected section): *Softer*, *Louder*, *Busier bass*, *Simpler piano*, *Add fill*, *Remove drums*, *Arrange whole song*.
- Input: multiline, Enter sends, Shift+Enter newline; mic button reserved (voice later, hidden in MVP).
- Undo: every AI change is one undo step; a small "Undo" link appears on each tool-event row.

### 4.6 Bottom transport and mix bar

- Play / Stop preview, **Sync** dropdown (Follow Cubase · Free loop), Loop section toggle, Start bar (when following Cubase).
- Per-role mini strip: Mute, Solo, volume knob/slider, level meter (role colour).
- **Export** button → menu: *Drag parts* (highlights drag handles), *Export section MIDI*, *Export song MIDI*, *Print to tracks…* (opens a guide dialog with the Cubase routing checklist).

### 4.7 Instruments screen (modal or full panel)

- Four role cards: current instrument (Built-in preset dropdown, or hosted plugin name), **Choose plugin…** (searchable list from scan), **Open editor**, **Remove**.
- "Scan plugins" button with progress and last-scan time; scanning runs in the background.

### 4.8 Settings

Tabs: **AI** (providers, models, keys, test), **Cubase link** (port status, script status, test buttons for play/stop), **Audio** (preview sync mode default, latency info), **Appearance** (UI scale 90–125 %, reduced motion toggle), **About** (version, licences, logs folder button).

### 4.9 Live chord view (v1)

Full-panel view: big current chord (display font, brand colour), next chord smaller, scrolling lead-sheet of the section with lyrics (Sinhala supported). Uses the Chordarium chord-highlight animation. Input: MIDI keyboard (or the Keyboard Input add-on later).

### 4.10 Keyboard Input add-on screens (later, hidden behind a feature flag)

Calibration wizard: input select, level meter, "play each key" progress across a keyboard graphic, result summary. Not in MVP.

---

## 5. Components (build in `ui/src/components/`)

| Component | Notes |
| --- | --- |
| `BrandLogo` | Uses the extracted Chordarium logo; variants: full, mark-only; optional intro animation |
| `TopBar`, `BottomBar`, `Panel`, `Drawer` | Layout shells |
| `StatusChip` | ready / warning / error / off, with dot |
| `ChordChip` | Chordarium chord-chip look; states: normal, active (playing), warning, editing |
| `ChordGrid`, `ChordInput` | Bar cells, autocomplete, validation |
| `SectionStrip`, `SectionListItem` | Selection, rename, reorder |
| `PartLane`, `MiniPianoRoll`, `DrumGrid` | Canvas rendering for performance (use `<canvas>` for notes; DOM for controls) |
| `Playhead` | rAF-driven, transform only |
| `PartInspector` | Radix sliders/segmented controls |
| `ChatPanel`, `ChatMessage`, `ToolEventRow`, `QuickChips`, `ThinkingIndicator` | Streaming, undo links |
| `ProviderCard`, `ConnectionTest` | Setup + settings |
| `MixStrip`, `LevelMeter` | Meters at ≤ 30 fps |
| `Toast`, `ConfirmDialog`, `EmptyState` | Brand motion |
| `DragHandleSlot` | Reserves space + reports rect for the native handle |

Each component gets a Storybook-free **demo route** (`/dev/components`) in browser mode for visual checks.

---

## 6. States and copy

| Situation | UI behaviour | Copy |
| --- | --- | --- |
| Core not running | Top banner, retry every 3 s | "Starting Chordarium engine…" → after 15 s: "Can't reach the engine. Restart the plugin or check logs." |
| No song | Empty state in Song panel | "Paste a chord sheet to begin." |
| Parser warnings | Warning outlines + count badge on the section | "3 bars need a quick check" |
| No AI connected | Assistant shows rules-only chips | "No AI connected — quick edits still work. Connect one in Settings." |
| AI planning | Thinking animation on bubble + affected lanes | "Planning Chorus 1…" |
| Invalid AI plan fixed by defaults | Info toast | "Used the style default for the drum pattern." |
| Provider error / rate limit | Error toast with action | "Groq limit reached. Try again in a minute or switch provider." |
| Cubase link missing | Chip grey; tooltip | "Optional: set up Cubase link for transport control." |
| WebView2 missing | Native JUCE fallback screen (not React) | "Chordarium Studio needs Microsoft Edge WebView2." + link |
| Locked part edit attempt | Shake animation (reduced-motion: outline flash) | "Bass is locked. Unlock to change it." |

Tone: short, friendly, musician language ("bars", "parts", "feel"), no technical jargon in user-facing text.

---

## 7. Interaction details

- **Keyboard shortcuts:** Space play/stop preview, ↑/↓ select section, 1–4 select lane, M mute lane, S solo lane, L lock lane, R regenerate lane, Ctrl+Z / Ctrl+Shift+Z undo/redo, Ctrl+Enter send chat, Ctrl+E export section. Shortcuts only fire when the plugin window has focus and no text field is active (DAW shortcuts must not be swallowed otherwise).
- **Undo/redo:** global history of song edits, plan changes and part regenerations (max 100 steps), stored in the session.
- **Selection model:** one selected section at a time (MVP); "Arrange whole song" applies to all unlocked sections.
- **Drag to Cubase:** hover a lane → drag handle highlights; while dragging, a tooltip "Drop on a MIDI or instrument track in Cubase".
- **Autosave:** every change saved (no Save button); a subtle "Saved" tick in the top bar.

---

## 8. Accessibility

- All interactive elements reachable by Tab, visible focus ring in `--brand`.
- Radix primitives for dialogs, menus, sliders (ARIA built in).
- Contrast: text ≥ 4.5:1, UI elements ≥ 3:1 against their background (check every brand-derived token).
- Never rely on colour alone: lanes also show role names and icons; status chips show icons + text.
- UI scale setting (90–125 %) for small/large screens.
- Reduced motion respected everywhere (section 1.6).

---

## 9. Build order (aligned with build spec milestones)

1. **Brand pack** (section 1): copy `brand/` into `ui/src/brand/`, confirm the derived role colours in `BRAND.md` with Lapalu.
2. Tokens, fonts, motion presets, `BrandLogo`, layout shells, `/dev/components` route.
3. Song panel (import, chord grid) against core → M3.
4. Arrangement view (lanes, canvas rendering, playhead with mock bridge) → M3.
5. Assistant panel + quick chips + rules-only path → M3/M5.
6. Bottom bar, export menu, settings, first-run wizard → M3/M4.
7. Plugin bridge wiring (real transport, meters, drag rects) → M4.
8. Instruments screen → M6. Live chord view → v1. Add-on screens → later.

---

## 10. Acceptance checklist

- [ ] Logo, colours, fonts and animations match the original Chordarium app (side-by-side screenshots added to `BRAND.md`).
- [ ] No raw hex values in components (lint rule or grep check).
- [ ] Full flow works in browser dev mode and inside the plugin in Cubase 15.
- [ ] Sinhala lyrics render correctly in paste preview, chord grid tooltips and live chord view.
- [ ] Reduced motion mode removes all movement animations.
- [ ] UI CPU < 3 % while playing; no animation runs while idle or hidden.
- [ ] Keyboard-only use covers import → arrange → edit → export.
- [ ] Every state in section 6 is reachable in a test and shows the specified copy.
