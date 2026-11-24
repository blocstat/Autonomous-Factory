"""Record the ADXL355 stream from the ESP32-S3 over USB, then check it.

Needs the step 3 firmware on the board and pyserial
(pip install -r python/requirements.txt). The data saved is a real ADXL355
measurement, labelled data_origin: adxl355, uncalibrated (+/-8 % in g).

Usage, from the repository root (board on the USB-to-UART port):

    python python/scripts/capture_adxl355.py --port /dev/cu.usbserial-0001 \\
        --condition rest --mount desk-flat --repeat 1

By default the script resets the board first (as idf.py monitor does), so
the capture starts at sample 0 with the ID check. It records --seconds of
data, saves data/measured/adxl355/raw/YYYYMMDD-HHMM_adxl355_<condition>_
<mount>_r<N>.csv (raw counts, lossless), then prints the step 3 checks.
Close idf.py monitor first: only one program can hold the port.
"""

from __future__ import annotations

import argparse
import re
import sys
import time
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from af_signal.adxl355_noise import checks, format_report, plot_noise, summarize  # noqa: E402
from af_signal.adxl355_stream import (  # noqa: E402
    Capture,
    StreamParser,
    estimate_odr_hz,
    load_capture_csv,
    write_capture_csv,
)

DEFAULT_RAW = ROOT.parent / "data" / "measured" / "adxl355" / "raw"
DEFAULT_OUT = ROOT.parent / "data" / "measured" / "adxl355" / "out"
LABEL = re.compile(r"^[a-z0-9-]+$")
START_TIMEOUT_S = 10.0
SILENCE_TIMEOUT_S = 3.0


def label(value: str) -> str:
    if not LABEL.match(value):
        raise argparse.ArgumentTypeError("use lowercase letters, digits and '-' only")
    return value


def open_port(port: str, baud: int):
    try:
        import serial  # pyserial
    except ImportError:
        sys.exit("pyserial is missing: run  pip install -r python/requirements.txt")
    try:
        return serial.Serial(port, baud, timeout=0.05)
    except serial.SerialException as error:
        sys.exit(f"Cannot open {port}: {error}\nIs idf.py monitor still running? "
                 "List ports with: ls /dev/cu.usb*")


def reset_board(ser) -> None:
    # Same lines as esptool's hard reset: RTS pulls EN low, DTR stays off so
    # GPIO0 is high and the chip boots the app, not the bootloader.
    ser.dtr = False
    ser.rts = True
    time.sleep(0.1)
    ser.rts = False
    ser.reset_input_buffer()


def record(ser, seconds: float) -> tuple[Capture, StreamParser]:
    parser = StreamParser()
    capture = Capture()
    started = time.monotonic()
    first_frame_at = None
    last_data_at = started
    next_progress = 5.0
    while True:
        now = time.monotonic()
        chunk = ser.read(8192)
        if chunk:
            last_data_at = now
        for event in parser.feed(chunk):
            if isinstance(event, str):
                if not event.startswith("AF,status,"):
                    print(event)
            elif first_frame_at is None:
                first_frame_at = now
                print(f"Streaming; recording {seconds:g} s ...")
            capture.add(event)
        if first_frame_at is None:
            if now - started > START_TIMEOUT_S:
                sys.exit("No sample frames within 10 s. Check that the step 3 firmware is "
                         "flashed and the AF,id line says PASS; press RST and try again.")
            continue
        elapsed = now - first_frame_at
        if elapsed >= next_progress:
            print(f"  {elapsed:4.0f} s, {capture.n_sets} sets, CRC errors {parser.crc_errors}")
            next_progress += 5.0
        if now - last_data_at > SILENCE_TIMEOUT_S:
            print("WARNING: the stream stopped; saving what was received.")
            return capture, parser
        if elapsed >= seconds + 1.2:  # +1.2 s so a final status line is included
            return capture, parser


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--port", required=True, help="e.g. /dev/cu.usbserial-0001")
    ap.add_argument("--baud", type=int, default=921600)
    ap.add_argument("--seconds", type=float, default=30.0)
    ap.add_argument("--condition", type=label, default="rest")
    ap.add_argument("--mount", type=label, default="desk-flat")
    ap.add_argument("--repeat", type=int, default=1)
    ap.add_argument("--note", default="", help="free text saved in the file header")
    ap.add_argument("--no-reset", action="store_true", help="do not reset the board first")
    ap.add_argument("--raw-dir", type=Path, default=DEFAULT_RAW)
    ap.add_argument("--out-dir", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args(argv)

    stamp = datetime.now()
    name = (f"{stamp:%Y%m%d-%H%M}_adxl355_{args.condition}_{args.mount}"
            f"_r{args.repeat}.csv")
    path = args.raw_dir / name
    if path.exists():
        sys.exit(f"{path} already exists; use another --repeat number")

    ser = open_port(args.port, args.baud)
    try:
        if not args.no_reset:
            reset_board(ser)
        capture, parser = record(ser, args.seconds)
    finally:
        ser.close()

    if capture.n_sets == 0:
        sys.exit("No samples received; nothing saved.")
    odr = estimate_odr_hz(capture.status_lines())
    header = {
        "sensor": "ADXL355 on EVAL-ADXL355-PMDZ, +/-2 g, ODR 4000 Hz nominal, low-pass 1000 Hz",
        "scale": "256000 LSB/g typical, uncalibrated (+/-8 %); raw counts are 20-bit",
        "host": "ESP32-S3 (DevKitC-1 copy, XH-S3E N16R8), SPI2 8 MHz, UART0 stream",
        "port": f"{args.port} at {args.baud} baud",
        "captured_at": stamp.astimezone().isoformat(timespec="seconds"),
        "condition": args.condition,
        "mount": args.mount,
        "repeat": str(args.repeat),
        "note": args.note,
        "odr_estimate_hz": f"{odr:.2f}" if odr else "",
        "crc_errors": str(parser.crc_errors),
        "skipped_bytes": str(parser.skipped_bytes),
        "frames": str(capture.frames),
        "missing_sets": str(capture.missing_sets),
        "sequence_gaps": str(capture.sequence_gaps),
        "restarts": str(capture.restarts),
        "frames_flagged_overrun": str(capture.overrun_flags),
        "frames_flagged_dropped": str(capture.dropped_flags),
        "columns": "index = set number from start of streaming; x/y/z_raw = counts",
    }
    write_capture_csv(path, capture, header)
    print(f"Saved {path}")
    if capture.restarts:
        print(f"WARNING: the board restarted {capture.restarts} time(s) during the capture.")

    loaded = load_capture_csv(path)
    try:
        row = summarize(loaded)
    except ValueError as error:
        print(f"Too little data to check: {error}")
        return 1
    print()
    print(format_report(row, checks(loaded, row)))
    args.out_dir.mkdir(parents=True, exist_ok=True)
    plot = args.out_dir / f"{path.stem}_noise.png"
    plot_noise(loaded, plot)
    print(f"Noise plot: {plot}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
