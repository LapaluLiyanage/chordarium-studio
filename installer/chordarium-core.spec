# PyInstaller spec for chordarium-core (one-file exe). Build: pyinstaller installer/chordarium-core.spec
# [VERIFY] hidden imports on a clean machine during M8.
a = Analysis(['../core/src/chordarium_core/app.py'],
             pathex=['../engine/src', '../core/src', '../mcp/src'],
             datas=[('../engine/src/chordarium_engine/styles/*.yaml', 'chordarium_engine/styles')],
             hiddenimports=['uvicorn.logging', 'uvicorn.protocols.http.auto', 'uvicorn.protocols.websockets.auto', 'keyring.backends.Windows'])
pyz = PYZ(a.pure)
exe = EXE(pyz, a.scripts, a.binaries, a.datas, [], name='chordarium-core', console=True)
