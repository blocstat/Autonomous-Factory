"""Read the ADXL355 binary stream sent by the step 3 firmware, and save it.

Data handled here is a real measurement from the product sensor (ADXL355),
labelled ``data_origin: adxl355``. Values in g use the data sheet's typical
256,000 LSB/g and are good to about +/-8 % until the unit is calibrated.

The frame format is defined in firmware/main/stream_frame.hpp; this module
must stay in step with it. Summary:

    sync A5 5A | version u8 | sequence u16 | first set index u32 |
    number of sets u8 | flags u8 | 9 bytes per set | CRC-16/CCITT-FALSE u16

Multi-byte header fields are little-endian. Each set is x, y, z, each the
3 raw FIFO bytes (20-bit two's complement, left-justified, MSB first).
The firmware also sends text lines that start with "AF," and end with "\\n".
"""

from __future__ import annotations

import binascii
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable

import numpy as np

DATA_ORIGIN_ADXL355 = "adxl355"

SYNC = b"\xA5\x5A"
TEXT_PREFIX = b"AF,"
VERSION = 1
HEADER_SIZE = 11
SET_SIZE = 9
CRC_SIZE = 2
MAX_SETS_PER_FRAME = 32
MAX_TEXT_LINE = 512

FLAG_FIFO_OVERRUN = 0x01
FLAG_WORD_DROPPED = 0x02

NOMINAL_ODR_HZ = 4000.0
LSB_PER_G = 256000.0


def crc16_ccitt(data: bytes) -> int:
    """CRC-16/CCITT-FALSE (poly 0x1021, init 0xFFFF), as in the firmware."""
    return binascii.crc_hqx(bytes(data), 0xFFFF)


def build_frame(sequence: int, first_index: int, sets: bytes, flags: int = 0) -> bytes:
    """Build one frame exactly as the firmware does (used by tests)."""
    if len(sets) % SET_SIZE != 0:
        raise ValueError("sets must be a multiple of 9 bytes")
    n_sets = len(sets) // SET_SIZE
    if not 1 <= n_sets <= MAX_SETS_PER_FRAME:
        raise ValueError("1 to 32 sets per frame")
    body = (
        bytes([VERSION])
        + (sequence & 0xFFFF).to_bytes(2, "little")
        + (first_index & 0xFFFFFFFF).to_bytes(4, "little")
        + bytes([n_sets, flags & 0xFF])
        + bytes(sets)
    )
    return SYNC + body + crc16_ccitt(body).to_bytes(2, "little")


def decode_sets(payload: bytes) -> np.ndarray:
    """Decode 9-byte x/y/z sets into an (N, 3) int32 array of raw 20-bit counts."""
    raw = np.frombuffer(bytes(payload), dtype=np.uint8)
    if raw.size % SET_SIZE != 0:
        raise ValueError("payload must be a multiple of 9 bytes")
    words = raw.reshape(-1, 3, 3).astype(np.int32)
    value = (words[..., 0] << 12) | (words[..., 1] << 4) | (words[..., 2] >> 4)
    return np.where(value & 0x80000, value - 0x100000, value).astype(np.int32)


def encode_sets(counts: np.ndarray) -> bytes:
    """Inverse of decode_sets, with the x-axis marker bit set as the sensor does.

    Used only to build SYNTHETIC streams for tests.
    """
    counts = np.asarray(counts, dtype=np.int64).reshape(-1, 3)
    if counts.min(initial=0) < -0x80000 or counts.max(initial=0) > 0x7FFFF:
        raise ValueError("counts must fit in 20 bits")
    value = counts & 0xFFFFF
    out = np.empty(counts.shape + (3,), dtype=np.uint8)
    out[..., 0] = value >> 12
    out[..., 1] = (value >> 4) & 0xFF
    out[..., 2] = (value & 0xF) << 4
    out[:, 0, 2] |= 0x01
    return out.tobytes()


@dataclass(frozen=True)
class Frame:
    sequence: int
    first_index: int
    flags: int
    counts: np.ndarray  # (N, 3) int32, x/y/z raw counts


