"""Tests for xflash.tui (stdlib unittest, runs with the project's test suite).

Run with:
    python -m unittest discover -s tests -v
or:
    python -m unittest tests.test_tui -v
"""
import io
import os
import queue
import sys
import threading
import time
import unittest

from xflash.tui import (App, Backend, Chart, Check, CheckUpdate, Command, KV, NotSupported, Page,
                         ScanFailed, ScanFinished, ScanOptions, ScanStarted, Status, Theme, main,
                         run_scan_blocking, screen)
from xflash.tui.demo import DemoBackend, build_demo_session
from xflash.tui.screens import SCREENS
from xflash.tui.term import parse_keys
from xflash.tui.widgets import clip, render_block, strip, vlen

THEMES = {
    "truecolor": Theme("truecolor", True),
    "basic":     Theme("basic", True),
    "none":      Theme("none", True),
    "ascii":     Theme("none", False),
}
SIZES = [(80, 24), (100, 30), (130, 34), (200, 50)]


def loaded_app(theme, size, backend=None):
    app = App(backend or DemoBackend(0), theme, size)
    app.set_session(build_demo_session())
    return app


def views(app):
    """Yield screen names for every view the demo can show."""
    for name in ("home", "rules"):
        app.goto(name)
        yield name
    for pid in app.session.pages:
        app.goto("page", pid)
        yield f"page:{pid}"
    app.goto("rules")
    app.mode, app.buf = "cmd", "s"
    yield "palette"
    app.mode, app.help = "nav", True
    yield "help"
    app.help = False


def wait_for(app, cond, timeout=3.0):
    end = time.time() + timeout
    while time.time() < end:
        app.pump()
        if cond():
            return True
        time.sleep(0.01)
    return False


# ═══════════════════════════════════════════════════════════════════════════════
# Status
# ═══════════════════════════════════════════════════════════════════════════════

class StatusTests(unittest.TestCase):

    def test_unknown_input_never_becomes_pass(self):
        for raw in ("???", "", None, "healthy-ish", 42):
            self.assertIs(Status.parse(raw), Status.UNSURE,
                          f"Status.parse({raw!r}) should be UNSURE, not PASS")

    def test_known_aliases(self):
        self.assertIs(Status.parse("Critical"),    Status.FAIL)
        self.assertIs(Status.parse("inconclusive"), Status.UNSURE)
        self.assertIs(Status.parse("skipped"),     Status.OPEN)
        self.assertIs(Status.parse(Status.WARN),   Status.WARN)

    def test_every_status_has_a_word(self):
        for s in Status:
            self.assertTrue(s.word, f"{s} has no word")

    def test_bucket_groups(self):
        self.assertEqual(Status.FAIL.bucket,  "fail")
        self.assertEqual(Status.CLAIM.bucket, "fail")
        self.assertEqual(Status.WARN.bucket,  "warn")
        self.assertEqual(Status.PASS.bucket,  "pass")
        self.assertEqual(Status.OPEN.bucket,  "open")
        self.assertEqual(Status.UNSURE.bucket, "open")


# ═══════════════════════════════════════════════════════════════════════════════
# Key parser
# ═══════════════════════════════════════════════════════════════════════════════

class KeyParserTests(unittest.TestCase):

    def test_arrow_sequences(self):
        self.assertEqual(parse_keys(b"\x1b[A\x1b[B\x1b[C\x1b[D"),
                         ["up", "down", "right", "left"])
        self.assertEqual(parse_keys(b"\x1bOA"), ["up"])

    def test_single_escape(self):
        self.assertEqual(parse_keys(b"\x1b"), ["esc"])

    def test_printable_and_control(self):
        self.assertEqual(parse_keys(b"j\r\x7f\t\x03"),
                         ["j", "enter", "backspace", "tab", "ctrl-c"])

    def test_tilde_sequences(self):
        self.assertEqual(parse_keys(b"\x1b[3~\x1b[5~"), ["delete", "pgup"])

    def test_garbage_does_not_raise(self):
        # Must not raise under any malformed input
        parse_keys(b"\xff\xfe\x1b[999;999;X\x1b[")


# ═══════════════════════════════════════════════════════════════════════════════
# Widget primitives
# ═══════════════════════════════════════════════════════════════════════════════

