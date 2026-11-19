# Systems Engineering Review: ESP32-S3 Monitoring MVP

**Date:** 2026-11-18
**Author:** Claude (systems engineering review, per `docs/AI_STARTER_PROMPTS.md`)
**Inputs read:** `docs/MASTER_CONTEXT.md`, `CLAUDE.md`, `AGENTS.md`, `docs/WEEK_01_SPRINT.md`, `.cursor/rules/engineering.mdc`, and `../autonomous_factory_weekly_execution.md` (the V0.1 product spec lives there).
**Status:** Proposal for founder review. Nothing here has been built, purchased or measured. Two recommendations were accepted on 2026-11-18 (USB first; discovery in parallel); see section 8 and `docs/DECISIONS.md`. The rest are still proposals.

Every section separates three kinds of statement:

- **Fact:** stated in the project documents, or a published component property (marked *datasheet, verify* where I am quoting from memory and you should confirm against the current datasheet before relying on it).
- **Assumption:** something the plan depends on that has not been tested.
- **Recommendation:** my advice. You decide.

---

## 1. Summary

1. **The biggest risk is not technical.** Vibration and temperature monitoring for rotating equipment is a crowded, mature market (Schaeffler OPTIME, SKF, ABB, Siemens and many low-cost wireless sensors). The product hypothesis has no customer evidence yet. Customer discovery should run in parallel with the first hardware work, not after it.
2. **The V0.1 stack in the weekly execution plan contradicts MASTER_CONTEXT.** The weekly plan specifies MQTT + PostgreSQL + Grafana this week. MASTER_CONTEXT says USB serial first and MQTT "only when justified". I recommend following MASTER_CONTEXT: USB serial, files on disk, Python analysis. Defer MQTT/PostgreSQL/Grafana to Phase 3.
3. **"100 timestamped readings" is the wrong acceptance metric.** At 4 kSPS that is 25 ms of data. Use "N complete capture windows with zero dropped samples and verified sample rate" instead.
4. **The ADXL355 limits what faults you can see.** At its maximum 4 kHz output rate the usable bandwidth is roughly 1 kHz (*datasheet, verify*). That is enough for imbalance, misalignment and looseness on typical motors and fans. It is not enough for early bearing-defect detection, which typically relies on content in the multi-kHz range. This is fine for an MVP, but it narrows the product claim and must be stated.
5. **The safest useful first experiment uses no industrial machine at all:** a 12 V DC PC case fan with a tachometer wire, run from a certified low-voltage adapter, with controlled imbalance added to a blade. Before any purchase, the same experiment can be done with the Galaxy S22 Ultra's built-in accelerometer.
6. **Validate in this order:** known-answer tests on synthetic data, then acquisition integrity, then repeatability, then detectability of a controlled fault, then false-positive rate. No machine learning until a simple statistical baseline has been shown to fail for a documented reason.

---

## 2. Architecture challenge

### 2.1 Proposed pipeline (fact, from MASTER_CONTEXT)

Machine → Sensors → Signal conditioning → ESP32-S3 → Edge processing → Transport → Backend → Storage → Analytics → Dashboard → Human operator.

### 2.2 What I would change for the MVP (recommendation)