class StreamParser:
    """Split a byte stream into frames and AF text lines.

    Bytes that are neither (boot messages at another baud rate, a frame with
    a bad CRC, a partial line) are skipped and counted, and the parser looks
    for the next sync or "AF," marker.
    """

    def __init__(self) -> None:
        self._buffer = bytearray()
        self.crc_errors = 0
        self.skipped_bytes = 0

    def feed(self, data: bytes) -> list[Frame | str]:
        self._buffer.extend(data)
        events: list[Frame | str] = []
        buf = self._buffer
        while True:
            if buf.startswith(SYNC):
                if len(buf) < HEADER_SIZE:
                    break
                n_sets = buf[9]
                if buf[2] != VERSION or not 1 <= n_sets <= MAX_SETS_PER_FRAME:
                    self._skip(1)
                    continue
                length = HEADER_SIZE + SET_SIZE * n_sets + CRC_SIZE
                if len(buf) < length:
                    break
                body_end = length - CRC_SIZE
                if crc16_ccitt(buf[2:body_end]) != int.from_bytes(buf[body_end:length], "little"):
                    self.crc_errors += 1
                    self._skip(1)
                    continue
                events.append(
                    Frame(
                        sequence=int.from_bytes(buf[3:5], "little"),
                        first_index=int.from_bytes(buf[5:9], "little"),
                        flags=buf[10],
                        counts=decode_sets(buf[HEADER_SIZE:body_end]),
                    )
                )
                del buf[:length]
                continue
            if buf.startswith(TEXT_PREFIX):
                end = buf.find(b"\n")
                if end < 0:
                    if len(buf) > MAX_TEXT_LINE:
                        self._skip(1)
                        continue
                    break
                line = bytes(buf[:end]).rstrip(b"\r")
                if any(b < 0x20 or b > 0x7E for b in line):
                    # Not a clean text line (e.g. a cut line run into a frame).
                    self._skip(1)
                    continue
                events.append(line.decode("ascii"))
                del buf[: end + 1]
                continue
            if SYNC.startswith(bytes(buf)) or TEXT_PREFIX.startswith(bytes(buf)):
                break  # could still become a marker; wait for more bytes
            starts = [i for i in (buf.find(SYNC, 1), buf.find(TEXT_PREFIX, 1)) if i > 0]
            if starts:
                self._skip(min(starts))
                continue
            # No marker: drop everything except a tail that could start one.
            cut = len(buf)
            for i in range(max(1, len(buf) - 2), len(buf)):
                tail = bytes(buf[i:])
                if SYNC.startswith(tail) or TEXT_PREFIX.startswith(tail):
                    cut = i
                    break
            self._skip(cut)
            break
        return events

    def _skip(self, n: int) -> None:
        del self._buffer[:n]
        self.skipped_bytes += n


def parse_text_line(line: str) -> tuple[str, dict[str, str]]:
    """Split "AF,kind,key=value,..." into ("kind", {key: value})."""
    parts = line.strip().split(",")
    if len(parts) < 2 or parts[0] != "AF":
        return "", {}
    fields: dict[str, str] = {}
    for part in parts[2:]:
        key, sep, value = part.partition("=")
        if sep:
            fields[key] = value
    return parts[1], fields


def estimate_odr_hz(status_lines: Iterable[str]) -> float | None:
    """Output data rate from the first and last AF,status lines.

    The firmware counts sets against the ESP32's crystal-based timer, so this
    measures the ADXL355's own clock (data sheet: +/-1.4 % device to device).
    Returns None with fewer than two status lines or no progress between them.
    """
    points = []
    for line in status_lines:
        kind, fields = parse_text_line(line)
        if kind == "status" and "uptime_us" in fields and "sets" in fields:
            points.append((int(fields["uptime_us"]), int(fields["sets"])))
    if len(points) < 2:
        return None
    (t0, s0), (t1, s1) = points[0], points[-1]
    if t1 <= t0 or s1 <= s0:
        return None
    return (s1 - s0) / ((t1 - t0) / 1e6)


