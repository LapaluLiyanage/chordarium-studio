# M0 — Feasibility spikes: status

These need Cubase 15, loopMIDI, Claude Desktop or a local model, so they could not be run in the cloud build environment.
Each has a prepared test and a recorded fallback. Fill in the result column on the laptop.

| Spike | How to test | Fallback if it fails | Result |
| --- | --- | --- | --- |
| S1 VST3 MIDI out | Build `plugin/`, load in Cubase 15, press preview, record a MIDI track whose input is the plugin MIDI out | Drag-and-drop + export-to-folder only (drop print-to-tracks) | pending |
| S2 WebView | Plugin editor loads `ui/dist` and `getCoreConnection()` returns port+token | Open UI in the system browser at `http://127.0.0.1:47811/ui` | pending |
| S3 External drag | Drag an exported `.mid` from a native drag handle onto a Cubase track | "Reveal in folder" button + manual import | built, untested in Cubase |
| S4 MIDI Remote | Install `cubase/MIDI Remote/ChordariumStudio/Chordarium_Studio.js`, create loopMIDI port "Chordarium Remote", `POST /remote/play` | Transport tool reports "Cubase link not set up" (already the behaviour) | pending |
| S5 MCP | Add `chordarium-mcp` to Claude Desktop config, call `get_session` | Use the in-plugin chat only | pending (server itself is tested in-process) |
| S6 Local model | Ollama/LM Studio returns a tool call through `/chat` | JSON-mode fallback, then rules only (both implemented) | pending |

## Automated checks run on the dev laptop (2026-10-29)

- pluginval (latest release, `--strictness-level 5 --validate-in-process`) on `Chordarium Studio.vst3` (Release build): **SUCCESS**. The Steinberg `validator` step was skipped because no validator path was set.
- Cubase 15 and Kontakt 8 are installed on this machine. loopMIDI, Ollama, LM Studio and Claude Desktop are not, so S4, S5 and S6 are blocked until they are installed.
