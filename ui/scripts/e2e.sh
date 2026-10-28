#!/usr/bin/env bash
# Start a throw-away core on 127.0.0.1 and run the UI client e2e test against it.
set -euo pipefail
HOME_DIR=$(mktemp -d); PORT=${PORT:-47899}
CHORDARIUM_HOME="$HOME_DIR" chordarium-core --port "$PORT" & PID=$!
trap 'kill $PID 2>/dev/null; rm -rf "$HOME_DIR"' EXIT
for _ in $(seq 1 50); do curl -sf "http://127.0.0.1:$PORT/health" >/dev/null && break; sleep 0.2; done
CHORDARIUM_E2E_URL="http://127.0.0.1:$PORT" CHORDARIUM_E2E_TOKEN=$(cat "$HOME_DIR/token") pnpm exec vitest run src/__tests__/e2e.test.ts
