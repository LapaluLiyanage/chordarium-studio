# Getting started

1. Install Chordarium Studio, open Cubase 15 and insert the **Chordarium Studio** instrument track.
2. Click **Paste chord sheet**. English or Sinhala; chords over lyrics, `[G]inline`, or `| G | Em C |` bars.
   Bars the parser had to guess are flagged — click a chord to fix it.
3. Pick a style and press **Arrange**, or type a brief in the Assistant: "soft piano, bass, pad and light drums".
4. Press play to preview. Use Lock to protect a part, the Inspector to tweak it, or chips like "Busier bass" to edit by chat.
5. Drag a part row onto a Cubase track, or use Export section.

## AI options (no paid key needed)
- **Rules only** (default): softer, louder, busier, simpler, add fill, remove a part.
- **Ollama / LM Studio** running locally, or a free-tier key (Gemini, Groq, OpenRouter, Mistral) in Settings. Keys are kept in the Windows Credential Manager.
- **Claude Desktop / LM Studio MCP:** add `chordarium-mcp.exe` as an MCP server (see docs/decisions/providers-verify.md for the unconfirmed LM Studio format), then ask it to load a sheet and arrange.
