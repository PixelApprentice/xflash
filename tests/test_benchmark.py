"""Unit tests for the CPU thermal dissipation benchmark module."""
import unittest
from laptop_inspector.benchmark import run_cpu_pulse


class MockCollector:
    def __init__(self, start_temp=45.0, peak_temp=52.0, fans=None):
        self.start_temp = start_temp
        self.peak_temp = peak_temp
        self.call_count = 0
        self.fans = fans or [{"label": "cpu_fan", "rpm": 2200}]

    def collect_thermals(self):
        self.call_count += 1
        t = self.peak_temp if self.call_count > 2 else self.start_temp
        return {
            "average_temp_c": t,
            "max_temp_c": t,
            "cpu_temp_c": t,
            "zones": [{"zone": "core0", "type": "coretemp", "temp_c": t}],
        }

    def collect_fans(self):
        return {
            "fans": self.fans,
            "fan_count": len(self.fans),
        }


class BenchmarkTests(unittest.TestCase):
    def test_run_cpu_pulse_returns_valid_metrics(self):
        collector = MockCollector(start_temp=42.0, peak_temp=48.0)
        res = run_cpu_pulse(duration_seconds=1.0, collector=collector, worker_count=1)

        self.assertIn("duration_seconds", res)
        self.assertIn("initial_temp_c", res)
        self.assertIn("peak_temp_c", res)
        self.assertIn("temp_rise_c", res)
        self.assertIn("thermal_ramp_rate", res)
        self.assertIn("status", res)
        self.assertTrue(res["sensor_available"])
        self.assertFalse(res["throttle_detected"])
        self.assertGreaterEqual(res["peak_temp_c"], res["initial_temp_c"])

    def test_run_cpu_pulse_detects_throttling_above_95c(self):
        collector = MockCollector(start_temp=90.0, peak_temp=96.5)
        res = run_cpu_pulse(duration_seconds=1.0, collector=collector, worker_count=1)

        self.assertTrue(res["throttle_detected"])
        self.assertIn("throttling", res["status"].lower())

    def test_run_cpu_pulse_without_collector_reports_inconclusive(self):
        res = run_cpu_pulse(duration_seconds=1.0, collector=None, worker_count=1)

        self.assertFalse(res["sensor_available"])
        self.assertIn("INCONCLUSIVE", res["status"])
        self.assertEqual(res["temp_rise_c"], 0.0)


if __name__ == "__main__":
    unittest.main()
