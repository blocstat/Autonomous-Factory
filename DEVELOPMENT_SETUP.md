# Development setup — MacBook Pro

Inspection date: 18 November 2026. This file records what was on the machine, what this repository contains, and which commands were actually run.

## Facts from this machine

- MacBook Pro, Apple silicon (`arm64`, T8103), macOS 26.6.2.
- Command Line Tools Python: `/usr/bin/python3` is 3.9.6. That is below ESP-IDF's minimum of Python 3.10, so it is not the interpreter for this project.
- Homebrew Python: `/opt/homebrew/bin/python3.11` (`python@3.11` was already installed).
- Homebrew prefix: `/opt/homebrew`.
- Git 2.50.1. The repository had no commits yet.
- Not present: `idf.py`, CMake, Ninja, `~/esp`, `~/.espressif`. ESP-IDF was not installed, and this session did not install it.

## What was added

```text
firmware/                 ESP-IDF v6.1 project, ESP32-S3 heartbeat only
python/af_signal/         synthetic waveforms, features, preview writer
python/tests/             pytest suite; uses generated data, not files from a sensor
data/synthetic/           output location for synthetic previews
data/measured/            reserved and empty
```

The firmware does not read pins or enable Wi-Fi. The Python package never reads a serial port. Synthetic samples use dimensionless amplitude, not calibrated engineering units.

ESP-IDF was left uninstalled on purpose. The toolchain is a large download and changes the machine outside this repository. Install it when you want a firmware build, using the steps below.

## Python harness

From the repository root:

```bash
/opt/homebrew/bin/python3.11 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r python/requirements.txt
python -m pytest python
python python/scripts/preview_synthetic.py
```

Expected preview paths, both marked synthetic:

```text
data/synthetic/out/preview.csv
data/synthetic/out/preview.png
```

`pytest` does not need those files. It writes its own preview into a temporary directory.

## ESP-IDF v6.1.1 for ESP32-S3

Recommended installer is the Espressif Installation Manager, from the [ESP32-S3 macOS setup for v6.1.1](https://docs.espressif.com/projects/esp-idf/en/v6.1.1/esp32s3/get-started/macos-setup.html). These commands were **not** executed here:

```bash
brew install libgcrypt glib pixman sdl2 libslirp dfu-util cmake python
brew tap espressif/eim
brew install eim
eim install -i v6.1.1
```

EIM prints an activation command when install finishes. It looks like:

```bash
source "$HOME/.espressif/tools/activate_idf_v6.1.1.sh"
```

Use the path EIM prints if it differs. Then, still without a board attached:

```bash
cd firmware
idf.py set-target esp32s3
idf.py build
```

Do not run `idf.py flash` unless a board is connected and you intend to program it. A successful host build is still not a hardware test.

If `eim install` offers targets, install the ESP32-S3 tools only. This project sets `CONFIG_IDF_TARGET="esp32s3"` in `firmware/sdkconfig.defaults`. The first `idf.py set-target esp32s3` is still required.

## Verification record — 18 November 2026

Commands were run from the repository root with `.venv/bin/python` (Homebrew Python 3.11). Installed versions: NumPy 2.4.6, SciPy 1.17.1, Matplotlib 3.11.2, pytest 8.4.2.

| Command | Result |
| --- | --- |
| Tool inspection (`python3`, `idf.py`, `cmake`, `ninja`, Homebrew) | `/usr/bin/python3` is 3.9.6. `/opt/homebrew/bin/python3.11` exists. `idf.py`, CMake, Ninja, and ESP-IDF were absent. |
| `.venv/bin/python -m pip install -r python/requirements.txt` | Exit 0. Packages listed above installed into `.venv` only. |
| `.venv/bin/python -m pytest python -q` | Exit 0. `13 passed in 56.67s`. |
| `.venv/bin/python python/scripts/preview_synthetic.py` | Exit 0. Printed `data_origin=synthetic` and wrote `data/synthetic/out/preview.csv` and `data/synthetic/out/preview.png`. |
| `idf.py set-target esp32s3` and `idf.py build` | Not run. Toolchain absent. |

The preview CSV header contains `data_origin: synthetic` and `not_a_sensor_measurement: true`. The PNG title reads `SYNTHETIC — not a sensor measurement`. These files are generated output, not a recording. No board was connected and nothing was flashed.

## Verification record — 19 November 2026

This run was on a Linux host (`Linux 6.12.113+ x86_64`), not the MacBook above. `/opt/homebrew/bin/python3.11` and `python3.11` were absent. `/usr/bin/python3` is Python 3.12.3. `python3 -m venv .venv` failed until `python3.12-venv` was installed with apt, because `ensurepip` was missing. The venv was then created with that Python 3.12.3. No packages were added beyond `python/requirements.txt`. No test was edited. No serial port was opened.

Installed into `.venv`: pip 26.3, NumPy 2.5.5, SciPy 1.18.1, Matplotlib 3.11.2, pytest 8.4.2.

| Command | Result |
| --- | --- |
| `python3 -m venv .venv` after installing `python3.12-venv` | Exit 0. Interpreter `.venv/bin/python` is Python 3.12.3. |
| `.venv/bin/python -m pip install --upgrade pip` | Exit 0. pip 26.3. |
| `.venv/bin/python -m pip install -r python/requirements.txt` | Exit 0. Versions listed above, in `.venv` only. |
| `.venv/bin/python -m pytest python -q` | Exit 0. `27 passed in 1.53s`. |
| `.venv/bin/python python/scripts/preview_synthetic.py` | Exit 0. Printed `data_origin=synthetic` and wrote `data/synthetic/out/preview.csv` and `data/synthetic/out/preview.png`. |

The first line of `preview.csv` is `# data_origin: synthetic`. The following header line is `# not_a_sensor_measurement: true`. The PNG title is `SYNTHETIC — not a sensor measurement`. These files are generated output, not a recording. No `fan_baseline` or `fan_imbalance` file was produced. Nothing was flashed.