| Stage | As proposed | Recommended for MVP | Why |
|---|---|---|---|
| Sensor | ADXL355 + PT100/MAX31865 | ADXL355 only. Temperature deferred (use the ADXL355's on-die temperature for drift context only). | One sensor means one driver, one mounting problem, one calibration. PT100 adds a second analog chain with little value on a bench fan. |
| Edge processing | RMS, peak, crest, FFT on device | **None at first.** Stream raw samples; compute features on the Mac. Port to firmware only after Python features are validated. | You can't validate edge features without a trusted reference implementation. Python is that reference. |
| Transport | MQTT over Wi-Fi | USB CDC serial, framed binary with sequence numbers and CRC. | Deterministic, no network, no broker, no credentials. ~48 kB/s fits easily. |
| Backend / storage | PostgreSQL | Raw waveform captures as files (`.npz` or Parquet) + a `captures.csv` metadata index. | See data-volume note below. |
| Dashboard | Grafana | Matplotlib plots saved as PNG evidence artifacts. | The operator for now is you. |

**Data-volume note (calculation, not measurement):** 3 axes × 4,000 samples/s × 4 bytes ≈ 48 kB/s ≈ 173 MB/hour of raw data per device. Stored as one database row per sample that is about 12,000 rows/s, or ~43 million rows/hour. Raw waveforms do not belong in a relational database row-per-sample. The long-term pattern is: raw waveform snapshots to object/file storage, extracted features (a few numbers per window) to a time-series store. That is a Phase 3 decision.

### 2.3 Where the end-to-end ambition fits

A credible end-to-end demo for a customer conversation does not need a broker and a database. It needs: sensor on a machine → live plot → "baseline" → "deviation detected" with a measured false-positive rate. Build that first over USB. Adding MQTT later is a transport swap if the frame format is designed well (section 5.3).

---

## 3. High-risk assumptions

Ranked by how badly the project fails if the assumption is wrong.

| # | Assumption | Risk | How to test cheaply |
|---|---|---|---|
| A1 | SMEs have a monitoring problem they will pay a new entrant to solve, and the product can differentiate from incumbents. | **Critical.** No evidence yet. | Five discovery conversations before buying more than ~one sensor's worth of hardware. Ask what they monitor today, what failed last year, what it cost, who decides. |
| A2 | A bandwidth of ~1 kHz (ADXL355 at 4 kHz ODR) is enough to detect the faults customers care about. | **High.** Bearing faults, often the most valuable to catch early, typically need higher bandwidth or envelope analysis. | Ask in discovery which failure modes matter. Check against public bearing datasets sampled at 12 kHz+ by decimating them to 4 kHz and seeing what detectability is lost. |
| A3 | Measured vibration reflects the machine, not the mounting. | **High.** Breadboard wires, double-sided tape and loose brackets add resonances and damping that dominate the spectrum. | Mounting comparison test: same fan, three mounting methods, compare spectra. |
| A4 | Timestamps are "reliable". | **Medium-high.** The ADXL355 runs on its own internal oscillator; actual ODR deviates from nominal. Host timestamps on USB packets jitter by milliseconds. | Use sample index as the time base. Measure actual ODR against the host clock over ≥10 minutes. Count dropped samples via sequence numbers. |
| A5 | A baseline learned on one machine transfers to another. | **Medium-high.** Baselines are per machine, per mounting, per operating condition (speed, load). | Change fan speed and remount; quantify how much the baseline moves. |
| A6 | A Wi-Fi device will be allowed onto a plant network. | **Medium.** IT/OT policies often refuse it. | Ask in discovery. Keep the transport swappable (USB, Wi-Fi, later wired/gateway). |
| A7 | A dev board can go into a customer site. | **Medium.** It cannot without enclosure, EMC, power and environmental work. MASTER_CONTEXT already states this. | Keep pilots on non-critical, low-voltage, customer-supervised equipment, with professional review. |
| A8 | ~14 h/week covers firmware, signal processing, hardware and discovery. | **Medium.** It covers one of these well per week. | Each sprint picks one technical outcome plus a fixed discovery block. |
| A9 | Current sensing can be added later. | Low now, high later. Any mains-side current measurement is a safety issue. | Defer. If needed, only a non-invasive, rated clamp CT on equipment installed by a qualified person. |

---

## 4. Minimal sensors and a safe first experiment

### 4.1 Minimal sensor set (recommendation)

| Phase | Sensor | Cost | Purpose |
|---|---|---|---|
| 0 (now) | None. Synthetic signals. | $0 | Build and verify the analysis code against known answers. |
| 0b (now) | Galaxy S22 Ultra accelerometer, via a free logging app such as phyphox. | $0 | First **real** (not synthetic) vibration data. Teaches mounting, noise and labelling before any purchase. Label as `source=phone`, never as product-sensor data. |
| 1 | ADXL355 on an evaluation/breakout board, SPI to ESP32-S3. | Check current price before buying. | Product-candidate sensor. 20-bit, low noise, ±2/±4/±8 g ranges, 96-sample FIFO, max 4 kHz ODR (*datasheet, verify*). |
| 1 | Fan tachometer wire (free with a 4-pin fan). | $0 | **Ground-truth speed.** Lets you check that the FFT 1× peak matches the actual RPM. This is the cheapest validation signal available. |
| Later | PT100 + MAX31865, or a simpler digital sensor. | — | Only when a test needs temperature. |

**Note on the ADXL355 range:** ±8 g maximum (*datasheet, verify*) can clip on some industrial machines with impacts. Fine for a fan; revisit before a field pilot.

**Note on the ESP32-S3's internal ADC:** if an analog accelerometer is ever considered for higher bandwidth, the S3's built-in ADC is not suitable for precision vibration work; an external ADC would be needed. Another reason to stay with a digital SPI sensor for the MVP.

### 4.2 Safe first experiment: instrumented PC fan (recommendation)

**Rig:** a 120 mm, 4-pin 12 V DC PC case fan (has PWM speed control and a tachometer output), in its frame, with a finger guard, powered by a certified 12 V DC wall adapter. Fan frame screwed or clamped to a rigid block of wood or aluminium. No mains wiring is touched; the only mains contact is the adapter's own certified plug.

**Why a fan:** low voltage, low energy, cheap, guarded, has a known rotational speed, and produces clear 1× (shaft) and blade-pass peaks. At ~1,000–2,000 RPM the 1× peak is at ~17–33 Hz and blade-pass (7 blades) at ~117–233 Hz, both well inside the ADXL355's bandwidth. (Calculation; check your fan's actual blade count and speed.)

