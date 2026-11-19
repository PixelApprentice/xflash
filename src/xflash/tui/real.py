"""RealBackend: connects the TUI to Xflash's own collector, analysis, report and database code.

Imports are lazy so this module always loads; if a piece is missing the user sees a message in
the status bar instead of a traceback. Tests patch the four `_*` wrappers below.

Known limit: collectors are single-shot (`collect_snapshot`), so the live scan shows two real
steps (collect, analyze) instead of one row per rule. Per-check streaming needs a progress
callback in the collector; when it exists, emit more CheckUpdate events from scan().
"""
from __future__ import annotations

import contextlib
import io
import json
import platform
import re
import socket
import threading
import time
from pathlib import Path
from typing import Callable, Optional

from .adapter import to_session
from .backend import Backend, CheckUpdate, NotSupported, ScanFinished, ScanOptions, ScanStarted
from .model import Session, Status

# ───────────────────────── thin wrappers around the project's functions (patched in tests)


def _collect(claims: dict) -> dict:
    from ..cli import _collect_live_or_fallback        # same fallback behaviour as `xflash scan`
    return _collect_live_or_fallback(claims)


def _analyze(snapshot: dict) -> dict:
    from ..analysis import analyze_snapshot
    return analyze_snapshot(snapshot)


def _render_report(report: dict, fmt: str) -> str:
    from ..report import to_html, to_json
    return to_html(report) if fmt == "html" else to_json(report)


def _save_db(snapshot: dict, report: dict, portable: bool) -> str:
    from ..db import Database, get_default_db_path
    path = get_default_db_path(portable=portable)
    Database(path).save_session(snapshot, report, operator_notes="TUI Inspection")
    return str(path)


def _run_server(host: str, port: int, portable: bool) -> None:
    from ..web.server import run_server
    run_server(host=host, port=port, portable=portable, open_browser=False)


# ───────────────────────── claims coming from the palette (--claim-ram 16 ...) -> snapshot claims
_CLAIM_KEYS = {"model": ("model", str), "cpu": ("cpu", str), "ram": ("ram_gib", float),
               "storage": ("storage_capacity_gb", float), "price": ("price", float), "url": ("listing_url", str)}


def claims_from_options(raw: dict) -> dict:
    out = {}
    for key, value in (raw or {}).items():
        if key not in _CLAIM_KEYS:
            raise ValueError(f"unknown claim '--claim-{key}'. Known: " + ", ".join(sorted(_CLAIM_KEYS)))
        name, cast = _CLAIM_KEYS[key]
        try:
            out[name] = cast(value)
        except ValueError:
            raise ValueError(f"--claim-{key} expects a number, got '{value}'") from None
    return out


class RealBackend(Backend):
    name = "xflash"

    def __init__(self, portable: bool = False):
        self.portable = portable
        self._server: Optional[threading.Thread] = None

    # -- static facts for the home screen (cheap, no hardware probing) -----------------------
    def machine(self) -> dict:
        return {"System": f"{platform.system()} {platform.release()}", "Machine": platform.machine(),
                "Mode": "portable (zero-trace)" if self.portable else "installed",
                "Network": "none used (offline)"}

    # -- live scan, on a worker thread -------------------------------------------------------
    def scan(self, opts: ScanOptions, emit: Callable, cancel: threading.Event) -> None:
        claims = claims_from_options(opts.claims)
        emit(ScanStarted(["collect hardware", "analyze rules"]))
        t0 = time.monotonic()
        emit(CheckUpdate(0, Status.RUNNING))
        notes = io.StringIO()
        with contextlib.redirect_stderr(notes):           # the collector prints notices to stderr
            snapshot = _collect(claims)
        note = notes.getvalue().strip().splitlines()[-1] if notes.getvalue().strip() else ""
        if cancel.is_set():
            return
        emit(CheckUpdate(0, Status.WARN if note else Status.PASS, time.monotonic() - t0,
                         note or "hardware snapshot collected"))
        t1 = time.monotonic()
        emit(CheckUpdate(1, Status.RUNNING))
        report = _analyze(snapshot)
        if cancel.is_set():
            return
        n = report.get("finding_count", len(report.get("findings") or [])) if isinstance(report, dict) else 0
        emit(CheckUpdate(1, Status.PASS, time.monotonic() - t1, f"{n} finding{'s' if n != 1 else ''}"))
        session = to_session(snapshot, report)
        if self.portable:                                  # same rule as `xflash scan --portable`
            try:
                _save_db(snapshot, report, True)
            except Exception:  # noqa: BLE001 - persistence is best effort, as in the CLI
                pass
        emit(ScanFinished(session))

    # -- :open / --session -----------------------------------------------------------------
    def load(self, ref: str) -> Session:
        path = Path(ref)
        try:
            snapshot = json.loads(path.read_text(encoding="utf-8"))
        except OSError as e:
            raise NotSupported(f"cannot read {ref}: {e.strerror or e}") from None
        except json.JSONDecodeError as e:
            raise NotSupported(f"{ref} is not valid JSON: {e.msg}") from None
        if not isinstance(snapshot, dict):
            raise NotSupported("top-level JSON value must be an object")
        return to_session(snapshot, _analyze(snapshot))

    # -- :export / :save / :serve ------------------------------------------------------------
    def export(self, session: Session, fmt: str, path: Optional[str]) -> str:
        if not (isinstance(session.raw, tuple) and len(session.raw) == 2):
            raise NotSupported("this session has no report to export")
        out = Path(path) if path else Path("aegis_reports") / (re.sub(r"[^\w.-]+", "_", session.id) + "." + fmt)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(_render_report(session.raw[1], fmt), encoding="utf-8")
        return str(out)

    def save(self, session: Session) -> str:
        if not (isinstance(session.raw, tuple) and len(session.raw) == 2):
            raise NotSupported("this session has no report to save")
        return _save_db(session.raw[0], session.raw[1], self.portable)

    def serve(self, host: str = "127.0.0.1", port: int = 8080) -> str:
        if self._server and self._server.is_alive():
            return f"http://{host}:{port}"
        with socket.socket() as s:                         # fail fast with a clear message if the port is taken
            if s.connect_ex((host, port)) == 0:
                raise OSError(f"port {port} is already in use")
        self._server = threading.Thread(target=_run_server, args=(host, port, self.portable), daemon=True,
                                        name="xflash-dashboard")
        self._server.start()
        return f"http://{host}:{port}"