class WidgetTests(unittest.TestCase):

    def test_clip_is_ansi_aware(self):
        th = THEMES["truecolor"]
        s = th.paint("w", "abcdefghij")
        out = clip(s, 5)
        self.assertEqual(vlen(out), 5)
        self.assertTrue(out.endswith("\x1b[0m"), "clip should close open escape")

    def test_broken_block_is_contained(self):
        th = THEMES["none"]
        # "x", "y", "z" are not floats → r_chart raises → render_block catches it
        out = render_block(th, Chart("TEMP", ["x", "y", "z"], 0, 1), 40)
        self.assertTrue(any("cannot draw" in line for line in out))

    def test_stext_always_has_a_word(self):
        from xflash.tui.widgets import stext
        for th in THEMES.values():
            for st in Status:
                self.assertIn(st.word, strip(stext(th, st)),
                              f"stext missing word for {st} in {th.color} theme")


# ═══════════════════════════════════════════════════════════════════════════════
# Rendering geometry
# ═══════════════════════════════════════════════════════════════════════════════

class RenderTests(unittest.TestCase):

    def test_geometry_for_every_screen_theme_and_size(self):
        """Every rendered frame must be exactly H rows, each ≤ W columns."""
        for tname, th in THEMES.items():
            for size in SIZES:
                app = loaded_app(th, size)
                for view in views(app):
                    lines = app.render()
                    ctx = f"{tname} {size} {view}"
                    self.assertEqual(len(lines), size[1], f"{ctx}: wrong row count")
                    for i, line in enumerate(lines):
                        self.assertLessEqual(vlen(line), size[0], f"{ctx} row {i}: too wide")

    def test_idle_state_renders_correctly(self):
        for size in SIZES:
            app = App(DemoBackend(0), THEMES["none"], size)
            self.assertEqual(len(app.render()), size[1])

    def test_scan_state_renders_correctly(self):
        for size in SIZES:
            app = App(DemoBackend(0), THEMES["none"], size)
            app.start_scan(ScanOptions())
            wait_for(app, lambda: app.session is not None)
            self.assertEqual(len(app.render()), size[1])

    def test_ascii_theme_emits_only_ascii(self):
        app = loaded_app(THEMES["ascii"], (130, 34))
        for view in views(app):
            for line in app.render():
                self.assertTrue(line.isascii(), f"{view}: non-ASCII in ascii theme: {line!r}")

    def test_no_color_theme_has_no_escape_codes(self):
        app = loaded_app(THEMES["none"], (130, 34))
        for view in views(app):
            for line in app.render():
                self.assertNotIn("\x1b", line, f"{view}: escape code in no-color theme")

    def test_demo_is_always_marked(self):
        """DEMO DATA chip must be visible in every demo render."""
        app = loaded_app(THEMES["none"], (130, 34))
        self.assertIn("DEMO DATA", "\n".join(app.render()))

    def test_failing_screen_does_not_kill_session(self):
        @screen("boom")
        def boom(app, w, h):
            raise ValueError("kaput")
        try:
            app = loaded_app(THEMES["none"], (100, 30))
            app.goto("boom")
            text = "\n".join(app.render())
            self.assertIn("kaput", text, "error message should appear in render")
            app.goto("home")
            self.assertEqual(len(app.render()), 30, "session should survive a broken screen")
        finally:
            SCREENS.pop("boom", None)

    def test_page_from_backend_needs_no_ui_code(self):
        """A backend can deliver a Page and it renders without any screen-specific code."""
        p = Page("fans", "Fans", "FANS", "two fans", "", [[KV("Fan 1", [("rpm", "2,100")])]])
        app = loaded_app(THEMES["none"], (120, 30))
        app.session.pages["fans"] = p
        app.goto("page", "fans")
        self.assertIn("2,100", "\n".join(app.render()))


# ═══════════════════════════════════════════════════════════════════════════════
# User flow
# ═══════════════════════════════════════════════════════════════════════════════

