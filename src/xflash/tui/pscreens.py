"""Pixel-lens screens: the XFLASH banner, bay tiles, rules, detail pages and the live scan.

Needs a Unicode terminal of at least PIXEL_MIN (120 x 34). Smaller terminals fall back to
the expert lens automatically; `v` switches lenses by hand.
"""
from __future__ import annotations

from .model import Status
from .pixel import (BAY_SPRITES, accent_role, bigtext, fan_deg, fit_big, panel, pixel_chart, segments,
                    side_by_side, sprite_lines)
from .screens import PIXEL_SCREENS, screen
from .widgets import clamp, cols, glyph, pad, padl, render_blocks, sec, stext, vlen

PIXEL_MIN = (120, 34)
BANNER_ROWS = 6


def _dim(th, s):
    return th.paint("t3", s)


def banner(app, W: int) -> list:
    """Laptop sprite + XFLASH wordmark on the left, live machine/verdict summary on the right."""
    th, s = app.th, app.session
    left = side_by_side(sprite_lines(th, "laptop"),
                        bigtext(th, "XFLASH", "w", 2) + [_dim(th, "check before you pay · offline · read only")], gap=2)
    left = (left + [""] * BANNER_ROWS)[:BANNER_ROWS]
    lw = max(vlen(x) for x in left)
    if W - lw < 56:
        return ["  " + x for x in left]
    c = app.counts()
    info = [th.paint("t", s.title if s else (app.machine.get("Product") or "no session loaded"), bold=True),
            _dim(th, (f"session {s.id}" if s else "type :scan to inspect this laptop")
                 + f" · {app.backend.name} backend")]
    if s and s.verdict:
        info.append(th.chip(s.verdict_status.role, f" {s.verdict_status.word} ") + " " + th.paint("t", s.verdict))
        info.append(th.paint("c", f"{c['fail']} fail") + _dim(th, " · ") + th.paint("w", f"{c['warn']} warn")
                    + _dim(th, " · ") + _dim(th, f"{c['open']} open") + _dim(th, " · ") + th.paint("p", f"{c['pass']} pass"))
    else:
        info += ["", ""]
    mini = "  ".join(th.paint("w" if i == app.bay else "t3", f"{i + 1}") + glyph(th, b.status, app.tick)
                     for i, b in enumerate(app.bays()))
    info += [mini, (th.chip("c", " DEMO DATA ") if app.backend.is_demo else "")]
    return ["  " + pad(a, lw) + "   " + b for a, b in zip(left, info + [""] * BANNER_ROWS)]


