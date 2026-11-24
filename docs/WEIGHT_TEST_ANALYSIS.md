# Weight-test analysis script

One command turns a weight test's captures into **PASS / NOT DETECTED / INCONCLUSIVE**, using rules fixed in code before the next session's data exists. It replaces the manual analysis done for `docs/PHASE1_WEIGHT_TEST_2026-11-24.md`.

Scope: one bench test on the Havit USB cooling pad. It is **not** fault detection on machines and not predictive maintenance.

- Code: `python/af_signal/weight_test.py` (measurement and rules), `python/scripts/weight_test.py` (command line).
- Tests: `python/tests/test_weight_test.py` (**synthetic** signals, labelled `data_origin: synthetic`), `python/tests/test_weight_test_measured.py` (the real 24 Nov captures).
- No new dependencies (NumPy and SciPy, already in `requirements.txt`).

## How to run it (next session)

Captures in time order. With the usual `--condition` names (`baseline`, `baseline-after`, `sham-restart` = no weight; `steady-check` and `fans-off` are refused; anything else, e.g. `screw-left` = weight on), the files group themselves:

```bash
cd autonomous-factory
python python/scripts/weight_test.py data/measured/adxl355/raw/20261125-*_adxl355_*.csv
```

If a baseline is reused or the names are off, name the groups yourself, in order:

```bash
R=data/measured/adxl355/raw
python python/scripts/weight_test.py \
  --off $R/20261124-1109_*.csv $R/20261124-1110_*.csv \
  --on  $R/20261124-114[34]_*.csv \
  --off $R/20261124-115[23]_*.csv
```

One weighted group (off / on / off) uses the **detect** rule; two or more (off / on / off / on / off) use the **confirm** rule. `--rule` forces one, `--axis` changes the decision axis (default `y`; choose it before the data). Exit code: 0 PASS, 1 NOT DETECTED, 2 INCONCLUSIVE, 3 bad input. About 2 s for 15 captures.

## What it measures

| Quantity | How |
| --- | --- |
| Fan speeds | Each fan makes lines at 2×, 4×, 6× and 9× (blade pass, 9 blades) its speed (seen 23 Nov). For every candidate speed 18–32 Hz, the geometric mean of the x+y+z spectrum over its running median at those four lines; peaks ≥ 2.0, strongest 3 kept. Done on each group's mean spectrum. The 1× line is not part of this score, so the line under test does not steer its own search. |
| 1× level | Peak within ±0.3 Hz of every fan speed tracked anywhere in the test; the strongest on the decision axis. Every capture uses the same windows, so on and off captures are compared like for like, and the windows move with the fans instead of being fixed bands. |
| Rub band | 800–1500 Hz RMS (4th-order band-pass), median of 1 s pieces, z axis. |
| Data path | `missing_sets`, `crc_errors`, `sequence_gaps`, `restarts`, `frames_flagged_overrun`, `frames_flagged_dropped` all 0. |

Spectra: Welch, Hann, 32,768 points (0.12 Hz bins), first 0.5 s skipped; each file's own `odr_estimate_hz` (4,009.4–4,010.1 Hz on 24 Nov; 4,010.3 Hz if missing).

## Rules (agreed 24 Nov before the data, as coded)

- **Bad data** in any capture → INCONCLUSIVE.
- **Rub** DETECTED when every weighted group's rub band is more than 1.5× every unweighted group's. A rub makes the imbalance verdict INCONCLUSIVE (the 1× rule assumes nothing touches).
- **Detect (A-B-A).** INCONCLUSIVE if a fan's speed differs by more than 1 % between the two baselines, or fewer than 2 fans can be matched between them. Otherwise PASS if the weighted group's 1× median minus the first baseline's median is larger than the largest difference between any baseline capture and any baseline-after capture; else NOT DETECTED.
- **Confirm (A-B-A-B-A).** PASS if **every** weighted capture's 1× is at least 3× the first baseline's median, and **every** later unweighted capture is below that same 3× threshold; else NOT DETECTED. Speed drift is printed as a warning only: the confirm rule written before the data has no drift limit, and every restart moves the fans 1–3 %.

