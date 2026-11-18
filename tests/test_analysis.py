import copy
import json
import unittest
from pathlib import Path

from xflash.analysis import analyze_snapshot, analyze_battery, analyze_memory, analyze_storage, validate_snapshot_shape
from xflash.report import to_html, to_json

FIXTURE = Path(__file__).parents[1] / "examples" / "sample_session.json"


class BatteryTests(unittest.TestCase):
    def test_low_cycles_high_degradation_is_flagged(self):
        findings, evaluated = analyze_battery({
            "design_capacity_mwh": 60000,
            "full_charge_capacity_mwh": 43200,
            "cycle_count": 30,
            "source": "fixture",
        })
        codes = {f["code"] for f in findings}
        self.assertTrue(evaluated)
        self.assertIn("BATTERY_CAPACITY_DEGRADATION", codes)
        self.assertIn("LOW_CYCLES_HIGH_DEGRADATION", codes)
        degradation = next(f for f in findings if f["code"] == "BATTERY_CAPACITY_DEGRADATION")
        self.assertEqual(degradation["severity"], "warning")
        self.assertEqual(degradation["evidence"]["degradation_percent"], 28.0)

    def test_high_degradation_is_high_severity(self):
        findings, _ = analyze_battery({"design_capacity_mwh": 50000, "full_charge_capacity_mwh": 25000, "cycle_count": 12})
        self.assertTrue(any(f["severity"] == "high" for f in findings))

    def test_missing_battery_is_inconclusive_not_pass(self):
        findings, evaluated = analyze_battery(None)
        self.assertFalse(evaluated)
        self.assertEqual(findings[0]["severity"], "inconclusive")

    def test_zero_design_capacity_is_inconclusive(self):
        findings, evaluated = analyze_battery({"design_capacity_mwh": 0, "full_charge_capacity_mwh": 40000})
        self.assertFalse(evaluated)
        self.assertEqual(findings[0]["code"], "BATTERY_CAPACITY_INVALID_OR_MISSING")

    def test_non_finite_capacity_is_inconclusive(self):
        findings, evaluated = analyze_battery({"design_capacity_mwh": float("nan"), "full_charge_capacity_mwh": 40000})
        self.assertFalse(evaluated)
        self.assertEqual(findings[0]["severity"], "inconclusive")

    def test_boolean_capacity_is_invalid_not_numeric(self):
        findings, evaluated = analyze_battery({"design_capacity_mwh": True, "full_charge_capacity_mwh": 1})
        self.assertFalse(evaluated)
        self.assertEqual(findings[0]["severity"], "inconclusive")

    def test_extreme_capacity_above_design_does_not_claim_healthy(self):
        findings, _ = analyze_battery({"design_capacity_mwh": 10000, "full_charge_capacity_mwh": 13000})
        self.assertEqual(findings[0]["code"], "BATTERY_CAPACITY_IMPLAUSIBLE")

    def test_negative_cycle_count_is_invalid(self):
        findings, evaluated = analyze_battery({
            "design_capacity_mwh": 50000,
            "full_charge_capacity_mwh": 35000,
            "cycle_count": -5,
        })
        self.assertTrue(evaluated)
        self.assertTrue(any(f["code"] == "BATTERY_CYCLE_COUNT_INVALID" for f in findings))
        self.assertFalse(any(f["code"] == "LOW_CYCLES_HIGH_DEGRADATION" for f in findings))

    def test_zero_full_charge_capacity_is_critical(self):
        findings, evaluated = analyze_battery({
            "design_capacity_mwh": 50000,
            "full_charge_capacity_mwh": 0,
            "cycle_count": 100,
        })
        self.assertTrue(evaluated)
        self.assertTrue(any(f["code"] == "BATTERY_CAPACITY_DEPLETED" for f in findings))
        depleted = next(f for f in findings if f["code"] == "BATTERY_CAPACITY_DEPLETED")
        self.assertEqual(depleted["severity"], "critical")