@dataclass
class Capture:
    """Sample sets collected from a stream, with the counters needed to judge it."""

    counts: list[np.ndarray] = field(default_factory=list)
    indices: list[np.ndarray] = field(default_factory=list)
    text_lines: list[str] = field(default_factory=list)
    frames: int = 0
    missing_sets: int = 0
    sequence_gaps: int = 0
    overrun_flags: int = 0
    dropped_flags: int = 0
    restarts: int = 0
    _next_index: int | None = None
    _next_sequence: int | None = None

    def add(self, event: Frame | str) -> None:
        if isinstance(event, str):
            self.text_lines.append(event)
            if parse_text_line(event)[0] == "stream":
                # The firmware restarted: indices count from 0 again.
                if self._next_index is not None:
                    self.restarts += 1
                self._next_index = None
                self._next_sequence = None
            return
        n = event.counts.shape[0]
        if self._next_index is not None and event.first_index != self._next_index:
            if event.first_index > self._next_index:
                self.missing_sets += event.first_index - self._next_index
            else:
                self.restarts += 1
        if self._next_sequence is not None and event.sequence != self._next_sequence:
            self.sequence_gaps += 1
        self._next_index = event.first_index + n
        self._next_sequence = (event.sequence + 1) & 0xFFFF
        self.frames += 1
        if event.flags & FLAG_FIFO_OVERRUN:
            self.overrun_flags += 1
        if event.flags & FLAG_WORD_DROPPED:
            self.dropped_flags += 1
        self.counts.append(event.counts)
        self.indices.append(np.arange(event.first_index, event.first_index + n, dtype=np.int64))

    @property
    def n_sets(self) -> int:
        return int(sum(c.shape[0] for c in self.counts))

    def arrays(self) -> tuple[np.ndarray, np.ndarray]:
        if not self.counts:
            return np.zeros(0, dtype=np.int64), np.zeros((0, 3), dtype=np.int32)
        return np.concatenate(self.indices), np.concatenate(self.counts)

    def status_lines(self) -> list[str]:
        return [line for line in self.text_lines if line.startswith("AF,status,")]


@dataclass(frozen=True)
class LoadedCapture:
    index: np.ndarray  # int64 set index from the start of streaming
    counts: np.ndarray  # (N, 3) int32 raw counts
    header: dict[str, str]
    text_lines: list[str]
    source_file: str
    data_origin: str = DATA_ORIGIN_ADXL355

    @property
    def g(self) -> np.ndarray:
        return self.counts.astype(np.float64) / LSB_PER_G

    @property
    def odr_hz(self) -> float:
        value = self.header.get("odr_estimate_hz", "")
        try:
            return float(value)
        except ValueError:
            return NOMINAL_ODR_HZ


def write_capture_csv(path: Path, capture: Capture, header: dict[str, str]) -> None:
    """Save raw counts (lossless) with '#' comment lines for the metadata.

    The firmware's AF text lines are kept as '# AF,...' lines.
    """
    index, counts = capture.arrays()
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        handle.write(f"# data_origin: {DATA_ORIGIN_ADXL355}\n")
        for key, value in header.items():
            handle.write(f"# {key}: {value}\n")
        for line in capture.text_lines:
            handle.write(f"# {line}\n")
        handle.write("index,x_raw,y_raw,z_raw\n")
        rows = np.column_stack([index, counts.astype(np.int64)])
        np.savetxt(handle, rows, fmt="%d", delimiter=",")


def load_capture_csv(path: Path) -> LoadedCapture:
    path = Path(path)
    header: dict[str, str] = {}
    text_lines: list[str] = []
    skip = 0
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            if not line.startswith("#"):
                break
            skip += 1
            content = line[1:].strip()
            if content.startswith("AF,"):
                text_lines.append(content)
            else:
                key, sep, value = content.partition(":")
                if sep:
                    header[key.strip()] = value.strip()
    if header.get("data_origin") != DATA_ORIGIN_ADXL355:
        raise ValueError(f"{path.name}: not an ADXL355 capture (data_origin missing)")
    data = np.loadtxt(path, delimiter=",", skiprows=skip + 1, dtype=np.int64, ndmin=2)
    if data.shape[0] == 0:
        raise ValueError(f"{path.name}: no samples")
    return LoadedCapture(
        index=data[:, 0],
        counts=data[:, 1:4].astype(np.int32),
        header=header,
        text_lines=text_lines,
        source_file=path.name,
    )
