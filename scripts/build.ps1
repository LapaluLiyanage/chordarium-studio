# Build everything. Run from the repo root in a VS 2022 developer shell.
$ErrorActionPreference = 'Stop'
Push-Location ui; pnpm install --frozen-lockfile; pnpm build; Pop-Location
pyinstaller --noconfirm installer\chordarium-core.spec
pyinstaller --noconfirm installer\chordarium-mcp.spec
cmake -S plugin -B plugin\build -G Ninja -DCMAKE_BUILD_TYPE=Release
cmake --build plugin\build
