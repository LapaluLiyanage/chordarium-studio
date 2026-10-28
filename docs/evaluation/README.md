# Evaluation (M7)

Tools are ready; the numbers must come from real listeners and real sheets, so none are recorded yet.

- `scripts/make_listening_kit.py` — blinded, shuffled clips + `answer_key.csv` + `rating_form.csv`. Currently yields 7 clips from the
  public-domain fixtures; add Lapalu's sheets to reach 10, and put human-made reference MIDI files in `--refs`.
- `scripts/parse_benchmark.py` — bar-level parse accuracy against `<sheet>.expected.json` (Amazing Grace is the worked example: 16/16).
  Add expected files for the Sinhala sheets once supplied.
- Timing metrics: `python -m cProfile` on `chordarium-studio arrange`; the engine arranges all fixtures in about a second.

Results table (fill in): parse accuracy ___ · listening-test mean musicality ___ · naturalness ___ · AI-vs-human guess rate ___ · time-to-first-arrangement ___
