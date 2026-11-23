"""Noise floor and pass/fail checks for an ADXL355 capture at rest.

Inputs are real ADXL355 captures (``data_origin: adxl355``) saved by
python/scripts/capture_adxl355.py. Values in g use the typical
256,000 LSB/g and are uncalibrated (+/-8 %).

The checks are for the sensor and the data path only (no machine is
involved): every sample arrived, the output rate matches the sensor's
clock tolerance, gravity reads about 1 g, and the noise density is close
to the data sheet's 22.5 ug/sqrt(Hz).
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from scipy import signal

from af_signal.adxl355_stream import LoadedCapture, parse_text_line

DATASHEET_NOISE_UG = 22.5  # ug/sqrt(Hz), typical, +/-2 g range, all axes
NOISE_BAND_HZ = (10.0, 800.0)  # below the 1000 Hz low-pass corner
NOISE_PASS_UG = (11.0, 45.0)  # half to twice the typical value
ODR_PASS_HZ = (3944.0, 4056.0)  # 4000 Hz +/-1.4 % (data sheet clock tolerance)
GRAVITY_PASS_G = (0.92, 1.08)  # 1 g +/-8 % (sensitivity tolerance)
TEMP_PASS_C = (15.0, 40.0)
SETTLE_S = 0.5  # skip the first half second after the sensor leaves standby
AXES = ("x", "y", "z")


@dataclass(frozen=True)
class Check:
    name: str
    result: str  # "PASS", "FAIL" or "CHECK" (data fine, environment suspected)
    detail: str


def noise_density(samples_g: np.ndarray, rate_hz: float, nperseg: int = 4096):
    """One-sided amplitude spectral density in g/sqrt(Hz) (Welch, Hann, linear detrend)."""
    samples_g = np.asarray(samples_g, dtype=np.float64)
    nperseg = min(nperseg, samples_g.size)
    freqs, psd = signal.welch(
        samples_g, fs=rate_hz, window="hann", nperseg=nperseg, detrend="linear",
        scaling="density",
    )
    return freqs, np.sqrt(psd)


def band_median(freqs: np.ndarray, values: np.ndarray, band: tuple[float, float]) -> float:
    mask = (freqs >= band[0]) & (freqs <= band[1])
    if not mask.any():
        raise ValueError("no frequency bins in band")
    return float(np.median(values[mask]))


def summarize(capture: LoadedCapture, settle_s: float = SETTLE_S) -> dict[str, object]:
    rate = capture.odr_hz
    start = int(round(settle_s * rate))
    g = capture.g[start:]
    if g.shape[0] < 2048:
        raise ValueError(f"{capture.source_file}: too short after settling ({g.shape[0]} sets)")
    expected = int(capture.index[-1] - capture.index[0] + 1)
    row: dict[str, object] = {
        "data_origin": capture.data_origin,
        "file": capture.source_file,
        "sets": int(capture.index.size),
        "missing_sets": expected - int(capture.index.size),
        "duration_s": round(capture.index.size / rate, 2),
        "odr_hz": round(rate, 1),
    }
    for i, axis in enumerate(AXES):
        freqs, asd = noise_density(g[:, i], rate)
        row[f"{axis}_mean_g"] = round(float(np.mean(g[:, i])), 5)
        row[f"{axis}_sd_mg"] = round(float(np.std(g[:, i])) * 1e3, 4)
        row[f"{axis}_noise_ug_rthz"] = round(band_median(freqs, asd, NOISE_BAND_HZ) * 1e6, 2)
    row["gravity_g"] = round(float(np.linalg.norm(np.mean(g, axis=0))), 4)
    return row


def checks(capture: LoadedCapture, row: dict[str, object]) -> list[Check]:
    header = capture.header
    status = [parse_text_line(line)[1] for line in capture.text_lines
              if line.startswith("AF,status,")]
    last = status[-1] if status else {}
    out: list[Check] = []

    def counter(name: str, value: object, source: str) -> None:
        try:
            number = int(value)  # type: ignore[arg-type]
        except (TypeError, ValueError):
            out.append(Check(name, "FAIL", f"not recorded ({source})"))
            return
        out.append(Check(name, "PASS" if number == 0 else "FAIL", f"{number} ({source})"))

    counter("missing sets", row["missing_sets"], "gaps in the set index")
    counter("CRC errors", header.get("crc_errors"), "host")
    counter("FIFO overruns", last.get("fifo_overruns"), "firmware")
    counter("dropped FIFO words", last.get("dropped_words"), "firmware")
    counter("SPI errors", last.get("spi_errors"), "firmware")

    odr = header.get("odr_estimate_hz", "")
    try:
        odr_value = float(odr)
        ok = ODR_PASS_HZ[0] <= odr_value <= ODR_PASS_HZ[1]
        out.append(Check("output data rate", "PASS" if ok else "FAIL",
                         f"{odr_value:.1f} Hz (pass {ODR_PASS_HZ[0]:.0f}-{ODR_PASS_HZ[1]:.0f})"))
    except ValueError:
        out.append(Check("output data rate", "FAIL", "no estimate (fewer than 2 status lines)"))

    gravity = float(row["gravity_g"])  # type: ignore[arg-type]
    ok = GRAVITY_PASS_G[0] <= gravity <= GRAVITY_PASS_G[1]
    out.append(Check("gravity at rest", "PASS" if ok else "FAIL",
                     f"{gravity:.4f} g (pass {GRAVITY_PASS_G[0]}-{GRAVITY_PASS_G[1]})"))

    for axis in AXES:
        noise = float(row[f"{axis}_noise_ug_rthz"])  # type: ignore[arg-type]
        if noise < NOISE_PASS_UG[0]:
            result = "FAIL"  # far below the data sheet: data likely stuck or wrong
        elif noise > NOISE_PASS_UG[1]:
            result = "CHECK"  # usually vibration from the desk or room
        else:
            result = "PASS"
        out.append(Check(f"{axis} noise density", result,
                         f"{noise:.1f} ug/rtHz, median {NOISE_BAND_HZ[0]:.0f}-"
                         f"{NOISE_BAND_HZ[1]:.0f} Hz (pass {NOISE_PASS_UG[0]:.0f}-"
                         f"{NOISE_PASS_UG[1]:.0f}; data sheet {DATASHEET_NOISE_UG})"))

    temp = last.get("temp_c")
    try:
        temp_value = float(temp)  # type: ignore[arg-type]
        ok = TEMP_PASS_C[0] <= temp_value <= TEMP_PASS_C[1]
        out.append(Check("temperature", "PASS" if ok else "CHECK",
                         f"{temp_value:.1f} C, uncalibrated"))
    except (TypeError, ValueError):
        out.append(Check("temperature", "CHECK", "not recorded"))
    return out


def overall(results: list[Check]) -> str:
    if any(c.result == "FAIL" for c in results):
        return "FAIL"
    if any(c.result == "CHECK" for c in results):
        return "CHECK"
    return "PASS"


def plot_noise(capture: LoadedCapture, path, settle_s: float = SETTLE_S) -> None:
    """Save a noise-density plot (log-log) with the data sheet's typical value."""
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import matplotlib.ticker

    rate = capture.odr_hz
    g = capture.g[int(round(settle_s * rate)):]
    colors = {"x": "#2a78d6", "y": "#eb6834", "z": "#1baf7a"}
    fig, ax = plt.subplots(figsize=(8, 4.5), dpi=150)
    fig.patch.set_facecolor("#fcfcfb")
    ax.set_facecolor("#fcfcfb")
    for i, axis in enumerate(AXES):
        freqs, asd = noise_density(g[:, i], rate)
        keep = freqs > 0
        ax.loglog(freqs[keep], asd[keep] * 1e6, color=colors[axis], linewidth=1.2, label=axis)
    ax.axhline(DATASHEET_NOISE_UG, color="#52514e", linestyle="--", linewidth=1)
    ax.text(1.2, DATASHEET_NOISE_UG * 1.3, f"data sheet typical {DATASHEET_NOISE_UG} ug/rtHz",
            color="#52514e", fontsize=8)
    ax.axvspan(*NOISE_BAND_HZ, color="#52514e", alpha=0.06, linewidth=0)
    ax.text(np.sqrt(NOISE_BAND_HZ[0] * NOISE_BAND_HZ[1]), 1.3, "checked band",
            color="#52514e", fontsize=8, ha="center")
    ax.set_xlim(1, rate / 2)
    top = max(1000.0, max(line.get_ydata().max() for line in ax.get_lines()[:3]) * 1.5)
    ax.set_ylim(1, top)
    ax.yaxis.set_major_formatter(matplotlib.ticker.FuncFormatter(lambda v, _: f"{v:g}"))
    ax.xaxis.set_major_formatter(matplotlib.ticker.FuncFormatter(lambda v, _: f"{v:g}"))
    ax.set_xlabel("Frequency (Hz)", color="#52514e")
    ax.set_ylabel("Noise density (ug/sqrt(Hz))", color="#52514e")
    ax.set_title(f"ADXL355 at rest, data_origin: adxl355\n{capture.source_file}",
                 fontsize=9, color="#0b0b0b")
    ax.grid(True, which="major", color="#e4e3df", linewidth=0.6)
    for side in ("top", "right"):
        ax.spines[side].set_visible(False)
    ax.legend(frameon=False, loc="upper left", ncol=3)
    fig.tight_layout()
    fig.savefig(path)
    plt.close(fig)


def format_report(row: dict[str, object], results: list[Check]) -> str:
    lines = [
        f"ADXL355 capture {row['file']} (data_origin: {row['data_origin']}, uncalibrated)",
        f"  {row['sets']} sets, {row['duration_s']} s at {row['odr_hz']} Hz",
        "  mean g   x {x_mean_g:+.4f}  y {y_mean_g:+.4f}  z {z_mean_g:+.4f}".format(**row),
        "  sd mg    x {x_sd_mg:.3f}  y {y_sd_mg:.3f}  z {z_sd_mg:.3f}".format(**row),
    ]
    width = max(len(c.name) for c in results)
    for c in results:
        lines.append(f"  {c.result:<5}  {c.name:<{width}}  {c.detail}")
    lines.append(f"  OVERALL: {overall(results)}")
    return "\n".join(lines)
