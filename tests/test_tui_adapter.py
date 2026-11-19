"""Adapter tests: real-shaped data in, honest view-model out. Includes a drift check against cli_ui."""
import copy
import re
import unittest

from xflash.tui import App, Status, Theme
from xflash.tui.adapter import _impact, _verdict, to_session
from xflash.tui.demo import DemoBackend
from xflash.tui.widgets import strip, vlen

try:                                    # `python -m unittest discover -s tests` and `python -m unittest tests.x`
    from tui_fixtures import fixture
except ImportError:
    from tests.tui_fixtures import fixture

SIZES = [(80, 24), (100, 30), (120, 34), (200, 50)]
THEMES = [Theme("none", True), Theme("truecolor", True), Theme("none", False)]


def app_for(session, size=(140, 40), theme=None, lens="auto"):
    app = App(DemoBackend(0), theme or Theme("none", True), size)
    app.lens_pref = lens
    app.set_session(session)
    return app


def every_view(app):
    app.goto("home")
    yield "home"
    app.goto("rules")
    yield "rules"
    for pid in app.session.pages:
        app.goto("page", pid)
        yield f"page:{pid}"


def all_text(session) -> str:
    out = []
    for lens in ("expert", "pixel"):
        app = app_for(session, (160, 60), lens=lens)
        for _ in every_view(app):
            out += [strip(x) for x in app.render()]
        for i in range(len(session.findings)):
            app.goto("rules")
            app.sel = i
            out += [strip(x) for x in app.render()]
    return "\n".join(out)


class AdapterShapeTests(unittest.TestCase):
    def setUp(self):
        self.snap, self.rep = fixture()
        self.s = to_session(self.snap, self.rep)
        self.bay = {b.name: b for b in self.s.bays}

    def test_identity_and_verdict(self):
        self.assertEqual(self.s.id, "XPS13-2026-11-15")
        self.assertEqual(self.s.title, "Dell Inc. XPS 13 9310")
        self.assertEqual((self.s.verdict_status, self.s.verdict), (Status.WARN, "REVIEW DISCREPANCIES (3 Findings)"))

    def test_bays(self):
        b = self.bay
        self.assertEqual((b["BAT"].status, round(b["BAT"].gauge, 2), b["BAT"].big), (Status.WARN, 0.72, "72.0%"))
        self.assertEqual(b["SSD"].status, Status.PASS)
        self.assertAlmostEqual(b["SSD"].gauge, 0.92)
        self.assertEqual(b["MEM"].status, Status.CLAIM)                  # RAM claim shortfall finding
        self.assertEqual(b["CPU"].status, Status.PASS)                   # coverage says CLEAN
        self.assertEqual(b["FAN"].status, Status.UNSURE)                 # data present, but not in coverage
        self.assertEqual(b["DSP"].status, Status.OPEN)                   # coverage says skipped
        self.assertEqual(b["CPU"].value, "44 °C")

    def test_findings(self):
        f = {x.id: x for x in self.s.findings}
        self.assertEqual(f["battery_degradation"].status, Status.WARN)
        self.assertEqual(f["ram_claim_shortfall"].status, Status.FAIL)
        self.assertEqual(f["os_recent_wipe"].status, Status.OPEN)        # severity info
        kinds = [b.kind for b in f["battery_degradation"].blocks]
        self.assertEqual(kinds, ["hero", "bars", "card", "kv"])
        card = next(b for b in f["ram_claim_shortfall"].blocks if b.kind == "card")
        self.assertEqual(card.items[2][1], "Ask the seller for the missing module or a discount.")   # rule's own action wins

    def test_battery_threshold_marker(self):
        bars = next(b for b in self.s.findings[0].blocks if b.kind == "bars")
        self.assertEqual(bars.rows[0][4], 0.80)

    def test_pages_and_hints(self):
        self.assertEqual(set(self.s.pages), {"battery", "storage", "memory", "cpu", "thermal", "display", "system",
                                             "specs", "coverage"})
        self.assertEqual(self.s.pages["battery"].rules_hint, "battery_degradation")
        self.assertEqual(self.s.pages["memory"].rules_hint, "ram_claim_shortfall")

    def test_unknown_and_info_severities(self):
        self.rep["findings"] = [{"severity": "weird", "rule_id": "x"}, {"severity": "low", "rule_id": "y"},
                                {"severity": "CRITICAL", "rule_id": "z"}, {"rule_id": "w"}]
        st = [f.status for f in to_session(self.snap, self.rep).findings]
        self.assertEqual(st, [Status.WARN, Status.OPEN, Status.FAIL, Status.WARN])    # unknown never hides

    def test_coverage_page_statuses(self):
        rows = dict(self.s.pages["coverage"].columns[0][0].rows)
        self.assertEqual(rows["battery_health"], "@pass")
        self.assertEqual(rows["memory_capacity"], "@warn")
        self.assertEqual(rows["display_panel"], "@open")


