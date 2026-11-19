"""App: state, input, commands and chrome. Rendering is a pure function of state."""
from __future__ import annotations

import os
import queue
import shlex
import threading
import traceback
from dataclasses import dataclass, field
from typing import Callable, Optional

from .backend import (Backend, CheckUpdate, NotSupported, PulseSample, ScanFailed, ScanFinished, ScanOptions,
                      ScanStarted)
from .model import DEFAULT_BAYS, Bay, Check, Page, Session, Status
from .screens import SCREENS
from .theme import Theme
from .widgets import bar, clamp, clip, pad, spark, stext, vlen

try:
    from . import pscreens as _pscreens  # noqa: F401 — registers pixel screens
except ImportError:
    pass


@dataclass
class Command:
    name: str
    desc: str
    fn: Callable                 # fn(app, args: list[str]) -> None
    usage: str = ""
    needs: str = ""              # Backend method required; "" = always available

    @property
    def shown(self) -> str:
        return self.usage or self.name


@dataclass
class ScanState:
    checks: list = field(default_factory=list)
    pulse: list = field(default_factory=list)
    partial: dict = field(default_factory=dict)      # bay index -> live Bay
    cancel: threading.Event = field(default_factory=threading.Event)
    running: bool = True
    ident: int = 0


class _ThreadDone:
    pass