class StorageTests(unittest.TestCase):
    def test_nonzero_media_errors_flag_even_when_wear_is_low(self):
        findings, evaluated = analyze_storage({"devices": [{"model": "fixture SSD", "nvme_percentage_used": 8, "media_errors": 14}]})
        self.assertTrue(evaluated)
        self.assertIn("STORAGE_MEDIA_ERRORS", {f["code"] for f in findings})
        self.assertNotIn("NVME_HIGH_ENDURANCE_USAGE", {f["code"] for f in findings})

    def test_controller_critical_warning_is_high(self):
        findings, _ = analyze_storage({"devices": [{"model": "fixture", "nvme_critical_warning": 2}]})
        finding = next(f for f in findings if f["code"] == "NVME_CRITICAL_WARNING")
        self.assertEqual(finding["severity"], "high")

    def test_missing_storage_is_inconclusive(self):
        findings, evaluated = analyze_storage({"devices": []})
        self.assertFalse(evaluated)
        self.assertEqual(findings[0]["severity"], "inconclusive")

    def test_capacity_claim_uses_decimal_gb_not_gib(self):
        findings, evaluated = analyze_storage({"devices": [{"model": "512 GB SSD", "capacity_bytes": 512_000_000_000}]}, {"storage_capacity_gb": 512})
        self.assertTrue(evaluated)
        self.assertFalse(any(f["code"].startswith("STORAGE_CAPACITY_CLAIM_MISMATCH") or f["code"] == "STORAGE_CAPACITY_SMALL_MISMATCH" for f in findings))

    def test_material_storage_capacity_mismatch_is_flagged(self):
        findings, evaluated = analyze_storage({"devices": [{"model": "claimed 1 TB, actual 512 GB", "capacity_bytes": 512_000_000_000}]}, {"storage_capacity_gb": 1024})
        self.assertTrue(evaluated)
        self.assertIn("STORAGE_CAPACITY_CLAIM_MISMATCH", {f["code"] for f in findings})

    def test_negative_nvme_percentage_used_is_invalid(self):
        findings, evaluated = analyze_storage({"devices": [{"model": "fixture", "nvme_percentage_used": -5}]})
        self.assertTrue(evaluated)
        self.assertTrue(any(f["code"] == "STORAGE_DATA_INVALID" for f in findings))

    def test_negative_media_errors_is_invalid(self):
        findings, evaluated = analyze_storage({"devices": [{"model": "fixture", "media_errors": -1}]})
        self.assertTrue(evaluated)
        self.assertTrue(any(f["code"] == "STORAGE_DATA_INVALID" for f in findings))

    def test_nvme_critical_warning_decoding_and_negative_check(self):
        # bit 0 (spare threshold) + bit 1 (temperature) = 3
        findings, evaluated = analyze_storage({"devices": [{"model": "fixture", "nvme_critical_warning": 3}]})
        self.assertTrue(evaluated)
        warning_finding = next(f for f in findings if f["code"] == "NVME_CRITICAL_WARNING")
        self.assertIn("decoded_flags", warning_finding["evidence"])
        self.assertIn("available_spare_below_threshold", warning_finding["evidence"]["decoded_flags"])
        self.assertIn("temperature_threshold_exceeded", warning_finding["evidence"]["decoded_flags"])

        # negative critical warning
        neg_findings, _ = analyze_storage({"devices": [{"model": "fixture", "nvme_critical_warning": -1}]})
        self.assertTrue(any(f["code"] == "STORAGE_DATA_INVALID" for f in neg_findings))


class MemoryTests(unittest.TestCase):
    def test_16_gib_is_not_false_positive_for_claimed_16_gib(self):
        findings, evaluated = analyze_memory({"total_bytes": 16 * (1024 ** 3)}, {"ram_gib": 16})
        self.assertTrue(evaluated)
        self.assertEqual(findings, [])

    def test_material_ram_shortfall_flags(self):
        findings, evaluated = analyze_memory({"total_bytes": 8 * (1024 ** 3)}, {"ram_gib": 16})
        self.assertTrue(evaluated)
        self.assertEqual(findings[0]["code"], "RAM_CLAIM_MISMATCH")
        self.assertEqual(findings[0]["severity"], "high")

    def test_claim_without_observation_is_inconclusive(self):
        findings, evaluated = analyze_memory({}, {"ram_gib": 16})
        self.assertFalse(evaluated)
        self.assertEqual(findings[0]["severity"], "inconclusive")

    def test_non_finite_memory_value_is_inconclusive(self):
        findings, evaluated = analyze_memory({"total_bytes": float("inf")}, {"ram_gib": 16})
        self.assertFalse(evaluated)
        self.assertEqual(findings[0]["severity"], "inconclusive")

    def test_zero_observed_memory_is_invalid(self):
        findings, evaluated = analyze_memory({"total_bytes": 0}, {"ram_gib": 16})
        self.assertFalse(evaluated)
        self.assertEqual(findings[0]["code"], "RAM_DATA_UNAVAILABLE")


class ReportTests(unittest.TestCase):
    def test_sample_contains_expected_findings(self):
        snapshot = json.loads(FIXTURE.read_text(encoding="utf-8"))
        report = analyze_snapshot(snapshot)
        codes = {f["code"] for f in report["findings"]}
        self.assertIn("LOW_CYCLES_HIGH_DEGRADATION", codes)
        self.assertIn("STORAGE_MEDIA_ERRORS", codes)
        self.assertEqual(report["risk_state"], "review")

    def test_html_escapes_untrusted_text(self):
        snapshot = {"inspection": {"id": "<script>alert(1)</script>"}, "battery": None, "storage": {"devices": []}, "memory": {}, "claims": {}}
        html = to_html(analyze_snapshot(snapshot))
        self.assertNotIn("<script>alert(1)</script>", html)
        self.assertIn("&lt;script&gt;", html)

    def test_json_is_parseable(self):
        report = analyze_snapshot(json.loads(FIXTURE.read_text(encoding="utf-8")))
        parsed = json.loads(to_json(report))
        self.assertEqual(parsed["report_schema_version"], "1.0")

    def test_report_includes_coverage_summary(self):
        report = analyze_snapshot(json.loads(FIXTURE.read_text(encoding="utf-8")))
        self.assertIn("coverage", report)
        self.assertIsInstance(report["coverage"], dict)
        self.assertIn("battery_capacity", report["coverage"])
        self.assertIn("battery_cycles", report["coverage"])
        self.assertIn("storage_integrity", report["coverage"])

    def test_html_renders_coverage_table(self):
        report = analyze_snapshot(json.loads(FIXTURE.read_text(encoding="utf-8")))
        html = to_html(report)
        self.assertIn("Test coverage", html)
        self.assertIn("battery_capacity", html)

    def test_malformed_component_structure_is_rejected(self):
        self.assertIn("'battery' must be an object or null", validate_snapshot_shape({"battery": "bad"}))
        with self.assertRaises(ValueError):
            analyze_snapshot({"storage": {"devices": "not-an-array"}})


if __name__ == "__main__":
    unittest.main()
