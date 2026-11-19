"""Xflash terminal UI: stdlib-only, backend-agnostic.

Usage:
    xflash tui                      # interactive (DEMO DATA until real.py exists)
    xflash tui --plain              # plain text, automatic when piped
    xflash tui --once storage       # one frame, for docs and screenshots
    flags: --session REF  --width N --height N  --no-color  --ascii
"""
from .app import App, Command
from .backend import (Backend, CheckUpdate, NotSupported, PulseSample, ScanFailed, ScanFinished, ScanOptions,
                      ScanStarted, run_scan_blocking)
from .cli import main
from .model import (Bars, Bay, Card, Chart, Check, Finding, Grid, Hero, Hist, Keycaps, KV,
                    Lines, Page, Session, SessionRef, Stats, Status)
from .screens import screen
from .theme import Theme
from .widgets import register_block

__all__ = [n for n in dir() if not n.startswith("_")]
