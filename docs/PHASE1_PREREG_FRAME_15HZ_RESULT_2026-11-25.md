# Result: pre-registered 13–19 Hz test, frame mount, 25 November 2026 evening

**Verdict: NOT DETECTED**, by the rule fixed in `docs/PHASE1_PREREG_FRAME_15HZ.md` before the session.

All 6 screw-on captures passed easily (11–50× the baseline). The rule still fails, because the 3 sham-restart captures (no screw, pad only unplugged and plugged back in) read 3.4–3.5× the baseline. The pass mark needed every no-screw capture below 3×. A restart alone pushed this band over the line, so the band cannot tell the screw from a restart by itself.

Data: `data_origin: adxl355`, measured on the bench, uncalibrated (±8 %). One USB cooling pad, not a machine. Nothing here is about fault detection or prediction on real equipment.

## Session

- 25 Nov 2026, 21:46–22:56 Toronto, run by Rami. Sensor on the frame beside the left fan (`frame-left`), as in the pre-registration. TV and appliances off.
- 22 captures in `data/measured/adxl355/raw/20261125-2[12]*`: mount check (fans off), two steady checks, and blocks 2–7.
- Data path: every capture used in the decision is clean (0 missing sets, CRC errors, sequence gaps, restarts, overruns, dropped words). Baseline r3 at 22:00 had 32 missing sets and 1 CRC error. It is kept on disk and replaced by its re-take at 22:03, per the amendment written at 22:06, before the decision measure was computed.
- Between blocks, only the data path, the rub band and kurtosis were checked. The 13–19 Hz values were first computed by the decision command below, run once after the last block.

## Decision command (as pre-registered)

```bash
cd autonomous-factory
R=data/measured/adxl355/raw
python python/scripts/weight_test.py --axis z --band 13 19 \
  $(ls $R/20261125-2[12]*_adxl355_{baseline,screw-left,baseline-after,sham-restart}_frame-left_r*.csv \
    | grep -v 20261125-2200_adxl355_baseline_frame-left_r3)
# VERDICT (13-19 Hz peak, z): NOT DETECTED, exit 1
```

## Numbers (z, peak between 13 and 19 Hz, µg/√Hz)

Baseline level 493 (median of 523, 493, 460), so the threshold is 1,478 (3×).

| Block | Captures | 13–19 Hz peak | × baseline | Peak at | Rule |
| --- | --- | --- | --- | --- | --- |
| 2 Baseline | r1–r3 | 460–523 | 0.9–1.1 | 14.6 Hz | sets the level |
| 3 Screw on | r1–r3 | 5,390–5,845 | 11–12 | 13.7–13.8 Hz | ≥ 3×: pass |
| 4 Screw off | r1–r3 | 492–598 | 1.0–1.2 | 15.8–16.3 Hz | < 3×: pass |
| 5 Sham restart | r1–r3 | **1,682–1,725** | **3.4–3.5** | 18.5–18.6 Hz | < 3×: **fail** |
| 6 Screw on | r4–r6 | 21,126–24,654 | 43–50 | 18.1 Hz | ≥ 3×: pass |
| 7 Screw off | r4–r6 | 499–771 | 1.0–1.6 | 16.2–16.5 Hz | < 3×: pass |

- Bumps: none. 800–1500 Hz z kurtosis was 3.0–3.5 in every capture, so nothing was left out.
- Rub guard: not tripped (the lowest screw-on block is 0.70× the highest no-screw block). Rub z by block: 3.80, 3.54, 4.34–4.41, 5.75–5.78, 5.72, 4.04 mg. The sham block had the highest level of the night without any screw.

Reported only, not part of the verdict:

- **26–34 Hz (z).** Baseline 126, screw on 317–440 (round 1) and 185–212 (round 2), no screw 145–261. No clear screw effect.
- **Tracked fan speeds** moved a lot between blocks: 26.5 and 27.3 Hz in the baseline, 20.8–26.6 Hz with the screw in round 1, 18.5–24.7 Hz in blocks 4–5, and 18.1–27.1 Hz in round 2. The tracker found no fans in block 7.

## What the numbers suggest (found after the verdict, so not evidence)

- The line is not fixed near 15 Hz. With the screw on, it sat at 13.7 Hz in round 1 and 18.1 Hz in round 2.
- In blocks 4–5 the tracker found a fan at 18.51 Hz, and the sham block's peak sits at 18.48–18.60 Hz. In round 2 a fan was tracked at 18.09 Hz, and the screw-on peak was at 18.11 Hz. So when one fan runs slow, its own speed line can fall inside 13–19 Hz, with or without the screw. The pre-registration warned about a close call near the band's top (25 Nov: 18.2–18.4 Hz at 2.1–2.3×). Tonight it went over.
- The screw does make a very large change on this mount (medians 11× and 47× the baseline in the two rounds; the weakest screw-on capture, 5,390, is still 3.1× the strongest sham capture, 1,725). But "how much bigger than a restart" was not the pre-registered measure, so it cannot be used to turn the verdict into a pass.

## What this means

- The lead from 25 Nov (a fixed 13–19 Hz z band) did not pass its own test. Nothing should be built on that band.
- What did repeat: on the frame mount, a taped screw on the left fan raises the low-frequency z level a lot in every capture. Whatever comes next has to separate that from a fan simply changing speed after a restart. The sham block is what caught this, and it should stay in any future plan.
- Any new rule (for example, comparing against the sham block, or following the line's frequency) would be a new hypothesis. It needs its own pre-registration and a fresh session, not tonight's data.

## Reproduce

```bash
cd autonomous-factory/python
python -m pytest -q tests/test_weight_test_measured.py   # includes this session's verdict as a regression test
```