class App:
    def __init__(self, backend: Backend, theme: Theme, size: tuple = (120, 36)):
        self.backend, self.th, self.size = backend, theme, size
        self.session: Optional[Session] = None
        self.lens_pref: str = "auto"   # "auto" | "expert" | "pixel"
        self.screen, self.page_id = "home", ""
        self.bay = self.sel = self.pal = self.tick = 0
        self.filter = self.buf = self.msg = ""
        self.mode = "nav"            # nav | cmd | filter
        self.help = False
        self.quit = False
        self.scan: Optional[ScanState] = None
        self.extra: dict = {}        # transient Pages (diff, tools)
        self.events: queue.Queue = queue.Queue()
        self._scan_id = 0
        self.machine = self._safe(backend.machine, {})
        self.history = self._safe(backend.history, [])
        self.commands: list = []
        _default_commands(self)

    @property
    def lens(self) -> str:
        if not self.th.unicode:
            return "expert"
        if self.lens_pref == "expert":
            return "expert"
        if self.lens_pref == "pixel":
            return "pixel"
        return "pixel"

    # ───────────────────────── plumbing
    @staticmethod
    def _safe(fn, default):
        try:
            return fn()
        except Exception:  # noqa: BLE001 - home screen info is optional
            return default

    def register(self, cmd: Command) -> None:
        """Add a palette command (plugins, extra tools)."""
        self.commands.append(cmd)

    def command_available(self, name: str) -> bool:
        return any(c.name == name and (not c.needs or self.backend.supports(c.needs)) for c in self.commands)

    def set_session(self, s: Session, screen: str = "rules") -> None:
        self.session, self.sel, self.filter = s, 0, ""
        self.goto(screen)

    def goto(self, screen: str, page_id: str = "") -> None:
        self.screen, self.page_id, self.help, self.mode = screen, page_id, False, "nav"

    def current_page(self) -> Optional[Page]:
        return self.extra.get(self.page_id) or (self.session.pages.get(self.page_id) if self.session else None)

    def rules_filtered(self) -> list:
        if not self.session:
            return []
        q = self.filter.lower()
        return [f for f in self.session.findings if not q or q in f"{f.id} {f.name} {f.status.word}".lower()]

    def counts(self) -> dict:
        c = {"fail": 0, "warn": 0, "open": 0, "pass": 0}
        for f in (self.session.findings if self.session else []):
            c[f.status.bucket] += 1
        return c

    def bays(self) -> list:
        if self.session:
            return self.session.bays
        out = []
        for i, name in enumerate(DEFAULT_BAYS):
            if self.scan and i in self.scan.partial:
                out.append(self.scan.partial[i])
            elif self.scan:
                running = any(c.bay == i and c.status is Status.RUNNING for c in self.scan.checks)
                out.append(Bay(name, "—", Status.RUNNING if running else Status.QUEUED,
                               sub="reading" if running else "waiting"))
            else:
                out.append(Bay(name, "—", Status.IDLE, sub="ready"))
        return out

    # ───────────────────────── scan lifecycle
    def start_scan(self, opts: ScanOptions) -> None:
        if self.scan and self.scan.running:
            self.msg = "a scan is already running"
            return
        self._scan_id += 1
        sid = self._scan_id
        self.session = None
        self.scan = ScanState(ident=sid)
        self.goto("scan")
        cancel = self.scan.cancel

        def work():
            try:
                self.backend.scan(opts, lambda ev: self.events.put((sid, ev)), cancel)
            except Exception as e:  # noqa: BLE001
                self.events.put((sid, ScanFailed(f"{type(e).__name__}: {e}")))
            finally:
                self.events.put((sid, _ThreadDone()))

        threading.Thread(target=work, daemon=True, name="xflash-scan").start()

    def stop_scan(self) -> bool:
        if not (self.scan and self.scan.running):
            return False
        self.scan.cancel.set()
        self.scan.running = False
        for c in self.scan.checks:
            if c.status is Status.RUNNING:
                c.status = Status.QUEUED
        self.goto("home")
        self.msg = "scan stopped · partial results kept"
        return True

    def pump(self) -> None:
        """Apply queued backend events. Call from the UI thread only."""
        while True:
            try:
                sid, ev = self.events.get_nowait()
            except queue.Empty:
                return
            if sid != self._scan_id or self.scan is None or self.scan.cancel.is_set():
                continue                     # stale event from a cancelled or older scan
            self._apply(ev)

    def _apply(self, ev) -> None:
        sc = self.scan
        if isinstance(ev, ScanStarted):
            sc.checks = [Check(n) for n in ev.checks]
        elif isinstance(ev, CheckUpdate):
            if 0 <= ev.index < len(sc.checks):
                c = sc.checks[ev.index]
                c.status, c.seconds, c.bay = ev.status, ev.seconds, ev.bay
                if ev.text:
                    c.text = ev.text
            if ev.bay is not None and ev.bay_view is not None:
                sc.partial[ev.bay] = ev.bay_view
        elif isinstance(ev, PulseSample):
            sc.pulse.append(ev.value)
        elif isinstance(ev, ScanFinished):
            sc.running = False
            self.set_session(ev.session)
            self.msg = "scan complete · session kept"
        elif isinstance(ev, ScanFailed):
            sc.running = False
            self.goto("home")
            self.msg = f"scan failed: {ev.message}"
        elif isinstance(ev, _ThreadDone) and sc.running:
            sc.running = False
            self.goto("home")
            self.msg = "scan ended without a result"

    # ───────────────────────── commands
    def entries(self, q: str) -> list:
        ql = q.strip().lower()
        if " " in ql:
            first = ql.split()[0]
            return [c for c in self.commands if c.name == first]
        pre = [c for c in self.commands if c.shown.lower().startswith(ql)]
        return pre + [c for c in self.commands if c not in pre and ql in c.shown.lower()]

    def run_command(self, text: str) -> None:
        try:
            tokens = shlex.split(text, posix=os.name != "nt")
        except ValueError as e:
            self.msg = f"cannot parse command: {e}"
            return
        if not tokens:
            return
        hit = next((c for c in self.commands if c.name == tokens[0]), None)
        if hit is None:                       # not an exact name: take the palette's highlighted match
            m = self.entries(text)
            if m:
                hit = m[clamp(self.pal, 0, len(m) - 1)]
                tokens = [hit.name] + tokens[1:]
        if hit is None:
            self.msg = f"unknown command: {tokens[0]}"
            return
        if hit.needs and not self.backend.supports(hit.needs):
            self.msg = f":{hit.name} is not available in the {self.backend.name} backend"
            return
        try:
            hit.fn(self, tokens[1:])
        except NotSupported as e:
            self.msg = f":{hit.name} is not available ({e})"
        except Exception as e:  # noqa: BLE001
            self.msg = f":{hit.name} failed: {type(e).__name__}: {e}"
            self._debug()

    def open_bay(self, i: int) -> None:
        bays = self.bays()
        self.bay = clamp(i, 0, len(bays) - 1)
        if not self.session:
            self.msg = "no session loaded, press s or type :scan"
            return
        b = bays[self.bay]
        if b.target == "rules":
            self.filter = ""
            self.sel = next((k for k, f in enumerate(self.session.findings) if f.id == b.rule), 0)
            self.goto("rules")
        elif b.target in self.session.pages:
            self.goto("page", b.target)
        else:
            self.msg = f"no detail page for {b.name}"

    @staticmethod
    def _debug() -> None:
        if os.environ.get("XFLASH_TUI_DEBUG"):
            raise

    # ───────────────────────── input
    def handle_key(self, k: str) -> None:
        try:
            self._key(k)
        except Exception as e:  # noqa: BLE001 - a bad key must never kill the session
            self.msg = f"error: {type(e).__name__}: {e}"
            if os.environ.get("XFLASH_TUI_DEBUG"):
                self.msg += " | " + traceback.format_exc().splitlines()[-3].strip()
                raise

    def _key(self, k: str) -> None:
        if k == "ctrl-c":
            self.quit = True
            return
        if self.mode == "cmd":
            m = self.entries(self.buf)
            if k == "esc":
                self.mode, self.buf = "nav", ""
            elif k == "enter":
                text, self.mode, self.buf = self.buf, "nav", ""
                self.run_command(text)
                self.pal = 0
            elif k == "tab" and m:
                self.buf = m[clamp(self.pal, 0, len(m) - 1)].shown.split("<")[0].split("[")[0].lstrip()
            elif k == "up":
                self.pal = max(0, self.pal - 1)
            elif k == "down":
                self.pal = min(max(0, len(m) - 1), self.pal + 1)
            elif k == "backspace":
                self.buf, self.pal = self.buf[:-1], 0
            elif len(k) == 1:
                self.buf, self.pal = self.buf + k, 0
            return
        if self.mode == "filter":
            if k == "esc":
                self.filter, self.mode = "", "nav"
            elif k == "enter":
                self.mode = "nav"
            elif k == "backspace":
                self.filter = self.filter[:-1]
            elif len(k) == 1:
                self.filter, self.sel = self.filter + k, 0
            return
        self.msg = ""
        n = len(self.rules_filtered()) if self.screen == "rules" else 0
        nb = len(self.bays())
        home = self.screen == "home"
        if k == "q":
            self.quit = True
        elif k == "esc":
            if not self.stop_scan():
                self.goto("home")
        elif len(k) == 1 and k.isdigit() and 1 <= int(k) <= nb:
            self.open_bay(int(k) - 1)
        elif k == ":":
            self.mode, self.buf, self.pal, self.help = "cmd", "", 0, False
        elif k == "/":
            if self.session:
                self.goto("rules")
                self.mode = "filter"
            else:
                self.msg = "no session loaded, type :scan first"
        elif k == "?":
            self.help = not self.help
        elif k == "r":
            if self.session:
                self.goto("rules")
            else:
                self.msg = "no session loaded, press s or type :scan"
        elif k == "v":
            self.lens_pref = "expert" if self.lens == "pixel" else "pixel"
            self.msg = f"switched to {self.lens} lens"
        elif k == "s" and home:
            self.run_command("scan")
        elif k == "d" and home:
            self.run_command("diff")
        elif home and k in ("right", "down", "l", "j"):
            self.bay = min(nb - 1, self.bay + 1)
        elif home and k in ("left", "up", "h", "k"):
            self.bay = max(0, self.bay - 1)
        elif k in ("down", "j"):
            self.sel = clamp(self.sel + 1, 0, max(0, n - 1))
        elif k in ("up", "k"):
            self.sel = clamp(self.sel - 1, 0, max(0, n - 1))
        elif k == "enter" and home:
            if self.session:
                self.open_bay(self.bay)
            else:
                self.run_command("scan")

    # ───────────────────────── rendering (pure given state)
    def _strip(self, W: int) -> list:
        if self.lens == "pixel":
            try:
                from .pscreens import banner
                return banner(self, W)
            except ImportError:
                pass
        th, g, bays = self.th, self.th.g, self.bays()
        D = lambda s: th.paint("ls", s)  # noqa: E731
        nb = len(bays)
        if W < 100:
            return [f"  {th.paint('w' if i == self.bay else 't3', str(i + 1))} {pad(b.name, 4)} "
                    f"{pad(b.value, 18)}{stext(th, b.status, self.tick, True)}" for i, b in enumerate(bays)] + [""]
        cw = clamp((W - 4 - (nb + 1)) // nb, 15, 22)
        top, r1, r2, r3, bot = D(g["Htl"]), D(g["Hv"]), D(g["Hv"]), D(g["Hv"]), D(g["Hbl"])
        for i, b in enumerate(bays):
            sel, last = i == self.bay, i == nb - 1
            label = f" {i + 1} {b.name} "
            if b.bar is not None:
                second = bar(th, b.bar, cw - 2, b.status.role)
            elif b.spark:
                second = th.paint(b.status.role, spark(th, b.spark, cw - 2))
            else:
                second = th.paint("t3", b.sub)
            top += D(g["Hh"]) + th.paint("w" if sel else "t2", label, bold=sel) \
                + D(g["Hh"] * (cw - 1 - len(label)) + (g["Htr"] if last else g["Htt"]))
            cell = lambda s: " " + pad(clip(s, cw - 1, g["ell"]), cw - 1) + D(g["Hv"])  # noqa: E731
            r1 += cell(th.paint("t", b.value))
            r2 += cell(second)
            r3 += cell(stext(th, b.status, self.tick, True))
            bot += D(g["Hh"] * cw + (g["Hbr"] if last else g["Hbt"]))
        return ["  " + x for x in (top, r1, r2, r3, bot)]

    def _status(self) -> tuple:
        th, s = self.th, self.session
        if self.screen == "scan" and self.scan:
            done = sum(c.status not in (Status.QUEUED, Status.RUNNING) for c in self.scan.checks)
            return "w", "SCAN", f"reading hardware · {done} of {len(self.scan.checks)} checks", "esc stops, results are kept"
        if self.screen == "rules" and s:
            n = len(self.rules_filtered())
            return "w", "INSPECT", f"{s.id} · rules", f"rule {self.sel + 1 if n else 0} of {n}"
        if self.screen == "page" and self.current_page():
            p = self.current_page()
            return "w", p.label, p.summary, p.right
        if s:
            return "p", "READY", f"{s.id} loaded · offline · read only", ""
        return "t3", "READY", "no session loaded · offline · read only", ""

    def _status_bar(self, W: int) -> str:
        th = self.th
        role, label, text, right = self._status()
        left = th.chip(role, f" {label} ") + " " + th.paint("t", text)
        r = th.paint("t3", right)
        if self.backend.is_demo:
            r = th.chip("c", " DEMO DATA ") + " " + th.paint("t3", "not a real inspection" if not right else right)
        return "  " + left + " " * max(1, W - 4 - vlen(left) - vlen(r)) + r

    def _cmd_line(self) -> str:
        th = self.th
        cur = "\x1b[7m \x1b[0m" if th.color != "none" else "_"
        if self.mode == "cmd":
            return "  " + th.paint("w", ":") + self.buf + cur
        if self.mode == "filter":
            return "  " + th.paint("w", "/") + self.filter + cur
        return "  " + th.paint("t3", self.msg or "press : for commands · / to filter · ? for help")

    def _hotkeys(self) -> str:
        th = self.th
        if self.screen == "home" and not self.session:
            keys = [("s", "scan"), ("1-6", "bay"), ("v", "lens"), (":", "command"), ("?", "help"), ("q", "quit")]
        else:
            keys = [("1-6", "bay"), ("j k", "move"), ("r", "rules"), ("v", "lens"), ("/", "filter"), (":", "command"), ("?", "help")]
        return "  " + "  ".join(th.chip("t3", f" {k} ") + th.paint("t3", " " + t) for k, t in keys)

    def _box(self, title: str, lines: list, w: int) -> list:
        th, g = self.th, self.th.g
        D = lambda s: th.paint("ls", s)  # noqa: E731
        out = [D(g["Rtl"] + g["h"] + " ") + th.paint("t", title) + D(" " + g["h"] * max(0, w - len(title) - 5) + g["Rtr"])]
        out += [D(g["v"]) + " " + pad(clip(x, w - 4, g["ell"]), w - 4) + " " + D(g["v"]) for x in lines]
        return out + [D(g["Rbl"] + g["h"] * (w - 2) + g["Rbr"])]

    def _overlay(self, W: int):
        th, w = self.th, min(76, W - 8)
        if self.help:
            return self._box("Keys", ["j k / ↑ ↓   move          1-6   open a bay        h l   pick a bay",
                                      "enter       open          /     filter rules      :     command palette",
                                      "r           rules         v     switch lens       s     scan",
                                      "esc         back/home     ?     this help         q     quit"], w)
        if self.mode == "cmd":
            m = self.entries(self.buf)[:7]
            self.pal = clamp(self.pal, 0, max(0, len(m) - 1))
            rows = []
            for i, c in enumerate(m):
                ok = not c.needs or self.backend.supports(c.needs)
                line = pad(":" + c.shown, 34) + (c.desc if ok else "(not available here)")
                rows.append((th.paint("w", th.g["sel"]) if i == self.pal else "  ") + (line if ok else th.paint("t3", line)))
            rows = rows or [th.paint("t3", "  nothing matches")]
            return self._box(f"Commands matching :{self.buf.strip()}", rows + [th.paint("t3", "tab completes · enter runs · esc closes")], w)
        return None

    def render(self) -> list:
        W, H = self.size
        th = self.th
        strip = self._strip(W)
        hb = max(4, H - len(strip) - 3)
        try:
            from .screens import SCREENS, PIXEL_SCREENS
            registry = PIXEL_SCREENS if self.lens == "pixel" else SCREENS
            fn = registry.get(self.screen) or SCREENS.get(self.screen)
            if fn is None:
                raise KeyError(self.screen)
            body = fn(self, W - 4, hb)
        except Exception as e:  # noqa: BLE001 - a failing screen must not end the session
            body = [th.paint("c", f"! screen '{self.screen}' failed: {type(e).__name__}: {e}")]
            self._debug_render()
        body = ["  " + x for x in body][:hb]
        body += [""] * (hb - len(body))
        ov = self._overlay(W)
        if ov:
            for k, line in enumerate(ov):
                at = hb - len(ov) + k
                if at >= 0:
                    body[at] = "  " + line
        lines = [*strip, *body, self._status_bar(W), self._cmd_line(), self._hotkeys()][:H]
        return [clip(th.safe(x), W, th.g["ell"]) for x in lines]   # transliterate first: it can widen text

    @staticmethod
    def _debug_render() -> None:
        if os.environ.get("XFLASH_TUI_DEBUG"):
            raise

    # ───────────────────────── main loop
    def run(self, term) -> None:
        try:
            while not self.quit:
                self.pump()
                self.size = term.size()
                term.draw(self.render())
                for k in term.poll(0.1):
                    self.handle_key(k)
                self.tick += 1
        except KeyboardInterrupt:
            pass
        finally:
            if self.scan:
                self.scan.cancel.set()


# ───────────────────────── default command set
def _claims(args: list) -> dict:
    out, i = {}, 0
    while i < len(args):
        if args[i].startswith("--claim-") and i + 1 < len(args):
            out[args[i][8:]] = args[i + 1]
            i += 2
        else:
            i += 1
    return out


def _default_commands(app: App) -> None:
    def need_session(a: App):
        if not a.session:
            raise NotSupported("run :scan first")
        return a.session

    def c_open(a, args):
        ref = " ".join(args) or (a.history[0].id if a.history else "")
        if not ref:
            raise NotSupported("usage: :open <session>")
        a.set_session(a.backend.load(ref))

    def c_export(a, args):
        s = need_session(a)
        fmt = next((x for x in args if x in ("json", "html")), "html")
        path = next((x for x in args if x not in ("json", "html")), None)
        a.msg = f"exported {a.backend.export(s, fmt, path)}"

    def c_save(a, args):
        a.msg = f"saved {a.backend.save(need_session(a))}"

    def c_serve(a, args):
        a.msg = f"dashboard at {a.backend.serve()}"

    def c_diff(a, args):
        pair = args[:2] if len(args) >= 2 else [r.id for r in a.history[:2]]
        if len(pair) < 2:
            raise NotSupported("need two sessions")
        a.extra["diff"] = a.backend.diff(*pair)
        a.goto("page", "diff")

    def c_tool(a, args):
        res = a.backend.tool((args or ["screen"])[0])
        if isinstance(res, Page):
            a.extra[res.id] = res
            a.goto("page", res.id)
        else:
            a.msg = str(res)

    def c_bay(a, args):
        a.open_bay(int(args[0]) - 1)

    for cmd in (
        Command("scan", "inspect this laptop", lambda a, x: a.start_scan(ScanOptions(_claims(x))), needs="scan"),
        Command("scan", "compare with the seller listing", lambda a, x: a.start_scan(ScanOptions(_claims(x))),
                "scan --claim-ram <GiB> --claim-storage <GB>", needs="scan"),
        Command("rules", "open the rules list", lambda a, x: a.goto("rules")),
        Command("bay", "open a bay by number", c_bay, "bay <n>"),
        Command("open", "load a saved session", c_open, "open <session>", needs="load"),
        Command("diff", "compare two sessions", c_diff, "diff [a] [b]", needs="diff"),
        Command("export", "write json or html", c_export, "export [json|html] [path]", needs="export"),
        Command("save", "write report to this USB drive", c_save, needs="save"),
        Command("serve", "local dashboard on 127.0.0.1", c_serve, needs="serve"),
        Command("screen", "dead pixel, grayscale, refresh", c_tool, needs="tool"),
        Command("home", "back to the start screen", lambda a, x: a.goto("home")),
        Command("help", "show keys", lambda a, x: setattr(a, "help", True)),
        Command("quit", "leave xflash", lambda a, x: setattr(a, "quit", True)),
    ):
        app.register(cmd)
