# The Autonomous Factory Company — AI Engineering Workspace

This starter pack aligns ChatGPT, Claude, Claude Code and Cursor around the same project context.

## Start here
1. Read `docs/MASTER_CONTEXT.md`.
2. Open the folder in Cursor.
3. Keep `CLAUDE.md` at repository root for Claude Code.
4. Keep `.cursor/rules/engineering.mdc` for Cursor project rules.
5. Use `docs/AI_STARTER_PROMPTS.md` for the first assignments.
6. Track the first week using `docs/WEEK_01_SPRINT.md`.

These files are instructions and planning artifacts, **not** a completed firmware or monitoring application.

## Foundation code

- `docs/DEVELOPMENT_SETUP.md` — Mac setup, what was installed, and commands that were actually run.
- `docs/CURSOR_SETUP.md` — open the repo in Cursor, select `.venv`, run the tests from the Testing panel.
- `docs/PHASE0B_PHONE_SESSION.md` — phone-accelerometer session: setup, safety, phyphox, file naming, analysis.
- `firmware/` — ESP-IDF skeleton for ESP32-S3. Heartbeat log only. Not built or flashed here.
- `python/` — synthetic signal-processing harness and pytest suite. No serial port and no measured data.
- `data/synthetic/` and `data/measured/` — synthetic output versus future recordings. Measured is empty.
