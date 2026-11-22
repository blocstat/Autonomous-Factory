# Phase 0b results — second phone session, 22 November 2026

**Data origin:** `phone`. All captures are real measurements from the Galaxy S22 Ultra's built-in accelerometer (phyphox, "Acceleration (with g)"). They are **not** from the product sensor (ADXL355), not synthetic, and not evidence about any industrial machine.

**Raw data:** `data/measured/phone/raw/20261122-*_phone_*.csv` (9 files). File names were corrected by Claude to match what was done (see "File notes").
**Analysis:** `python python/scripts/analyze_phone.py data/measured/phone/raw/20261122-*.csv --shaft-hz 23.3`, plus band levels and time-sliced spectra computed with the same `af_signal` functions, run by Claude in a Linux cloud container on 22 November 2026. The 100 s baseline was cut into three 30 s pieces (5–35, 35–65, 65–95 s) for the repeat comparison.
**Previous session:** `docs/PHASE0B_RESULTS_2026-11-20.md`.

## Summary

| Question | Answer |
| --- | --- |
| Did the new mount fix the problems from 20 November? | **Yes.** No spikes, and the remount spread is about 30× smaller. |
| Where did the 65–68 Hz peak come from? | **The cooling pad's mesh top.** It is gone with the phone off the mesh. |
| Is the fan's 1× peak visible? | **No.** The 19–26 Hz band does not change when the fans are unplugged. |
| Can the phone tell fans on from fans off? | **Yes.** Unplugging the fans lowers z RMS from 0.0126 to 0.0096 m/s², mostly at 55–80 Hz and 110–130 Hz. |
| What was the 20.2 Hz peak in the baseline? | **The building's washing machine** (spin cycle, 1,212 RPM), confirmed by Rami. Not the fan. |

## Setup (as recorded)

- **Fan:** Havit HV-F2056 cooling pad, all three fans on (no per-fan switch), powered from a USB port on a power bar. Speed tag `high` is the only speed.
- **Board:** the pad stands on a bamboo board, which rests on rubber corner caps on the desk.
- **Phone:** out of its case, **screen down** on the board beside the pad (not on the mesh), inside a tape outline, with a small gap to the pad. Mount tag `board-beside-down`. Screen down was needed because, screen up, the phone rocks on its camera bumps.
- **Laptop:** on the desk during `off` and `remount`; removed for `baseline` and `unplug-test`; put back for `baseline-laptop`.
- **Washing machine:** running in the building during `baseline` (12:50). Not noted for the other captures.

| File (condition) | What was done |
| --- | --- |
| `off` r1–r3 | Fans unplugged, 30 s each. |
| `remount` r1–r3 | Fans on, phone lifted and replaced on the tape between 30 s runs. |
| `baseline` r1 | Fans on, one 100 s run, phone untouched (split into three 30 s pieces for analysis). |
| `unplug-test` r1 | Fans on, 60 s run; fan USB cable unplugged at about 30 s without touching the phone or board. |
| `baseline-laptop` r1 | Fans on, laptop back on the desk, 60 s run. |

## Results

Vertical axis (z), mean removed, m/s². Sampling was 419.98–420.08 Hz, jitter ≤ 0.12 %, on every capture.

| Condition | z RMS | z kurtosis | Strongest z peak, Hz |
| --- | --- | --- | --- |
| off (r1, r2, r3) | 0.0085, 0.0089, 0.0088 | 3.0, 5.3, 5.0 | 38.2, 59.3, 59.3 |
| remount (r1, r2, r3) | 0.0108, 0.0120, 0.0110 | 2.9, 3.9, 3.1 | 57.3, 58.1, 58.8 |
| baseline (3 pieces) | 0.0116, 0.0114, 0.0117 | 3.1, 3.0, 3.0 | 59.1, 59.1, 20.2 |
| baseline-laptop | 0.0113 | about 3 | 58.8 |

Comparison with 20 November (phone in its case on the mesh):

