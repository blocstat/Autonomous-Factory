# af_monitor firmware skeleton

ESP-IDF C++ application for an ESP32-S3. It logs a heartbeat and does nothing else.

It does not sample sensors, join a network, or drive outputs. Do not flash it onto a board that is wired to mains, machinery, or safety-critical controls.

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