class FlowTests(unittest.TestCase):

    def test_scan_then_navigate_bays(self):
        app = App(DemoBackend(0), THEMES["none"], (130, 34))
        app.handle_key("1")
        self.assertIn("no session", app.msg)
        app.start_scan(ScanOptions())
        self.assertTrue(wait_for(app, lambda: app.session is not None))
        self.assertEqual(app.screen, "rules")
        for key, pid in (("2", "storage"), ("4", "thermal"), ("3", "memory")):
            app.handle_key(key)
            self.assertEqual((app.screen, app.page_id), ("page", pid))
        app.handle_key("1")
        self.assertEqual(app.screen, "rules")
        self.assertEqual(app.rules_filtered()[app.sel].id, "BAT-01")

    def test_filter_and_selection_clamp(self):
        app = loaded_app(THEMES["none"], (130, 34))
        for k in ("/", "u", "s", "b", "enter"):
            app.handle_key(k)
        self.assertEqual([f.id for f in app.rules_filtered()], ["USB-03"])
        for _ in range(5):
            app.handle_key("j")
        self.assertEqual(app.sel, 0, "selection should clamp at the last item")
        app.handle_key("/")
        app.handle_key("esc")
        self.assertEqual(len(app.rules_filtered()), 7, "clearing filter should restore all rules")

    def test_palette_completes_home_command(self):
        app = loaded_app(THEMES["none"], (130, 34))
        for k in (":", "h", "o", "m", "e", "enter"):
            app.handle_key(k)
        self.assertEqual(app.screen, "home")

    def test_palette_bay_command(self):
        app = loaded_app(THEMES["none"], (130, 34))
        for k in (":", "b", "a", "y", " ", "2", "enter"):
            app.handle_key(k)
        self.assertEqual(app.page_id, "storage")

    def test_unsupported_command_is_explained_not_fatal(self):
        class ScanOnly(Backend):
            name = "scan-only"
            def scan(self, opts, emit, cancel):
                emit(ScanFinished(build_demo_session()))

        app = loaded_app(THEMES["none"], (130, 34), ScanOnly())
        self.assertTrue(app.backend.supports("scan"))
        self.assertFalse(app.backend.supports("export"))
        for text in ("export", "serve", "open x", "diff", "nonsense"):
            app.run_command(text)
            self.assertTrue(app.msg, f"command '{text}' should set a message")
            self.assertFalse(app.quit)
        app.mode, app.buf = "cmd", "exp"
        self.assertIn("not available here", "\n".join(app.render()))

    def test_custom_command_registration(self):
        app = loaded_app(THEMES["none"], (130, 34))
        app.register(Command("ping", "say pong",
                              lambda a, args: setattr(a, "msg", "pong " + " ".join(args))))
        app.run_command("ping 1 2")
        self.assertEqual(app.msg, "pong 1 2")

    def test_backend_exception_becomes_message_not_crash(self):
        class Bad(Backend):
            def scan(self, opts, emit, cancel):
                raise OSError("sensor bus offline")

        app = App(Bad(), THEMES["none"], (120, 30))
        app.start_scan(ScanOptions())
        self.assertTrue(wait_for(app, lambda: not app.scan.running))
        self.assertIn("sensor bus offline", app.msg)
        self.assertEqual(app.screen, "home")

    def test_scan_that_never_finishes_is_detected(self):
        class Silent(Backend):
            def scan(self, opts, emit, cancel):
                emit(ScanStarted(["a"]))

        app = App(Silent(), THEMES["none"], (120, 30))
        app.start_scan(ScanOptions())
        self.assertTrue(wait_for(app, lambda: not app.scan.running))
        self.assertIn("without a result", app.msg)

    def test_cancel_discards_stale_events(self):
        gate = threading.Event()

        class Slow(Backend):
            def scan(self, opts, emit, cancel):
                emit(ScanStarted(["a", "b"]))
                gate.wait(2)
                emit(ScanFinished(build_demo_session()))

        app = App(Slow(), THEMES["none"], (120, 30))
        app.start_scan(ScanOptions())
        wait_for(app, lambda: app.scan.checks)
        app.handle_key("esc")
        self.assertIn("scan stopped", app.msg)
        gate.set()
        time.sleep(0.1)
        app.pump()
        self.assertIsNone(app.session, "stale ScanFinished should be discarded after cancel")
        self.assertEqual(app.screen, "home")

    def test_second_scan_ignores_first_scans_stale_events(self):
        app = App(DemoBackend(0), THEMES["none"], (120, 30))
        app.start_scan(ScanOptions())
        wait_for(app, lambda: app.session is not None)
        first = app._scan_id
        app.events.put((first - 1, ScanFailed("old")))
        app.pump()
        self.assertNotIn("old", app.msg)

    def test_bad_key_handling_never_raises(self):
        app = loaded_app(THEMES["none"], (100, 30))
        for k in ["up", "down", "left", "right", "tab", "backspace",
                  "delete", "pgup", "ctrl-x", "?", "?", "z", "9"]:
            app.handle_key(k)
        self.assertFalse(app.quit)

    def test_quit_keys(self):
        for k in ("q", "ctrl-c"):
            app = loaded_app(THEMES["none"], (100, 30))
            app.handle_key(k)
            self.assertTrue(app.quit, f"key '{k}' should set app.quit")


