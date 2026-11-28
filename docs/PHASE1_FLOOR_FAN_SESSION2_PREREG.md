# Floor fan, session 2: does cardboard on the intake show? (pre-registered)

**Status:** rule fixed on 27 November 2026, before any session 2 data exists. The numbers come from session 1 (`docs/PHASE1_FLOOR_FAN_RESULTS_2026-11-27.md`). Rami can still change anything here until the first session 2 capture. After that, nothing changes.
**Test object:** the same household 12" floor fan (AC-30S, 120 V). A result says what this sensor sees on this fan. It is **not** evidence of fault detection or predictive maintenance on machines.
**Time needed:** about 1 hour 15 minutes.

## The question

Taping stiff cardboard flat on the **outside** of the rear guard, over about a third of the intake, changes the airflow and the load on the motor. With captures compared only at a matching speed, does the overall vibration level change by more than anything changed on its own in session 1?

## Safety (same rules as session 1)

- Never open the motor, the switch box or the wiring. Both guards stay on.
- **Unplug the fan before putting the cardboard on or taking it off.** Hands go near the guard only when it is unplugged.
- Cardboard only on the **outside** of the rear guard, taped at all four edges so it can't be pulled in. Nothing on the blades.
- Tilt knobs tight, head level, cord away from the blades. Stop if anything looks damaged or the motor smells hot.
- Don't leave the cardboard on for more than about 15 minutes at a time. A partly blocked intake makes the motor work a little harder; the fan is thermally protected, but there's no reason to push it.

## Setup

- Same place (taped feet), same mount `fan-box-top` on the drawn outline. Same USB cable as the end of session 1.
- TV, washer and dishwasher off for the whole session. Nobody walking near the fan during a capture. Guitar away.
- Cardboard cut and tape strips ready before the fan starts, so each swap is quick.
- Fan cold: not run for 30 minutes before.
- Knob at **3** for every running capture.

## Captures

All 30 s, with `--port /dev/cu.usbserial-0001 --mount fan-box-top`. Every block, including the baseline blocks, starts with the same steps (knob to 0, unplug, wait, plug in, knob to 3, wait 3 min), so every comparison crosses one restart on both sides.

| # | Block | `--condition` | Repeats | Before it |
| --- | --- | --- | --- | --- |
| 0 | Mount check | `fan-off` | r1 | fan unplugged, nobody touching anything |
| 1 | Warm-up | `warmup` | r1, `--seconds 600` | plug in, knob 3, start straight away (this is the 8-minute warm-up, measured) |
| 2 | Baseline | `baseline` | r1–r3 | knob 0, unplug, hands on the rear guard for 30 s (no cardboard), plug in, knob 3, wait 3 min |
| 3 | Cardboard, round 1 | `cardboard` | r1–r3 | knob 0, unplug, tape the cardboard on, plug in, knob 3, wait 3 min |
| 4 | Cardboard off | `baseline-after` | r1–r3 | knob 0, unplug, remove the cardboard, plug in, knob 3, wait 3 min |
| 5 | Sham | `sham-restart` | r1–r3 | knob 0, unplug, hands on the rear guard for 30 s (no cardboard), plug in, knob 3, wait 3 min |
| 6 | Cardboard, round 2 | `cardboard` | r4–r6 | as block 3 |
| 7 | Cardboard off | `baseline-after` | r4–r6 | as block 4 |
| 8 | End check | `fan-off` | r2 | unplug, wait 1 min |

Blocks 2–7 should run in one stretch without a long pause: session 1 showed the speed drifting 2.2 % over a day, and the rule needs captures within ±1 %.

A capture that fails the data path (missing sets, CRC errors, gaps, restarts) is re-taken with the next `--repeat` number, and both files are kept. The script leaves out bad-data and bumped captures by itself.

## The rule (fixed now)

Code: `python/af_signal/fan_change.py`, with `python/scripts/fan_change_test.py`. Measures as in session 1 (`af_signal/rotor.py`).

- **Primary measure:** 10–1000 Hz RMS on the **y** axis. Session 1's largest no-change spread for it was 1.11× (captures 4 hours apart). **Pass mark: a change of at least 1.25×, in either direction.**
- **Secondary measure, reported only:** the 1× line on y, against 1.5× (session 1's largest was 1.34×, after restarts). It does not decide the verdict.
- **Blade pass is not used:** restarts alone moved it 1.94×.
- **Speed matching:** a capture counts only if its speed is within **±1 %** of the median speed of the block it is compared with.
- **Comparisons**, each the ratio of block medians:
  - Round 1: cardboard (block 3) against baseline (block 2).
  - Round 2: cardboard (block 6) against sham (block 5).
  - Guards, which must all stay **under 1.25×** with ±1 % speed: sham against block 4, block 4 against baseline, block 7 against sham.

Verdict, checked in this order:

1. **INCONCLUSIVE** if any block has fewer than 2 clean, unbumped captures.
2. **SPEED SHIFTED** if, in either round, fewer than 2 cardboard captures are within ±1 % of the reference speed. The speed change is reported. This would mean the cardboard changes the speed itself, so a same-speed comparison can't be made. That is a finding, not a failure.
3. **INCONCLUSIVE** if any guard reaches 1.25×, or falls outside the speed window.
4. **DETECTED** if both rounds change by at least 1.25× in the same direction.
5. **NOT DETECTED** if neither round reaches 1.25×.
6. **INCONCLUSIVE** otherwise (the rounds disagree).

Post-hoc findings (another axis, another band, another line) are reported as leads for a later pre-registered test, never as a result.

## Running it

```bash
cd autonomous-factory
python python/scripts/fan_change_test.py data/measured/adxl355/raw/<date>-*_fan-box-top_*
cd python && python -m pytest -q tests/test_fan_change.py   # synthetic known-answer tests
```

## Acceptance

- The rule's synthetic tests pass: a 2.3× synthetic change gives DETECTED, no change gives NOT DETECTED, a +2.7 % speed change gives SPEED SHIFTED, a sham that moves gives INCONCLUSIVE, and bad data is left out.
- Session 2 is complete when every block has at least 2 clean, unbumped captures. The result note reports the verdict exactly as the script prints it.