| | 20 Nov | 22 Nov |
| --- | --- | --- |
| Captures with kurtosis > 100 | 6 of 15 | 0 of 9 |
| Remount spread, z RMS | 0.094–0.133 | 0.0108–0.0120 |
| 65–68 Hz peak with fans on | strong | gone |
| 35 Hz background with fans off | present | not seen |

### Unplug test

Same capture, phone untouched: fans on (5–28 s) versus fans off (33–56 s), z band RMS in mm/s².

| Band, Hz | Fans on | Fans off | Ratio |
| --- | --- | --- | --- |
| 19–22 and 22–26 (1× range) | 1.64, 1.85 | 1.67, 1.98 | about 1.0 |
| 55–62 | 4.90 | 2.06 | 2.4 |
| 62–80 | 5.61 | 3.01 | 1.9 |
| 110–130 | 4.84 | 2.27 | 2.1 |
| 200–210 | 1.61 | 0.61 | 2.6 |
| **Total z RMS** | **12.6** | **9.6** | 1.3 |

### What the data shows

1. **Mounting is now repeatable.** On the stiff board, remount changes the level by about ±5 %, compared with ±20 % on the mesh. This is the main lesson for attaching the real sensor: mount on a stiff surface, not a thin panel.
2. **The 65–68 Hz peak was the mesh.** With the phone off the mesh it disappears, so it was the panel's response, not a property of the fans.
3. **The fans' 1× is not visible on this setup.** The 1× band is unchanged when the fans stop. Small, balanced fans produce very little 1× force, and three fans at slightly different speeds spread it further.
4. **The fans are still detectable.** They raise the 55–80 Hz and 110–130 Hz bands about 2× and the 200–210 Hz band about 2.6×. The 200–210 Hz rise is probably blade-pass (9 blades × about 23 Hz), but it sits at the phone's 210 Hz limit, so it is not measured reliably.
5. **The phone picked up a washing machine elsewhere in the building.** A steady 20.20 Hz peak on all three axes (about 4.6 mm/s², about 14× the fans-off level) appeared only during the 12:50 baseline. It was absent in the unplug test and in `baseline-laptop`. Rami confirmed a washing machine was running; 20.2 Hz is 1,212 RPM, a typical spin speed. This is a reminder that the environment can add a stronger, steadier tone than the machine being measured.
6. **A weaker 57–59 Hz peak appears with the fans off too** (`off` r2, r3), and drifts between captures. Part of it is the fans (it drops at the unplug), part is something in the building. Not identified.
7. **The laptop's weight made no visible difference.**

## Acceptance criteria (from the session guide)

- [x] Raw files in `data/measured/phone/raw/`, named with `_phone_`, labelled `data_origin: phone`.
- [x] `summary.csv` reports the actual sample rate and jitter.
- [x] 1× peak: **not identified**, with reasons (point 3); fan presence shown by the unplug test instead.
- [x] Remount spread recorded: z RMS 0.0108–0.0120.
- [x] Imbalance test: **not run**, as advised for this pad.
- [x] Safety: no deviations; fans unplugged at the USB connector, nothing touched while running.
- [x] This note.

## File notes

Original names on Rami's Mac were corrected when committing: `off` files had spaces instead of underscores; `off` and `remount` had mount tag `block-flat` (they were screen down on the board, as z ≈ −9.65 m/s² confirms) and `remount` had speed `samespeed`; `unplug-test` and `baseline-laptop` had no date stamp, so their stamps (13:18, 13:21) come from the file export times. The `baseline` r1 file is one 100 s capture; `analyze_phone.py` treats it as one capture, and the three-piece split above was done separately.

## What this does and does not show

It shows the phone, on a stiff mount, gives repeatable readings and can tell the fans on from off. It does **not** show that the method can detect imbalance or any fault, and it says nothing about industrial machines or about the ADXL355. Phase 0b's purpose (rehearse capture, labelling and analysis; learn about mounting) is met. Next step is the real sensor: Phase 1 with the ESP32-S3 and ADXL355, mounted on a stiff surface.
