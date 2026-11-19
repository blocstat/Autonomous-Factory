# Data directories

| Path | Contents |
| --- | --- |
| `data/synthetic/` | Waveforms produced by `python/af_signal`. Always labeled `data_origin: synthetic`. |
| `data/measured/` | Recordings from a real sensor. Do not copy synthetic files here. |
| `data/measured/phone/raw/` | Phone accelerometer captures (phyphox CSV), labelled `data_origin: phone`. Real measurements from the phone, **not** the product sensor. See `docs/PHASE0B_PHONE_SESSION.md`. |

Generated previews go to `data/synthetic/out/` and are gitignored. Recreate them with the command in `docs/DEVELOPMENT_SETUP.md`. Nothing in this repository is a measurement of an industrial machine. Phone results in `data/measured/phone/out/` are gitignored; recreate them with `python python/scripts/analyze_phone.py`.
