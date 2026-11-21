# Phase 0b — Phone accelerometer session

**Goal:** collect the project's first real (not synthetic) vibration data with the Galaxy S22 Ultra's built-in accelerometer, and run it through the same analysis code. This is a rehearsal of mounting, labelling and analysis before buying the ADXL355. See `docs/SYSTEMS_ENGINEERING_REVIEW.md` sections 4.1 and 4.2.

**Time:** about 2 hours. **Cost:** $0 if you already own a fan.

Every file from this session is labelled `data_origin: phone`. Phone data is a real measurement, but from the phone's sensor, not the product sensor. It must never be presented as ADXL355 data or as evidence about any industrial machine.

## What to expect (assumptions, not results)

- The phone chooses its own sample rate and timestamps are irregular. The analysis script measures and reports both; don't assume a rate.
- A fan at 1,000–2,000 RPM has its 1× peak at about 17–33 Hz. That should be visible if the phone samples at even ~100 Hz.
- The blade-pass tone (blades × shaft speed, often 100–250 Hz) may sit above half the phone's sample rate. If so it will be missing or folded to a wrong frequency (aliasing). Note it, don't interpret it.
- Phone mass, the case and loose contact will damp and colour the signal. That is part of what this session teaches.

## 1. Equipment

- Galaxy S22 Ultra with **phyphox** installed (free, from the Play Store).
- A fan. Two options:
  - **Preferred:** a 12 V PC case fan powered by a certified 12 V DC wall adapter, with a finger guard, screwed or clamped to a rigid block.
  - **Acceptable:** an ordinary desk fan, used as sold. With a mains-powered desk fan, **do not add masses to the blades and do not open or remove the guard.** Run only the baseline, speed and remount captures.
- Masking tape to mark the phone position. Optional: a small piece of putty for the PC-fan imbalance test.
- Safety glasses for any run with an added mass.
- A way to note the fan speed. A PC fan datasheet gives RPM per setting; a desk fan's speed is unknown, so record the setting (1/2/3).

## 2. Safety rules

1. Unplug the fan before touching it, placing masses, or adjusting anything.
2. Added masses only on the low-voltage PC fan, small and firmly attached. A loose mass becomes a projectile. Guard on; wear safety glasses while it runs.
3. Never exceed the fan's rated voltage. Never modify a mains-powered appliance.
4. Fan on a stable, clamped base; cables away from the blades; the phone never touching the blades.
5. If anything rattles, wobbles badly or smells hot, unplug and stop.

## 3. Set up phyphox

1. Open phyphox → **Acceleration (with g)**. This uses the raw accelerometer. Gravity shows as a constant offset that the analysis removes. ("Without g" is filtered by the phone and less suitable here.)
2. Menu (⋮) → **Timed run**: start delay **5 s**, duration **30 s**. The delay lets you put the phone down without your hand in the data.
3. Put the phone in **airplane mode** and turn off auto-rotate, so notifications and screen changes don't interfere.
4. Take the phone out of its case if practical, and keep that choice the same all session.

## 4. Mounting

- Lay the phone **flat, screen up, on the fan's base** (or on the clamped block next to a PC fan), in the same orientation every time. Mark its outline with tape so remounts are comparable.
- With the phone flat, the **z axis** is vertical. Most fan vibration on a base shows up in z; x and y are logged too.
- Don't touch the table during a capture. Don't run other machines nearby.

## 5. Captures

Do the runs in this order. Three repeats each (`r1`, `r2`, `r3`), 30 s each.

| # | Condition label | What to do | Fan |
| --- | --- | --- | --- |
| 1 | `off` | Fan unplugged. Measures the phone's noise floor on this surface. | any |
| 2 | `baseline` | Fan on, each speed setting. | any |
| 3 | `remount` | One speed; lift the phone and put it back on the tape mark between repeats. | any |
| 4 | `imbalance-small` | Unplug, fix a small mass near one blade tip, then run each speed. | **PC fan only** |
| 5 | `baseline-after` | Unplug, remove the mass, rerun one speed. Checks the fan returned to normal. | **PC fan only** |

That is about 15–30 captures. Keep notes as you go: time, condition, speed, anything unusual.

## 6. Export and file naming

After each capture: menu (⋮) → **Export data** → **CSV (Comma, decimal point)** → share to Google Drive or email it to yourself. (The analysis also reads the semicolon / decimal-comma and tab formats, but comma is simplest.)

Rename each file to:

```text
YYYYMMDD-HHMM_phone_<condition>_<speed>_<mount>_r<N>.csv
```

- `condition`: `off`, `baseline`, `remount`, `imbalance-small`, `baseline-after`
- `speed`: `low`, `mid`, `high`, `s1`/`s2`/`s3`, or RPM such as `1500rpm`
- `mount`: short tag for how the phone sits, e.g. `base-flat`, `block-flat`
- lowercase, hyphens inside a field, underscores between fields

Example: `20261120-1030_phone_baseline_high_base-flat_r1.csv`

If phyphox exports a `.zip` with several files, keep the accelerometer CSV.

Put the files in the repository at:

```text
data/measured/phone/raw/
```

Files that don't match the pattern are still analysed but marked `UNLABELLED`.

## 7. Analyse

From the repository root, in Cursor's terminal:

```bash
source .venv/bin/activate
python python/scripts/analyze_phone.py data/measured/phone/raw/*.csv
```

If you know the fan speed, add the shaft frequency (RPM ÷ 60) to report the 1× level:

```bash
python python/scripts/analyze_phone.py data/measured/phone/raw/*.csv --shaft-hz 25
```

Outputs, in `data/measured/phone/out/` (git-ignored, regenerate anytime):

- `summary.csv`: one row per capture. Includes the measured sample rate, timing jitter, longest gap, and per axis: RMS, crest factor, kurtosis, strongest frequency above 3 Hz, and 1× level if `--shaft-hz` was given. The first line is `# data_origin: phone`.
- One spectrum PNG per capture, titled "PHONE accelerometer (data_origin=phone), not the product sensor".

## 8. Acceptance criteria (from the review's sprint, session 6)

- [ ] Every raw file is in `data/measured/phone/raw/` and named with `_phone_`.
- [ ] `summary.csv` reports the phone's actual sample rate and jitter.
- [ ] The 1× peak is identified in the baseline captures, **or** there is a written reason it wasn't (e.g. unknown speed, too noisy).
- [ ] For the PC fan: the 1× level for `imbalance-small` compared with `baseline` at the same speed, with the spread across the three repeats shown alongside. A difference smaller than the repeat-to-repeat spread is not a detection.
- [ ] `remount` spread recorded: this is the first measure of how much mounting alone changes the result.
- [ ] Safety rules in section 2 followed; any deviation written down.
- [ ] A short note (a few lines in `docs/` or the weekly review) with what was observed, including what didn't work.

Don't draw conclusions about real machines from this session. It tests the method, not a product.
