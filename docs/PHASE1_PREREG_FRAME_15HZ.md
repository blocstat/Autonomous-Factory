# Pre-registration: screw on the left fan, sensor on the frame, 13–19 Hz line

Written on 25 November 2026, **before** the session it describes. Nothing in this file may change after the first capture of that session. If something must change, write the change and its reason here with a date and time **before** looking at the new data.

## Why this test

On the night of 24–25 November (`docs/PHASE1_FRAME_MOUNT_2026-11-25.md`), with the sensor on the pad's frame, a line at 14.7–17 Hz on z rose 12–25× in all 6 captures with the screw on, and fell back without it. That band was found **after** looking at the data. With 3 axes and hundreds of bands, something can look different by chance, so last night is a lead and not a result.

This session tests that lead with the band, axis and pass mark written down first. If it passes, it is the first time this setup has detected a deliberate change (a screw on one fan blade) by a rule fixed in advance. If it fails, the lead was not reliable, and nothing gets built on it.

Scope: one USB laptop cooling pad on a desk. A PASS says nothing about industrial machines, other faults, or predicting failures.

## Hypothesis

With the sensor on the frame beside the left fan, the taped screw on the left fan makes the z peak between 13 and 19 Hz at least 3× its no-screw level, every time the screw is on, and it falls below that every time the screw is off.

What the 15 Hz line physically is (half the fan's speed, a rocking pad, the taped sensor) is **not** tested here.

## Setup (same as Part B on 25 Nov)

- Pad on the bamboo board, bottom cover off, TV and appliances off.
- Sensor taped flat on the frame beside the left fan, the same spot as on 25 Nov (`docs/img/frame_mount_setup_2026-11-25_0017.jpg`), chip end taped, about 5 mm off the fan's ring. Mount tag `frame-left`.
- The same small screw, fully taped, on the same spot of the same left-fan blade.
- Fan connectors pressed in. The safety rules from 24 Nov still hold: the screw fully taped, cover off only while the pad is watched, hands away from the blades when it runs.

## Captures (30 s each, `python/scripts/capture_adxl355.py`)

| # | Block | `--condition` | Repeats | Before it |
| --- | --- | --- | --- | --- |
| 0 | Mount check, fans off | `fans-off` | 1 | — |
| 1 | Steady check | `steady-check` | 1 | 5 min running |
| 2 | Baseline | `baseline` | r1–r3 | right after the steady check |
| 3 | Screw on | `screw-left` | r1–r3 | unplug, add the screw, plug in, 5 min running |
| 4 | Screw off | `baseline-after` | r1–r3 | unplug, remove the screw, plug in, 5 min |
| 5 | Sham restart (no screw) | `sham-restart` | r1–r3 | unplug, touch nothing, plug in, 5 min |
| 6 | Screw on | `screw-left` | r4–r6 | as block 3 |
| 7 | Screw off | `baseline-after` | r4–r6 | as block 4 |
| 8 | Optional: tap test, fans off | `tap-test` | 1 | tap a pad corner lightly a few times; not part of the decision |

About 1.5 hours. Blocks 0, 1 and 8 are checks and are not part of the decision; the script refuses `fans-off` and `steady-check` files in a decision run, so leave them out of the command.

## The decision (fixed in code, `python/af_signal/weight_test.py`)

Command, run once on blocks 2–7, nothing else:

```bash
cd autonomous-factory
python python/scripts/weight_test.py --axis z --band 13 19 \
  data/measured/adxl355/raw/<date>-*_adxl355_{baseline,screw-left,baseline-after,sham-restart}_frame-left_r*.csv
```

| Item | Rule |
| --- | --- |
| Measure | Per capture: the highest z value of the spectrum between 13 and 19 Hz (Welch, Hann, 32,768 points, first 0.5 s skipped), in µg/√Hz. |
| Baseline level | Median of the 3 baseline captures (block 2). |
| **PASS** | Every screw-on capture (r1–r6) is **≥ 3×** the baseline level, **and** every later no-screw capture (blocks 4, 5, 7) is **below** 3×. |
| NOT DETECTED | Any screw-on capture below 3×, or any later no-screw capture at or above 3×. |
| INCONCLUSIVE | Any capture with a missing set, CRC error, sequence gap, restart, overrun or dropped word; or a rub (see below); or every capture of a block is a bump. |
| Bumps | A capture whose 800–1500 Hz z kurtosis is above 5 (a knock on the desk) is reported and left out of the decision. |
| Rub guard | Rub = every screw-on block's 800–1500 Hz z level (median of 1 s pieces) is more than 1.5× **every** no-screw block's level. See "One rule to confirm" below. |
| Reported only | The same command with `--band 26 34` (the line at about twice 15 Hz), the tracked fan speeds, x and y. None of these changes the verdict. |

## One rule to confirm before the session

The 25 Nov plan compared the rub level with the **baseline block only**, and r6 tripped it at 1.54× (limit 1.5×). But no-screw blocks that night also varied up to 1.45× (screw-off round 1: 5.9 mg against 4.1 mg baseline), with no knocks (kurtosis 3.0–3.4). On the frame, the high band moves that much without any rub. The script compares each screw-on block with **every** no-screw block instead. That still catches a real rub (24 Nov: 8.7×) and does not trip on the normal spread. **Rami decides which one applies;** the code currently does the second.

## Dry run on the 25 Nov captures (not evidence)

The same command on the 25 Nov frame-mount captures gives PASS: baseline 653 µg/√Hz, threshold 1,960; screw on 13,055–16,177 (r1–r3) and 7,683–10,239 (r4–r6); no-screw 536–1,527. This only shows the code does what this file says. Those captures are where the band came from, so they cannot confirm it.

The closest call that night was screw-off round 1 at 1,386–1,527 (2.1–2.3×, with a peak at 18.2–18.4 Hz, near the band's top). A similar block in the new session would still be below 3×, but not by much.

## Acceptance tests for the code

```bash
cd autonomous-factory/python
python -m pytest -q tests/test_weight_test.py        # synthetic, includes 6 fixed-band tests
python -m pytest -q tests/test_weight_test_measured.py  # real captures; the 25 Nov dry run skips if those files are not in the checkout
```
