# af_monitor firmware skeleton

ESP-IDF C++ application for an ESP32-S3 (Phase 1 bring-up). It reads the ADXL355 ID registers over SPI, prints PASS or FAIL, then prints one uncalibrated reading per second (x, y, z in g and temperature). Wiring and pass/fail checks: `docs/PHASE1_BRINGUP.md`.

It does not stream at full rate, store data, join a network, or drive outputs. Power the board from USB only. Do not flash it onto a board that is wired to mains, machinery, or safety-critical controls.

- `main/adxl355.hpp`, `main/adxl355.cpp`: minimal SPI driver (ID, reset, measurement mode, one burst read of temperature and x/y/z).
- `main/main.cpp`: pins (SPI2 on GPIO10 CS, 11 MOSI, 12 SCLK, 13 MISO), ID check, 1 Hz readout. Lines meant for scripts start with `AF,`.

## Build status

As of 18 November 2026 this project has **not** been configured or compiled in this repository. `idf.py`, CMake, and Ninja were not on the machine, and ESP-IDF was not installed. Do not treat the source tree as a successful firmware build.

After ESP-IDF v6.1.1 is installed and the environment is activated (see `docs/DEVELOPMENT_SETUP.md`):

```bash
cd firmware
idf.py set-target esp32s3
idf.py build
```

`idf.py set-target` writes `sdkconfig` and clears `build/`. Both are gitignored.

Flashing and serial monitoring are separate steps and require a connected board. They are intentionally not part of this skeleton's verification.
