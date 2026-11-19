"""Report host tools and ESP-IDF install locations. Does not install or build anything.

``idf.py build``, ``idf.py flash``, and ``idf.py set-target`` are not invoked.
A missing tool is a line in the report, not something this module repairs.
Mac install steps stay in ``DEVELOPMENT_SETUP.md``.
"""

from __future__ import annotations

import os
import shutil
import subprocess
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class ToolStatus:
    name: str
    present: bool
    detail: str


@dataclass(frozen=True)
class CommandResult:
    returncode: int
    stdout: str
    stderr: str


@dataclass(frozen=True)
class HostReport:
    platform: str
    tools: tuple[ToolStatus, ...]
    environment_paths: tuple[ToolStatus, ...]


WhichFn = Callable[[str], str | None]
RunFn = Callable[[Sequence[str]], CommandResult]


def default_probe_commands() -> tuple[tuple[str, tuple[str, ...]], ...]:
    """Version checks only. No configure, build, or flash arguments."""
    return (
        ("python3", ("python3", "--version")),
        ("git", ("git", "--version")),
        ("cmake", ("cmake", "--version")),
        ("ninja", ("ninja", "--version")),
        ("idf.py", ("idf.py", "--version")),
        ("pytest", ("python3", "-m", "pytest", "--version")),
    )


def probe_tool(name: str, argv: Sequence[str], *, which: WhichFn, run: RunFn) -> ToolStatus:
    """Return whether ``argv`` can be executed, and the first output line."""
    if not argv:
        raise ValueError("argv must not be empty")
    if which(argv[0]) is None:
        return ToolStatus(name, False, "not found")
    try:
        completed = run(argv)
    except (OSError, subprocess.TimeoutExpired):
        return ToolStatus(name, False, "failed to run")
    detail = _first_line(completed.stdout, completed.stderr)
    if not detail:
        detail = f"exit {completed.returncode}"
    if completed.returncode != 0:
        return ToolStatus(name, False, detail)
    return ToolStatus(name, True, detail)


def idf_path_status(environ: Mapping[str, str]) -> ToolStatus:
    value = environ.get("IDF_PATH", "").strip()
    if not value:
        return ToolStatus("IDF_PATH", False, "unset")
    return ToolStatus("IDF_PATH", True, value)


def environment_path_status(name: str, path: Path) -> ToolStatus:
    return ToolStatus(name, path.is_dir(), str(path))


def default_environment_paths(home: Path) -> tuple[tuple[str, Path], ...]:
    return (
        ("espressif_tools", home / ".espressif"),
        ("esp_directory", home / "esp"),
        ("opt_esp_idf", Path("/opt/esp-idf")),
    )


def current_platform() -> str:
    info = os.uname()
    return f"{info.sysname} {info.release} {info.machine}"


def build_report(
    *,
    platform: str,
    tools: Sequence[ToolStatus],
    environment_paths: Sequence[ToolStatus],
) -> HostReport:
    return HostReport(
        platform=platform,
        tools=tuple(tools),
        environment_paths=tuple(environment_paths),
    )


def collect_live_report(*, home: Path | None = None) -> HostReport:
    """Probe this process's PATH and environment. Still does not build firmware."""
    home_dir = Path.home() if home is None else home
    tools = [
        probe_tool(name, argv, which=shutil.which, run=_run_command)
        for name, argv in default_probe_commands()
    ]
    tools.append(idf_path_status(os.environ))
    env_paths = [
        environment_path_status(name, path)
        for name, path in default_environment_paths(home_dir)
    ]
    return build_report(
        platform=current_platform(),
        tools=tools,
        environment_paths=env_paths,
    )


def render_report(report: HostReport) -> str:
    lines = [f"platform: {report.platform}", "tools:"]
    for status in report.tools:
        lines.append(f"  {_format_status(status)}")
    lines.append("environment_paths:")
    for status in report.environment_paths:
        lines.append(f"  {_format_status(status)}")
    lines.append("firmware_build: not_run")
    return "\n".join(lines) + "\n"


def _format_status(status: ToolStatus) -> str:
    state = "present" if status.present else "absent"
    return f"{status.name}: {state}: {status.detail}"


def _run_command(argv: Sequence[str]) -> CommandResult:
    completed = subprocess.run(
        list(argv),
        check=False,
        capture_output=True,
        text=True,
        timeout=10,
    )
    return CommandResult(
        returncode=completed.returncode,
        stdout=completed.stdout,
        stderr=completed.stderr,
    )


def _first_line(stdout: str, stderr: str) -> str:
    combined = "\n".join(part.strip() for part in (stdout, stderr) if part and part.strip())
    for line in combined.splitlines():
        stripped = line.strip()
        if stripped:
            return stripped
    return ""