Two readings of the agreed wording:

1. **"Back within the baseline range"** is coded as *below the 3× threshold* (approved by Rami, 24 Nov 2026). Read literally (no higher than the highest of the 3 first-baseline captures), it fails about 2 times in 3 on noise alone: each new capture has a 1-in-4 chance of beating the highest of 3, and there are 6 later baseline captures. The synthetic test `test_confirm_rule_passes_when_every_round_agrees` is such a case.
2. **"Differs between baseline and baseline-after"** (detect rule, not yet confirmed by Rami) is coded as the largest capture-to-capture difference, not the difference of the two medians. With medians only, every one of the five 24 Nov tests showed some "growth", including the three where nothing changed.

## Validation on the real 24 Nov captures

`data_origin: adxl355`, measured. "Doc" is the written conclusion in `docs/PHASE1_WEIGHT_TEST_2026-11-24.md`.

| Test | Script: 1× (y) | Script: verdict | Doc |
| --- | --- | --- | --- |
| Two bags, 07:11 / 07:31 / 07:42 | 22 → 21 → 24 µg/√Hz, not grown | **Rub DETECTED** (8.7×); imbalance INCONCLUSIVE | Rub detected; imbalance untested |
| Tape, middle fan, 07:42 / 08:13 / 08:20 | 39 → 26 → 25, not grown | INCONCLUSIVE: fan speed moved 4.0 % | Not detected; drift (+4 %) larger than the tape |
| Screw, middle fan, 08:20 / 08:37 / 08:49 | 29 → 30 → 34, not grown | INCONCLUSIVE: only 1 fan tracked in both baselines | Not detected; fans slowed 5–10 % |
| Taped screw, middle fan, 10:32 / 10:47 / 11:09 | 29 → 39 → 45, not grown | INCONCLUSIVE: fan speed moved 2.8 % | Inconclusive (2–3 %), not detected |
| Taped screw, left fan, 11:09 / 11:43 / 11:52 | 27 → **108** → 22, grown (at 26.3–26.6 Hz) | INCONCLUSIVE: fan speed moved 1.5 % | 1× appears at 26.3–26.5 Hz; inconclusive (1.9 %) |

The script agrees with every written conclusion. Where the doc said "not detected" for the tape and the first screw, those tests were judged before the 1 % drift rule existed; under today's rules they are INCONCLUSIVE, and the 1× did not grow in either.

**Dry run of the confirm rule on the left-fan round** (`--rule confirm`): NOT DETECTED, because r2 with the screw reads 47 µg/√Hz against a threshold of 81 (3 × 27). r1 and r3 read 108 and 115. So the confirm rule, as written, fails if even one weighted capture is as weak as today's r2. That is the rule doing its job, but worth knowing before the session.

## Limits

- Which tracked speed belongs to which physical fan is not known. The 24 Nov speeds are about 19–21, 25–27 and 28–31 Hz; the 23 Nov session found 23.8, 25.2 and 25.7 Hz with a different method. The 1× decision does not depend on this (it takes the strongest window), but the drift check matches speeds by nearness, which can pair the wrong lines when two fans are within about 1 %.
- Tracking constants (comb score 2.0, ±0.3 Hz, 18–32 Hz) were set while looking at the 23–24 Nov captures. The decision thresholds (1 %, 1.5×, 3×) were not; they come from the rules agreed before the data.
- 30 s captures give 6 spectral averages; one bumped capture can move its own 1× value, which is why the rules use medians (detect) or name every capture (confirm).

## Acceptance tests

```bash
cd autonomous-factory/python
python -m pytest -q tests/test_weight_test.py tests/test_weight_test_measured.py   # 19 passed
python -m pytest -q                                                                  # whole suite, all pass
cd ..
R=data/measured/adxl355/raw
python python/scripts/weight_test.py --off $R/20261124-1109_*.csv $R/20261124-1110_*.csv \
  --on $R/20261124-114[34]_*.csv --off $R/20261124-115[23]_*.csv; echo "exit $?"
# expect: 1x median 27 -> 108 -> 22, "grown", VERDICT INCONCLUSIVE (fan speed moved 1.5 %), exit 2
```
