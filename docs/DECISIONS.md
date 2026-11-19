# Decision Log

Each entry records the choice, who made it, why, and what would make us revisit it.

---

## D1. MVP transport and storage: USB first

- **Date:** 2026-11-18
- **Decided by:** Rami (founder)
- **Decision:** The MVP streams data from the ESP32-S3 over USB serial. Captures are saved as files on the Mac and analysed in Python. MQTT, PostgreSQL and Grafana are deferred.
- **Why:** USB is deterministic and needs no network, broker or credentials. Raw vibration data (~48 kB/s per device at 4 kSPS, 3 axes) does not belong in a database one row per sample. This matches `docs/MASTER_CONTEXT.md` ("Initial USB serial transport; Wi-Fi/MQTT only when justified"). See `docs/SYSTEMS_ENGINEERING_REVIEW.md` section 2.
- **Supersedes:** the MQTT → PostgreSQL → Grafana pipeline in `autonomous_factory_weekly_execution.md` (updated the same day).
- **Revisit when:** a pilot or customer demo needs remote or multi-device data, or the USB pipeline passes validation levels V1 to V3 in the review.

## D2. Customer discovery runs in parallel with the first hardware work

- **Date:** 2026-11-18
- **Decided by:** Rami (founder)
- **Decision:** Start talking to potential customers now, alongside the first prototype hardware work (done as part of Rami's apprenticeship), rather than after the prototype works.
- **Why:** The largest project risk is unproven customer demand (review, assumption A1). Early conversations also answer technical questions: which failure modes matter (A2) and whether plants allow connected devices (A6).
- **Revisit when:** discovery shows the monitoring problem is not worth paying for, or points to a different product wedge.
