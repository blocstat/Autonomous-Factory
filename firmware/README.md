# af_monitor firmware

ESP-IDF C++ application for an ESP32-S3 (Phase 1 bring-up). It checks the ADXL355 ID registers over SPI, then streams every x/y/z sample (4,000 per second, ±2 g, 1,000 Hz low-pass, uncalibrated) to the host over the USB-to-UART port at 921,600 baud, in CRC-checked binary frames, with one text status line per second. Wiring, commands and pass/fail checks: `docs/PHASE1_BRINGUP.md` (step 3). Read the stream with `python/scripts/capture_adxl355.py`, not `idf.py monitor`.

It does not store data, join a network, or drive outputs. Power the board from USB only. Do not flash it onto a board that is wired to mains, machinery, or safety-critical controls.

- `main/adxl355.hpp`, `main/adxl355.cpp`: minimal SPI driver (ID, reset, measurement mode, status and FIFO reads, temperature).
- `main/stream_frame.hpp`: frame format, CRC-16 and FIFO word parser. No ESP-IDF headers, so it is tested on the host. The Python reader `python/af_signal/adxl355_stream.py` must stay in step with it.
- `main/main.cpp`: pins (SPI2 on GPIO10 CS, 11 MOSI, 12 SCLK, 13 MISO), ID check, streaming task. Text lines meant for scripts start with `AF,`.
- `test/host/`: known-answer tests that build with any C++17 compiler (commands at the top of each file).

## Build

After ESP-IDF v6.1.1 is installed and the environment is activated (see `docs/DEVELOPMENT_SETUP.md`):

```bash
cd firmware
rm -f sdkconfig
idf.py set-target esp32s3
idf.py build
```

`idf.py set-target` writes `sdkconfig` from `sdkconfig.defaults` and clears `build/`. Both are gitignored. Delete an `sdkconfig` made before step 3: the stream needs `CONFIG_FREERTOS_HZ=1000`, and the build stops with an error if it is not set.

Build and test records: `docs/DEVELOPMENT_SETUP.md`.
