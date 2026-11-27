# Floor fan, session 1: learn the fan before judging any change

**Status:** plan only. Nothing here has been measured. Written 27 November 2026, from Rami's photos of the fan.
**Test object:** a household 12" floor fan. It is a stand-in until a real machine is available. A result here says what this sensor can see on this fan; it is **not** evidence of fault detection or predictive maintenance on machines.
**Time needed:** about 1 hour 10 minutes.

## Why this fan, and why this session

The cooling pad has three near-identical fans with no tach wire, and they change speed by 1–15 % on every restart. On 25 November a restart alone (no screw) pushed the pre-registered band over its limit (`docs/PHASE1_PREREG_FRAME_15HZ_RESULT_2026-11-25.md`).

This fan has one motor and one 3-blade rotor, so there is one speed to follow. Outside advice Rami received on 27 November says:

- log speed with every capture;
- compare only within matching speeds;
- start after warm-up;
- do remount runs first, before judging any change.

**Session 1 judges nothing.** It measures the numbers a change test needs:

1. The speed at each knob setting, and how much it moves between captures and between restarts.
2. How long the warm-up takes.
3. How much removing and re-taping the sensor moves the readings (remount spread).
4. How much switching off and on moves them (restart spread).

Session 2 will be a pre-registered change test whose pass mark comes from these numbers. It is outlined at the end and will be written down before its data exists.

## The fan (from the label)

| Item | Value |
| --- | --- |
| Type | 12" floor fan, model AC-30S, stock no. 51201 |
| Supply | 120 V AC, 60 Hz, 0.60 A, thermally protected, ETL listed |
| Date | 01-16 (2016) |
| Rotor | 3 blades, so blade pass = 3 × speed |
| Controls | rotary speed knob on the rear switch box; tilt knob on each side |

