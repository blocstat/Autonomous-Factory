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

Expected preview paths, all marked synthetic:

```text
data/synthetic/out/preview.csv
data/synthetic/out/preview.png
data/synthetic/out/fan_baseline.csv
data/synthetic/out/fan_baseline.png
data/synthetic/out/fan_imbalance.csv
data/synthetic/out/fan_imbalance.png
```

The `fan_*` files are a computed fan-like signal (25 Hz shaft, 7-blade pass at 175 Hz, 4 kHz sample rate), with and without extra 1x amplitude standing in for imbalance. They are test signals, not a physical model of a fan.

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

## Verification record — 19 November 2026 (Phase 0, V0 known-answer tests)

Added to `python/`:

- `af_signal/synthetic.py`: `generate_fan_vibration()`, a synthetic 1x shaft + harmonics + blade-pass + optional impulses + noise signal. Imbalance is modelled only as extra 1x amplitude.
- `af_signal/features.py`: `peak_to_peak` in `time_domain_features()`, plus `kurtosis()` and `band_rms()`.
- `af_signal/preview.py`: optional `stem` argument; CSV header now lists components and impulses.
- `tests/test_known_answers.py`: the V0 known-answer tests from `docs/SYSTEMS_ENGINEERING_REVIEW.md` section 6.3, plus one more preview test.

These runs were made by Claude in a Linux cloud container, **not on the Mac**: Python 3.13, NumPy 2.5.5, SciPy 1.18.1, Matplotlib 3.11.2, pytest 8.4.2.

| Command | Result |
| --- | --- |
| `python -m pytest -q` (from `python/`) | Exit 0. `32 passed in 3.84s` on the Phase 0 branch alone; `46 passed in 7.91s` after rebasing onto `main` with the stdlib window-check tests. |
| `python python/scripts/preview_synthetic.py` | Exit 0. Wrote `preview`, `fan_baseline` and `fan_imbalance` CSV/PNG; every CSV header starts `data_origin: synthetic`. |

Not yet run on the Mac (Python 3.11). To confirm there, from the repository root:

```bash
source .venv/bin/activate
python -m pytest python -q          # expect 58 passed (46 before the phone loader was added)
python python/scripts/preview_synthetic.py
```

All data in these tests is synthetic. Passing them shows the feature code is correct on known signals; it says nothing about real sensors or machines.

## Verification record — 19 November 2026 (Phase 0b, phone capture loader)

Added `python/af_signal/phone.py` (phyphox CSV loader, sample-rate statistics, resampling), `python/scripts/analyze_phone.py`, `python/tests/test_phone.py`, and `docs/PHASE0B_PHONE_SESSION.md`. No new dependencies. The test CSVs are synthetic fixtures written in phyphox's format inside a temporary directory; no phone data was used.

Run by Claude in a Linux cloud container (Python 3.13, NumPy 2.5.5, SciPy 1.18.1, Matplotlib 3.11.2, pytest 8.4.2), not on the Mac:

| Command | Result |
| --- | --- |
| `python -m pytest -q` (from `python/`) | Exit 0. `58 passed in 3.12s`. |
| `analyze_phone.py` on one synthetic fixture, `--shaft-hz 20` | Exit 0. Reported `median_rate_hz 400.66`, `z_peak_hz 20.02`; summary first line `# data_origin: phone`. |

At the time of this record no real phone capture had been analysed. Real captures were analysed later; see `docs/PHASE0B_RESULTS_2026-11-20.md` and `docs/PHASE0B_RESULTS_2026-11-22.md`.

## Verification record — 22 November 2026 (first test run on the Mac)

Run by Rami on the MacBook Pro in Cursor's terminal, branch `phase0b-phone-capture`, project `.venv` (Python 3.11), from the repository root. Reported to Claude with a screenshot of the terminal.

| Command | Result |
| --- | --- |
| `python -m pip install -r python/requirements.txt` | All requirements already satisfied. |
| `python -m pytest python -q` | `58 passed in 2.91s`. |

This is the first confirmation on the Mac that the Phase 0 and Phase 0b tests pass. The tests use synthetic data and synthetic phone-format fixtures only.

## Verification record — 22 November 2026 (Phase 1 firmware, build only)

