# Floor fan, session 1: results (27 November 2026)

**What this is:** measured data (`data_origin: adxl355`, uncalibrated, ±8 %) from a household 12" floor fan (AC-30S, 120 V), with the sensor taped on top of the switch box (`fan-box-top`). The plan is `docs/PHASE1_FLOOR_FAN_PLAN.md`. Session 1 **measures only and judges nothing**. Nothing here is about machines, faults or prediction.

**In one paragraph.** This fan's speed is easy to read in every capture. The three knob settings are 17.1, 19.9 and 22.4 Hz, with no overlap between them. From cold, the fan slows by about 5 % and settles after 7–8.5 minutes. With nothing touched, the 1× line, the 120 Hz line and the overall level repeat within about 1.2×. Remounting the sensor adds little. **Switching the fan off and on moves the 1× and blade-pass lines more** (up to 2.1× and 1.9×), even though the speed comes back to within one frequency bin. The overall 10–1000 Hz level and the 120 Hz line stay within about 1.15×, whatever was done. Vibration does not grow with speed: the 1× line on y is strongest at the middle setting. The tap test suggests a y resonance of the stand near 18.6 Hz.

## Session

- Rami ran it on 27 Nov, 11:15–20:40 Toronto. There was a pause of about 4 hours between block 5 and block 6, and of about 2.5 hours before the end check.
- Blocks 3–9 were captured from Claude through Remote Control on Rami's Mac. Rami turned the knob, remounted the sensor and said "ready". The wait times were as planned, except block 6, which waited 8 minutes after the 4-hour pause instead of 3, so the fan was warm again.
- Fan head level, tilt knobs tight. ESP32 on a stool beside the fan, not touching it. Guitar moved away.

### Data path

- **Every 30 s capture is clean** (0 missing sets, 0 CRC errors, 0 gaps, 0 restarts), including the mount check, tap test and end check.
- **The 10-minute captures lost data in short bursts.** 11:25 lost 1.6 s, 11:53 lost 1.9 s and 12:09 lost 0.4 s, at different moments in each file. The sensor itself reported no FIFO overruns and no dropped words, so the loss was between the USB cable and the laptop.
  - Rami changed the USB cable at about 12:56. Every capture after that is clean.
  - The warm-up analysis leaves out any 30 s piece that holds a gap. That rule was added to `rotor.warmup` before the warm-up measure was computed, with a synthetic test.
- **Extra warm-up files.** There are five warm-up files instead of one:
  - 11:24 was aborted after 9 s, with a restart.
  - 11:25 is the cold start.
  - 11:40 stopped after 69 s.
  - 11:53 and 12:09 are full 10-minute runs. 12:09 starts at 23.4 Hz, so the fan had been off long enough to cool.
  - All files are kept. The 11:25 file is the plan's block 2.

## Results

### Speed per setting

| Knob | Block | Speed (Hz) | rpm |
| --- | --- | --- | --- |
| 3 | 3 (13:00) | 22.39–22.51 | 1,343–1,351 |
| 2 | 4 | 19.94 (all 3) | 1,197 |
| 1 | 5 | 17.13–17.25 | 1,028–1,035 |
| 3 | 6 (17:17, after the pause) | 22.14–22.39 | 1,329–1,343 |
| 3 | 7, remounts | 22.15–22.27 | 1,329–1,336 |
| 3 | 8, sham restarts | 22.51–22.63 | 1,351–1,358 |

- The spectrum's resolution is 0.12 Hz (about 0.5 %). A spread of "0.00 %" or "0.54 %" means "the same bin" or "one bin apart".
- At setting 3, the speed ranged from 22.14 to 22.63 Hz over the day (2.2 %). The plan's tolerance of "about 1 %" would split captures taken at the same setting.

### Warm-up (30 s pieces, speed in Hz)

| File | Start | After 2 min | Final | Settled (within 0.5 %) |
| --- | --- | --- | --- | --- |
| 11:25 (cold start) | 23.37 | 22.51 | 22.15–22.27 | from 420 s |
| 12:09 (cooled again) | 23.37 | 22.64 | 22.39–22.51 | from 510 s |
| 11:53 (already warm) | 22.51 | 22.39 | 22.39 | from 330 s (essentially flat) |

