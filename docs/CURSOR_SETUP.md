# Running the Python harness in Cursor

How to open this repository in Cursor on the MacBook and run the synthetic signal-processing tests. Everything here uses **synthetic data only**. No sensor, board or serial port is involved.

## One-time setup

1. **Open the folder.** In Cursor: *File → Open Folder…* and pick `autonomous-factory` (the folder that contains `CLAUDE.md`). Opening the parent folder instead breaks the paths below.
2. **Install the Python extension** if Cursor asks (`ms-python.python`, or Cursor's bundled Python support). It is needed for the interpreter picker and the Testing panel.
3. **Create the virtual environment** if `.venv/` does not exist yet. Open Cursor's terminal (*View → Terminal*) and run from the repository root:

   ```bash
   /opt/homebrew/bin/python3.11 -m venv .venv
   source .venv/bin/activate
   python -m pip install --upgrade pip
   python -m pip install -r python/requirements.txt
   ```

   Use Homebrew's Python 3.11. `/usr/bin/python3` is 3.9 and is too old for ESP-IDF later.
4. **Select the interpreter.** `Cmd+Shift+P` → *Python: Select Interpreter* → choose `./.venv/bin/python`. The committed `.vscode/settings.json` already points there, so this is usually automatic.
5. **Reload the window** (`Cmd+Shift+P` → *Developer: Reload Window*) so the test settings are picked up.

## Run the tests

- **Testing panel:** click the flask icon in the left sidebar. The tests under `python/tests/` appear there. Click ▶ to run all, or one test at a time. `.vscode/settings.json` sets the test directory to `python/`, which is where `pytest.ini` lives.
- **Terminal:** from the repository root:

  ```bash
  source .venv/bin/activate
  python -m pytest python -q
  ```

  **Expected:** `58 passed`. If you see a different number, write down the actual output; don't assume the expected one.

## Generate the synthetic previews

```bash
source .venv/bin/activate
python python/scripts/preview_synthetic.py
```

This writes `preview`, `fan_baseline` and `fan_imbalance` `.csv` and `.png` files to `data/synthetic/out/`, which git ignores. Every CSV starts with `data_origin: synthetic` and every chart is titled `SYNTHETIC — not a sensor measurement`.

## Troubleshooting

| Symptom | Fix |
| --- | --- |
| `ModuleNotFoundError: numpy` (or scipy, matplotlib) | Wrong interpreter. Run `which python`; it must end in `autonomous-factory/.venv/bin/python`. Re-select the interpreter and reload the window. |
| `ModuleNotFoundError: af_signal` | Tests were started from the wrong folder. Run `python -m pytest python` from the repository root, or check `python.testing.cwd` in `.vscode/settings.json`. |
| Testing panel is empty | Python extension missing, or the window wasn't reloaded. Open *Output → Python* to see the discovery error. |
| `.venv` was made with another Python | Delete `.venv` and redo step 3. |

## Prompt for Cursor's agent

Paste this into Cursor's chat (Agent mode) to have it verify the setup:

```text
Read CLAUDE.md, AGENTS.md and docs/DEVELOPMENT_SETUP.md. Then, on this Mac:
1. Check that .venv exists and uses Python 3.11. If it doesn't, create it with
   /opt/homebrew/bin/python3.11 and install python/requirements.txt. Do not add
   other packages.
2. Run `python -m pytest python -q` from the repository root and show me the
   exact output.
3. Run `python python/scripts/preview_synthetic.py` and confirm each generated
   CSV header starts with `data_origin: synthetic`.
4. If anything fails, explain the cause and propose a fix before changing code.
   Never edit or skip a test to make it pass.
5. Add a dated row to the verification record in docs/DEVELOPMENT_SETUP.md with
   only the commands you actually ran and their real results.
Do not connect to any serial port or hardware.
```