Firmware for ADXL355 bring-up (`firmware/main/`, guide in `docs/PHASE1_BRINGUP.md`). Built by Claude in a Linux cloud container, **not on the Mac and not on a board**. ESP-IDF v6.1.1 was cloned from GitHub; its Python environment was installed with `idf_tools.py install-python-env --no-constraints` because the container could not reach dl.espressif.com for the constraints file.

| Command | Result |
| --- | --- |
| `idf.py set-target esp32s3` then `idf.py build` (in `firmware/`) | Exit 0, no compiler warnings. `Project build complete`. `af_monitor.bin` is 0x2e670 bytes, 82 % of the 1 MB app partition free. Flash size 16MB. |
| `c++ -std=c++17 -Wall -Wextra -I firmware/main firmware/test/host/test_adxl355_decode.cpp -o /tmp/test_adxl355_decode && /tmp/test_adxl355_decode` (g++ 13.3) | 9 known-answer checks on hand-made byte patterns, `all passed`. |

Nothing was flashed and no sensor was read. The ID check and the gravity check in `docs/PHASE1_BRINGUP.md` are the first hardware tests and have not been run yet.

## Verification record — 22 November 2026 (Phase 1 step 1 on the Mac and board)

Run by Rami on the MacBook Pro, reported to Claude as terminal output. Branch `phase1-adxl355-bringup` (app version `4971518`), ESP-IDF v6.1.1.

| Command | Result |
| --- | --- |
| `idf.py set-target esp32s3`, `idf.py build` | Built. `af_monitor.bin` 0x2e670 bytes, same as the cloud build. |
| `idf.py -p /dev/cu.usbmodem1234561 flash monitor` | Failed to connect: "Invalid head of packet (0x1B)". |
| `idf.py -p /dev/cu.usbserial-0001 -b 115200 flash monitor` | Flashed and hash verified. esptool: ESP32-S3 (QFN56) revision v0.2, embedded PSRAM 8MB (AP_3v3), 40 MHz crystal; flash chip "boya", 16MB. App started; with no sensor wired it printed `AF,id,devid_ad=0x00,devid_mst=0x00,partid=0x00,revid=0x00,result=FAIL` every 2 s, as expected for step 1. |

Step 1 (toolchain, build, flash, log) passed. The ADXL355 had not been wired; no sensor data exists yet.

## Verification record — 22 November 2026 (Phase 1 step 2: first ADXL355 readings)

Run by Rami on the second ESP32-S3 board of the pack (the first had our firmware from step 1; this one still had the factory `led_strip` demo and was flashed first). EVAL-ADXL355-PMDZ wired as in `docs/PHASE1_BRINGUP.md`. Output saved in `data/measured/adxl355/raw/20261122-2246_adxl355_bringup-static_board-flat.txt` (`data_origin: adxl355`).

| Check | Result |
| --- | --- |
| ID registers | `devid_ad=0xAD, devid_mst=0x1D, partid=0xED, revid=0x01`, `result=PASS`. Matches the data sheet. |
| Gravity at rest, 16 readings | Mean x 0.1145 g, y −0.0177 g, z 0.9914 g. Total 0.9982 g (0.9959–1.0055). Within the ±8 % tolerance; the x and y values are a tilt of about 6.7°. |
| Stability | Standard deviation x 0.0005 g, y 0.0010 g, z 0.0022 g at 1 reading/s. One z reading of 0.9989 (14090 ms) stands out; possibly a touch. |
| Temperature | 26.0–26.4 °C, uncalibrated. |

The SPI wiring, settings and data decoding work on real hardware. Sample rate, noise density and vibration response are not tested yet (step 3).

## Verification record — 23 November 2026 (Phase 1 step 3 firmware and capture tools, build and tests only)

Streaming firmware, Python reader, capture and analysis scripts (branch `phase1-adxl355-stream`, guide in `docs/PHASE1_BRINGUP.md` step 3). Built and tested by Claude in a Linux cloud container, **not on the Mac and not on a board**. Every capture used in these tests is synthetic (generated noise and hand-made bytes).