The 1× y level rises during warm-up, from about 37,000 to about 65,000 µg/√Hz in the cold start. **Rule for session 2: wait 8 minutes after a cold start.**

### Spreads at setting 3 (max ÷ min within a block; x / y / z)

| What changed between captures | 1× | Blade pass | 120 Hz | 10–1000 Hz RMS |
| --- | --- | --- | --- | --- |
| Nothing (block 3, n=3) | 1.19 / 1.04 / 1.11 | 1.36 / 1.12 / 1.29 | 1.03 / 1.03 / 1.04 | 1.03 / 1.04 / 1.01 |
| Nothing (block 6, n=3) | 1.19 / 1.08 / 1.05 | 1.28 / 1.44 / 1.23 | 1.07 / 1.07 / 1.07 | 1.06 / 1.02 / 1.10 |
| Remount (block 7, n=4) | 1.35 / 1.12 / 1.23 | 1.19 / 1.37 / 1.14 | 1.08 / 1.10 / 1.09 | 1.06 / 1.02 / 1.03 |
| Off-and-on restart (block 8, n=3) | **2.09 / 1.34 / 1.45** | **1.76 / 1.94 / 1.90** | 1.01 / 1.01 / 1.11 | 1.15 / 1.03 / 1.12 |
| 4 hours apart (blocks 3 + 6, n=6) | 1.77 / 1.09 / 1.12 | 1.40 / 1.51 / 1.29 | 1.07 / 1.07 / 1.15 | 1.08 / 1.11 / 1.23 |

- Spread at the other settings, with nothing touched: speed 2 is at most 1.19× on every measure. Speed 1 is at most 1.21×, except the z 1× line, which is tiny there (870–1,420 µg/√Hz, near the floor).
- Knocks: 800–1500 Hz z kurtosis was 3.1–3.8 in every running capture, so there were no bumps.
- Remount spread is about the same size as the repeat spread on this mount. Restarts move the 1× and blade-pass lines more than remounts, even though the speed comes back to within one bin.

### Speed does not order the vibration

The 1× line on y is about 105,000 µg/√Hz at setting 2 (19.9 Hz), against about 67,000 at setting 3 and about 60,000 at setting 1. The overall y level is also highest at setting 2.

Found after the data, so not evidence: the tap test (fan off) shows a y peak at 18.6 Hz that the x and z axes don't show. The stand probably has a y resonance near 19–20 Hz, which setting 2 sits close to. This is exactly why the advice says to compare only at matching speeds.

## What this means for session 2

The rule chosen from these numbers is in `docs/PHASE1_FLOOR_FAN_SESSION2_PREREG.md`: 10–1000 Hz RMS on y, pass mark 1.25×, speed within ±1 %.

The session 2 change is cardboard on the outside of the rear guard. To count as detected, it must move a measure by more than the largest spread above, with captures compared only at a matching speed. From today's numbers:

| Candidate measure (setting 3) | Largest spread today, without any change | Possible pass mark |
| --- | --- | --- |
| 10–1000 Hz RMS, y | 1.11× (4 h apart) | change ≥ 1.25× |
| 1× line, y | 1.34× (restarts) | change ≥ 1.5× |
| Blade pass, any axis | 1.94× (restarts) | not usable: too unsteady |
| 120 Hz line | 1.15× | steady, but it comes from the mains, so it may not respond to airflow |

Two points to settle first:

1. **Speed tolerance.** Setting 3 itself wandered by 2.2 % over the day. A ±1 % window around a same-session baseline is still possible, if the baseline and the change are taken within an hour of each other, after the 8-minute warm-up.
2. **The change may move the speed.** Blocking the intake changes the motor's load, so the speed may shift by more than the tolerance. That would mean the speed-matched comparison cannot be made, which is a result in itself. Record the speed either way.

## Files

28 captures in `data/measured/adxl355/raw/20261127-*_fan-box-top_*`. The four warm-up files over 5 MB are stored gzipped (`.csv.gz`); the loader reads them directly. Re-running the script below on these files gives the numbers above.

## Reproduce

```bash
cd autonomous-factory
python python/scripts/fan_characterise.py data/measured/adxl355/raw/20261127-*_fan-box-top_*
```
