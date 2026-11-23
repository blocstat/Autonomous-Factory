# Phase 1 — ADXL355 bring-up on the ESP32-S3

**Goal:** get the product sensor (ADXL355) talking to the ESP32-S3 over SPI, and prove it with known answers before any vibration data is trusted. This guide covers steps 1 and 2. Step 3 (full-rate raw streaming over USB into the Python analysis) comes after step 2 passes.

**Time:** step 1 about 1 hour (mostly download), step 2 about 1 hour. **Cost:** $0, the parts are already here.

Every reading from this hardware is labelled as ADXL355 data. Until the unit is calibrated, values in g are good to about ±8 % (the data sheet's sensitivity tolerance). Nothing here says anything about an industrial machine.

## Hardware for this step

| Part | What you have | Notes |
| --- | --- | --- |
| ESP32-S3 board | DIYmall ESP32-S3-DevKitC-1 copy, Sparkle IoT XH-S3E N16R8 module (16 MB flash, 8 MB PSRAM) | Header labels match Espressif's DevKitC-1. |
| Accelerometer | Analog Devices EVAL-ADXL355-PMDZ | 12-pin Pmod connector, SPI only, powered at 3.3 V by the host. |
| Cable | USB-C to the Mac | Power comes from USB only. |
| Wires | 6 female-to-female jumper wires (7 if you add DRDY) | Keep them short, under 15 cm. |

Everything else in the kit (PT100, current clamp, RS485, microSD, Ethernet, display, 24 V supply) waits.

## Safety and handling

1. **USB power only.** The Mean Well HDR-15-24 connects to mains (120 V). Do not wire it for bench work.
2. **3.3 V, never 5 V, to the sensor.** The ADXL355 supply is 2.25–3.6 V (absolute maximum 5.4 V). The ESP32 header has both a `3V3` and a `5V` pin; use `3V3`.
3. **Wire with the USB cable unplugged.** Check every wire against the table before plugging in.
4. **Static:** touch something metal first, hold boards by their edges, keep them on their anti-static bags.

## Step 1 — Toolchain and a first flash

1. Install ESP-IDF v6.1.1 as in `docs/DEVELOPMENT_SETUP.md` (section "ESP-IDF v6.1.1 for ESP32-S3").
2. Activate it in Cursor's terminal (use the path the installer printed):

   ```bash
   source "$HOME/.espressif/tools/activate_idf_v6.1.1.sh"
   ```

3. Build, with no board connected yet. Run this from **this repository** (not from the ESP-IDF folder `~/esp/esp-idf`, which gives "is not buildable"), on the `phase1-adxl355-bringup` branch until it is merged:

   ```bash
   cd ~/"Documents/the Autonomous factory company/autonomous-factory"
   git fetch
   git checkout phase1-adxl355-bringup
   cd firmware
   idf.py set-target esp32s3
   idf.py build
   ```

   **Pass:** the build ends with `Project build complete`. **Fail:** copy the last 30 lines of output into the thread.

4. Plug the ESP32 board into the Mac with nothing else wired to it. Find its port:

   ```bash
   ls /dev/cu.usb*
   ```

   The board has two USB-C ports. Either works for this step: the one marked **USB** (the ESP32-S3's own USB) shows up as `/dev/cu.usbmodem…`, the other (USB-to-UART bridge) as `/dev/cu.usbserial…` or `/dev/cu.wchusbserial…`.

5. Flash and watch the log (replace the port with yours):

   ```bash
   idf.py -p /dev/cu.usbmodem1101 flash monitor
   ```

   With no sensor wired, the firmware prints `AF,id,…,result=FAIL` every 2 seconds. **That is the expected result for step 1**: it proves the build, flash and log path work. Exit the monitor with `Ctrl+]`.

   If flashing fails to connect: hold **BOOT**, press and release **RST**, release **BOOT**, then run the command again.

   On Rami's board (22 November 2026), flashing failed on `/dev/cu.usbmodem1234561` ("Invalid head of packet (0x1B)") and worked on `/dev/cu.usbserial-0001` with `-b 115200`. Use that port first.

## Step 2 — Wire the ADXL355 and check its ID

Unplug the USB cable first.

### Wiring

Pmod pin numbers: on the EVAL-ADXL355-PMDZ connector, pins 1–6 are one row and 7–12 the other; pin 1 is marked on the board (a "1" or a square pad). **Check the marking on your board before wiring.** ESP32 pins are by the label printed next to each header pin.

| ADXL355 Pmod P1 | Signal | ESP32-S3 board pin | DevKitC-1 header position |
| --- | --- | --- | --- |
| 1 | CS | **10** | J1 pin 16 |
| 2 | MOSI | **11** | J1 pin 17 |
| 3 | MISO | **13** | J1 pin 19 |
| 4 | SCLK | **12** | J1 pin 18 |
| 5 | DGND | **G** (GND) | J1 pin 22 |
| 6 | VDD | **3V3** | J1 pin 1 |
| 10 | DRDY | 4 (optional, for step 3) | J1 pin 4 |
| 7, 8, 9, 11, 12 | INT1, NC, INT2, DGND, VDD | not connected | |

Why these pins: GPIO10–13 are the ESP32-S3's dedicated SPI2 pins (fastest, simplest routing). GPIO35–37 are avoided because the N16R8 module's PSRAM uses them.

### Run it

Plug the USB cable back in, then:

```bash
idf.py -p /dev/cu.usbmodem1101 monitor
```

(No need to flash again: the step 1 firmware already contains the sensor code. Press **RST** on the board to restart it.)

### Pass/fail checks

| Check | Pass | If it fails |
| --- | --- | --- |
| **ID** | `AF,id,devid_ad=0xAD,devid_mst=0x1D,partid=0xED,…,result=PASS` | All `0x00` or all `0xFF`: power or MISO/CS problem. Check 3V3, GND, MISO, CS. Mixed wrong values: SCLK/MOSI swapped or a loose wire. The firmware retries every 2 s, so you can fix a wire (with USB unplugged) and replug. |
| **Gravity, board flat on the table** | One axis (usually z) reads about **±1.0 g** (0.92–1.08 allowed by the ±8 % tolerance); the other two read within **±0.1 g** of 0 | Turn the sensor board on its side: the 1 g should move to another axis. If nothing changes, write down what you see. |
| **Temperature** | Between 15 and 40 °C, and roughly room temperature | Write it down; it is uncalibrated. |
| **Stability** | Readings change by less than about 0.01 g between lines while nothing is touched | Write down the spread. |

`REVID` is printed for the record; any value is accepted.

Record the result in the thread: the `AF,id` line and about 10 `AF,sample` lines with the board flat. Those become the first ADXL355 verification record in `docs/DEVELOPMENT_SETUP.md`.

## What step 2 proves and does not prove

It proves the wiring, the SPI settings and the data decoding (ID registers are fixed values; gravity is a known 1 g input). It does not test sample rate, noise or vibration: that is step 3, which streams every sample at 4,000 per second over USB and measures the noise floor with nothing running, the same way the phone sessions did.

## Sources

- ADXL354/ADXL355 data sheet, Rev. D (Analog Devices): register map, SPI mode 0 and 0.1–10 MHz clock, 20-bit two's-complement data, 256,000 LSB/g typical at ±2 g, supply 2.25–3.6 V.
- EVAL-ADXL355-PMDZ user guide (Analog Devices wiki): P1 pin table; Pmod 3.3 V supplied by the host.
- Analog Devices no-OS ADXL355 driver: first SPI byte is `(address << 1) | 1` for a read, `(address << 1)` for a write.
- ESP-IDF v6.1 SPI Master documentation (ESP32-S3): SPI2 IO_MUX pins CS0 10, MOSI 11, SCLK 12, MISO 13.
- ESP32-S3-DevKitC-1 v1.1 user guide (Espressif): J1/J3 header tables; GPIO35–37 used by octal flash/PSRAM.
