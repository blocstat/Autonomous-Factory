# Phase 1 — ADXL355 bring-up on the ESP32-S3

**Goal:** get the product sensor (ADXL355) talking to the ESP32-S3 over SPI, and prove it with known answers before any vibration data is trusted. Steps 1 and 2 (toolchain, wiring, ID and gravity) passed on 22 November 2026. Step 3 streams every sample at 4,000 per second over USB into Python and measures the noise floor at rest.

**Time:** step 1 about 1 hour (mostly download), step 2 about 1 hour, step 3 about 45 minutes. **Cost:** $0, the parts are already here.

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

This applies to the step 1–2 firmware only. The step 3 firmware sends binary data, which `idf.py monitor` shows as garbage; read it with the capture script in step 3.

### Pass/fail checks

| Check | Pass | If it fails |
| --- | --- | --- |
| **ID** | `AF,id,devid_ad=0xAD,devid_mst=0x1D,partid=0xED,…,result=PASS` | All `0x00` or all `0xFF`: power or MISO/CS problem. Check 3V3, GND, MISO, CS. Mixed wrong values: SCLK/MOSI swapped or a loose wire. The firmware retries every 2 s, so you can fix a wire (with USB unplugged) and replug. |
| **Gravity, sensor at rest** | The total, √(x² + y² + z²), is **1.0 g** within 0.92–1.08 (the ±8 % tolerance), with most of it on one axis. Small values on the other axes are tilt: a Pmod board held by its jumper wires rarely sits level (0.1 g is about 6°). | Turn the sensor board on its side: the 1 g should move to another axis. If nothing changes, write down what you see. |
| **Temperature** | Between 15 and 40 °C, and roughly room temperature | Write it down; it is uncalibrated. |
| **Stability** | Readings change by less than about 0.01 g between lines while nothing is touched | Write down the spread. |

`REVID` is printed for the record; any value is accepted.

Record the result in the thread: the `AF,id` line and about 10 `AF,sample` lines with the board flat. Those become the first ADXL355 verification record in `docs/DEVELOPMENT_SETUP.md`.

## Step 3 — Stream every sample and measure the noise floor

**What it does.** The firmware reads the ADXL355's FIFO every millisecond and sends every x/y/z sample (4,000 per second, 1,000 Hz low-pass, ±2 g) to the Mac in small binary packets with a checksum, on the same USB cable and port you flash with (`/dev/cu.usbserial-0001`), at 921,600 baud. Once per second it adds a text status line with counters (FIFO overruns, dropped words, SPI errors) and the temperature. A Python script records the stream into a CSV file of raw counts and checks it.

**What it proves.** That no sample is lost between the sensor and the Mac, that the sample rate is what the sensor's clock allows, and that the noise floor at rest is close to the data sheet's 22.5 µg/√Hz. It says nothing about a fan or a machine yet; that comes after this passes.

Wiring is unchanged from step 2. Use the board that passed step 2.

### 3.1 Get the code and the one new Python package

```bash
cd ~/"Documents/the Autonomous factory company/autonomous-factory"
git fetch
git checkout phase1-adxl355-stream
source .venv/bin/activate
python -m pip install -r python/requirements.txt
python -m pytest python -q
```

The new package is `pyserial` (reads the USB port). **Pass:** pytest ends with `73 passed`.

### 3.2 Build and flash

The streaming firmware needs a 1 ms scheduler tick, a setting that only takes effect in a fresh `sdkconfig`. So delete the old one first (if you forget, the build stops with "CONFIG_FREERTOS_HZ must be 1000").

```bash
source "$HOME/.espressif/tools/activate_idf_v6.1.1.sh"
cd firmware
rm -f sdkconfig
idf.py set-target esp32s3
idf.py build
idf.py -p /dev/cu.usbserial-0001 -b 115200 flash
cd ..
```

Use `flash` only, not `flash monitor`. **Pass:** `Hash of data verified` and `Hard resetting via RTS pin...`.

### 3.3 Record three captures at rest

Set up:

1. Sensor board flat on the desk, as in step 2. Nothing touching it, including the jumper wires (tape the wires to the desk a few cm from the board if they pull on it).
2. Fans off. Washing machine off if you can. Don't type on or bump the desk during a capture.
3. No `idf.py monitor` running: only one program can open the port.

Run, from the repository root (the virtual environment still active):

