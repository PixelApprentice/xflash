"""View-model: everything the UI knows how to draw.

Backends and adapters produce these objects; the UI never sees raw collector
output. A new hardware screen is just a Page made of Blocks, with no UI code.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional, Union


class Status(Enum):
    PASS = "pass"
    WARN = "warn"
    FAIL = "fail"
    CLAIM = "claim"        # observed value contradicts the seller's listing
    OPEN = "open"          # skipped / not run
    UNSURE = "unsure"      # inconclusive: never shown as healthy
    IDLE = "idle"
    QUEUED = "queued"
    RUNNING = "running"

    @property
    def word(self) -> str:
        return self.value.upper()

    @property
    def short(self) -> str:
        return "OK" if self is Status.PASS else self.word

    @property
    def role(self) -> str:
        return {Status.PASS: "p", Status.WARN: "w", Status.FAIL: "c", Status.CLAIM: "c",
                Status.RUNNING: "w"}.get(self, "t3")

    @property
    def bucket(self) -> str:
        if self in (Status.FAIL, Status.CLAIM):
            return "fail"
        return {Status.WARN: "warn", Status.PASS: "pass"}.get(self, "open")

    @classmethod
    def parse(cls, value) -> "Status":
        """Tolerant parser. Unknown input becomes UNSURE, never PASS."""
        if isinstance(value, Status):
            return value
        key = str(value).strip().lower().replace("-", "_").replace(" ", "_")
        return _ALIASES.get(key, Status.UNSURE)


_ALIASES = {
    "pass": Status.PASS, "ok": Status.PASS, "healthy": Status.PASS, "good": Status.PASS,
    "warn": Status.WARN, "warning": Status.WARN,
    "fail": Status.FAIL, "failed": Status.FAIL, "critical": Status.FAIL, "error": Status.FAIL,
    "claim": Status.CLAIM, "mismatch": Status.CLAIM, "discrepancy": Status.CLAIM,
    "open": Status.OPEN, "skipped": Status.OPEN, "skip": Status.OPEN, "not_run": Status.OPEN,
    "inconclusive": Status.UNSURE, "unknown": Status.UNSURE, "unsure": Status.UNSURE,
    "idle": Status.IDLE, "queued": Status.QUEUED, "running": Status.RUNNING,
}

# ───────────────────────── blocks (generic building pieces for Pages)
# A short ALL-CAPS title (<= 8 chars) renders as a coloured chip, anything else as bold text.


@dataclass
class KV:
    title: str
    rows: list                      # [(key, value)]; value "@warn" renders a status
    kind: str = "kv"


@dataclass
class Chart:
    title: str
    values: list
    lo: float
    hi: float
    sub: str = ""
    x_left: str = ""
    x_right: str = ""
    role: str = "w"
    height: int = 5
    kind: str = "chart"


@dataclass
class Bars:
    title: str
    rows: list                      # [(label, fraction 0..1, text, role)]
    sub: str = ""
    kind: str = "bars"


@dataclass
class Hist:
    title: str
    rows: list                      # [(label, count)]
    sub: str = ""
    footer: str = ""
    kind: str = "hist"


@dataclass
class Grid:
    title: str
    cells: list                     # [[0..100, ...], ...]
    sub: str = ""
    footer: str = ""
    kind: str = "grid"


@dataclass
class Keycaps:
    title: str
    rows: list                      # ["1234567890", "QWERTYUIOP", ...]
    untested: str = ""
    flagged: dict = field(default_factory=dict)   # key -> reason
    pressed: int = 0
    total: int = 0
    sub: str = ""
    note: str = ""
    kind: str = "keycaps"


@dataclass
class Lines:
    title: str
    lines: list
    sub: str = ""
    kind: str = "lines"


Block = Union[KV, Chart, Bars, Hist, Grid, Keycaps, Lines]

# ───────────────────────── session pieces


@dataclass
class Bay:
    name: str
    value: str = "—"
    status: Status = Status.IDLE
    bar: Optional[float] = None
    spark: Optional[list] = None
    sub: str = ""
    plain: str = ""                 # text for --plain output
    target: str = ""                # "rules" or a Page id opened by the bay key
    rule: str = ""                  # finding id to preselect when target == "rules"


@dataclass
class Finding:
    id: str
    name: str
    status: Status
    value: str = ""
    note: str = ""                  # e.g. "threshold 80 %"
    title: str = ""
    blocks: list = field(default_factory=list)


@dataclass
class Page:
    id: str
    title: str
    label: str                      # status-bar chip, e.g. "STORAGE"
    summary: str = ""
    right: str = ""
    columns: list = field(default_factory=list)   # list of columns, each a list of Blocks
    note: str = ""


@dataclass
class SessionRef:
    id: str
    date: str
    fail: int = 0
    warn: int = 0


@dataclass
class Session:
    id: str
    title: str
    bays: list
    findings: list
    machine: dict = field(default_factory=dict)
    pages: dict = field(default_factory=dict)
    report_path: str = ""


@dataclass
class Check:
    name: str
    status: Status = Status.QUEUED
    seconds: float = 0.0
    text: str = ""
    bay: Optional[int] = None


DEFAULT_BAYS = ["BAT", "SSD", "MEM", "CPU", "FAN", "DSP"]
