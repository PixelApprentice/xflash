"""The contract between the UI and the real inspector.

Subclass Backend and override only what you support. The UI asks
`backend.supports("scan")` etc., and greys out the rest in the command palette.

Threading rule: `scan()` runs on a worker thread. It must call `emit(event)` for
progress, poll `cancel.is_set()` between steps, and finish with ScanFinished or
ScanFailed. Everything else is called on the UI thread and should be quick.
"""
from __future__ import annotations

import threading
from dataclasses import dataclass, field
from typing import Callable, Optional

from .model import Bay, Page, Session, SessionRef, Status


class NotSupported(Exception):
    """Raised by Backend methods the concrete backend does not implement."""


@dataclass
class ScanOptions:
    claims: dict = field(default_factory=dict)   # {"ram": "16", "storage": "512", "model": "..."}


@dataclass
class ScanStarted:
    checks: list                      # names, in order


@dataclass
class CheckUpdate:
    index: int
    status: Status                    # RUNNING when it starts, then the final status
    seconds: float = 0.0
    text: str = ""
    bay: Optional[int] = None         # which bay this check feeds
    bay_view: Optional[Bay] = None    # live value to show in that bay (optional)


@dataclass
class PulseSample:
    value: float                      # package temperature sample for the scan chart


@dataclass
class ScanFinished:
    session: Session


@dataclass
class ScanFailed:
    message: str


class Backend:
    name = "backend"
    is_demo = False

    def machine(self) -> dict:
        """Static facts for the home screen (vendor, product, BIOS...). Must be fast."""
        return {}

    def history(self) -> list:
        """list[SessionRef] saved on this USB drive."""
        return []

    def scan(self, opts: ScanOptions, emit: Callable, cancel: threading.Event) -> None:
        raise NotSupported("scan")

    def load(self, ref: str) -> Session:
        raise NotSupported("open")

    def export(self, session: Session, fmt: str, path: Optional[str]) -> str:
        """Write json/html, return the path written."""
        raise NotSupported("export")

    def save(self, session: Session) -> str:
        """Persist to the USB drive, return the path written."""
        raise NotSupported("save")

    def serve(self) -> str:
        """Start the local dashboard and return its URL."""
        raise NotSupported("serve")

    def diff(self, a: str, b: str) -> Page:
        raise NotSupported("diff")

    def tool(self, name: str):
        """Interactive tools (screen studio...). Return a Page to display, or a message string."""
        raise NotSupported(name)

    def supports(self, op: str) -> bool:
        base = getattr(Backend, op, None)
        return base is not None and getattr(type(self), op, None) is not base


def run_scan_blocking(backend: Backend, opts: Optional[ScanOptions] = None) -> Session:
    """Drive backend.scan() to completion without a UI (used for --plain)."""
    result: list = []

    def emit(ev):
        if isinstance(ev, ScanFinished):
            result.append(ev.session)
        elif isinstance(ev, ScanFailed):
            raise RuntimeError(ev.message)

    backend.scan(opts or ScanOptions(), emit, threading.Event())
    if not result:
        raise RuntimeError("scan ended without a result")
    return result[0]
