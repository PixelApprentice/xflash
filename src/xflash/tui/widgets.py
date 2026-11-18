"""Pure drawing helpers: (theme, data, width) -> list[str]. No I/O, no state."""
from __future__ import annotations

import re
from typing import Callable

from .model import Bars, Block, Chart, Grid, Hist, Keycaps, KV, Lines, Page, Status
from .theme import ANSI_RE, RST, Theme

_ESC_SPLIT = re.compile(r"(\x1b\[[0-9;?]*[A-Za-z])")


def strip(s: str) -> str:
    return ANSI_RE.sub("", s)


def vlen(s: str) -> int:
    return len(strip(s))


def pad(s: str, n: int) -> str:
    return s + " " * max(0, n - vlen(s))


def padl(s: str, n: int) -> str:
    return " " * max(0, n - vlen(s)) + s


def clip(s: str, n: int, ell: str = "…") -> str:
    """ANSI-aware truncate to n visible cells."""
    if n <= 0:
        return ""
    if vlen(s) <= n:
        return s
    out, seen, styled = [], 0, False
    for part in _ESC_SPLIT.split(s):
        if part.startswith("\x1b"):
            out.append(part)
            styled = True
            continue
        for ch in part:
            if seen >= n - 1:
                return "".join(out) + ell + (RST if styled else "")
            out.append(ch)
            seen += 1
    return "".join(out)


def clamp(x, lo, hi):
    return max(lo, min(hi, x))


# ───────────────────────── status glyphs
_GLYPH_KEY = {Status.PASS: "ok", Status.WARN: "warn", Status.FAIL: "fail", Status.CLAIM: "fail",
              Status.OPEN: "open", Status.UNSURE: "unsure", Status.IDLE: "open", Status.QUEUED: "open"}


def glyph_raw(th: Theme, st: Status, tick: int = 0) -> str:
    if st is Status.RUNNING:
        spin = th.g["spin"]
        return spin[tick % len(spin)]
    return th.g[_GLYPH_KEY[st]]


def glyph(th: Theme, st: Status, tick: int = 0) -> str:
    return th.paint(st.role, glyph_raw(th, st, tick))


def stext(th: Theme, st: Status, tick: int = 0, short: bool = False) -> str:
    """Glyph AND word, always: colour is never the only signal."""
    return th.paint(st.role, f"{glyph_raw(th, st, tick)} {st.short if short else st.word}")


# ───────────────────────── primitives
def resample(vals: list, w: int) -> list:
    if len(vals) < 2 or len(vals) == w:
        return list(vals)
    out = []
    for i in range(w):
        p = i * (len(vals) - 1) / max(1, w - 1)
        lo = int(p)
        hi = min(len(vals) - 1, lo + 1)
        out.append(vals[lo] * (1 - (p - lo)) + vals[hi] * (p - lo))
    return out


def bar(th: Theme, frac: float, w: int, role: str = "t2") -> str:
    n = clamp(round(frac * w), 0, w)
    return th.paint(role, th.g["full"] * n) + th.paint("ls", th.g["empty"] * (w - n))


def hbar(th: Theme, frac: float, w: int, role: str = "t2") -> str:
    cells = frac * w
    full = int(cells)
    rem = round((cells - full) * 8)
    if rem == 8:
        full, rem = full + 1, 0
    tail = th.g["eighths"][rem] if rem else ""
    if frac > 0 and full == 0 and not tail:
        full = 1
    return th.paint(role, th.g["full"] * full + tail)


def spark(th: Theme, vals: list, w: int) -> str:
    v = resample(vals, w)
    lo, hi = min(v), max(v)
    return "".join(th.g["blocks"][clamp(round((x - lo) / ((hi - lo) or 1) * 7) + 1, 1, 8)] for x in v)


def sec(th: Theme, role: str, label: str, text: str = "") -> str:
    return th.chip(role, f" {label} ") + (" " + th.paint("t3", text) if text else "")


def header(th: Theme, title: str, sub: str = "", role: str = "w") -> str:
    if not title:
        return th.paint("t3", sub) if sub else ""
    head = sec(th, role, title, sub) if title.isupper() and len(title) <= 8 \
        else th.paint("t", title, bold=True) + (" " + th.paint("t3", sub) if sub else "")
    return head


def cols(blocks: list, widths: list, gap: int = 3) -> list:
    n = max((len(b) for b in blocks), default=0)
    out = []
    for i in range(n):
        cells = [b[i] if i < len(b) else "" for b in blocks]
        out.append((" " * gap).join(pad(c, widths[j]) if j < len(cells) - 1 else c for j, c in enumerate(cells)))
    return out


def _num(x) -> str:
    return str(int(x)) if float(x) == int(x) else f"{x:g}"


# ───────────────────────── block renderers
def r_kv(th: Theme, b: KV, w: int) -> list:
    g, D = th.g, (lambda s: th.paint("ls", s))
    rows = [(str(k), str(v)) for k, v in b.rows]
    a = max([len(b.title) + 1] + [len(k) for k, _ in rows])
    bw = max(8, w - a - 7)
    out = [D(g["tl"] + (g["h"] + " " + b.title + " ").ljust(a + 2, g["h"]) + g["tt"] + g["h"] * (bw + 2) + g["tr"])]
    for k, v in rows:
        val = stext(th, Status.parse(v[1:])) if v.startswith("@") else v
        out.append(f"{D(g['v'])} {pad(k, a)} {D(g['v'])} {pad(clip(val, bw, g['ell']), bw)} {D(g['v'])}")
    out.append(D(g["bl"] + g["h"] * (a + 2) + g["bt"] + g["h"] * (bw + 2) + g["br"]))
    return out


