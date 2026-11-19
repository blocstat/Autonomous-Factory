# Week 1 — Engineering Foundation (14 hours)

**Outcome:** Reproducible development setup, documented MVP architecture, and a tested synthetic sensor-data analysis baseline. Hardware is not assumed available.

- [ ] **Day 1 (2h):** Load master context into Claude; review architecture and risks. Evidence: review notes.
- [ ] **Day 2 (2h):** Set up Git, Cursor, Claude Code instructions and repository. Evidence: initial commit.
- [ ] **Day 3 (2h):** Review ESP32-S3 architecture, sensor candidates, BOM and safety. Evidence: decision log.
- [ ] **Day 4 (2h):** Prepare ESP-IDF environment and a minimal firmware skeleton (without claiming device flashing). Evidence: configuration and documented build status.
- [ ] **Day 5 (2h):** Generate clearly labeled synthetic vibration samples and visualization. Evidence: script and chart.
- [ ] **Day 6 (2h):** Implement and test simple time-domain/FFT features. Evidence: passing tests and saved outputs.
- [ ] **Day 7 (2h):** Review actual evidence, blockers, costs and next sprint. Evidence: weekly report.

**Acceptance:** Repo and setup instructions exist; sample data is reproducible and marked synthetic; tests can be run locally; hardware gaps and safety assumptions are documented. Record failures honestly.

## Evidence note — 18 November 2026

The first development assignment added `firmware/` (unbuilt ESP-IDF skeleton) and `python/af_signal` (synthetic tone, RMS/crest factor, dominant FFT bin, pytest). Setup and the commands that were run are in `docs/DEVELOPMENT_SETUP.md`.

Still open on this sprint: architecture review notes, a Git commit (none exists yet), sensor/BOM/safety decision log, an actual `idf.py build`, and the weekly report. Days 4–6 are only partly covered, so their boxes stay unchecked.