# ═══════════════════════════════════════════════════════════════════════════════
# Backend contract
# ═══════════════════════════════════════════════════════════════════════════════

class BackendContractTests(unittest.TestCase):

    def test_all_base_methods_raise_not_supported(self):
        b = Backend()
        cases = [
            ("scan",   (ScanOptions(), print, threading.Event())),
            ("load",   ("x",)),
            ("export", (None, "json", None)),
            ("save",   (None,)),
            ("serve",  ()),
            ("diff",   ("a", "b")),
            ("tool",   ("screen",)),
        ]
        for op, args in cases:
            with self.assertRaises(NotSupported, msg=f"Backend.{op}() should raise NotSupported"):
                getattr(b, op)(*args)
            self.assertFalse(b.supports(op))

    def test_run_scan_blocking_returns_session(self):
        s = run_scan_blocking(DemoBackend(0))
        self.assertEqual(s.id, build_demo_session().id)

    def test_run_scan_blocking_raises_on_failure(self):
        class Bad(Backend):
            def scan(self, opts, emit, cancel):
                emit(ScanFailed("nope"))
        with self.assertRaises(RuntimeError):
            run_scan_blocking(Bad())

    def test_supports_detects_overridden_methods(self):
        class ScanOnly(Backend):
            def scan(self, opts, emit, cancel):
                pass
        b = ScanOnly()
        self.assertTrue(b.supports("scan"))
        self.assertFalse(b.supports("export"))
        self.assertFalse(b.supports("serve"))


# ═══════════════════════════════════════════════════════════════════════════════
# CLI entry points
# ═══════════════════════════════════════════════════════════════════════════════

class CLITests(unittest.TestCase):

    def test_plain_report_contains_all_status_words(self):
        out = io.StringIO()
        rc = main(["--plain", "--no-color"], DemoBackend(0), out)
        self.assertEqual(rc, 0)
        text = out.getvalue()
        for word in ("WARN", "FAIL", "PASS", "OPEN", "CLAIM", "BAT-01"):
            self.assertIn(word, text, f"plain report missing '{word}'")

    def test_once_snapshot_produces_correct_line_count(self):
        pages = ("home", "rules", "scan", "palette", "help",
                 "storage", "thermal", "keys", "memory", "display")
        for name in pages:
            out = io.StringIO()
            rc = main(["--once", name, "--width", "110", "--height", "30"],
                      DemoBackend(0), out)
            self.assertEqual(rc, 0, f"--once {name} returned non-zero")
            lines = out.getvalue().rstrip("\n").split("\n")
            self.assertEqual(len(lines), 30, f"--once {name}: expected 30 lines, got {len(lines)}")

    def test_xflash_tui_subcommand_wired_in_cli(self):
        """The 'xflash tui' subcommand must be reachable from the top-level CLI."""
        from xflash.cli import build_parser
        p = build_parser()
        # just check the subcommand is registered; parsing --help would exit
        subcommand_names = [a.dest if hasattr(a, "dest") else ""
                            for a in p._subparsers._actions]
        # the subparser action stores choices
        for action in p._subparsers._actions:
            if hasattr(action, "_name_parser_map"):
                self.assertIn("tui", action._name_parser_map,
                              "'tui' subcommand not registered in xflash CLI")
                return
        self.fail("No subparser action found in the top-level CLI")


# ═══════════════════════════════════════════════════════════════════════════════
# Real-backend adapter (no hardware required; uses the sample_session fixture)
# ═══════════════════════════════════════════════════════════════════════════════