```bash
python python/scripts/capture_adxl355.py --port /dev/cu.usbserial-0001 --condition rest --mount desk-flat --repeat 1
```

The script resets the board, prints the `AF,id` line, records 30 seconds (progress every 5 s), saves the file and prints the checks. Then run it twice more with `--repeat 2` and `--repeat 3`, without moving anything.

Files:

- `data/measured/adxl355/raw/YYYYMMDD-HHMM_adxl355_rest_desk-flat_r1.csv`: raw counts for every sample plus every status line, labelled `data_origin: adxl355`. About 3 MB each.
- `data/measured/adxl355/out/…_noise.png`: noise density plot (not committed; recreate any time).

To re-check saved files later: `python python/scripts/analyze_adxl355.py data/measured/adxl355/raw/*_adxl355_rest_*.csv`.

### Pass/fail checks (printed by the script)

| Check | Pass | If it fails |
| --- | --- | --- |
| **Missing sets** | 0 | Samples were lost on the way. Try another USB port on the Mac (no hub) and repeat. |
| **CRC errors** | 0 | Bytes were corrupted on the cable. Same as above; a different USB-C cable is the next thing to try. |
| **FIFO overruns, dropped FIFO words** | 0 | The board fell behind the sensor. Check that you deleted `sdkconfig` before building (3.2). |
| **SPI errors** | 0 | A loose wire. Unplug USB, check the step 2 wiring, repeat. |
| **Output data rate** | 3,944–4,056 Hz (4,000 Hz ±1.4 %, the data sheet's clock tolerance) | Write down the value. Outside this range means the rate is not what we think it is; stop and report it. |
| **Gravity at rest** | Total 0.92–1.08 g, as in step 2 | Same as step 2. |
| **x, y, z noise density** | Median from 10 to 800 Hz between 5 and 45 µg/√Hz (the data sheet's typical is 22.5; the first board measured 12–17) | Above 45 shows as **CHECK**: almost always vibration from the room or desk, not the sensor. Look at the plot for peaks, move the board to a heavier surface (floor tile, kitchen counter) and repeat. Below 5 is a **FAIL**: the data is probably stuck or wrong. |
| **Temperature** | 15–40 °C | Uncalibrated; write it down. |

**Step 3 passes** when all three captures say `OVERALL: PASS` (or `CHECK` only on noise, with a peak you can explain). The three captures should agree with each other on noise within about 20 %.

### Troubleshooting

- *"Cannot open /dev/cu.usbserial-0001 … Resource busy":* close `idf.py monitor` (Ctrl+]) or any other terminal using the port.
- *"No sample frames within 10 s":* if the `AF,id` line says FAIL, it's wiring (step 2 table). If nothing printed at all, the firmware may not be flashed, or the board didn't reset: run the script with `--no-reset` and press **RST** right after starting it.
- *The stream stops mid-capture:* the board restarted or the cable moved. The script saves what arrived and says so; repeat the capture.

### What to send back

Say "done" in the thread. Claude reads the three CSV files from the repository folder on the Mac, checks the numbers and adds them to `docs/DEVELOPMENT_SETUP.md` as the first full-rate ADXL355 record.

## What step 2 proves and does not prove

It proves the wiring, the SPI settings and the data decoding (ID registers are fixed values; gravity is a known 1 g input). It does not test sample rate, noise or vibration: that is step 3 above.

## Sources

- ADXL354/ADXL355 data sheet, Rev. D (Analog Devices): register map, SPI mode 0 and 0.1–10 MHz clock, 20-bit two's-complement data, 256,000 LSB/g typical at ±2 g, supply 2.25–3.6 V. FIFO: 96 words, x-axis marker in bit 0 and empty marker in bit 1 of each word, FIFO_DATA does not auto-increment. Noise density 22.5 µg/√Hz typical at ±2 g. Internal clock ±1.4 % device to device.
- EVAL-ADXL355-PMDZ user guide (Analog Devices wiki): P1 pin table; Pmod 3.3 V supplied by the host.
- Analog Devices no-OS ADXL355 driver: first SPI byte is `(address << 1) | 1` for a read, `(address << 1)` for a write.
- ESP-IDF v6.1 SPI Master documentation (ESP32-S3): SPI2 IO_MUX pins CS0 10, MOSI 11, SCLK 12, MISO 13.
- ESP32-S3-DevKitC-1 v1.1 user guide (Espressif): J1/J3 header tables; GPIO35–37 used by octal flash/PSRAM.
