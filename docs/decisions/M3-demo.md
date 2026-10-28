# M3 — UI in browser dev mode

Status: code complete. Automated checks pass; visual/interaction review in Chrome is still a manual check.

## What exists
React 19 + TypeScript + Vite + Zustand. Screens: top bar (key/BPM/time), song panel with editable chord grid,
arrangement lanes with canvas mini piano roll and playhead, inspector (pattern/density/velocity/register/fills),
assistant (chat + quick chips + connected-AI activity feed), bottom bar (transport, loop, sync mode, mix, export),
paste dialog, setup/settings dialog, toasts, live-chord view. All colours come from `brand/tokens.css`
(`pnpm lint` fails on raw hex). In browser dev mode a mock bridge supplies transport/meters; token via `?token=`.

## Checks
- `pnpm exec tsc --noEmit`, `pnpm test` (Vitest, 7 tests), `pnpm build`, `pnpm lint`.
- `scripts/e2e.sh` starts a throw-away core and runs paste -> fix chord -> arrange -> edit -> lock -> export through the real API client.

## Not verified here
- Looking at it in Chrome against real data (design fidelity vs. the Design canvas).
- Playwright browser flow (spec section 15) — replace the API-level e2e when a browser is available.
