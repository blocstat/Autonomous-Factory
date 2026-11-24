# Phase 1 — next fan-pad session plan (left-fan confirmation, then frame mount)

**Status:** plan only. Nothing here has been measured yet. Written 24 November 2026 from the results in `docs/PHASE1_WEIGHT_TEST_2026-11-24.md` (PR #7, branch `phase1-weight-test`).
**Test object:** the Havit USB laptop cooling pad, **not an industrial machine**. A result here says what this sensor and mount can see on this pad; it is not evidence of fault detection on machines or of predictive maintenance.
**Time needed:** about 3 hours in total, in two parts that can be done on different days (Part A about 1 h 30 min, Part B about 1 h 30 min, plus an optional hour).

## Why this session

On 24 November a small taped screw on the **left fan** (nearest the sensor) gave a 26.3–26.5 Hz line on the y axis 8–9× above the floor in 2 of 3 captures, gone when the screw was removed. It was inconclusive because a fan line moved 1.9 % between the two baselines (limit 1 %). The same screw on the middle fan was not detected. A rub was detected easily.

This session answers two questions, in order:

1. **Part A:** is the left-fan 1× line from the screw repeatable? (two more screw on/off rounds, same mount)
2. **Part B:** does mounting the sensor on the pad's frame make the 1× line easier to see? (same protocol, new mount)

Do Part B only after Part A, whatever Part A's result: Part A's numbers are the board-beside reference that Part B is compared against.

## Rules decided before the data

These are fixed now, before any capture. The analysis script being written in a separate task applies rules like these; if its definitions differ in detail, the wording below is what counts for this session.

**Measure.** For each capture: the y-axis peak in **25.5–27 Hz** (µg/√Hz, Welch spectrum, as in PR #7), its frequency, the 800–1500 Hz z level (median of 1 s pieces), the 800–1500 Hz kurtosis, and the fans' blade-pass lines.

**Clean data.** Every capture must have 0 missing sets and 0 CRC errors. A capture that fails is re-taken (next `--repeat` number); both files are kept.

**Bumps.** A capture with 800–1500 Hz kurtosis above 5 counts as bumped (someone touched the desk or board). Take one extra capture of that condition straight away. The rule is judged on the unbumped captures; bumped files are kept and reported.

**Rub guard.** If any screw-on capture has the 800–1500 Hz z level above 1.5× the baseline block, the screw is touching something: stop, fix it, and the round does not count.

**Restart control (sham), new in this plan.** Unplugging and re-plugging the pad shifts fan speeds by 1–3 %, so the earlier "baselines within 1 %" rule fails on almost any test with several restarts. Instead, this plan adds one *sham* block: the pad is unplugged, the screw is picked up and put down beside the pad, the blade is touched as if placing it, and the pad is plugged back in **without** the screw. That measures directly what a restart alone does to the 25.5–27 Hz line. The blade-pass lines are still recorded and reported for every block.

**Decision (Part A and Part B alike).** Let *baseline level* be the mean y peak of the 3 baseline captures, and *baseline max* the highest of them.

| Outcome | Condition |
| --- | --- |
| **Confirmed** | Every screw-on capture (both rounds, 6 or more) has a y peak at least **3× the baseline level**, and every no-screw capture after the baseline (screw-off and sham, 9 or more) is no higher than the **baseline max**. |
| **Inconclusive** | Any sham capture reaches 3× the baseline level (a restart alone makes the line), or the rub guard trips and cannot be fixed, or fewer than 2 clean, unbumped captures remain in any block. |
| **Not confirmed** | Anything else, for example one screw-on capture below 3×, or a screw-off capture above the baseline max. |

The y axis and the 25.5–27 Hz band are kept from PR #7 so the result is comparable. If a fan's speed moves the left fan's line outside 25.5–27 Hz, that is reported, and the outcome is judged as written anyway.

## Safety (both parts)

- **Unplug the pad at the USB end** (the pad's own cable, at the laptop or charger) before touching anything near the fans. Keep the ESP32-S3's USB cable plugged in; it is a separate cable. Put a piece of tape labelled "PAD" on the pad's plug so the two are not confused.
- The screw is **fully covered in tape** (no metal showing), or use a small blob of putty of similar size instead. Same blade, same spot as on 24 November (top face, about halfway out).
- **Hand-spin check** before every plug-in: with the pad unplugged, turn the fan slowly through one full turn with a pencil on the hub. The screw stays put, nothing touches the frame, and no wire or tape is within reach of a blade.
- Cover off means the blades are exposed: **wear glasses**, keep face and fingers away from the open side while it runs, and do not reach over the running pad. If you hear a tick or rattle, unplug at the USB end and check.
- The setup runs from USB 5 V only. No mains wiring is opened or changed.

## Before you start (10 min)

```bash
cd "/Users/ramisaintus/Documents/the Autonomous factory company/autonomous-factory"
git checkout main && git pull
source .venv/bin/activate
ls /dev/cu.usb*                      # expect /dev/cu.usbserial-0001
```

- The board already has the step 3 stream firmware; no flashing needed.
- Close `idf.py monitor` if it is open (only one program can hold the port).
- Check the fan connectors inside the pad are pressed fully in (the 24 Nov slowing was probably a loose one).
- Have ready: taped screw (or putty), pencil, glasses, phone for photos, a clock.

Every capture below is one 30 s run of `capture_adxl355.py` (about 45 s with the board reset). `--repeat` only sets the `rN` number in the file name, so each block runs it three times. The script refuses to overwrite a file; if it says the name exists, use the next number.

---

## Part A — confirm the left-fan result (about 1 h 30 min)

**Setup:** exactly as on 24 November: sensor taped on the bamboo board about 1 cm from the pad's edge, mount tag `board-beside`, cover off. Check the tape is still holding and the sensor has not moved (compare with the 23 November photo). If you have to re-tape it, take a photo and say so in the notes.

### A1. Warm-up and steady check (20 min)

Plug the pad in and start a timer. Do not touch the desk or board from here on except to change the screw.

At **5 min** and again at **15 min**:

```bash
python python/scripts/capture_adxl355.py --port /dev/cu.usbserial-0001 \
  --condition steady-check --mount board-beside --repeat 1 \
  --note "Part A warm-up, 5 min after plug-in, no screw, cover off"
# at 15 min: same command with --repeat 2 and "15 min" in the note
```

Then post "steady check done" in the project chat; Claude can read the two files from the Mac and compare the blade-pass lines in a few minutes. Continue straight to A2 without waiting: the steady check is reported with the results, it does not stop the session.

### A2. Baseline, no screw (3 min)

Right after A1, without unplugging:

```bash
for r in 1 2 3; do
  python python/scripts/capture_adxl355.py --port /dev/cu.usbserial-0001 \
    --condition baseline --mount board-beside --repeat $r \
    --note "Part A baseline, no screw, pad running since warm-up, cover off"
done
```

### A3. Round 1: screw on, then off (2 × 10 min)

1. Unplug the pad at the USB end. Put the taped screw on the **left fan** (nearest the sensor). Hand-spin check. Plug in. **Wait 5 min.**
2. Capture:
   ```bash
   for r in 1 2 3; do
     python python/scripts/capture_adxl355.py --port /dev/cu.usbserial-0001 \
       --condition screw-left --mount board-beside --repeat $r \
       --note "Part A round 1, taped screw on left fan, 5 min after plug-in"
   done
   ```
3. Unplug. Remove the screw (and its tape). Hand-spin check. Plug in. **Wait 5 min.**
4. Capture with `--condition baseline-after --repeat 1, 2, 3` and the note `"Part A round 1, screw removed, 5 min after plug-in"`.

### A4. Sham restart (10 min)

Unplug. Pick up the screw, touch the left fan's blade at the same spot as if placing it, put the screw back down **beside** the pad. Hand-spin check. Plug in. **Wait 5 min.** Capture:

```bash
for r in 1 2 3; do
  python python/scripts/capture_adxl355.py --port /dev/cu.usbserial-0001 \
    --condition sham-restart --mount board-beside --repeat $r \
    --note "Part A sham: unplugged and handled, no screw, 5 min after plug-in"
done
```

### A5. Round 2: screw on, then off (2 × 10 min)

Same as A3, with `--repeat 4, 5, 6` for both `screw-left` and `baseline-after`, and `round 2` in the notes.

### A6. Wrap up (5 min)

Unplug the pad. Take one photo of the setup. Post in the project chat: "Part A done", plus anything unusual (a bump, a noise, a re-take, a moved wire). Claude then analyses the 20 files with the rules above and writes the result note. **Do not change the rules after seeing the data.**

**Part A total:** 10 (prep) + 20 + 3 + 20 + 10 + 20 + 5 ≈ **1 h 30 min**.

---

## Part B — sensor on the pad's frame (about 1 h 30 min)

### B1. Mount the sensor (20 min, pad unplugged)

1. Unplug the pad at the USB end. Unplug the ESP32-S3's USB too while you move the sensor wires.
2. Choose a spot on a **flat, solid part of the pad's plastic frame** (not the mesh: in Phase 0b the mesh added its own 65–68 Hz peak), as close as practical to the **left fan's** mounting, for example next to one of its screw posts, and at least 2 cm outside the circle the blades sweep.
3. Lay the EVAL-ADXL355-PMDZ flat on that spot and tape it down the same way as on the board (clear tape across the top, pressed firmly at both ends). Keep the same orientation as on the board if the spot allows; either way, photograph it with the x and y arrows on the sensor visible.
4. Route the wires along the frame away from every fan opening. Tape them to the frame every few cm, leave a slack loop, then tape them to the bamboo board before they go to the ESP32-S3, so a tug on the wires cannot pull the sensor. Nothing may hang over a fan.
5. Hand-spin check on **all three** fans. Plug the ESP32-S3 back in.
6. The pad stays on the bamboo board on its rubber corner caps, as before.

New mount tag: **`frame-left`**. Results with this mount are compared only with `frame-left` baselines, never directly with `board-beside` levels, because the floor and the resonances will be different.

### B2. Mount check, fans off (2 min)

Pad still unplugged:

```bash
python python/scripts/capture_adxl355.py --port /dev/cu.usbserial-0001 \
  --condition fans-off --mount frame-left --repeat 1 \
  --note "Part B mount check, pad unplugged, sensor taped on frame near left fan"
python python/scripts/analyze_adxl355.py data/measured/adxl355/raw/*_adxl355_fans-off_frame-left_r1.csv
```

Pass: the data-path checks (missing sets, CRC, rate) say PASS. The noise-floor check may say CHECK because of building vibration; that alone is fine. If the data path fails, re-seat the wires and repeat before going on.

### B3 to B7. Same protocol as Part A (about 1 h 10 min)

Repeat A1 to A6 exactly, with `--mount frame-left` in every command and `Part B` in every note: warm-up and steady check (20 min), baseline ×3, round 1 (screw-left ×3, baseline-after ×3), sham-restart ×3, round 2 (screw-left r4–r6, baseline-after r4–r6), wrap-up photo and message.

Part B uses the **same decision rule** as Part A. Part B also reports, for each block, how far the y line stands above its local floor, so the two mounts can be compared side by side. The frame mount counts as **better** for this purpose only if Part B is Confirmed **and** the median peak-to-floor ratio of its screw-on captures is higher than Part A's. If Part A is not Confirmed but Part B is, that is reported as "frame mount sees it, beside does not", from one session.

### B8 (optional, only if there is an hour left). Middle fan on the frame mount

The middle fan's screw was not detected beside the pad. With the sensor still on the frame near the left fan, repeat one round (baseline ×3, screw on **middle** fan ×3 as `--condition screw-middle`, baseline-after ×3) with the same rule but one round only, so the outcome can be at most "seen once", not Confirmed.

---

## What is not in this plan

- No new firmware, dependencies or purchases.
- No new fault types; the rub is already detected and is not re-tested here.
- No machine learning or automatic alarms. If Parts A and B both confirm, the next step is still a written result note and a decision with Rami, not a detector.

## After the session

Claude copies the captures from the Mac, applies the rules above (using the analysis script once it is merged), and opens a results PR with a dated note in the style of `PHASE1_WEIGHT_TEST_2026-11-24.md`: plan and rule first, then the numbers, then what it means. Every figure in that note comes from the captures; nothing is filled in from this plan.