class HonestyTests(unittest.TestCase):
    def test_empty_input_never_passes(self):
        s = to_session({}, {})
        self.assertEqual(s.verdict_status, Status.UNSURE)
        self.assertEqual(s.verdict, "INCONCLUSIVE TELEMETRY")
        for b in s.bays:
            self.assertNotEqual(b.status, Status.PASS, b.name)

    def test_clean_report_with_data_passes_and_without_does_not(self):
        snap, rep = fixture()
        rep.update(risk_state="pass", findings=[], finding_count=0, coverage={})
        s = to_session(snap, rep)
        self.assertEqual({b.name: b.status for b in s.bays}["BAT"], Status.PASS)
        self.assertEqual({b.name: b.status for b in s.bays}["FAN"], Status.PASS)
        snap.pop("battery")
        self.assertNotEqual({b.name: b.status for b in to_session(snap, rep).bays}["BAT"], Status.PASS)

    def test_garbage_never_raises_and_always_renders(self):
        junk = [None, "x", 5, [], {"battery": "oops", "storage": {"devices": 5}, "cpu": [1], "memory": "y",
                                   "display": 3, "claims": "no", "system": None, "thermal": {"fan": {"x": [1, 2]}}},
                {"storage": {"devices": [None, 5, {"capacity_bytes": "big", "nvme_percentage_used": "n/a"}]}}]
        reports = [None, "r", {"findings": [None, "x", {"severity": 5, "evidence": "bad"}, {"rule_id": None}],
                               "coverage": ["a"], "risk_state": 7, "finding_count": "many"}]
        for snap in junk:
            for rep in reports:
                s = to_session(snap, rep)
                for size in SIZES:
                    for theme in THEMES:
                        for lens in ("expert", "pixel"):
                            app = app_for(s, size, theme, lens)
                            for view in every_view(app):
                                lines = app.render()
                                self.assertEqual(len(lines), size[1], (view, size))
                                self.assertTrue(all(vlen(x) <= size[0] for x in lines), (view, size, lens))

    def test_secrets_are_redacted_everywhere(self):
        snap, rep = fixture()
        text = all_text(to_session(snap, rep))
        for secret in ("ABC123XYZ", "SELLER-PC", "S6XXXX"):
            self.assertNotIn(secret, text)
        self.assertIn("(redacted)", text)


class ReconciliationTests(unittest.TestCase):
    @staticmethod
    def checks(snap):
        rows = to_session(snap, fixture()[1]).pages["specs"].columns[0][0].rows
        return [v for k, v in rows if k == "  check"]

    def test_tolerances_match_cli_ui(self):
        snap, _ = fixture()
        snap["claims"] = {"model": "XPS 13 9310", "ram_gib": 16, "storage_capacity_gb": 512}   # 15.6 vs 16: within 1.2
        self.assertEqual(self.checks(snap), ["@pass", "@pass", "@pass"])
        snap["claims"] = {"model": "ThinkPad T14", "ram_gib": 32, "storage_capacity_gb": 1000}
        self.assertEqual(self.checks(snap), ["@claim", "@claim", "@claim"])

    def test_no_claims_explains_how(self):
        snap, rep = fixture()
        snap["claims"] = {}
        self.assertIn(":scan --claim-ram", to_session(snap, rep).pages["specs"].note)


class DriftAgainstCliUiTests(unittest.TestCase):
    """If cli_ui.py wording changes, these fail and tell you to update adapter.py."""

    @classmethod
    def setUpClass(cls):
        try:
            from xflash.cli_ui import format_terminal_report
        except ImportError:
            raise unittest.SkipTest("xflash.cli_ui not importable here")
        cls.fmt = staticmethod(format_terminal_report)

    def terminal(self, snap, rep) -> str:
        return strip(self.fmt(snap, rep, use_color=False))

    def test_verdict_text_for_every_state(self):
        for state in ("pass", "no_detected_anomaly_in_evaluated_checks", "review", "warning", "high", "high_risk",
                      "critical", "inconclusive", "something_new"):
            snap, rep = fixture()
            rep["risk_state"] = state
            _, title, note = _verdict(rep)
            text = " ".join(self.terminal(snap, rep).split())
            self.assertIn(title, text, state)
            self.assertIn(note, text, state)

    def test_three_part_finding_text(self):
        snap, rep = fixture()
        text = " ".join(self.terminal(snap, rep).split())
        for comp, rid in (("battery", "battery_degradation"), ("memory", "ram_claim_shortfall"),
                          ("storage", "nvme_x"), ("cpu", "thermal_x"), ("system", "other")):
            why, action = _impact(comp, rid)
            snap2, rep2 = fixture()
            rep2["findings"] = [{"severity": "warning", "rule_id": rid, "component": comp, "title": "T", "details": "D"}]
            t = " ".join(self.terminal(snap2, rep2).split())
            self.assertIn(why, t, comp)
            self.assertIn(action, t, comp)
        self.assertIn("Installed RAM below listing", text)

    def test_reconciliation_numbers_agree(self):
        snap, rep = fixture()
        text = self.terminal(snap, rep)
        m = re.search(r"delta: ([+-][\d.]+) GiB", text)
        self.assertIsNotNone(m)
        rows = dict(to_session(snap, rep).pages["specs"].columns[0][0].rows)
        self.assertEqual(rows["  delta"], f"{m.group(1)} GiB")
        self.assertIn("72.0% Health", text)
        self.assertEqual(to_session(snap, rep).bays[0].big, "72.0%")


class ScaleTests(unittest.TestCase):
    def test_many_findings_scroll_and_keep_selection_visible(self):
        snap, rep = fixture()
        rep["findings"] = [{"severity": "warning", "rule_id": f"rule_number_{i:02d}", "component": "battery",
                            "title": f"Finding number {i}", "details": "d"} for i in range(40)]
        s = to_session(snap, rep)
        for lens in ("expert", "pixel"):
            app = app_for(s, (140, 40), lens=lens)
            app.goto("rules")
            for i in range(39):
                app.handle_key("j")
            text = "\n".join(strip(x) for x in app.render())
            self.assertIn("rule_number_39", text, lens)
            if lens == "expert":
                self.assertIn("rule 40 of 40", text)


if __name__ == "__main__":
    unittest.main()
