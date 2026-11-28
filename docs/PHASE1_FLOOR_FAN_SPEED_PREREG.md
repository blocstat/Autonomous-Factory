# Floor fan, speed test: does carton on the intake speed the fan up? (pre-registered)

**Status:** the rule was fixed on 28 November 2026, after midnight Toronto time, before any data for this test exists. It comes from a lead found **after** session 2's data (`docs/PHASE1_FLOOR_FAN_SESSION2_RESULT_2026-11-27.md`), so only new captures can confirm it. Rami can change anything here until the first capture. After that, nothing changes.
**Test object:** the same household 12" floor fan (AC-30S, 120 V), mount `fan-box-top`, knob 3. A result says what this sensor sees on this fan. It is **not** evidence of fault detection or predictive maintenance on machines.
**Time needed:** about 1 hour 10 minutes.

## The question

With the carton over the bottom third of the rear intake, does the fan turn faster than without it? Session 2 read 23.00 Hz in 4 of 6 carton captures and in none of 12 without. That difference was only one step of the old 0.12 Hz speed grid.

A partly blocked intake moves less air, so the motor has less load and less slip. A small speed-up is therefore plausible. It is not the same thing as "the sensor sees the carton through vibration".

## What is new: a finer speed estimate

`python/af_signal/fine_speed.py` estimates the speed of each 30 s capture about 50 times more finely than the old grid:

- **One FFT over the whole capture.** It uses a single Hann window, zero-padded to 2²¹ points, with x, y and z magnitudes added.
- **Peak refinement.** The 1×, 2×, 3× and 6× lines are each refined with a 3-point parabola.
- **Combining the lines.** Lines more than 10× above their local floor are kept. They are averaged as f_k / k, weighted by k².
- **Synthetic check.** On synthetic signals it recovers the speed within 0.002 Hz, and it separates a 0.25 % step (`python/tests/test_fine_speed.py`).

On the session 1 and 2 captures, it shows that the real speed wanders: 30 s captures in the same block differ by up to about 0.1 Hz (0.5 %). That is why each block uses 3 captures and takes their median.

Seen with this estimate, after the data, session 2 gives:
- **Round 1:** +0.08 % against the blocks around it.
- **Round 2:** +0.83 %.

The lead is mixed, which is why it needs a proper test.

## Safety and setup (same as session 2)

- **Never open anything.** Don't open the motor, the switch box or the wiring. Both guards stay on.
- **Unplug before touching the carton.** Unplug the fan before putting the carton on or taking it off.
- **Carton placement.** The carton goes only on the **outside** of the rear guard, on its corner marks. Its top edge stays below the motor cover, and it is taped along the top. Nothing goes on the blades.
- **Same setup.** Same place, same sensor outline, and the ESP32 on the stool, not touching the fan. TV, washer and dishwasher off. Nobody near the fan during captures.
- **Cold start.** The fan should not run for 30 minutes before the session.

## Captures

All are 30 s, with `--port /dev/cu.usbserial-0001 --mount fan-box-top`. Every block from 2 to 10 starts the same way: knob to 0, unplug, carton on or off (or hands on the guard for 30 s if it stays off), plug in, knob 3, wait 3 minutes, then 3 captures.

| # | Block | `--condition` | Repeats |
| --- | --- | --- | --- |
| 0 | Mount check, fan unplugged | `fan-off` | r1 |
| 1 | Cold start, 10 min | `warmup` | r1, `--seconds 600` |
| 2 | N0, no carton | `no-carton` | r1–r3 |
| 3 | C1, carton | `carton` | r1–r3 |
| 4 | N1, no carton | `no-carton` | r4–r6 |
| 5 | C2, carton | `carton` | r4–r6 |
| 6 | N2, no carton | `no-carton` | r7–r9 |
| 7 | C3, carton | `carton` | r7–r9 |
| 8 | N3, no carton | `no-carton` | r10–r12 |
| 9 | C4, carton | `carton` | r10–r12 |
| 10 | N4, no carton | `no-carton` | r13–r15 |
| 11 | End check, fan unplugged | `fan-off` | r2 |

- **Each block is its own restart.** Carton and no-carton blocks alternate, so any slow drift over the session (warming, mains voltage) affects both alike.
- **Failed captures.** A capture that fails the data path is re-taken with the next repeat number, and both files are kept. The script leaves out bad-data and bumped captures by itself.

## The rule (fixed now)

Code: `python/af_signal/fine_speed.py` (`speed_verdict`) and `python/scripts/fan_speed_test.py`.

- **Block value:** the median fine speed of the block's clean captures. A block needs at least 2 clean captures.
- **Carton rounds:** for i = 1 to 4, d_i is C_i compared with the mean of the no-carton blocks just before and after it, in %. Taking the mean of the two neighbours cancels a steady drift.
- **No-carton controls:** for j = 1 to 3, e_j is N_j compared with the mean of N_{j-1} and N_{j+1}, in %. These show how much a block moves with no carton, from restarts and uneven drift.
- **One-sided test.** The lead predicts a speed-up.

Verdict:

1. **INCONCLUSIVE** if any block has fewer than 2 clean captures with a fine speed.
2. **NOT DETECTED** if the mean of d is below **+0.4 %**.
3. **DETECTED** if the mean of d is at least +0.4 %, **every** d_i is above 0, **and** the mean of d is larger than every |e_j|.
4. **INCONCLUSIVE** otherwise.

**Why +0.4 %.** In session 2, the four no-carton block medians spread by 0.22 % (standard deviation), mostly from restarts.
- **Noise level.** A d_i then scatters by about 0.27 %, and the mean of four by about 0.13 %. With no real effect, the mean of d passes +0.4 % with a chance well under 1 %, and all four d_i come out positive with a chance of 1 in 16.
- **Power.** If the true speed-up is about 0.45 % (the average of session 2's two rounds), the test passes about 5 times in 10. If it is 0.8 %, it passes about 97 times in 100. These figures come from a simulation of the rule (4,000 runs each); with no effect it gave DETECTED 0.2 % of the time.

## Running it

```bash
cd autonomous-factory
python python/scripts/fan_speed_test.py data/measured/adxl355/raw/<date>-*_fan-box-top_*
cd python && python -m pytest -q tests/test_fine_speed.py   # synthetic known-answer tests
```

## Acceptance

- **Synthetic tests pass.** The speed is recovered within 0.002 Hz, and a 0.25 % step is resolved. A 0.8 % speed-up with drift gives DETECTED, no change gives NOT DETECTED, a wild no-carton block gives INCONCLUSIVE, and too few captures gives INCONCLUSIVE.
- **The session is complete** when every block from 2 to 10 has at least 2 clean, unbumped captures. The result note gives the verdict exactly as the script prints it.
