"""Entry point:  xflash tui [--session FILE] [--plain] [--once SCREEN] [--ascii] [--no-color]

Backend selection: if xflash/tui/real.py defines `RealBackend`, it is used.
Otherwise the clearly-marked DEMO backend runs, so the UI is always explorable.
"""
from __future__ import annotations

import argparse
import importlib
import sys
from typing import Optional

from .app import App, ScanState
from .backend import Backend, ScanOptions, run_scan_blocking
from .demo import DemoBackend
from .plain import render_plain
from .term import Terminal
from .theme import Theme


def default_backend() -> Backend:
    try:
        return importlib.import_module(f"{__package__}.real").RealBackend()
    except ModuleNotFoundError as e:
        if e.name != f"{__package__}.real":
            raise                      # real.py exists but one of ITS imports is broken: say so
        return DemoBackend()


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="xflash tui", description="Terminal UI for Xflash.")
    p.add_argument("snapshot", nargs="?", help="optional snapshot JSON file to open")
    p.add_argument("--session", metavar="REF", help="open a saved session instead of scanning")
    p.add_argument("--plain", action="store_true", help="plain text report (default when output is piped)")
    p.add_argument("--once", metavar="SCREEN", nargs="?", const="rules",
                   help="print one frame and exit: home, rules, scan, palette, help, or a page id")
    p.add_argument("--width", type=int)
    p.add_argument("--height", type=int)
    p.add_argument("--no-color", action="store_true")
    p.add_argument("--ascii", action="store_true", help="ASCII-only glyphs for legacy consoles")
    p.add_argument("--lens", choices=["auto", "expert", "pixel"], default="auto", help="UI lens preference")
    return p


def _snapshot(app: App, name: str, backend: Backend, args) -> None:
    session_ref = getattr(args, "session", None) or getattr(args, "snapshot", None)
    if name == "scan" and isinstance(backend, DemoBackend):
        for i, ev in enumerate(backend.events()):
            if i >= 22:
                break
            app.scan = app.scan or ScanState()
            app._apply(ev)
        app.goto("scan")
        return

    if session_ref:
        app.set_session(backend.load(session_ref))
    elif name != "home":
        if backend.is_demo:
            app.set_session(backend.load("demo"))
        else:
            app.set_session(run_scan_blocking(backend))

    if name == "home":
        app.goto("home")
    elif name == "palette":
        app.mode, app.buf = "cmd", "s"
    elif name == "help":
        app.help = True
    elif name == "rules":
        app.goto("rules")
    elif name != "scan":
        app.goto("page", name)


def main(argv: Optional[list] = None, backend: Optional[Backend] = None, stdout=None) -> int:
    args = build_parser().parse_args(argv)
    out = stdout or sys.stdout
    if hasattr(out, "reconfigure"):
        try:
            out.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass
    backend = backend or default_backend()
    theme = Theme.detect(out, no_color=args.no_color, ascii_only=args.ascii)
    session_ref = getattr(args, "session", None) or getattr(args, "snapshot", None)

    if args.plain or (not getattr(out, "isatty", lambda: False)() and args.once is None):
        session = backend.load(session_ref) if session_ref else (
            backend.load("demo") if backend.is_demo else run_scan_blocking(backend))
        print(render_plain(theme, session), file=out)
        return 0

    if args.once is not None:
        size = (args.width or 120, args.height or 36)
        app = App(backend, theme, size)
        app.lens_pref = getattr(args, "lens", "auto")
        _snapshot(app, args.once, backend, args)
        print("\n".join(app.render()), file=out)
        return 0

    if not sys.stdin.isatty():
        print("xflash tui needs an interactive terminal. Use --plain for piped output.", file=sys.stderr)
        return 2
    app = App(backend, theme)
    app.lens_pref = getattr(args, "lens", "auto")
    if session_ref:
        app.set_session(backend.load(session_ref), "home")
    with Terminal() as term:
        app.run(term)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
