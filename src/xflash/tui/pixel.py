"""Pixel lens primitives. Everything is drawn with half-blocks (▀ ▄ █): one terminal cell is
1 pixel wide and 2 pixels tall, which makes the pixels square. Sprites are the ones from the
Xflash design board, pixel for pixel.

Legend: "#" frame (text colour)  "X" accent (status colour)  "g" fixed green  "a" fixed amber
"""
from __future__ import annotations

import math
from itertools import zip_longest

from .model import Bars, Card, Chart, Hero, KV, Stats, Status
from .theme import Theme
from .widgets import (PIXEL_RENDERERS, clamp, clip, glyph, header, pad, padl, resample, stext, vlen)

SPRITES = {
    "laptop": [
        "  ############  ",
        "  #          #  ",
        "  # gggggggg #  ",
        "  # gggggggg #  ",
        "  # gggggggg #  ",
        "  #          #  ",
        "  ############  ",
        " ############## ",
        "################",
        "#              #",
        "################",
    ],
    "battery": [
        "##############  ",
        "#            #  ",
        "# XXXXXXXX   ###",
        "# XXXXXXXX   ###",
        "# XXXXXXXX   ###",
        "#            #  ",
        "##############  ",
    ],
    "chip": [
        "  #  #  #  #  ",
        " ############ ",
        "##          ##",
        " #  XXXXXX  # ",
        "##  XXXXXX  ##",
        " #  XXXXXX  # ",
        "##          ##",
        " ############ ",
        "  #  #  #  #  ",
    ],
    "fan": [
        "    a    ",
        "    #    ",
        "  # # #  ",
        "   ###   ",
        "####g####",
        "   ###   ",
        "  # # #  ",
        "    #    ",
        "    #    ",
    ],
    "monitor": [
        "##############",
        "#            #",
        "# XXXXXXXXXX #",
        "# XXXXXXXXXX #",
        "# XXXXXXXXXX #",
        "# XXXXXXXXXX #",
        "#            #",
        "##############",
        "     ####     ",
        "   ########   ",
    ],
}
BAY_SPRITES = {"BAT": "battery", "SSD": "chip", "MEM": "chip", "CPU": "chip", "FAN": "fan", "DSP": "monitor"}

# ───────────────────────── half-block rendering
def _cell(th: Theme, top, bot) -> str:
    if top is None and bot is None:
        return " "
    if top == bot:
        return th.paint(top, "█")
    if bot is None:
        return th.paint(top, "▀")
    if top is None:
        return th.paint(bot, "▄")
    return th.paint2(top, bot, "▀")


def _cells(th: Theme, grid: list) -> list:
    """Pixel rows (lists of role|None) -> terminal rows, two pixel rows per row."""
    width = max((len(r) for r in grid), default=0)
    grid = [r + [None] * (width - len(r)) for r in grid]
    if len(grid) % 2:
        grid.append([None] * width)
    return ["".join(_cell(th, t, b) for t, b in zip(grid[y], grid[y + 1])) for y in range(0, len(grid), 2)]


def accent_role(status: Status) -> str:
    return {Status.PASS: "p", Status.WARN: "w", Status.FAIL: "c", Status.CLAIM: "w", Status.RUNNING: "w"}.get(status, "t3")


def rotate(rows: list, deg: float) -> list:
    """Nearest-neighbour rotation about the centre; this is what makes the fan spin in 45 degree steps."""
    h, w = len(rows), max(len(r) for r in rows)
    rows = [r.ljust(w) for r in rows]
    cx, cy, a = (w - 1) / 2, (h - 1) / 2, math.radians(deg)
    ca, sa = math.cos(a), math.sin(a)
    out = []
    for y in range(h):
        line = ""
        for x in range(w):
            sx, sy = round(cx + (x - cx) * ca + (y - cy) * sa), round(cy - (x - cx) * sa + (y - cy) * ca)
            line += rows[sy][sx] if 0 <= sx < w and 0 <= sy < h else " "
        out.append(line)
    return out


def sprite_lines(th: Theme, name: str, accent: str = "p", deg: float = 0) -> list:
    rows = SPRITES[name]
    if deg:
        rows = rotate(rows, deg)
    mapping = {"#": "t", "g": "p", "a": "w", "X": accent}
    return _cells(th, [[mapping.get(ch) for ch in r] for r in rows])