**Conditions:**

| Label | Change | Expected effect (hypothesis, to be tested) |
|---|---|---|
| `baseline_speed_low/mid/high` | PWM duty 30/60/100 % | 1× and blade-pass peaks move with speed |
| `imbalance_small` | Small mass (a few mm of putty or a short piece of tape) firmly attached near one blade tip | 1× amplitude rises |
| `imbalance_large` | ~2–3× that mass | 1× rises further |
| `loose_mount` | One frame screw loosened | Broadband/harmonic content rises |
| `remount` | Remove and reattach sensor | Measures repeatability, not a fault |

**Safety rules for this rig:**
- Unplug the adapter before attaching masses or touching the fan.
- Masses must be firmly attached and small; a detached mass is a projectile. Keep the guard on; wear safety glasses while the fan runs with added mass.
- Do not exceed the fan's rated voltage. Do not use a fan rated for mains voltage.
- Fan on a stable, clamped base; keep cables away from the blades.

**Precursor (Phase 0b, $0):** run the same rig, or a desk fan you already own, with the phone lying on the fan's base or the table. The data will be worse than the ADXL355 (lower sample rate, phone mass, poor mounting), and that is the point: it gives a first real dataset and exercises the full analysis code path.

---

## 5. Firmware architecture (recommendation)

### 5.1 Principles

- **ESP-IDF + FreeRTOS**, C (or a restrained subset of C++). No Arduino layer; it hides the timing you need to control.
- **Raw-first.** The firmware's only job in Phase 1 is to move every sample to the host, losslessly, with integrity metadata.
- **Sample index is the clock.** Each sample has a monotonic 64-bit index. Wall-clock time is attached per frame and is secondary.
- **Observable.** Every failure mode increments a counter that is sent to the host.

### 5.2 Tasks

```
ADXL355 ──SPI──► [ISR: FIFO watermark / DRDY GPIO]
                        │ task notify
                        ▼
              acq_task (highest app priority, pinned core 1)
                - burst-read FIFO over SPI
                - tag first_sample_index
                - push block into ring buffer (PSRAM)
                        │
                        ▼
              tx_task (core 0)
                - pop block, build frame, CRC32
                - write to USB CDC
                        │
              health_task (1 Hz)
                - counters: fifo_overflow, ring_overflow, spi_errors,
                  usb_backpressure, sensor_temp, uptime
              cmd_task
                - parse host commands: start, stop, set_odr,
                  set_range, set_pwm (fan speed), get_info
```

- **Ring buffer** sized for at least ~1 s of data (~48 kB) so that host-side stalls don't drop samples. PSRAM is available on the N16R8.
- **FIFO watermark** interrupt rather than per-sample DRDY at 4 kHz: fewer interrupts, fewer chances to miss one. (Verify the ADXL355 FIFO behaviour and watermark configuration against the datasheet.)
- **Fan PWM and tach** from the ESP32-S3 (LEDC for 25 kHz PWM, PCNT for tach pulses) lets the device log speed alongside vibration. Fan PWM/tach lines are low voltage; check the fan's datasheet for the tach pull-up voltage before connecting to a 3.3 V GPIO.

### 5.3 Frame format (draft)

