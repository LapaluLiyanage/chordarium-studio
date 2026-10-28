# Dev helper: start core, then the UI dev server. Core binds to 127.0.0.1 only.
$root = Split-Path -Parent $PSScriptRoot
Start-Process -NoNewWindow -FilePath python -ArgumentList '-m','chordarium_core.app' -WorkingDirectory "$root\core"
Push-Location "$root\ui"; pnpm dev; Pop-Location
