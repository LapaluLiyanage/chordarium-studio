# One-shot plugin build for Windows. Works with VS 2022 or newer Build Tools (finds them via vswhere,
# loads the compiler environment itself, so no special prompt is needed).
#   powershell -ExecutionPolicy Bypass -File scripts\build-plugin.ps1
$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $PSScriptRoot
$vswhere = "${env:ProgramFiles(x86)}\Microsoft Visual Studio\Installer\vswhere.exe"
if (-not (Test-Path $vswhere)) { throw 'vswhere.exe not found: install Visual Studio or Build Tools first.' }
$vs = & $vswhere -latest -products * -requires Microsoft.VisualStudio.Component.VC.Tools.x86.x64 -property installationPath
if (-not $vs) { throw 'No VS install with the C++ x64 tools was found.' }
$vcvars = Join-Path $vs 'VC\Auxiliary\Build\vcvars64.bat'
Write-Host "Using $vs"

# Import the compiler environment into this PowerShell session.
cmd /c "`"$vcvars`" >nul && set" | ForEach-Object { if ($_ -match '^([^=]+)=(.*)$') { Set-Item "env:$($matches[1])" $matches[2] } }

foreach ($t in 'cmake','ninja','git','cl') { if (-not (Get-Command $t -ErrorAction SilentlyContinue)) { throw "$t not found on PATH" } }

# UI bundle (optional for the first plugin build; the editor currently points at the Vite dev server)
if (Get-Command pnpm -ErrorAction SilentlyContinue) { Push-Location "$root\ui"; pnpm install; pnpm build; Pop-Location }
else { Write-Warning 'pnpm not found: skipping UI build.' }

cmake -S "$root\plugin" -B "$root\plugin\build" -G Ninja -DCMAKE_BUILD_TYPE=Release
cmake --build "$root\plugin\build" 2>&1 | Tee-Object -FilePath "$root\plugin\build\build.log"
ctest --test-dir "$root\plugin\build" --output-on-failure
Write-Host "Done. VST3: $root\plugin\build\ChordariumStudio_artefacts\Release\VST3"
Write-Host "Log: $root\plugin\build\build.log  (send me the last 40 lines if anything failed)"
