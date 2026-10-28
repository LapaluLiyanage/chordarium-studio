# [VERIFY] AI provider base URLs and MCP config (checked 2026-10-28)

| Provider | Base URL in `core/config.py` | Status |
| --- | --- | --- |
| Gemini | `https://generativelanguage.googleapis.com/v1beta/openai/` | Confirmed on ai.google.dev/gemini-api/docs/openai; function calling documented. |
| Groq | `https://api.groq.com/openai/v1` | Confirmed on console.groq.com/docs/openai. Tool-calling support per model not checked. |
| Ollama | `http://127.0.0.1:11434/v1` | Not re-checked this session. Test on the laptop (spike S6). |
| LM Studio | `http://127.0.0.1:1234/v1` | Not re-checked this session. Test on the laptop (spike S6). |
| OpenRouter | `https://openrouter.ai/api/v1` | Not re-checked. |
| Mistral | `https://api.mistral.ai/v1` | Not re-checked. |

Tool-calling support differs per model, so the loop falls back to JSON mode when a model rejects `tools` (already implemented and tested).

## LM Studio `mcp.json`
LM Studio docs say it follows Cursor's `mcp.json` notation; edit via Program tab > Install > Edit mcp.json.
The docs page only shows a remote (`url`) example. A stdio entry is expected to be
`{"mcpServers": {"chordarium-studio": {"command": "C:\\Program Files\\Chordarium Studio\\chordarium-mcp.exe"}}}`,
which is **unconfirmed** — verify on the laptop (spike S5/S6) before putting it in the user guide.