| Command | Result |
| --- | --- |
| `rm -f sdkconfig; idf.py set-target esp32s3; idf.py build` (in `firmware/`) | Exit 0, no compiler warnings. `af_monitor.bin` 0x32fe0 bytes, 80 % of the app partition free. Generated `sdkconfig` has `CONFIG_FREERTOS_HZ=1000`. |
| Same build with `CONFIG_FREERTOS_HZ=100` in `sdkconfig` | Stops with "static assertion failed: CONFIG_FREERTOS_HZ must be 1000", as intended. |
| `c++ -std=c++17 -Wall -Wextra -I firmware/main firmware/test/host/test_stream_frame.cpp -o /tmp/test_stream_frame && /tmp/test_stream_frame` | 18 checks, `PASS (0 failures)`: CRC-16 check value 0x29B1, a known frame byte for byte, FIFO parser cases (split sets, orphan and empty words). |
| `test_adxl355_decode.cpp` (same command pattern) | `all passed`, unchanged. |
| `python -m pytest python -q` | 73 passed (58 before plus 15 new). The new tests feed a synthetic stream through the parser in 7-byte pieces, recover a corrupted frame, check the CSV round trip is lossless, and run the capture script end to end against a fake serial port. |

The 921,600 baud stream, the sample rate, and the noise floor have not been run on hardware yet. Those are the step 3 checks.

## Verification record — 23 November 2026 (Phase 1 step 3 on the board: 4 kHz stream and noise floor)

Run by Rami on the MacBook Pro and the board that passed step 2, branch `phase1-adxl355-stream` (8cfd1d7), flashed on `/dev/cu.usbserial-0001`. Three 30 s captures at rest, board flat on the desk, fans off, 10:40–10:43 America/Toronto. Files: `data/measured/adxl355/raw/20261123-1040…r1.csv`, `…1041…r2.csv`, `…1042…r3.csv` (`data_origin: adxl355`, raw counts, uncalibrated). Checked by Claude with `python python/scripts/analyze_adxl355.py data/measured/adxl355/raw/*_rest_*.csv`.

| Check | r1 | r2 | r3 |
| --- | --- | --- | --- |
| Sets received, missing | 125,248, 0 | 125,312, 0 | 125,376, 0 |
| CRC errors, FIFO overruns, dropped words, SPI errors | 0, 0, 0, 0 | 0, 0, 0, 0 | 0, 0, 0, 0 |
| Output data rate (from the ESP32 timer) | 4010.3 Hz | 4010.2 Hz | 4010.3 Hz |
| Mean x, y, z | −0.0337, +0.0344, +0.9947 g | same | −0.0338, +0.0344, +0.9947 g |
| Gravity (total) | 0.9959 g | 0.9959 g | 0.9959 g |
| Noise density x, y, z (median 10–800 Hz) | 12.5, 12.0, 16.5 µg/√Hz | 12.6, 12.0, 16.3 | 12.4, 12.1, 16.5 |
| Temperature (last status line) | 25.9 °C | 26.1 °C | 26.0 °C |
| Result | PASS | PASS | PASS |

What this shows:

- Every sample arrived: 0 lost sets and 0 corrupted frames in about 376,000 sets. The 7,900 skipped bytes at the start of each capture are the boot messages at 115,200 baud, as expected.
- The sensor's own clock runs at 4010.3 Hz, 0.26 % fast, within the data sheet's ±1.4 %, and the same in all three captures. Frequency axes must use the measured rate (the capture file records it), not 4000 Hz.
- The noise floor is flat at about 12–13 µg/√Hz on x and y and 16–17 on z from 50 to 500 Hz, then falls above about 600 Hz (the 1,000 Hz low-pass filter). That is below the data sheet's typical 22.5 µg/√Hz. The data is live (about 900 distinct x values per capture, filter roll-off and room vibration visible), so this is a quiet unit, not stuck data. The three captures agree within 2 %.
- Below 50 Hz the desk and building add vibration: peaks of 60–240 µg/√Hz at 5–20 Hz (all axes) and 40–45 Hz and about 90 Hz (z). Those come from the environment, not the sensor, and set the real floor for low-frequency measurements on this desk.

After seeing this data the stuck-data limit for noise was lowered from 11 to 5 µg/√Hz (y measured 12.0, too close to 11). All three captures passed under the original limits as well.

