"""Screens: functions (app, width, height) -> list[str], registered by name.

Add one with:
    @screen("mine")
    def mine(app, w, h): return ["hello"]
and reach it with app.goto("mine"). Hardware detail pages need no code at all:
return a Page from the backend and it is drawn by the generic "page" screen.
"""
from __future__ import annotations

from typing import Callable

from .model import KV, Status
from .widgets import (bar, clamp, cols, glyph, layout_page, pad, padl, render_block, render_blocks,
                      resample, sec, stext)
from .widgets import r_chart  # noqa: F401  (re-exported for custom screens)
from .model import Chart

SCREENS: dict = {}


def screen(name: str) -> Callable:
    def deco(fn):
        SCREENS[name] = fn
        return fn
    return deco


@screen("home")
def home(app, w, h):
    th = app.th
    machine = (app.session.machine if app.session and app.session.machine else app.machine)
    left = render_block(th, KV("Machine", list(machine.items())), 44) if machine else [th.paint("t3", "no machine info")]
    sessions = [th.paint("t", "Sessions"), th.paint("t3", "saved on this USB drive"), ""]
    for r in app.history:
        sessions.append(th.chip("t3", f" {r.date} ") + th.paint("t3", f" {r.id}  ") + th.paint("c", f"{r.fail}f")
                        + th.paint("w", f"{r.warn}w"))
    if not app.history:
        sessions.append(th.paint("t3", "none yet"))
    sessions += ["", th.paint("t3", "Press d to diff two sessions.")]
    cmds = [th.paint("t", "Commands"), ""]
    for name, desc in (("scan", "inspect now"), ("open", "load a session"), ("diff", "compare sessions"),
                       ("export", "json or html"), ("serve", "local dashboard"), ("screen", "display checks")):
        ok = app.command_available(name)
        cmds.append(th.chip("w" if ok else "t3", f" :{pad(name, 8)}") + th.paint("t3", " " + desc))
    if w < 104:
        return [*left, "", *sessions, "", *cmds]
    return cols([left, sessions, cmds], [44, max(24, (w - 50) // 2)])


@screen("rules")
def rules(app, w, h):
    th = app.th
    if not app.session:
        return [th.paint("t3", "no session loaded, type :scan to inspect this laptop")]
    shown = app.rules_filtered()
    app.sel = clamp(app.sel, 0, max(0, len(shown) - 1))
    c = app.counts()
    lw = min(54, w)
    stacked = w < lw + 46
    vw = clamp(max([4] + [len(f.value) for f in shown]), 4, 11)
    left = [sec(th, "w", "RULES", f"{c['fail']} fail · {c['warn']} warn · {c['open']} open · {c['pass']} pass"), ""]
    for i, f in enumerate(shown):
        nw = lw - 2 - 2 - 6 - 2 - vw - 1
        name = f.name if len(f.name) <= nw else f.name[:max(0, nw - 1)] + th.g["ell"]
        row = f"{th.paint('w', th.g['sel']) if i == app.sel else '  '}{glyph(th, f.status)} {pad(f.id, 6)}  " \
              f"{pad(name, nw)} {padl(f.value, vw)}"
        left.append(th.selected(row, lw) if i == app.sel else row)
    if not shown:
        left.append(th.paint("t3", f'  no rules match "{app.filter}"'))
    right = []
    if shown:
        f = shown[app.sel]
        right = [th.chip("t3", f" {f.id} ") + " " + th.paint("t", f.title or f.name, bold=True), ""]
        blocks = f.blocks or [KV("Evaluation", [("Observed", f.value), ("Result", "@" + f.status.value)])]
        right += render_blocks(th, blocks, min(62, w if stacked else w - lw - 3))
    return [*left, "", *right] if stacked else cols([left, right], [lw])


@screen("page")
def page(app, w, h):
    p = app.current_page()
    if p is None:
        return [app.th.paint("t3", "this page is not available")]
    out = layout_page(app.th, p, w)
    if p.note:
        out += ["", app.th.paint("t3", p.note)]
    return out


@screen("scan")
def scan(app, w, h):
    th, sc = app.th, app.scan
    checks = sc.checks if sc else []
    done = sum(c.status not in (Status.QUEUED, Status.RUNNING) for c in checks)
    out = [sec(th, "w", "LOG")]
    for c in checks:
        if c.status is Status.RUNNING:
            t, text = "", th.paint("t", "reading")
        elif c.status is Status.QUEUED:
            t, text = "", th.paint("t3", "queued")
        else:
            t, text = f"{c.seconds:g}s", th.paint("t3", c.text)
        out.append(f"{glyph(th, c.status, app.tick)} {pad(c.name, 10)} {padl(t, 4)}   {text}")
    if not checks:
        out.append(th.paint("t3", "waiting for the backend"))
    frac = done / len(checks) if checks else 0
    out += [""]
    if sc and len(sc.pulse) >= 2:
        out += render_block(th, Chart("PULSE", sc.pulse, 40, 60, "package temperature, °C", "0 s", "5 s"), w)
        out += [""]
    out += [f"overall  {bar(th, frac, 24, 'w')}  {round(frac * 100)} %  {done} of {len(checks)}",
            th.paint("t3", "no write is made to this machine")]
    return out