class RealAdapterTests(unittest.TestCase):
    """Verify to_session() maps correctly from the sample_session.json fixture."""

    def _load_fixture(self):
        import json
        from pathlib import Path
        fixture = Path(__file__).parent.parent / "examples" / "sample_session.json"
        if not fixture.exists():
            self.skipTest("examples/sample_session.json not found")
        with fixture.open() as fh:
            return json.load(fh)

    def test_to_session_produces_valid_session(self):
        from xflash.analysis import analyze_snapshot
        from xflash.tui.real import to_session
        snapshot = self._load_fixture()
        report = analyze_snapshot(snapshot)
        session = to_session(snapshot, report)
        self.assertIsInstance(session.id, str)
        self.assertTrue(session.id)
        self.assertEqual(len(session.bays), 6, "must have exactly 6 bays (BAT SSD MEM CPU FAN DSP)")

    def test_to_session_no_unknown_becomes_pass(self):
        """UNSURE must appear for missing data, never PASS."""
        from xflash.analysis import analyze_snapshot
        from xflash.tui.real import to_session
        # Minimal snapshot: only inspection key, everything else absent
        snapshot = {"inspection": {"id": "MINIMAL-001"}, "system": {}, "claims": {}}
        report = analyze_snapshot(snapshot)
        session = to_session(snapshot, report)
        for bay in session.bays:
            self.assertIsNot(bay.status, Status.PASS,
                             f"Bay {bay.name} should not be PASS when data is missing")

    def test_to_session_all_statuses_are_valid(self):
        """Every status in the produced session must be a known Status enum member."""
        from xflash.analysis import analyze_snapshot
        from xflash.tui.real import to_session
        snapshot = self._load_fixture()
        report = analyze_snapshot(snapshot)
        session = to_session(snapshot, report)
        for bay in session.bays:
            self.assertIsInstance(bay.status, Status)
        for finding in session.findings:
            self.assertIsInstance(finding.status, Status)

    def test_session_renders_at_all_sizes(self):
        """The session produced from real data must render without errors at all test sizes."""
        from xflash.analysis import analyze_snapshot
        from xflash.tui.real import to_session
        snapshot = self._load_fixture()
        report = analyze_snapshot(snapshot)
        session = to_session(snapshot, report)
        for size in SIZES:
            app = App(DemoBackend(0), THEMES["none"], size)
            app.set_session(session)
            lines = app.render()
            self.assertEqual(len(lines), size[1], f"Wrong row count at size {size}")

    def test_real_backend_load_file_directly(self):
        """RealBackend.load() must load local snapshot JSON files directly."""
        from xflash.tui.real import RealBackend
        backend = RealBackend()
        session = backend.load("examples/sample_session.json")
        self.assertEqual(session.id, "SYNTHETIC-DEMO-001")
        self.assertEqual(len(session.bays), 6)
        self.assertIn("storage", session.pages)
        self.assertIn("battery", session.pages)

    def test_healthy_hardware_battery_is_pass(self):
        """Clean battery with >= 80% retention and no warnings must be Status.PASS."""
        from xflash.analysis import analyze_snapshot
        from xflash.tui.real import to_session
        snapshot = {
            "inspection": {"id": "HEALTHY-001"},
            "system": {"vendor": "TestVendor", "model": "TestModel"},
            "battery": {
                "design_capacity_mwh": 50000,
                "full_charge_capacity_mwh": 45000,
                "cycle_count": 50,
            },
            "storage": {
                "devices": [{
                    "model": "Clean NVMe",
                    "protocol": "nvme",
                    "nvme_percentage_used": 5,
                    "media_errors": 0,
                    "capacity_bytes": 512000000000,
                }]
            },
            "memory": {"total_bytes": 16000000000},
            "claims": {},
        }
        report = analyze_snapshot(snapshot)
        session = to_session(snapshot, report)
        bat_bay = next(b for b in session.bays if b.name == "BAT")
        self.assertEqual(bat_bay.status, Status.PASS, "Healthy battery must be PASS")
        ssd_bay = next(b for b in session.bays if b.name == "SSD")
        self.assertEqual(ssd_bay.status, Status.PASS, "Healthy storage must be PASS")

    def test_real_backend_save_export_diff_history(self):
        """RealBackend operations (save, export, diff, history) must function without error."""
        import tempfile
        from xflash.tui.real import RealBackend
        backend = RealBackend()
        session = backend.load("examples/sample_session.json")

        # Test save
        db_path = backend.save(session)
        self.assertTrue(os.path.isfile(db_path))

        # Test export
        with tempfile.TemporaryDirectory() as td:
            json_out = backend.export(session, "json", os.path.join(td, "test_out.json"))
            self.assertTrue(os.path.isfile(json_out))
            html_out = backend.export(session, "html", os.path.join(td, "test_out.html"))
            self.assertTrue(os.path.isfile(html_out))

        # Test history
        hist = backend.history()
        self.assertIsInstance(hist, list)

        # Diff is intentionally not supported in RealBackend
        from xflash.tui.backend import NotSupported
        self.assertFalse(backend.supports("diff"))
        with self.assertRaises(NotSupported):
            backend.diff("examples/sample_session.json", "examples/sample_session.json")

    def test_real_backend_live_probe_battery_accuracy(self):
        """Live probe must calculate battery retention accurately from sysfs without sample data contamination."""
        from xflash.tui.real import RealBackend
        from xflash.collectors import get_collector
        collector = get_collector()
        bat = collector.collect_battery()
        if bat and bat.get("design_capacity_mwh") and bat.get("full_charge_capacity_mwh"):
            expected_retention = round(
                (bat["full_charge_capacity_mwh"] / bat["design_capacity_mwh"]) * 100.0, 1
            )
            backend = RealBackend()
            session = run_scan_blocking(backend)
            bat_bay = next(b for b in session.bays if b.name == "BAT")
            self.assertEqual(bat_bay.value, f"{expected_retention} %")
            self.assertIn("battery", session.pages)
            page = session.pages["battery"]
            self.assertEqual(page.title, "Battery")