# ───────────────────────── bitmap font (3x5), uppercase only
_FONT_SRC = {
    "0": "111 101 101 101 111", "1": "010 110 010 010 111", "2": "111 001 111 100 111",
    "3": "111 001 111 001 111", "4": "101 101 111 001 001", "5": "111 100 111 001 111",
    "6": "111 100 111 101 111", "7": "111 001 001 010 010", "8": "111 101 111 101 111",
    "9": "111 101 111 001 111",
    "A": "010 101 111 101 101", "B": "110 101 110 101 110", "C": "011 100 100 100 011",
    "D": "110 101 101 101 110", "E": "111 100 110 100 111", "F": "111 100 110 100 100",
    "G": "011 100 101 101 011", "H": "101 101 111 101 101", "I": "111 010 010 010 111",
    "J": "001 001 001 101 010", "K": "101 101 110 101 101", "L": "100 100 100 100 111",
    "M": "101 111 111 101 101", "N": "110 101 101 101 101", "O": "010 101 101 101 010",
    "P": "110 101 110 100 100", "Q": "010 101 101 011 001", "R": "110 101 110 101 101",
    "S": "011 100 010 001 110", "T": "111 010 010 010 010", "U": "101 101 101 101 111",
    "V": "101 101 101 101 010", "W": "101 101 111 111 101", "X": "101 101 010 101 101",
    "Y": "101 101 010 010 010", "Z": "111 001 010 100 111",
    ".": "0 0 0 0 1", ",": "0 0 0 1 1", ":": "0 1 0 1 0", "-": "000 000 111 000 000",
    "%": "101 001 010 100 101", "°": "111 101 111 000 000", "/": "001 001 010 100 100",
    "+": "000 010 111 010 000", "#": "101 111 101 111 101", "·": "0 0 1 0 0", "|": "1 1 1 1 1",
    "_": "000 000 000 000 111", " ": "00 00 00 00 00", "?": "111 001 010 000 010",
}
_ALIAS = {"—": "-", "–": "-", "×": "X", "µ": "U"}
FONT = {k: v.split() for k, v in _FONT_SRC.items()}


def _glyph(ch: str) -> list:
    ch = _ALIAS.get(ch, ch)
    return FONT.get(ch, FONT["?"])


def bigwidth(text: str, scale: int = 1) -> int:
    glyphs = [_glyph(c) for c in text.upper()]
    return scale * (sum(len(g[0]) for g in glyphs) + max(0, len(glyphs) - 1))


def bigtext(th: Theme, text: str, role: str = "t", scale: int = 1) -> list:
    """Bitmap text, 5 pixels tall: 3 terminal rows at scale 1, 5 rows at scale 2."""
    glyphs = [_glyph(c) for c in text.upper()]
    if not glyphs:
        return [""]
    rows = [[] for _ in range(5)]
    for gi, g in enumerate(glyphs):
        for r in range(5):
            rows[r] += [1 if c == "1" else 0 for c in g[r]]
            if gi < len(glyphs) - 1:
                rows[r].append(0)
    grid = []
    for r in rows:
        line = [role if v else None for v in r for _ in range(scale)]
        grid += [line] * scale
    return _cells(th, grid)


def fit_big(th: Theme, text: str, avail: int, role: str, scale: int = 1):
    """(big_lines, leftover). Shrinks to the numeric part if the whole value does not fit."""
    if bigwidth(text, scale) <= avail:
        return bigtext(th, text, role, scale), ""
    num = text.split(" ")[0]
    rest = text[len(num):].strip()
    if num and any(c.isdigit() for c in num) and bigwidth(num, scale) <= avail:
        return bigtext(th, num, role, scale), rest
    return [th.paint(role, clip(text, avail), bold=True)], ""


# ───────────────────────── panels, gauges, charts
def panel(th: Theme, lines: list, w: int, role: str = "ls") -> list:
    """Notched-corner pixel frame, like the design's clip-path panels."""
    inner = w - 4
    b = lambda s: th.paint(role, s)  # noqa: E731
    out = [" " + b("▄" * (w - 2)) + " "]
    out += [b("█") + " " + pad(clip(x, inner), inner) + " " + b("█") for x in lines]
    return out + [" " + b("▀" * (w - 2)) + " "]


def segments(th: Theme, frac: float, n: int, role: str, threshold=None) -> str:
    """Segmented gauge (the design's .sg). A white block marks the threshold."""
    n = max(1, n)
    on = clamp(round(frac * n), 0, n)
    tick = None if threshold is None else clamp(int(threshold * n), 0, n - 1)
    plain = th.color == "none"
    cells = []
    for i in range(n):
        if i == tick:
            cells.append(th.paint("t", "▓▓" if plain else "██", bold=True))
        elif i < on:
            cells.append(th.paint(role, "██"))
        else:
            cells.append(th.paint("ln", "░░" if plain else "██"))
    return " ".join(cells)


