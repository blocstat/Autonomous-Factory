# Floor fan, session 2: result (27 November 2026)

**Verdict by the pre-registered rule: NOT DETECTED.** A piece of carton covering the bottom third of the rear intake did not change the 10–1000 Hz y level by 1.25×, in either round.

**What this is:** measured data (`data_origin: adxl355`, uncalibrated, ±8 %) from the household 12" floor fan (AC-30S, 120 V), with the sensor on the switch box top (`fan-box-top`). The rule was fixed before the data, in `docs/PHASE1_FLOOR_FAN_SESSION2_PREREG.md` (PR #12, merged at 21:25 Toronto, before the first capture at 22:22). This is a household fan, not a machine. The result says what this sensor sees on this fan, and nothing about faults or prediction.

## Session

- Rami ran it on 27 Nov, 22:22–23:41 Toronto. Captures were taken from Claude through Remote Control on Rami's Mac.
- The carton was trimmed so its top edge sits below the motor cover. It was held by two ties and taped along the top, with its corners marked on the guard.
- Every block from 2 to 7 started the same way: knob to 0, unplug, carton on or off (or hands on the guard for 30 s), plug in, knob 3, wait 3 minutes, then 3 × 30 s captures.
- **Data path.** All 30 s captures are clean (0 missing sets, 0 CRC errors, 0 gaps, 0 restarts), and none was bumped (z kurtosis 2.93–3.05).
- **The first warm-up stopped at 322 s.** The board stopped sending with no restart and no data lost before the stop. The Mac did not sleep, and the USB device stayed attached. The cause is unknown.
  - A 10 s stream check (kept, `stream-check`, not used by the rule) and a full 10-minute repeat (`warmup` r2, fan already warm) were both clean.
  - The warm-up is descriptive only, so the rule doesn't use it.

## The rule's output

```
round 1: cardboard vs baseline:         n 3 vs 2/3 speed-matched, speed +0.54 %, RMS y 1.10x, 1x y 0.87x
round 2: cardboard vs sham restart:     n 3 vs 3/3 speed-matched, speed +0.53 %, RMS y 1.00x, 1x y 1.03x
sham restart vs baseline-after 1:       n 3 vs 3/3 speed-matched, speed +0.00 %, RMS y 1.00x, 1x y 0.99x
baseline-after 1 vs baseline:           n 3 vs 3/3 speed-matched, speed +0.54 %, RMS y 1.04x, 1x y 0.89x
baseline-after 2 vs sham restart:       n 3 vs 3/3 speed-matched, speed -0.54 %, RMS y 0.96x, 1x y 0.98x

VERDICT: NOT DETECTED
```

- **The guards all passed.** Every no-carton comparison stayed within 1.04×, so this session's restarts were quieter than session 1's.
- **Round 1:** one carton capture (23.00 Hz) was more than 1 % above the baseline's 22.76 Hz, so it was left out, as the rule says. The other two give 1.10×.
- **Round 2:** 1.00×.
- **Secondary measure:** the 1× line on y moved at most 0.87× / 1.03×, far from 1.5×.

## Per block (descriptive)

| Block | RMS y (µg) | Speed (Hz) |
| --- | --- | --- |
| 2 baseline | 43,129–43,565 | 22.76 ×3 |
| 3 carton, round 1 | 47,249–47,988 | 23.00, 22.88, 22.88 |
| 4 carton off | 44,463–45,327 | 22.88 ×3 |
| 5 sham restart | 44,395–45,961 | 22.88 ×3 |
| 6 carton, round 2 | 44,622–45,380 | 23.00 ×3 |
| 7 carton off | 42,655–43,295 | 22.88, 22.76, 22.76 |

## Found after the data (leads, not evidence)

- **Speed.** With the carton on, the speed read 23.00 Hz in 4 of 6 captures. Without it, it never did (0 of 12 since block 2). That fits a small speed-up when the intake is partly blocked, because a fan moving less air has less load. But it is one spectral bin (0.12 Hz, 0.5 %), at the limit of the current speed estimate. A test of this would need a finer speed estimate (for example a longer FFT or peak interpolation) and its own pre-registration.
- **Paired level.** Compared with the carton-off block straight after it, the y level was 6 % and 4–5 % higher with the carton. That is far below the 1.25× pass mark, and about the size of the spread between restarts.
- **Tilt.** The sensor's x gravity reading moved by about 18 mg (about 1°) between block 0 and the warm-up repeat, then stayed put. The sensor or the box seems to have shifted slightly early in the session. Noise and the 800–1500 Hz band at the end check match block 0.

## What it means

- **With this mount and this measure, a third of the intake blocked is not visible.** The airflow change is smaller than the 1.25× mark set from session 1's spreads.
- **This change is a weak test.** A change that moves the rotor's load or balance more would test the sensor better, but nothing goes on the blades of a mains fan. The next step is Rami's choice: stop the fan series, or pre-register the speed lead with a finer speed estimate.

## Files

23 captures in `data/measured/adxl355/raw/20261127-22*` and `20261127-23*`. The two warm-ups are stored gzipped.

```bash
cd autonomous-factory
ls data/measured/adxl355/raw/20261127-2[23]* | grep -v stream-check | xargs python python/scripts/fan_change_test.py
```