# ═══════════════════════════════════════════════════════════════════════════════
# PTY / interactive session (POSIX only)
# ═══════════════════════════════════════════════════════════════════════════════

@unittest.skipIf(os.name == "nt", "pty test is POSIX-only")
class PtyTests(unittest.TestCase):

    def test_interactive_session_restores_terminal(self):
        import fcntl
        import pty
        import select
        import struct
        import termios

        env = dict(os.environ,
                   PYTHONPATH=os.pathsep.join(sys.path),
                   TERM="xterm-256color",
                   PYTHONIOENCODING="utf-8")
        pid, fd = pty.fork()
        if pid == 0:
            os.execvpe(sys.executable,
                       [sys.executable, "-m", "xflash.tui"],
                       env)
        fcntl.ioctl(fd, termios.TIOCSWINSZ, struct.pack("HHHH", 34, 130, 0, 0))
        buf = b""

        def pump(t):
            nonlocal buf
            end = time.time() + t
            while time.time() < end:
                if select.select([fd], [], [], 0.05)[0]:
                    try:
                        buf += os.read(fd, 65536)
                    except OSError:
                        return

        pump(1.0)
        for key in (b":", b"scan", b"\r"):
            os.write(fd, key)
            pump(0.2)
        pump(8.0)
        os.write(fd, b"2")
        pump(0.5)
        screen_text = buf.decode("utf-8", "replace")
        self.assertIn("STORAGE", screen_text, "STORAGE screen should appear after navigating bay 2")
        os.write(fd, b"q")
        pump(0.8)
        _, status = os.waitpid(pid, 0)
        self.assertEqual(os.WEXITSTATUS(status), 0, "process should exit cleanly")
        self.assertIn(b"\x1b[?1049l", buf, "alternate screen should be restored")
        self.assertIn(b"\x1b[?25h", buf, "cursor should be restored")


class WindowsTerminalTests(unittest.TestCase):
    def test_windows_key_mapping(self):
        from xflash.tui.term import _WIN_KEYS, char_key
        self.assertEqual(_WIN_KEYS.get("H"), "up")
        self.assertEqual(_WIN_KEYS.get("P"), "down")
        self.assertEqual(_WIN_KEYS.get("K"), "left")
        self.assertEqual(_WIN_KEYS.get("M"), "right")
        self.assertEqual(_WIN_KEYS.get("G"), "home")
        self.assertEqual(_WIN_KEYS.get("O"), "end")
        self.assertEqual(_WIN_KEYS.get("S"), "delete")
        self.assertEqual(char_key("\r"), "enter")
        self.assertEqual(char_key("\n"), "enter")
        self.assertEqual(char_key("\x08"), "backspace")

    def test_windows_poll_emulation(self):
        from unittest.mock import patch, MagicMock
        from xflash.tui.term import Terminal

        t = Terminal()
        mock_msvcrt = MagicMock()
        mock_msvcrt.kbhit.side_effect = [True, False]
        mock_msvcrt.getwch.return_value = "q"

        with patch("os.name", "nt"), patch.dict("sys.modules", {"msvcrt": mock_msvcrt}):
            keys = t.poll(0.01)
            self.assertEqual(keys, ["q"])

    def test_windows_theme_wt_session_and_utf8(self):
        from xflash.tui.theme import Theme
        env = {"WT_SESSION": "12345-abc", "TERM": "xterm-256color"}
        th = Theme.detect(no_color=False, ascii_only=False, env=env)
        self.assertEqual(th.color, "truecolor")
        self.assertTrue(th.unicode)

        th_ascii = Theme.detect(no_color=False, ascii_only=True, env=env)
        self.assertFalse(th_ascii.unicode)


if __name__ == "__main__":
    unittest.main()