The label gives no speed. A small AC fan motor like this usually runs at about 900–1,700 rpm (15–28 Hz). Session 1 measures the real value. Expected lines: speed (1×), blade pass (3×), and 120 Hz (twice the mains frequency, from the motor's magnetic pull).

## Safety (mains-powered: these rules are not optional)

- **Never open the motor, the switch box or the wiring.** Do not remove either guard. Everything in this plan happens outside the guards.
- **Unplug the fan** before mounting or moving the sensor for the first time, and before touching anything near the guard other than the switch box top.
- **No weights, tape or putty on the blades.** This is the rule from November for mains fans: a mass thrown from a mains fan hits much harder than one from the USB pad.
- Check that the plug, the cord and the strain relief are undamaged, and that the cord can't reach the blades. If anything looks damaged, stop and don't use the fan.
- Tighten both tilt knobs before starting, so the head can't tip.
- Lint is visible on the motor. If you want to clean it, do so with the fan **unplugged**, with a vacuum or a dry brush from outside the guard. Don't open anything.
- Keep the sensor wires away from the guard openings, and tape them along the stand.

## Setup

- **Fan.** On the floor where it is now, the head level (tilt at 0°). Mark the four feet with tape, so the fan goes back to the same place. Nobody walks near it during a capture. TV, washer and dishwasher are off for the whole session (the rule from 25 November).
- **Sensor (mount tag `fan-box-top`).** See `docs/img/floor_fan_sensor_placement.jpg`. Taped flat on the top face of the black switch box on the rear guard, as close to the motor side as it fits. The box is screwed to the rear guard next to the motor bracket, outside the guard, and reachable without opening anything.
  - Put electrical tape under the board.
  - Tape the board down with clear tape over the top, as on the pad.
  - Draw the board's outline on the box with a marker, so each remount goes back to the same spot.
  - Take a photo of the mount before the first capture.
- **ESP32 and laptop.** On the floor or a chair beside the fan, not touching it. Leave the wires slack between the stand and the sensor, so they don't pull on the board.
- **Speed knob.** Check which positions are off, 1, 2 and 3. This plan assumes 0 = off and 3 = fastest.
- **Fan cold.** Don't run it for 30 minutes before the session, so the warm-up capture sees a real cold start.

## Captures

All commands are run from `autonomous-factory/`, with `--port /dev/cu.usbserial-0001 --mount fan-box-top`. Captures are 30 s unless a duration is given.

| # | Block | `--condition` | Repeats | Before it | Time |
| --- | --- | --- | --- | --- | --- |
| 0 | Mount check | `fan-off` | r1 | fan unplugged, nobody touching anything | 1 min |
| 1 | Tap test | `tap-test` | r1 | fan unplugged; during the capture, tap the stand's top tube lightly about 5 times | 1 min |
| 2 | Cold start | `warmup` | r1, `--seconds 600` | plug in, set speed 3, start the capture straight away | 10 min |
| 3 | Speed 3 | `speed-3` | r1–r3 | right after block 2 | 2 min |
| 4 | Speed 2 | `speed-2` | r1–r3 | set speed 2, wait 2 min | 4 min |
| 5 | Speed 1 | `speed-1` | r1–r3 | set speed 1, wait 2 min | 4 min |
| 6 | Speed 3 again | `speed-3` | r4–r6 | set speed 3, wait 3 min | 5 min |
| 7 | Remount | `remount` | r1–r4 | fan running at 3, guard on, hands only on the box top: peel the sensor, put it back on the outline, re-tape, then capture. Repeat 4 times. | 8 min |
| 8 | Restart (sham) | `sham-restart` | r1–r3 | knob to 0, wait 1 min, back to 3, wait 3 min, then capture. Sensor untouched. Repeat 3 times. | 14 min |
| 9 | End check | `fan-off` | r2 | unplug, wait 1 min | 2 min |

**Total:** about 55 minutes of captures, plus 15 minutes of setup.

Example command for block 4:

```bash
for r in 1 2 3; do
  python python/scripts/capture_adxl355.py --port /dev/cu.usbserial-0001 \
    --condition speed-2 --mount fan-box-top --repeat $r \
    --note "Floor fan session 1, speed 2, 2 min after switching"
done
```

Send "done" after each block. I check the data path (missing sets, CRC errors) and knocks (800–1,500 Hz kurtosis) before the next block, as on 25 November. A capture that fails the data path is re-taken with the next `--repeat` number, and both files are kept.

## Measures (fixed now, computed after the session)

These are measures only, with no pass mark. The spectrum is computed as in `af_signal/weight_test.py`: Welch, Hann, 32,768 points, first 0.5 s skipped, and each file's own `odr_estimate_hz`.

| Measure | Definition |
| --- | --- |
| **Speed f₀** | For every candidate f from 8 to 30 Hz, a score: the geometric mean, over the lines 1×, 2×, 3× and 6× f, of the x+y+z spectrum divided by its running median. f₀ is the best score, refined to the 1× peak within ±0.3 Hz. Reported in Hz and rpm. |
| **1× level** | Peak within ±0.3 Hz of f₀, on each axis. |
| **Blade-pass level** | Peak within ±0.5 Hz of 3 f₀, on each axis. |
| **120 Hz level** | Peak between 119 and 121 Hz, on each axis. |
| **Broadband** | RMS from 10 to 1,000 Hz, on each axis. |
| **Knocks** | 800–1,500 Hz z kurtosis; above 5 means a bump, reported and left out. |
| **Warm-up** | f₀ and the 1× level in each 30 s piece of block 2. *Settled* means f₀ stays within 0.5 % of its final value for 2 minutes. |
| **Spreads** | For each measure: max ÷ min within each block, and f₀'s range in %. Three numbers matter most: **repeat spread** (blocks 3 and 6, nothing touched), **remount spread** (block 7) and **restart spread** (block 8). |

The code is `python/af_signal/rotor.py` with `python/scripts/fan_characterise.py`, written before the session. The pad script assumed 9 blades and an 18–32 Hz range, so it could not be reused as is.

## What session 1 delivers

A short results note with:
- the speed at each setting;
- the warm-up time;
- the repeat, remount and restart spreads for each measure;
- how much each measure changes between speeds 1, 2 and 3.

From that, Rami picks session 2's measure and pass mark before session 2.

## Session 2 (outline only, not pre-registered yet)

- **Known, safe change:** a piece of stiff cardboard taped flat on the **outside** of the rear guard, covering about a third of the intake. It changes the airflow and the load on the motor, without touching the rotor or opening anything.
- **Protocol:** baseline / cardboard / off / sham restart / cardboard / off, as on 25 November, keeping the sham block.
- **Rule shape:** compare only captures whose speed is within a tolerance set from session 1 (probably about 1 %). A change counts only if it is larger than the largest of the repeat, remount and restart spreads.

## Running the measures

```bash
cd autonomous-factory
python python/scripts/fan_characterise.py data/measured/adxl355/raw/<date>-*_fan-box-top_*.csv
cd python && python -m pytest -q tests/test_rotor.py   # synthetic known-answer tests
```

## Acceptance

- Session 1 is complete when every block has at least 2 clean, unbumped captures and a mount photo exists.
- The helper script must pass its synthetic tests: a known speed and known levels are recovered within ±0.1 Hz and ±5 %.
