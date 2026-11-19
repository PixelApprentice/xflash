"""RealBackend tests. The project's collector/analysis/db/report/server are patched at the four
thin wrappers in real.py, so these run anywhere and still exercise every line of glue."""
import io
import json
import os
import sys
import tempfile
import threading
import time
import unittest
from contextlib import contextmanager
from unittest import mock

from xflash.tui import App, ScanFailed, ScanFinished, ScanOptions, Status, Theme, main
from xflash.tui import real
from xflash.tui.backend import run_scan_blocking
from xflash.tui.real import RealBackend, claims_from_options
from xflash.tui.widgets import vlen

try:                                    # `python -m unittest discover -s tests` and `python -m unittest tests.x`
    from tui_fixtures import fixture
except ImportError:
    from tests.tui_fixtures import fixture


@contextmanager
def patched(**over):
    snap, rep = fixture()
    defaults = dict(_collect=lambda claims: {**snap, "claims": claims}, _analyze=lambda s: rep,
                    _save_db=lambda s, r, portable: "xflash.db", _render_report=lambda r, fmt: f"REPORT:{fmt}",
                    _run_server=lambda host, port, portable: None)
    defaults.update(over)
    patchers = [mock.patch.object(real, k, v) for k, v in defaults.items()]
    for p in patchers:
        p.start()
    try:
        yield
    finally:
        for p in patchers:
            p.stop()


def events(backend, opts=None):
    out = []
    backend.scan(opts or ScanOptions(), out.append, threading.Event())
    return out


def wait_for(app, cond, timeout=3.0):
    end = time.time() + timeout
    while time.time() < end:
        app.pump()
        if cond():
            return True
        time.sleep(0.01)
    return False


class ClaimTests(unittest.TestCase):
    def test_palette_claims_become_snapshot_claims(self):
        self.assertEqual(claims_from_options({"ram": "16", "storage": "512", "model": "XPS 13", "cpu": "i7",
                                              "price": "400.5", "url": "http://x"}),
                         {"ram_gib": 16.0, "storage_capacity_gb": 512.0, "model": "XPS 13", "cpu": "i7",
                          "price": 400.5, "listing_url": "http://x"})

    def test_bad_claims_are_explained(self):
        with self.assertRaisesRegex(ValueError, "expects a number"):
            claims_from_options({"ram": "lots"})
        with self.assertRaisesRegex(ValueError, "unknown claim"):
            claims_from_options({"colour": "red"})


class ScanTests(unittest.TestCase):
    def test_event_sequence(self):
        with patched():
            ev = events(RealBackend())
        kinds = [type(e).__name__ for e in ev]
        self.assertEqual(kinds, ["ScanStarted", "CheckUpdate", "CheckUpdate", "CheckUpdate", "CheckUpdate", "ScanFinished"])
        self.assertEqual([e.status for e in ev[1:5]], [Status.RUNNING, Status.PASS, Status.RUNNING, Status.PASS])
        self.assertEqual(ev[-1].session.id, "XPS13-2026-11-15")
        self.assertIn("3 findings", ev[4].text)

    def test_claims_reach_the_collector(self):
        seen = {}
        with patched(_collect=lambda claims: seen.update(claims) or fixture()[0]):
            events(RealBackend(), ScanOptions({"ram": "32", "model": "XPS 13"}))
        self.assertEqual(seen, {"ram_gib": 32.0, "model": "XPS 13"})

    def test_collector_notices_on_stderr_never_leak(self):
        def noisy(claims):
            print("Notice: Live collector encountered: boom.", file=sys.stderr)
            return fixture()[0]
        err = io.StringIO()
        with patched(_collect=noisy), mock.patch("sys.stderr", err):
            ev = events(RealBackend())
        self.assertEqual(err.getvalue(), "")                                   # nothing reached the terminal
        collect = ev[2]
        self.assertEqual(collect.status, Status.WARN)                           # surfaced as a warning instead
        self.assertIn("boom", collect.text)

    def test_cancel_after_collect_emits_no_result(self):
        cancel, out = threading.Event(), []
        with patched(_collect=lambda c: cancel.set() or fixture()[0]):
            RealBackend().scan(ScanOptions(), out.append, cancel)
        self.assertFalse(any(isinstance(e, ScanFinished) for e in out))

    def test_portable_saves_best_effort(self):
        saved = []
        with patched(_save_db=lambda s, r, portable: saved.append(portable) or "db"):
            events(RealBackend(portable=True))
            events(RealBackend(portable=False))
        self.assertEqual(saved, [True])
        with patched(_save_db=mock.Mock(side_effect=OSError("read-only drive"))):
            self.assertIsInstance(events(RealBackend(portable=True))[-1], ScanFinished)   # swallowed, like the CLI

    def test_run_scan_blocking(self):
        with patched():
            self.assertEqual(run_scan_blocking(RealBackend()).title, "Dell Inc. XPS 13 9310")


