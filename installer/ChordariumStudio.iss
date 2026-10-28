; Inno Setup script (spec M8). VST3 -> Common Files\VST3, exes -> Program Files\Chordarium Studio.
[Setup]
AppName=Chordarium Studio
AppVersion=0.1.0
DefaultDirName={commonpf}\Chordarium Studio
OutputBaseFilename=ChordariumStudio-Setup
PrivilegesRequired=admin
ArchitecturesInstallIn64BitMode=x64compatible
[Files]
Source: "..\dist\chordarium-core.exe"; DestDir: "{app}"
Source: "..\dist\chordarium-mcp.exe"; DestDir: "{app}"
Source: "..\plugin\build\ChordariumStudio_artefacts\Release\VST3\Chordarium Studio.vst3\*"; DestDir: "{commoncf64}\VST3\Chordarium Studio.vst3"; Flags: recursesubdirs
Source: "..\cubase\MIDI Remote\ChordariumStudio\Chordarium_Studio.js"; DestDir: "{userdocs}\Steinberg\Cubase\MIDI Remote\Driver Scripts\Local\Chordarium\Studio"; Tasks: cubasescript
[Tasks]
Name: cubasescript; Description: "Install the optional Cubase MIDI Remote script"
[Code]
function WebView2Installed: Boolean;
begin
  Result := RegKeyExists(HKLM, 'SOFTWARE\WOW6432Node\Microsoft\EdgeUpdate\Clients\{F3017226-FE2A-4295-8BDF-00C3A9A7E4C5}');
end;
procedure CurStepChanged(S: TSetupStep);
begin
  if (S = ssPostInstall) and not WebView2Installed then
    MsgBox('Chordarium Studio needs Microsoft Edge WebView2. Download it from https://developer.microsoft.com/microsoft-edge/webview2/', mbInformation, MB_OK);
end;
[UninstallDelete]
; user data in %APPDATA%\ChordariumStudio is kept unless the user removes it manually
Type: filesandordirs; Name: "{app}"