```
magic(2) | version(1) | frame_type(1) | device_id(4) | seq(4)
first_sample_index(8) | n_samples(2) | odr_hz(2) | range_g(1) | flags(1)
payload: n_samples × 3 axes × int32
crc32(4)
```

Frame types: `DATA`, `HEALTH`, `INFO`, `ACK`. Gaps in `seq` or `first_sample_index` are dropped data, detected on the host. The same frame can later travel inside an MQTT message unchanged, which is what makes the transport swap cheap.

### 5.4 Host side (Python)

- `capture.py`: reads frames, verifies CRC, checks sequence continuity, writes one capture file per window with metadata (device id, condition label, data source `synthetic|phone|adxl355`, ODR, range, mounting, operator notes, git commit hash).
- `features.py`: pure functions, no I/O. Tested against synthetic known answers.
- `baseline.py`: fit and score, see section 6.
- Dependencies: NumPy, SciPy, Matplotlib, pyserial, pytest. Pandas only if it earns its place.

---

## 6. Signal processing and validation before ML

### 6.1 Processing chain (recommendation)

1. Convert raw counts to g using the configured range's scale factor.
2. Remove DC (gravity and offset) per window.
3. Window: fixed length (for example 1 s = 4,096 samples at 4 kHz), Hann window for spectra, 50 % overlap.
4. Time-domain features per axis: RMS, peak, peak-to-peak, crest factor, kurtosis.
5. Frequency-domain features: FFT magnitude; 1× amplitude (using tach speed when available); blade-pass amplitude; energy in fixed bands (for example 0–50, 50–200, 200–500, 500–1,000 Hz).
6. Every window carries its operating condition (speed) so baselines are compared like for like.

### 6.2 Baseline and deviation (recommendation)

- Baseline = mean and standard deviation (or median and MAD, which is more robust) of each feature over N windows of normal running, **per operating condition**.
- Score = maximum absolute z-score across a small, fixed feature set, or Mahalanobis distance once there are enough windows to estimate a covariance reliably.
- Threshold set from **held-out normal data** to hit a target false-positive rate (for example ≤1 false alarm per 1,000 windows), not chosen by eye.

### 6.3 Validation ladder

Each level is a gate. Don't move up until the level below passes, and record failures honestly.

| Level | Test | Acceptance criterion (proposed) | Data |
|---|---|---|---|
| V0 Known-answer | Feed synthetic signals with known parameters into `features.py`. | RMS of a sine of amplitude A equals A/√2 within 0.1 %; FFT peak within one bin of the true frequency; crest factor of a pure sine = √2 within 1 %; kurtosis of Gaussian noise ≈ 3 within tolerance set by window length. | Synthetic, labelled |
| V1 Acquisition integrity | Stream for ≥60 minutes. | Zero CRC failures, zero sequence gaps, zero FIFO/ring overflows; measured ODR reported with its deviation from nominal. | ADXL355 |
| V1b Sensor sanity | Static 1 g flip test on each axis; noise floor at rest on a quiet surface. | ±1 g readings within the datasheet's offset/sensitivity tolerance; noise floor reported and compared with datasheet noise density. | ADXL355 |
| V2 Repeatability | Same fan, same speed, 5 captures; then 5 remounts. | Coefficient of variation of 1× amplitude and band energies reported, within-mount vs across-mount. | ADXL355 |
| V3 Detectability | Baseline vs `imbalance_small` and `imbalance_large` at each speed. | Fault classes separable from baseline with a stated margin; 1× peak frequency matches tach RPM within one FFT bin. | ADXL355 |
| V4 False positives | Long normal run, plus speed changes and remounts, scored against the baseline. | Measured false-alarm rate on held-out normal data at the chosen threshold; documented list of what triggers false alarms. | ADXL355 |
| ML gate | — | Consider ML only if V3/V4 show a specific limitation of the statistical baseline **and** there is enough labelled data to train and hold out. | — |

V0 can be done today with no hardware. V1–V4 need the sensor. The phone experiment can rehearse V2–V3 at lower fidelity.

**Optional external check:** public bearing-fault datasets (for example the Case Western Reserve University bearing data) are widely used for algorithm testing. Use them only to exercise code and to study the bandwidth question in A2. Results on them say nothing about this hardware. Check their terms of use first.

---

## 7. 14-hour sprint (recommendation)

**Sprint outcome:** a tested, hardware-independent analysis pipeline; one real (phone) dataset from a safe fan rig; a go/no-go purchase decision for the ADXL355 informed by at least two discovery conversations.