def tile(app, i: int, bay, tw: int, selected: bool) -> list:
    th = app.th
    inner = tw - 4
    spr_name = bay.sprite or BAY_SPRITES.get(bay.name, "chip")
    spinning = spr_name == "fan" and bay.status not in (Status.IDLE, Status.QUEUED, Status.OPEN)
    spr = sprite_lines(th, spr_name, accent_role(bay.status), fan_deg(app.tick) if spinning else 0)
    sw = 17            # 16 sprite columns + 1 gap
    role = bay.value_role or (bay.status.role if bay.status.role != "t3" else "t")
    big, rest = fit_big(th, bay.big or bay.value, inner - sw, role)
    label = th.paint("w" if selected else "t2", f"{i + 1} {bay.name}", bold=True) + (("  " + _dim(th, rest)) if rest else "")
    right = [label] + big + [_dim(th, bay.sub)]
    top = (side_by_side([pad(x, sw - 1) for x in spr], right, 1) + [""] * 5)[:5]
    g = bay.gauge if bay.gauge is not None else bay.bar
    gauge = segments(th, g, (inner + 1) // 3, accent_role(bay.status), None) if g is not None else _dim(th, " ")
    status = stext(th, bay.status, app.tick, True) + ((" " + _dim(th, bay.note)) if bay.note else "")
    return panel(th, top + [gauge, status], tw, "w" if selected else "ls")


@screen("home", lens="pixel")
def p_home(app, w, h):
    th, bays = app.th, app.bays()
    tw = (w - 2) // 3
    out = []
    for r in range(0, len(bays), 3):
        tiles = [tile(app, r + k, b, tw, r + k == app.bay) for k, b in enumerate(bays[r:r + 3])]
        out += cols(tiles, [tw] * len(tiles), gap=1)
    if h - len(out) >= 4:
        sess = "  ".join(th.chip("t3", f" {x.date} ") + _dim(th, f" {x.id} ") + th.paint("c", f"{x.fail}f")
                         + th.paint("w", f"{x.warn}w") for x in app.history) or _dim(th, "none yet")
        cmds = "  ".join(th.paint("w" if app.command_available(n) else "t3", ":" + n)
                         for n in ("scan", "open", "diff", "export", "serve", "screen"))
        out += panel(th, [th.paint("t2", "SESSIONS ", bold=True) + sess, th.paint("t2", "COMMANDS ", bold=True) + cmds], w)
    return out


@screen("rules", lens="pixel")
def p_rules(app, w, h):
    th = app.th
    if not app.session:
        return panel(th, [_dim(th, "no session loaded, type :scan to inspect this laptop")], w)
    shown = app.rules_filtered()
    app.sel = clamp(app.sel, 0, max(0, len(shown) - 1))
    c = app.counts()
    ph = max(4, h - 2)
    idw = clamp(max([6] + [len(f.id) for f in shown]), 6, 24)
    lw = clamp(int(w * 0.45), 50, 66)
    li = lw - 4
    vw = clamp(max([4] + [len(f.value) for f in shown]), 4, 11)
    left = [th.paint("w", "RULES", bold=True) + " " + _dim(th, f"{c['fail']} fail · {c['warn']} warn · {c['open']} open"), ""]
    visible = max(3, ph - len(left))
    top = clamp(app.sel - visible // 2, 0, max(0, len(shown) - visible))
    for i in range(top, min(len(shown), top + visible)):
        f = shown[i]
        nw = max(8, li - 2 - 2 - idw - 2 - vw - 1)
        name = f.name if len(f.name) <= nw else f.name[:nw - 1] + th.g["ell"]
        row = (th.paint("w", th.g["sel"]) if i == app.sel else "  ") + glyph(th, f.status) + " " + th.paint("t", pad(f.id, idw)) \
            + "  " + pad(name, nw) + " " + _dim(th, padl(f.value, vw))
        left.append(th.selected(row, li) if i == app.sel else row)
    if not shown:
        left.append(_dim(th, f'  no rules match "{app.filter}"' if app.filter else "  no findings: nothing to flag"))
    right, role = [], "ls"
    if shown:
        f = shown[app.sel]
        role = {Status.WARN: "w", Status.FAIL: "c", Status.CLAIM: "c"}.get(f.status, "ls")
        right = [th.chip("w" if role == "w" else "t3", f" {f.id} ") + " " + th.paint("t", f.title or f.name, bold=True), ""]
        from .model import KV
        blocks = f.blocks or [KV("", [("Observed", f.value), ("Result", "@" + f.status.value)])]
        right += render_blocks(th, blocks, w - lw - 1 - 4, "pixel", app.tick)
    lp = panel(th, (left + [""] * ph)[:ph], lw, "ls")
    rp = panel(th, (right + [""] * ph)[:ph], w - lw - 1, role)
    return cols([lp, rp], [lw], gap=1)


@screen("page", lens="pixel")
def p_page(app, w, h):
    th, p = app.th, app.current_page()
    if p is None:
        return panel(th, [_dim(th, "this page is not available")], w)
    columns = [c for c in (p.pixel_columns or p.columns) if c]
    ph = max(4, h - 2)
    if not columns:
        return panel(th, [_dim(th, "this page has no content")], w)
    n = len(columns)
    if n == 1 or w < 84:
        all_blocks = [b for col in columns for b in col] if (n > 1 and w < 84) else columns[0]
        lines = render_blocks(th, all_blocks, w - 4, "pixel", app.tick)
        if p.rules_hint:
            lines += ["", _dim(th, f"press r for the related finding ({p.rules_hint})")]
        return panel(th, (lines + [""] * ph)[:ph], w, p.accent or "ls")
    elif n == 2:
        lw = max(40, min(w - 38, int(w * 0.52)))
        widths = [lw, w - lw - 1]
    else:
        widths = [(w - (n - 1)) // n] * n
    panels = []
    for i, col in enumerate(columns):
        lines = render_blocks(th, col, widths[i] - 4, "pixel", app.tick)
        if i == n - 1 and p.rules_hint:
            lines += ["", _dim(th, f"press r for the related finding ({p.rules_hint})")]
        role = p.accent if (i == n - 1 and p.accent) else "ls"
        panels.append(panel(th, (lines + [""] * ph)[:ph], widths[i], role))
    return cols(panels, widths[:-1] + [widths[-1]], gap=1)


@screen("scan", lens="pixel")
def p_scan(app, w, h):
    th, sc = app.th, app.scan
    checks = sc.checks if sc else []
    ph = max(4, h - 2)
    done = sum(c.status not in (Status.QUEUED, Status.RUNNING) for c in checks)
    frac = done / len(checks) if checks else 0
    left = [th.paint("w", "LOG", bold=True), ""]
    for c in checks:
        if c.status is Status.RUNNING:
            t, text = "", th.paint("t", "reading")
        elif c.status is Status.QUEUED:
            t, text = "", _dim(th, "queued")
        else:
            t, text = f"{c.seconds:g}s", _dim(th, c.text)
        left.append(f"{glyph(th, c.status, app.tick)} {pad(c.name, 10)} {padl(t, 4)}   {text}")
    lw = clamp(int(w * 0.55), 50, w - 40)
    rw = w - lw - 1
    right = [th.paint("w", "PULSE", bold=True) + " " + _dim(th, "package temperature, °C")]
    if sc and len(sc.pulse) >= 2:
        right += pixel_chart(th, sc.pulse, 40, 60, rw - 4, 8, "w", "0 s", "5 s")
    else:
        right += [_dim(th, "waiting for the first samples")]
    right += ["", th.paint("t2", "overall", bold=True) + f"  {round(frac * 100)} %  {done} of {len(checks)}",
              segments(th, frac, max(6, (rw - 4 + 1) // 3), "w"), "", _dim(th, "no write is made to this machine")]
    return cols([panel(th, (left + [""] * ph)[:ph], lw, "ls"), panel(th, (right + [""] * ph)[:ph], rw, "w")], [lw], gap=1)
