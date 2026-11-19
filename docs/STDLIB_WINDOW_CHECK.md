# Standard-library window check — 19 November 2026

This file records one check on a Linux host. It does not replace `DEVELOPMENT_SETUP.md` or `docs/DEVELOPMENT_SETUP.md`. Those two files are the same text: Mac setup, the ESP-IDF v6.1.1 install commands, and the NumPy/SciPy pytest run. None of that was repeated or re-run here.

## How the root docs changed this slice

Commit `8c33598` added root copies of the week-1 documents. Each one matches the file of the same name under `docs/`. Both copies stay where they are.

`WEEK_01_SPRINT.md` already counts `firmware/` and `python/af_signal` as the skeleton and the synthetic feature tests. This change does not add a second firmware tree and does not rewrite those modules.

`DECISIONS.md` D1 keeps the MVP on USB serial and defers Wi-Fi and MQTT. The code added here does not open a serial port, join a network, or store credentials. D2 is customer discovery; nothing here claims a customer, a measurement, or predictive maintenance.

`DEVELOPMENT_SETUP.md` already describes the founder's Apple silicon Mac (`arm64`, Homebrew prefix `/opt/homebrew`) and the EIM commands for ESP-IDF v6.1.1. Those commands were not run in this session. Espressif also publishes a separate macOS Intel (`x64`) installer at <https://dl.espressif.com/dl/eim/>. This session did not download either installer. Confirm `uname -m` and `brew --prefix` on the Mac before installing.

## What was added

```text
python/af_signal/window_stats.py    stdlib sine window, mean, RMS, peak, crest factor
python/af_signal/host_report.py     version probe; does not call idf.py build or flash
python/scripts/report_host.py       prints the probe
python/tests/test_stdlib_foundation.py
```

`window_stats.py` uses dimensionless synthetic samples. It rejects any `data_origin` other than `synthetic`. FFT stays in `python/af_signal/features.py`, which this session did not run.

The existing ESP32-S3 skeleton remains `firmware/`. It logs a heartbeat and does not sample pins, enable Wi-Fi, or drive outputs. See `firmware/README.md`. Hardware assumption: no board is attached, and this skeleton is not an industrial controller.

## Commands and results

Host: Linux 6.12.113+ x86_64. Working directory: repository root. Nothing was installed.

```bash
PYTHONPATH=python python3 -m unittest discover -s python/tests -p 'test_stdlib_foundation.py' -v
```

Exit 0. `Ran 14 tests in 0.002s` and `OK`.

```bash
PYTHONPATH=python python3 python/scripts/report_host.py
```

Exit 0. Output:

```text
platform: Linux 6.12.113+ x86_64
tools:
  python3: present: Python 3.12.3
  git: present: git version 2.43.0
  cmake: present: cmake version 3.28.3
  ninja: absent: not found
  idf.py: absent: not found
  pytest: absent: /usr/bin/python3: No module named pytest
  IDF_PATH: absent: unset
environment_paths:
  espressif_tools: absent: /home/ubuntu/.espressif
  esp_directory: absent: /home/ubuntu/esp
  opt_esp_idf: absent: /opt/esp-idf
firmware_build: not_run
```

```bash
python3 -m pytest python -q
```

Exit 1. `/usr/bin/python3: No module named pytest`. The 13 passing tests recorded in `DEVELOPMENT_SETUP.md` were not re-run. SciPy and Matplotlib were not installed. System NumPy 1.26.4 was already present and these new tests do not import it.

```bash
cmake -S firmware -B /tmp/af-monitor-configure
```

Exit 1. CMake looked for `/tools/cmake/project.cmake` because `IDF_PATH` is unset, then reported `Unknown CMake command "idf_build_set_property"`. Configuring did not finish.

```bash
g++ -std=c++17 -c firmware/main/main.cpp -o /tmp/af_monitor_main.o
```

Exit 1. `esp_log.h: No such file or directory`.

`idf.py` was not on `PATH`. `idf.py set-target`, `idf.py build`, and `idf.py flash` were not run.

## Still unverified

No board was connected and nothing was flashed. A firmware build has not succeeded. The Mac pytest run and the synthetic preview files in `DEVELOPMENT_SETUP.md` were not reproduced on this host. `data/measured/` was not written. These statistics are not a fault diagnosis.
