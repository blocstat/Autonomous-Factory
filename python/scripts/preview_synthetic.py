"""Create a labeled synthetic preview under data/synthetic/out/."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from af_signal.preview import write_synthetic_preview
from af_signal.synthetic import generate_fan_vibration, generate_tone


def main() -> None:
    repo_root = ROOT.parent
    output_dir = repo_root / "data" / "synthetic" / "out"
    waveform = generate_tone(
        sample_rate_hz=1000.0,
        duration_s=1.0,
        tone_hz=50.0,
        amplitude=1.0,
        noise_std=0.05,
        seed=1,
        description="synthetic 50 Hz tone plus Gaussian noise",
    )
    csv_path, png_path = write_synthetic_preview(output_dir, waveform)
    print(f"data_origin={waveform.data_origin}")
    print(csv_path)
    print(png_path)

    # Fan-like pair: same signal with and without extra 1x (imbalance).
    for stem, imbalance in (("fan_baseline", 0.0), ("fan_imbalance", 0.3)):
        fan = generate_fan_vibration(
            imbalance_amplitude=imbalance,
            harmonic_amplitudes=(0.05,),
            noise_std=0.05,
            seed=1,
            description=f"synthetic fan-like signal, imbalance_amplitude={imbalance}",
        )
        for path in write_synthetic_preview(output_dir, fan, stem=stem):
            print(path)


if __name__ == "__main__":
    main()