def pixel_chart(th: Theme, vals: list, lo: float, hi: float, w: int, rows: int, role: str,
                x_left: str = "", x_right: str = "") -> list:
    """The design's pixel grid: blocky area chart, 2 columns per sample."""
    ncols = max(8, (w - 6) // 2)
    v = resample([float(x) for x in vals], ncols)
    span = (hi - lo) or 1
    levels = [clamp(round((x - lo) / span * rows), 1, rows) for x in v]
    off = "░░" if th.color == "none" else "██"
    out = []
    for r in range(rows - 1, -1, -1):
        label = f"{hi:g}" if r == rows - 1 else f"{lo:g}" if r == 0 else ""
        cells = "".join(th.paint(role, "██") if lv > r else th.paint("ln", off) for lv in levels)
        out.append(th.paint("t3", padl(label, 5)) + " " + cells)
    gap = max(1, ncols * 2 - len(x_left) - len(x_right))
    out.append(" " * 6 + th.paint("t3", x_left + " " * gap + x_right))
    return out


def fan_deg(tick: int) -> float:
    return (tick // 2 % 8) * 45


def side_by_side(left: list, right: list, gap: int = 2) -> list:
    lw = max((vlen(x) for x in left), default=0)
    return [pad(a or "", lw) + " " * gap + (b or "") for a, b in zip_longest(left, right, fillvalue="")]


# ───────────────────────── pixel renderers for blocks (fn(th, block, width, tick))
def p_hero(th: Theme, b: Hero, w: int, tick: int = 0) -> list:
    spr = []
    if b.sprite in SPRITES:
        spr = sprite_lines(th, b.sprite, b.role if b.role in ("p", "w", "c") else "p",
                           fan_deg(tick) if b.sprite == "fan" else 0)
    sw = max((vlen(x) for x in spr), default=0) + (2 if spr else 0)
    scale = 2 if bigwidth(b.value, 2) <= w - sw else 1
    big, rest = fit_big(th, b.value, w - sw, b.role, scale)
    right = ([th.paint("t3", b.title + (" · " + b.sub if b.sub else ""))] if b.title else []) + big
    if rest:
        right.append(th.paint("t3", rest))
    return side_by_side(spr, right) if spr else right


def p_stats(th: Theme, b: Stats, w: int, tick: int = 0) -> list:
    out = [header(th, b.title)] if b.title else []
    half = max(12, w // 2)
    for i in range(0, len(b.items), 2):
        cells = []
        for label, value, role in b.items[i:i + 2]:
            big, rest = fit_big(th, str(value), half - 2, role or "t")
            cells.append([th.paint("t3", str(label))] + big + ([th.paint("t3", rest)] if rest else []))
        n = max(len(c) for c in cells)
        for r in range(n):
            out.append("".join(pad(c[r] if r < len(c) else "", half) for c in cells).rstrip())
        out.append("")
    return out[:-1] if out else out


def p_bars(th: Theme, b: Bars, w: int, tick: int = 0) -> list:
    out = [th.paint("t2", b.title, bold=True) + (" " + th.paint("t3", b.sub) if b.sub else "")] if b.title else []
    lw = clamp(max((len(str(r[0])) for r in b.rows), default=0), 6, 14)
    tw = max((len(str(r[2])) for r in b.rows), default=0)
    n = clamp((w - lw - tw - 3 + 1) // 3, 5, 12)
    for row in b.rows:
        label, frac, text, role = row[:4]
        thr = row[4] if len(row) > 4 else None
        on = str(label) == b.active
        name = th.paint("w", pad(str(label), lw), bold=True) if on else pad(str(label), lw)
        out.append(f"{name} {segments(th, float(frac), n, 'w' if on else (role or 'p'), thr)} {text}")
    if b.footer:
        out.append(th.paint("t3", b.footer))
    return out


def p_kv(th: Theme, b: KV, w: int, tick: int = 0) -> list:
    rows = [(str(k), str(v)) for k, v in b.rows]
    lw = clamp(max((len(k) for k, _ in rows), default=0), 8, 18)
    out = [th.paint("t2", b.title, bold=True)] if b.title else []
    for k, v in rows:
        val = stext(th, Status.parse(v[1:])) if v.startswith("@") else v
        out.append(th.paint("t3", pad(k, lw)) + "  " + clip(val, max(8, w - lw - 2)))
    return out


def p_chart(th: Theme, b: Chart, w: int, tick: int = 0) -> list:
    head = th.paint(b.role, b.title, bold=True) + (" " + th.paint("t3", b.sub) if b.sub else "")
    if len(b.values) < 2:
        return [head, th.paint("t3", "no samples")]
    return [head] + pixel_chart(th, b.values, b.lo, b.hi, w, max(6, b.height + 3), b.role, b.x_left, b.x_right)


def p_card(th: Theme, b: Card, w: int, tick: int = 0) -> list:
    out = [th.paint("t2", b.title, bold=True)] if b.title else []
    for label, text, role in b.items:
        r = role or "t"
        out.append(th.paint(r, f"▸ {label}:", bold=True))
        words = str(text).split()
        line = "   "
        for word in words:
            if len(line) + len(word) + 1 > max(12, w):
                out.append(th.paint("t3" if r == "t" else r, line))
                line = "   " + word
            else:
                line += (" " if line.strip() else "") + word
        if line.strip():
            out.append(th.paint("t3" if r == "t" else r, line))
    return out


PIXEL_RENDERERS.update({"hero": p_hero, "stats": p_stats, "bars": p_bars, "kv": p_kv, "chart": p_chart, "card": p_card})
