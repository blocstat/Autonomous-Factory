"""Tests for the ADXL355 stream reader, capture file and noise checks.

All streams and captures here are SYNTHETIC: hand-made bytes or random noise
generated in the test, run through the same code as real captures. None of
it is a measurement.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

import numpy as np
import pytest

from af_signal.adxl355_noise import checks, noise_density, overall, summarize
from af_signal.adxl355_stream import (
    FLAG_FIFO_OVERRUN,
    Capture,
    Frame,
    StreamParser,
    build_frame,
    crc16_ccitt,
    decode_sets,
    encode_sets,
    estimate_odr_hz,
    load_capture_csv,
    parse_text_line,
    write_capture_csv,
)

ROOT = Path(__file__).resolve().parents[1]

# Same vector as firmware/test/host/test_stream_frame.cpp.
SET_A = bytes([0x12, 0x34, 0x51, 0xFE, 0xDC, 0xB0, 0x00, 0x01, 0x00])
FRAME_A = bytes([0xA5, 0x5A, 0x01, 0x34, 0x12, 0x10, 0x00, 0x00, 0x00, 0x01, 0x03,
                 0x12, 0x34, 0x51, 0xFE, 0xDC, 0xB0, 0x00, 0x01, 0x00, 0x96, 0x71])


def _load_script(name: str):
    spec = importlib.util.spec_from_file_location(name, ROOT / "scripts" / f"{name}.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _synthetic_stream(counts: np.ndarray, per_frame: int = 16, odr_hz: float = 4000.0,
                      start_index: int = 0, skip_frames: tuple[int, ...] = ()) -> bytes:
    """Bytes as the firmware would send them for SYNTHETIC counts."""
    out = [b"AF,id,devid_ad=0xAD,devid_mst=0x1D,partid=0xED,revid=0x01,result=PASS\n",
           b"AF,stream,version=1,odr_hz=4000,lpf_hz=1000,range_g=2,lsb_per_g=256000,"
           b"sets_per_frame=16,start_us=500000\n"]
    sets_per_status = int(odr_hz)
    for number, first in enumerate(range(0, counts.shape[0], per_frame)):
        chunk = counts[first:first + per_frame]
        if number not in skip_frames:
            out.append(build_frame(number, start_index + first, encode_sets(chunk)))
        sent = first + chunk.shape[0]
        if sent % sets_per_status == 0:
            uptime = int(sent / odr_hz * 1e6)
            out.append(f"AF,status,uptime_us={uptime},sets={sent},fifo_overruns=0,"
                       f"dropped_words=0,spi_errors=0,temp_c=26.10\n".encode())
    return b"".join(out)


def _white_counts(n: int, noise_ug: float = 22.5, odr_hz: float = 4000.0, seed: int = 1):
    """SYNTHETIC white noise with the given density around (0.1, 0, 0.99) g."""
    rng = np.random.default_rng(seed)
    sd_g = noise_ug * 1e-6 * np.sqrt(odr_hz / 2)
    g = np.array([0.1, 0.0, 0.99]) + sd_g * rng.normal(size=(n, 3))
    return np.round(g * 256000).astype(np.int64)


def test_crc_check_value():
    assert crc16_ccitt(b"123456789") == 0x29B1


def test_build_frame_matches_firmware_vector():
    assert build_frame(0x1234, 16, SET_A, flags=0x03) == FRAME_A


def test_decode_sets_known_words():
    counts = decode_sets(SET_A)
    assert counts.tolist() == [[0x12345, -(0x100000 - 0xFEDCB), 0x10]]
    assert decode_sets(bytes([0x7F, 0xFF, 0xF1, 0x80, 0, 0, 0xFF, 0xFF, 0xF0])).tolist() == [
        [524287, -524288, -1]
    ]


def test_encode_decode_round_trip():
    counts = np.array([[0, 1, -1], [524287, -524288, 12345]])
    assert np.array_equal(decode_sets(encode_sets(counts)), counts)
    assert encode_sets(counts)[2] & 0x01 and not encode_sets(counts)[5] & 0x01


def test_parser_same_result_for_any_chunking():
    stream = _synthetic_stream(_white_counts(4000))
    whole = StreamParser().feed(stream)
    parser = StreamParser()
    pieces = []
    for i in range(0, len(stream), 7):
        pieces.extend(parser.feed(stream[i:i + 7]))
    assert len(pieces) == len(whole)
    frames = [e for e in pieces if isinstance(e, Frame)]
    assert len(frames) == 250
    assert parser.crc_errors == 0 and parser.skipped_bytes == 0
    assert [e for e in pieces if isinstance(e, str)][0].startswith("AF,id,")


def test_parser_resyncs_after_garbage_and_bad_crc():
    good = build_frame(1, 16, SET_A)
    bad = bytearray(build_frame(0, 0, SET_A))
    bad[12] ^= 0xFF
    boot_noise = bytes([0x00, 0xA5, 0xFF, 0x41, 0x46, 0x0D, 0xE0, 0xA5])
    parser = StreamParser()
    events = parser.feed(boot_noise + bytes(bad) + b"AF,hint,test\n" + good)
    assert parser.crc_errors == 1
    assert [e for e in events if isinstance(e, str)] == ["AF,hint,test"]
    frames = [e for e in events if isinstance(e, Frame)]
    assert len(frames) == 1 and frames[0].first_index == 16


def test_parse_text_line_and_odr():
    kind, fields = parse_text_line("AF,status,uptime_us=1000000,sets=4012,temp_c=26.1")
    assert kind == "status" and fields["sets"] == "4012"
    lines = ["AF,status,uptime_us=1000000,sets=4012", "AF,status,uptime_us=31000000,sets=124372"]
    assert estimate_odr_hz(lines) == pytest.approx(4012.0)
    assert estimate_odr_hz(lines[:1]) is None


def test_capture_counts_missing_sets_overruns_and_restarts():
    capture = Capture()
    counts = decode_sets(SET_A * 16)
    capture.add(Frame(0, 0, 0, counts))
    capture.add(Frame(2, 32, FLAG_FIFO_OVERRUN, counts))  # frame 1 lost
    assert capture.missing_sets == 16 and capture.sequence_gaps == 1
    assert capture.overrun_flags == 1
    capture.add("AF,stream,version=1")
    capture.add(Frame(0, 0, 0, counts))
    assert capture.restarts == 1 and capture.missing_sets == 16
    assert capture.n_sets == 48


def _capture_file(tmp_path: Path, counts: np.ndarray, **stream_kwargs) -> Path:
    parser = StreamParser()
    capture = Capture()
    for event in parser.feed(_synthetic_stream(counts, **stream_kwargs)):
        capture.add(event)
    header = {
        "note": "SYNTHETIC test data, not a measurement",
        "odr_estimate_hz": f"{estimate_odr_hz(capture.status_lines()):.2f}",
        "crc_errors": str(parser.crc_errors),
    }
    path = tmp_path / "20260101-0000_adxl355_synthetic_test_r1.csv"
    write_capture_csv(path, capture, header)
    return path


def test_csv_round_trip_is_lossless(tmp_path):
    counts = _white_counts(8000)
    loaded = load_capture_csv(_capture_file(tmp_path, counts))
    assert loaded.data_origin == "adxl355"
    assert np.array_equal(loaded.counts, counts)
    assert np.array_equal(loaded.index, np.arange(8000))
    assert loaded.odr_hz == pytest.approx(4000.0)
    assert loaded.text_lines[0].startswith("AF,id,")


def test_noise_density_recovers_white_noise_level():
    rng = np.random.default_rng(3)
    sd = 22.5e-6 * np.sqrt(2000.0)
    freqs, asd = noise_density(sd * rng.normal(size=120000), 4000.0)
    band = (freqs >= 10) & (freqs <= 800)
    assert np.median(asd[band]) * 1e6 == pytest.approx(22.5, rel=0.05)


def test_checks_pass_on_clean_synthetic_capture(tmp_path):
    loaded = load_capture_csv(_capture_file(tmp_path, _white_counts(40000)))
    row = summarize(loaded)
    results = checks(loaded, row)
    assert overall(results) == "PASS", results
    assert row["gravity_g"] == pytest.approx(np.hypot(0.1, 0.99), abs=1e-3)
    for axis in "xyz":
        # Quantisation (1 LSB = 3.9 ug) adds a little to 22.5 ug/rtHz.
        assert row[f"{axis}_noise_ug_rthz"] == pytest.approx(22.5, rel=0.1)


def test_checks_flag_missing_frames_and_loud_desk(tmp_path):
    lost = load_capture_csv(_capture_file(tmp_path, _white_counts(40000), skip_frames=(100,)))
    results = {c.name: c.result for c in checks(lost, summarize(lost))}
    assert results["missing sets"] == "FAIL"

    loud = load_capture_csv(_capture_file(tmp_path / "loud", _white_counts(40000, noise_ug=80)))
    results = {c.name: c.result for c in checks(loud, summarize(loud))}
    assert results["z noise density"] == "CHECK"


def test_checks_fail_on_stuck_data(tmp_path):
    stuck = load_capture_csv(_capture_file(tmp_path, np.tile([25600, 0, 253440], (40000, 1))))
    results = {c.name: c.result for c in checks(stuck, summarize(stuck))}
    assert results["x noise density"] == "FAIL"


def test_analyze_script_writes_summary_and_plot(tmp_path):
    path = _capture_file(tmp_path, _white_counts(40000))
    script = _load_script("analyze_adxl355")
    out_dir = tmp_path / "out"
    assert script.main([str(path), "--out-dir", str(out_dir)]) == 0
    assert (out_dir / "summary.csv").read_text().startswith("data_origin,")
    assert (out_dir / f"{path.stem}_noise.png").stat().st_size > 10000


class _FakeSerial:
    """Stands in for the USB port and replays a SYNTHETIC stream."""

    def __init__(self, data: bytes, chunk: int = 4096):
        self._data = b"\x00\xff\x13garbage at 115200" + data
        self._chunk = chunk
        self.dtr = True
        self.rts = True

    def read(self, n):
        piece, self._data = self._data[:min(n, self._chunk)], self._data[min(n, self._chunk):]
        return piece

    def reset_input_buffer(self):
        pass

    def close(self):
        pass


def test_capture_script_end_to_end_with_fake_port(tmp_path, monkeypatch, capsys):
    script = _load_script("capture_adxl355")
    fake = _FakeSerial(_synthetic_stream(_white_counts(16000)))
    monkeypatch.setattr(script, "open_port", lambda port, baud: fake)
    monkeypatch.setattr(script, "SILENCE_TIMEOUT_S", 0.2)
    code = script.main(["--port", "fake", "--seconds", "60", "--condition", "synthetic",
                        "--raw-dir", str(tmp_path / "raw"), "--out-dir", str(tmp_path / "out")])
    assert code == 0
    saved = list((tmp_path / "raw").glob("*_adxl355_synthetic_desk-flat_r1.csv"))
    assert len(saved) == 1
    loaded = load_capture_csv(saved[0])
    assert loaded.counts.shape == (16000, 3)
    assert loaded.header["missing_sets"] == "0" and loaded.header["crc_errors"] == "0"
    output = capsys.readouterr().out
    assert "AF,id," in output and "OVERALL: PASS" in output
