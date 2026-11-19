# Data directories

| Path | Contents |
| --- | --- |
| `data/synthetic/` | Waveforms produced by `python/af_signal`. Always labeled `data_origin: synthetic`. |
| `data/measured/` | Future recordings from a real sensor. Empty. Do not copy synthetic files here. |

Generated previews go to `data/synthetic/out/` and are gitignored. Recreate them with the command in `docs/DEVELOPMENT_SETUP.md`. Nothing in this repository is a machine measurement.
