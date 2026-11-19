"""Colour and glyph capabilities, resolved once and passed around explicitly.

Nothing in the UI reads the environment directly: build a Theme (usually with
Theme.detect()) and hand it to the App. That keeps rendering deterministic and
testable, and lets --no-color / --ascii / NO_COLOR work everywhere.
"""
from __future__ import annotations

import os
import re
import sys
from dataclasses import dataclass, field

ANSI_RE = re.compile(r"\x1b\[[0-9;?]*[A-Za-z]")
RST = "\x1b[0m"

PALETTE = {
    "p": (127, 214, 176),   # pass
    "w": (242, 184, 75),    # warn / accent
    "c": (255, 125, 104),   # fail / claim
    "t": (232, 230, 223),   # primary text
    "t2": (182, 180, 171),  # secondary text
    "t3": (155, 153, 143),  # dim text
    "ls": (114, 118, 122),  # lines
    "ln": (60, 64, 68),     # dark/inactive gauge lines & blocks
}
_BASIC = {"p": 32, "w": 33, "c": 31, "t": 97, "t2": 37, "t3": 90, "ls": 90, "ln": 90}
_SELBG_TC, _SELBG_BASIC = "\x1b[48;2;46;50;54m", "\x1b[100m"

UNI = dict(
    ok="●", warn="▲", fail="✕", open="○", unsure="◇", full="█", empty="░", ell="…",
    sel="▶ ", dot="·", cur="◂", spin="⠋⠙⠹⠸⠼⠴⠦⠧⠇⠏", blocks=" ▁▂▃▄▅▆▇█",
    eighths=["", "▏", "▎", "▍", "▌", "▋", "▊", "▉"],
    tl="┌", tr="┐", bl="└", br="┘", h="─", v="│", tt="┬", bt="┴",
    Htl="┏", Htr="┓", Hbl="┗", Hbr="┛", Hh="━", Hv="┃", Htt="┳", Hbt="┻",
    Rtl="╭", Rtr="╮", Rbl="╰", Rbr="╯",
)
ASCII = dict(
    ok="o", warn="^", fail="x", open=".", unsure="?", full="#", empty="-", ell="~",
    sel="> ", dot="|", cur="<", spin="|/-\\", blocks=" .:-=+*#@", eighths=[""] * 8,
    tl="+", tr="+", bl="+", br="+", h="-", v="|", tt="+", bt="+",
    Htl="+", Htr="+", Hbl="+", Hbr="+", Hh="=", Hv="|", Htt="+", Hbt="+",
    Rtl="+", Rtr="+", Rbl="+", Rbr="+",
)
_TRANSLIT = str.maketrans({"·": "|", "—": "-", "–": "-", "°": " deg", "×": "x", "…": "~",
                           "µ": "u", "◂": "<", "≥": ">=", "≤": "<=", "'": "'", "\u201c": '"', "\u201d": '"'})


@dataclass(frozen=True)
class Theme:
    color: str = "truecolor"      # "none" | "basic" | "truecolor"
    unicode: bool = True
    g: dict = field(init=False, repr=False, compare=False, default_factory=dict)

    def __post_init__(self):
        object.__setattr__(self, "g", UNI if self.unicode else ASCII)

    @classmethod
    def detect(cls, stream=None, no_color: bool = False, ascii_only: bool = False, env=None) -> "Theme":
        env = os.environ if env is None else env
        stream = stream or sys.stdout
        tty = bool(getattr(stream, "isatty", lambda: False)())
        if no_color or "NO_COLOR" in env or env.get("TERM") == "dumb" or not (tty or env.get("FORCE_COLOR")):
            color = "none"
        elif env.get("COLORTERM", "").lower() in ("truecolor", "24bit") or env.get("WT_SESSION"):
            color = "truecolor"
        else:
            color = "basic"
        enc = (getattr(stream, "encoding", None) or "").lower()
        return cls(color=color, unicode=not ascii_only and "utf" in enc)

    # -- colour ---------------------------------------------------------
    def _fg(self, role: str) -> str:
        if self.color == "truecolor":
            rgb = PALETTE.get(role, PALETTE.get("ls", (114, 118, 122)))
            return f"38;2;{';'.join(map(str, rgb))}"
        return str(_BASIC.get(role, 90))

    def paint(self, role: str, text: str, bold: bool = False) -> str:
        if self.color == "none" or text == "":
            return text
        return f"\x1b[{'1;' if bold else ''}{self._fg(role)}m{text}{RST}"

    def chip(self, role: str, text: str) -> str:
        if self.color == "none":
            return f"[{text.strip()}]"
        if self.color == "truecolor":
            rgb = PALETTE.get(role, PALETTE.get("w", (242, 184, 75)))
            code = f"48;2;{';'.join(map(str, rgb))};38;2;17;19;21"
        else:
            basic = _BASIC.get(role, 33)
            code = f"{basic};7"
        return f"\x1b[{code}m{text}{RST}"

    def selected(self, text: str, width: int) -> str:
        """Row highlight. Without colour the caller's gutter marker carries the state."""
        if self.color == "none":
            return text
        bg = _SELBG_TC if self.color == "truecolor" else _SELBG_BASIC
        n = len(ANSI_RE.sub("", text))
        return bg + (text + " " * max(0, width - n)).replace(RST, RST + bg) + RST

    def safe(self, s: str) -> str:
        """In ASCII mode, make arbitrary backend text safe for legacy consoles."""
        if self.unicode:
            return s
        return s.translate(_TRANSLIT).encode("ascii", "replace").decode("ascii")

    def paint2(self, top_role: str, bot_role: str, ch: str) -> str:
        """Half-block pixel rendering: top colour as foreground, bottom as background."""
        if self.color == "none":
            return ch
        if self.color == "truecolor":
            tr, br = PALETTE.get(top_role, PALETTE["t"]), PALETTE.get(bot_role, PALETTE["t"])
            code = f"38;2;{';'.join(map(str, tr))};48;2;{';'.join(map(str, br))}"
        else:
            code = f"{_BASIC.get(top_role, 97)};{_BASIC.get(bot_role, 97)};7"
        return f"\x1b[{code}m{ch}{RST}"