class AppIntegrationTests(unittest.TestCase):
    def app(self, size=(140, 40), lens="auto"):
        app = App(RealBackend(), Theme("none", True), size)
        app.lens_pref = lens
        return app

    def test_full_scan_flow_in_both_lenses(self):
        for lens in ("expert", "pixel"):
            with patched():
                app = self.app(lens=lens)
                app.run_command("scan --claim-ram 32 --claim-model \"XPS 13\"")
                self.assertTrue(wait_for(app, lambda: app.session is not None))
                self.assertFalse(app.backend.is_demo)
                text = "\n".join(app.render())
                self.assertNotIn("DEMO DATA", text)
                self.assertIn("REVIEW DISCREPANCIES", text)
                for key in ("1", "2", "3"):
                    app.handle_key(key)
                    self.assertEqual(len(app.render()), 40)

    def test_bad_claim_shows_message_not_traceback(self):
        with patched():
            app = self.app()
            app.run_command("scan --claim-ram lots")
            self.assertTrue(wait_for(app, lambda: not app.scan.running))
            self.assertIn("expects a number", app.msg)
            self.assertEqual(app.screen, "home")

    def test_collector_crash_is_a_message(self):
        with patched(_collect=mock.Mock(side_effect=RuntimeError("no sensors"))):
            app = self.app()
            app.run_command("scan")
            self.assertTrue(wait_for(app, lambda: not app.scan.running))
            self.assertIn("no sensors", app.msg)

    def test_open_errors_are_explained(self):
        with patched():
            app = self.app()
            app.run_command("open /definitely/not/here.json")
            self.assertIn("cannot read", app.msg)
            with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False) as f:
                f.write("{not json")
            app.run_command(f"open {f.name}")
            self.assertIn("not valid JSON", app.msg)
            with open(f.name, "w") as g:
                g.write("[1, 2]")
            app.run_command(f"open {f.name}")
            self.assertIn("must be an object", app.msg)
            os.unlink(f.name)

    def test_open_good_file_and_export(self):
        snap = fixture()[0]
        with patched(), tempfile.TemporaryDirectory() as d:
            path = os.path.join(d, "snap.json")
            with open(path, "w") as f:
                json.dump(snap, f)
            app = self.app()
            app.run_command(f"open {path}")
            self.assertEqual((app.session.id, app.screen), ("XPS13-2026-11-15", "rules"))
            out = os.path.join(d, "r", "out.html")
            app.run_command(f"export html {out}")
            self.assertIn("exported", app.msg)
            with open(out, encoding="utf-8") as fh:
                self.assertEqual(fh.read(), "REPORT:html")
            cwd = os.getcwd()
            os.chdir(d)
            try:
                app.run_command("export json")
                self.assertTrue(os.path.exists(os.path.join("aegis_reports", "XPS13-2026-11-15.json")))
            finally:
                os.chdir(cwd)

    def test_export_save_need_a_session(self):
        with patched():
            app = self.app()
            for cmd in ("export", "save"):
                app.run_command(cmd)
                self.assertIn("run :scan first", app.msg)

    def test_save_uses_portable_flag(self):
        got = []
        with patched(_save_db=lambda s, r, portable: got.append(portable) or "usb.db"):
            app = App(RealBackend(portable=True), Theme("none", True), (140, 40))
            app.set_session(real.to_session(*fixture()))
            app.run_command("save")
            self.assertEqual(got, [True])
            self.assertIn("saved usb.db", app.msg)

    def test_unsupported_ops_are_greyed_out(self):
        app = self.app()
        self.assertFalse(app.backend.supports("diff"))
        self.assertTrue(all(app.backend.supports(op) for op in ("scan", "load", "export", "save", "serve")))
        app.mode, app.buf = "cmd", "di"
        self.assertIn("not available here", "\n".join(app.render()))


