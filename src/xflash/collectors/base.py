"""Base collector protocols, data structures, and safe command execution."""
from __future__ import annotations

import os
import subprocess
import time
from dataclasses import dataclass
from typing import Any, Protocol


@dataclass
class CommandResult:
    args: list[str]
    returncode: int
    stdout: str
    stderr: str
    duration_seconds: float
    timed_out: bool = False
    error_message: str | None = None


def safe_exec(
    args: list[str],
    timeout_seconds: float = 5.0,
    max_bytes: int = 1_000_000,
) -> CommandResult:
    """Execute a subprocess safely with fixed argument array, timeout, and bounded output.

    Enforces shell=False, non-destructive execution, and handles missing binaries cleanly.
    """
    if not isinstance(args, list) or not all(isinstance(a, str) for a in args):
        raise TypeError("args must be a list of strings")
    if not args:
        raise ValueError("args must not be empty")

    start_time = time.monotonic()
    try:
        proc = subprocess.run(
            args,
            shell=False,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=timeout_seconds,
            check=False,
        )
        duration = time.monotonic() - start_time
        stdout = proc.stdout[:max_bytes].decode("utf-8", errors="replace")
        stderr = proc.stderr[:max_bytes].decode("utf-8", errors="replace")
        return CommandResult(
            args=args,
            returncode=proc.returncode,
            stdout=stdout,
            stderr=stderr,
            duration_seconds=duration,
        )
    except subprocess.TimeoutExpired as exc:
        duration = time.monotonic() - start_time
        stdout = (exc.stdout or b"")[:max_bytes].decode("utf-8", errors="replace")
        stderr = (exc.stderr or b"")[:max_bytes].decode("utf-8", errors="replace")
        return CommandResult(
            args=args,
            returncode=-1,
            stdout=stdout,
            stderr=stderr,
            duration_seconds=duration,
            timed_out=True,
            error_message=f"Command timed out after {timeout_seconds:.1f} seconds",
        )
    except FileNotFoundError as exc:
        duration = time.monotonic() - start_time
        return CommandResult(
            args=args,
            returncode=127,
            stdout="",
            stderr=str(exc),
            duration_seconds=duration,
            error_message=f"Executable '{args[0]}' was not found on PATH",
        )
    except PermissionError as exc:
        duration = time.monotonic() - start_time
        return CommandResult(
            args=args,
            returncode=126,
            stdout="",
            stderr=str(exc),
            duration_seconds=duration,
            error_message=f"Permission denied executing '{args[0]}'",
        )
    except Exception as exc:
        duration = time.monotonic() - start_time
        return CommandResult(
            args=args,
            returncode=1,
            stdout="",
            stderr=str(exc),
            duration_seconds=duration,
            error_message=f"Execution error: {exc}",
        )


class Collector(Protocol):
    """Protocol for platform-specific hardware inventory and sensor collectors."""

    def collect_battery(self) -> dict[str, Any] | None:
        ...

    def collect_system(self) -> dict[str, Any]:
        ...

    def collect_memory(self) -> dict[str, Any]:
        ...

    def collect_storage(self) -> dict[str, Any]:
        ...

    def collect_snapshot(self, claims: dict[str, Any] | None = None) -> dict[str, Any]:
        ...