Assumes the repo exists (it does: `autonomous-factory/`). Does not assume any hardware other than the MacBook and the phone.

| Session | Hours | Work | Deliverable | Acceptance |
|---|---:|---|---|---|
| 1 | 2 | Decide on this review: accept/reject recommendations, resolve the USB-vs-MQTT conflict, record decisions. | `docs/DECISIONS.md` with dated decisions | Each decision states choice, reason, and what would reverse it. |
| 2 | 2 | Python project skeleton; synthetic signal generator (sine + harmonics + noise + imbalance + impulses), every output labelled `source=synthetic`. | `analysis/synth.py`, `analysis/features.py` stubs, `pyproject.toml` or `requirements.txt` | `python -m pytest` runs (even with few tests). Generated files carry the synthetic label in metadata and filename. |
| 3 | 2 | Implement and test features (V0). | `features.py` + `tests/test_features.py` | All V0 known-answer tests pass locally; test output saved. |
| 4 | 2 | Baseline + scoring on synthetic data; threshold from held-out synthetic normals; false-positive report. | `baseline.py`, `tests/test_baseline.py`, a PNG report | Reported false-positive rate on held-out synthetic normals; detection of synthetic imbalance at stated margin. Clearly labelled synthetic. |
| 5 | 2 | Customer discovery: five prospects identified, outreach sent; ask about failure modes, current tools, network policy (A1, A2, A6). | `docs/discovery/` notes | Five named prospects; at least two conversations held or scheduled. Notes record what was said, not what was hoped. |
| 6 | 2 | Phone experiment (Phase 0b) on a safe low-voltage fan: baseline + small imbalance, 3 speeds if available. Load into the same pipeline. | Raw phone CSVs, capture metadata, plots | Data labelled `source=phone`; 1× peak identified (or a documented reason it wasn't); safety rules in 4.2 followed. |
| 7 | 2 | Review: actual results, blockers, hours and spend; ADXL355 + fan purchase go/no-go; plan sprint 2 (ESP-IDF skeleton and frame protocol). | Weekly report | Go/no-go stated with reasons, including discovery input. |

**Commands this sprint should end up supporting** (to be created; none exist yet):

```bash
cd autonomous-factory
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
python -m pytest -q                       # V0 known-answer tests
python analysis/synth.py --out data/synthetic/   # writes labelled synthetic captures
python analysis/report.py data/synthetic/ --out reports/   # features, baseline, FPR plot
```

**What this sprint deliberately leaves out:** firmware, MQTT, PostgreSQL, Grafana, PT100, edge inference, ML. The ESP-IDF install and firmware skeleton (the separate "first development assignment") moves to sprint 2, so that the firmware is written against a protocol and a Python receiver that already exist.

**Relationship to existing plans:** this overlaps with `docs/WEEK_01_SPRINT.md` (days 5–6) and differs from `autonomous_factory_weekly_execution.md`, which targets MQTT/PostgreSQL/Grafana this week. You will need to pick one; session 1 is for that.

---

## 8. Decisions needed from the founder

### Decided (2026-11-18, Rami)

- **D1. Transport and storage: USB first.** The MVP uses USB serial, with captures saved as files and analysed in Python. MQTT, PostgreSQL and Grafana are deferred until a later phase justifies them. Recorded in `docs/DECISIONS.md`.
- **D2. Customer discovery starts now,** in parallel with the first hardware work (the prototype, done as part of Rami's apprenticeship), not after it. Recorded in `docs/DECISIONS.md`.

### Still open

2. **Acceptance metric:** replace "100 timestamped readings" with capture windows + integrity checks?
3. **Sensor scope:** ADXL355 only for Phase 1, PT100 deferred?
4. **Product claim scope:** state explicitly that the MVP targets low-frequency faults (imbalance, misalignment, looseness), not early bearing defects, unless discovery says bearings are the must-have.
5. **Purchase timing:** buy the ADXL355 board and fan now, or after the phone experiment and two discovery conversations?

---

## 9. Unknowns

- Actual ADXL355 ODR accuracy, noise floor and mounting resonance on your rig (to be measured in V1).
- Which machines and failure modes your first prospects care about.
- Plant network and security constraints for any connected device.
- Applicable Québec/OIQ requirements for a customer pilot; needs a professional opinion, not an AI one.
- Current component prices and availability.