class ServeTests(unittest.TestCase):
    def test_serve_starts_once_and_reports_url(self):
        started = []
        with patched(_run_server=lambda host, port, portable: started.append((host, port, portable))):
            b = RealBackend(portable=True)
            url = b.serve(port=18765)
            b._server.join(1)
            self.assertEqual((url, started), ("http://127.0.0.1:18765", [("127.0.0.1", 18765, True)]))

    def test_busy_port_is_reported(self):
        import socket
        with socket.socket() as s:
            s.bind(("127.0.0.1", 0))
            s.listen(1)
            with patched(), self.assertRaisesRegex(OSError, "already in use"):
                RealBackend().serve(port=s.getsockname()[1])


class CliTests(unittest.TestCase):
    def test_plain_from_session_file(self):
        snap = fixture()[0]
        with patched(), tempfile.TemporaryDirectory() as d:
            path = os.path.join(d, "s.json")
            with open(path, "w") as f:
                json.dump(snap, f)
            out = io.StringIO()
            self.assertEqual(main(["--session", path, "--plain", "--no-color"], RealBackend(), out), 0)
            text = out.getvalue()
            for needle in ("REVIEW DISCREPANCIES", "battery_degradation", "CLAIM"):
                self.assertIn(needle, text)

    def test_once_snapshot_with_real_backend_both_lenses(self):
        snap = fixture()[0]
        with patched(), tempfile.TemporaryDirectory() as d:
            path = os.path.join(d, "s.json")
            with open(path, "w") as f:
                json.dump(snap, f)
            for lens in ("expert", "pixel"):
                out = io.StringIO()
                self.assertEqual(main(["--session", path, "--once", "rules", "--lens", lens, "--width", "140",
                                       "--height", "40", "--no-color"], RealBackend(), out), 0)
                lines = out.getvalue().rstrip("\n").split("\n")
                self.assertEqual(len(lines), 40)
                self.assertTrue(all(vlen(x) <= 140 for x in lines))

    def test_all_bay_pages_render_without_keyerror_in_pixel_lens(self):
        snap, rep = fixture()
        with patched():
            b = RealBackend()
            s = run_scan_blocking(b)
            for color_mode in ("truecolor", "basic", "none"):
                th = Theme(color=color_mode, unicode=True)
                app = App(b, th, (110, 32))
                app.set_session(s)
                for bay in app.bays():
                    if not bay.target:
                        continue
                    app.goto("page", bay.target)
                    rendered = app.render()
                    for line in rendered:
                        self.assertNotIn("KeyError", line)
                        self.assertNotIn("failed", line.lower())

    def test_theme_ln_role_and_safe_role_fallbacks(self):
        for color_mode in ("truecolor", "basic"):
            th = Theme(color=color_mode, unicode=True)
            # "ln" role must resolve cleanly
            fg_ln = th._fg("ln")
            self.assertTrue(bool(fg_ln))
            paint_ln = th.paint("ln", "test")
            self.assertIn("test", paint_ln)

            # Unknown role must never raise KeyError
            fg_unk = th._fg("non_existent_role")
            self.assertTrue(bool(fg_unk))
            chip_unk = th.chip("non_existent_role", "CHIP")
            self.assertIn("CHIP", chip_unk)


if __name__ == "__main__":
    unittest.main()
