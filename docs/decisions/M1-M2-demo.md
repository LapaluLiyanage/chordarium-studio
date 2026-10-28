# M1 (engine) and M2 (core + MCP): status

Code complete and tested: engine 629 tests (97% coverage), core 35, MCP 3.
Try it: `chordarium-studio arrange engine/tests/fixtures/sheets/amazing_grace.txt --section Chorus --style sinhala_ballad --out out.mid`.

Acceptance still open (needs you):
- M1: open the MIDI in Cubase and judge 5 songs by ear; add the 10 English + 10 Sinhala sheets.
- M2: in Claude Desktop, load a sheet and arrange the chorus as a soft ballad via the MCP server (spike S5).
Milestones are therefore not tagged `m1-done` / `m2-done` yet.
