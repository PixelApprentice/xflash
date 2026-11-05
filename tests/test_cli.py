"""Unit tests for Xflash CLI commands and terminal UI formatters."""
from __future__ import annotations

import io
import json
import unittest
from pathlib import Path
from unittest.mock import patch

from laptop_inspector.analysis import analyze_snapshot
from laptop_inspector.cli import build_parser, main
from laptop_inspector.cli_ui import format_terminal_report

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


if __name__ == "__main__":
    unittest.main()