def r_chart(th: Theme, b: Chart, w: int) -> list:
    out = [header(th, b.title, b.sub, b.role)]
    vals = [float(x) for x in b.values]
    if len(vals) < 2:
        return out + [th.paint("t3", "no samples")]
    cw = max(12, min(w - 6, 44))
    v = resample(vals, cw)
    span = (b.hi - b.lo) or 1
    for r in range(b.height - 1, -1, -1):
        s = "".join(th.g["blocks"][clamp(round((x - b.lo) / span * b.height * 8 - r * 8), 0, 8)] for x in v)
        label = _num(b.hi) if r == b.height - 1 else _num(b.lo) if r == 0 else ""
        out.append(th.paint("t3", label.rjust(5)) + " " + th.paint(b.role, s))
    gap = max(1, cw - len(b.x_left) - len(b.x_right))
    out.append(" " * 6 + th.paint("t3", b.x_left + " " * gap + b.x_right))
    return out


def r_bars(th: Theme, b: Bars, w: int) -> list:
    role = b.rows[0][3] if b.rows else "w"
    out = [header(th, b.title, b.sub, role or "w")]
    lw = max((len(str(r[0])) for r in b.rows), default=0)
    bw = clamp(w - lw - 14, 8, 22)
    for label, frac, text, rrole in b.rows:
        out.append(f"{pad(str(label), lw)} {bar(th, float(frac), bw, rrole or 't2')}  {text}")
    return out


def r_hist(th: Theme, b: Hist, w: int) -> list:
    out = [header(th, b.title, b.sub)]
    top = max((float(n) for _, n in b.rows), default=1) or 1
    lw = max((len(str(k)) for k, _ in b.rows), default=0)
    bw = clamp(w - lw - 10, 8, 22)
    for label, n in b.rows:
        out.append(f"{pad(str(label), lw)} {pad(hbar(th, float(n) / top, bw, 't2' if n > 5 else 'w'), bw)}  {n}")
    if b.footer:
        out.append(th.paint("t3", b.footer))
    return out


def r_grid(th: Theme, b: Grid, w: int) -> list:
    out = [header(th, b.title, b.sub)]
    for row in b.cells:
        out.append("  ".join(th.paint("c" if v == 0 else "w" if v < 90 else "t", padl(_num(v), 3)) for v in row))
    if b.footer:
        out.append(th.paint("c", b.footer))
    return out


def r_keycaps(th: Theme, b: Keycaps, w: int) -> list:
    def cap(ch: str) -> str:
        t = f"[{ch}]"
        return th.paint("w", t, bold=True) if ch in b.flagged else th.paint("t3", t) if ch in b.untested else th.paint("t", t)

    out = [header(th, b.title, b.sub), ""]
    for i, row in enumerate(b.rows):
        out.append(" " * (i * 2) + "".join(cap(c) for c in row))
    space = f"[{'Space':^19}]"
    out.append(" " * 6 + cap("Shift") + (th.paint("w", space, bold=True) if "Space" in b.flagged else th.paint("t", space))
               + th.paint("t", "[Enter][Back]"))
    out.append("")
    if b.total:
        out.append(f"{b.pressed} of {b.total} keys  {bar(th, b.pressed / b.total, 24, 'p')}")
    if b.note:
        out.append(th.paint("t3", b.note))
    return out


def r_lines(th: Theme, b: Lines, w: int) -> list:
    out = [header(th, b.title, b.sub)] if b.title or b.sub else []
    return out + [th.paint("t3", str(x)) for x in b.lines]


RENDERERS: dict = {"kv": r_kv, "chart": r_chart, "bars": r_bars, "hist": r_hist,
                   "grid": r_grid, "keycaps": r_keycaps, "lines": r_lines}


def register_block(kind: str, renderer: Callable) -> None:
    """Plug in a new block type: register_block('mykind', fn(th, block, width) -> list[str])."""
    RENDERERS[kind] = renderer


def render_block(th: Theme, b: Block, w: int) -> list:
    """Never raises: a broken block becomes a one-line error so the screen survives."""
    try:
        return RENDERERS[b.kind](th, b, w)
    except Exception as e:  # noqa: BLE001 - UI must not die on bad backend data
        return [th.paint("c", f"! cannot draw '{getattr(b, 'title', '?')}': {type(e).__name__}: {e}")]


def render_blocks(th: Theme, blocks: list, w: int) -> list:
    out = []
    for b in blocks:
        out += render_block(th, b, w) + [""]
    return out[:-1] if out else out


def layout_page(th: Theme, page: Page, w: int) -> list:
    """Columns side by side when there is room, stacked otherwise."""
    colsets = [c for c in page.columns if c]
    if not colsets:
        return [th.paint("t3", "this page has no content")]
    if len(colsets) == 1 or w < 100:
        out = []
        for c in colsets:
            out += render_blocks(th, c, min(w, 64)) + [""]
        return out[:-1]
    first = min(56, int(w * 0.46))
    rest = max(30, (w - first - 3 * (len(colsets) - 1)) // (len(colsets) - 1))
    widths = [first] + [rest] * (len(colsets) - 1)
    return cols([render_blocks(th, c, widths[i]) for i, c in enumerate(colsets)], widths)
