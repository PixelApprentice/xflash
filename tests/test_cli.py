"""Unit tests for Xflash CLI commands and terminal UI formatters."""
from __future__ import annotations

import io
import json
import unittest
from pathlib import Path
from unittest.mock import patch

from xflash.analysis import analyze_snapshot
from xflash.cli import build_parser, main
from xflash.cli_ui import format_terminal_report

FIXTURE_PATH = Path(__file__).parents[1] / "examples" / "sample_session.json"


class CLITests(unittest.TestCase):
    def setUp(self):
        with FIXTURE_PATH.open("r", encoding="utf-8") as f:
            self.sample_snapshot = json.load(f)
        self.sample_report = analyze_snapshot(self.sample_snapshot)

    def test_build_parser_subcommands(self):
        parser = build_parser()
        # Verify subcommands exist
        args_scan = parser.parse_args(["scan", "--claim-ram", "16", "--claim-storage", "512"])
        self.assertEqual(args_scan.subcommand, "scan")
        self.assertEqual(args_scan.claim_ram, 16.0)
        self.assertEqual(args_scan.claim_storage, 512.0)

        args_inspect = parser.parse_args(["inspect"])
        self.assertEqual(args_inspect.subcommand, "inspect")

        args_check = parser.parse_args(["check"])
        self.assertEqual(args_check.subcommand, "check")

        args_serve = parser.parse_args(["serve", "--port", "9090", "--no-browser"])
        self.assertEqual(args_serve.subcommand, "serve")
        self.assertEqual(args_serve.port, 9090)
        self.assertTrue(args_serve.no_browser)

        args_analyze = parser.parse_args(["analyze", str(FIXTURE_PATH), "--format", "terminal"])
        self.assertEqual(args_analyze.subcommand, "analyze")
        self.assertEqual(args_analyze.format, "terminal")

    def test_format_terminal_report_output_sections(self):
        output = format_terminal_report(self.sample_snapshot, self.sample_report, use_color=False)
        self.assertIn("XFLASH HARDWARE ASSURANCE", output)
        self.assertIn("VERDICT:", output)
        self.assertIn("HARDWARE SPECIFICATIONS & RECONCILIATION", output)
        self.assertIn("Model:", output)
        self.assertIn("Memory (RAM):", output)
        self.assertIn("Storage:", output)
        self.assertIn("Battery:", output)
        self.assertIn("DETECTED HARDWARE FINDINGS", output)
        self.assertIn("1. What’s Wrong:", output)
        self.assertIn("2. Why It Matters:", output)
        self.assertIn("3. Action:", output)
        self.assertIn("EVALUATION COVERAGE MATRIX", output)

    def test_format_terminal_report_clean_system(self):
        clean_snapshot = {
            "inspection": {"id": "CLEAN-TEST-001"},
            "system": {"vendor": "TestCorp", "model": "SafeBook 15"},
            "cpu": {"model": "Intel Core i5-12400", "cores": 6, "threads": 12},
            "memory": {"total_bytes": 17179869184},  # 16 GiB
            "storage": {"devices": [{"model": "SafeSSD", "capacity_bytes": 512000000000, "protocol": "nvme", "media_errors": 0, "nvme_percentage_used": 2}]},
            "battery": {"design_capacity_mwh": 50000, "full_charge_capacity_mwh": 48000, "cycle_count": 25, "status": "Normal"},
            "claims": {"ram_gib": 16.0, "storage_capacity_gb": 512.0},
        }
        clean_report = analyze_snapshot(clean_snapshot)
        output = format_terminal_report(clean_snapshot, clean_report, use_color=False)
        self.assertIn("VERDICT: PASSED", output)
        self.assertIn("NO HARDWARE FINDINGS", output)

    def test_cli_scan_with_snapshot_file(self):
        f = io.StringIO()
        with patch("sys.stdout", f):
            exit_code = main(["scan", str(FIXTURE_PATH), "--no-color"])
        # Should return 0 or 1 based on findings
        self.assertIn(exit_code, (0, 1))
        out = f.getvalue()
        self.assertIn("XFLASH HARDWARE ASSURANCE", out)
        self.assertIn("Example Laptop 14", out)

    def test_cli_analyze_json_format(self):
        f = io.StringIO()
        with patch("sys.stdout", f):
            exit_code = main(["analyze", str(FIXTURE_PATH), "--format", "json"])
        self.assertEqual(exit_code, 0)
        data = json.loads(f.getvalue())
        self.assertIn("risk_state", data)
        self.assertIn("findings", data)

    def test_cli_analyze_html_format(self):
        f = io.StringIO()
        with patch("sys.stdout", f):
            exit_code = main(["analyze", str(FIXTURE_PATH), "--format", "html"])
        self.assertEqual(exit_code, 0)
        out = f.getvalue()
        self.assertIn("<!doctype html>", out.lower())

    def test_cli_tui_subcommand_plain_output(self):
        f = io.StringIO()
        with patch("sys.stdout", f):
            exit_code = main(["tui", str(FIXTURE_PATH), "--plain", "--no-color"])
        self.assertEqual(exit_code, 0)
        out = f.getvalue()
        self.assertIn("offline", out)
        self.assertIn("read only", out)
        self.assertIn("BAT", out)
        self.assertIn("SSD", out)
        self.assertIn("MEM", out)

    def test_cli_tui_subcommand_once_snapshot(self):
        f = io.StringIO()
        with patch("sys.stdout", f):
            exit_code = main(["tui", str(FIXTURE_PATH), "--once", "storage", "--no-color", "--ascii"])
        self.assertEqual(exit_code, 0)
        lines = f.getvalue().rstrip("\n").split("\n")
        self.assertEqual(len(lines), 36)
        self.assertIn("Drive 0", f.getvalue())

    def test_cli_tui_subcommand_once_live_battery(self):
        f = io.StringIO()
        with patch("sys.stdout", f):
            exit_code = main(["tui", "--once", "battery", "--no-color", "--ascii"])
        self.assertEqual(exit_code, 0)
        out = f.getvalue()
        lines = out.rstrip("\n").split("\n")
        self.assertEqual(len(lines), 36)
        self.assertIn("retention", out)
        self.assertIn("BAT", out)

    def test_battery_capacity_calculation_accuracy(self):
        from xflash.tui.real import to_session
        # Synthetic fixture: 43,200 / 60,000 mWh -> exactly 72.0%
        fixture_snap = {
            "battery": {
                "design_capacity_mwh": 60000.0,
                "full_charge_capacity_mwh": 43200.0,
                "cycle_count": 30,
            }
        }
        fixture_report = analyze_snapshot(fixture_snap)
        fixture_sess = to_session(fixture_snap, fixture_report)
        bat_bay_fixture = next(b for b in fixture_sess.bays if b.name == "BAT")
        self.assertEqual(bat_bay_fixture.value, "72.0 %")
        # Ensure degradation finding exists with matching evidence
        deg_f = next(f for f in fixture_sess.findings if "battery" in f.id.lower())
        kv_block = next(b for b in deg_f.blocks if b.kind == "kv")
        self.assertTrue(any("72" in str(v) for _, v in kv_block.rows))

        # Real hardware measurements: 41,770 / 50,014 mWh -> exactly 83.5%
        real_snap = {
            "battery": {
                "design_capacity_mwh": 50014.0,
                "full_charge_capacity_mwh": 41770.0,
                "cycle_count": 432,
            }
        }
        real_report = analyze_snapshot(real_snap)
        real_sess = to_session(real_snap, real_report)
        bat_bay_real = next(b for b in real_sess.bays if b.name == "BAT")
        self.assertEqual(bat_bay_real.value, "83.5 %")


if __name__ == "__main__":
    unittest.main()
