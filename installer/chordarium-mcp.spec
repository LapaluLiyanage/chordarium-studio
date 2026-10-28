# PyInstaller spec for chordarium-mcp (one-file exe). Build: pyinstaller installer/chordarium-mcp.spec
# [VERIFY] hidden imports on a clean machine during M8.
a = Analysis(['../mcp/src/chordarium_mcp/server.py'],
             pathex=['../engine/src', '../core/src', '../mcp/src'],
             datas=[('../engine/src/chordarium_engine/styles/*.yaml', 'chordarium_engine/styles')],
             hiddenimports=['uvicorn.logging', 'uvicorn.protocols.http.auto', 'uvicorn.protocols.websockets.auto', 'keyring.backends.Windows'])
pyz = PYZ(a.pure)
exe = EXE(pyz, a.scripts, a.binaries, a.datas, [], name='chordarium-mcp', console=True)
