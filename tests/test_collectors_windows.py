"""Unit tests for the Windows hardware collector with synthetic mock execution."""
import json
import unittest

from laptop_inspector.collectors.base import CommandResult
from laptop_inspector.collectors.windows import WindowsCollector


class WindowsCollectorTests(unittest.TestCase):
    def test_collect_battery_healthy(self):
        def mock_executor(args, timeout):
            data = {
                "Name": "Internal Battery",
                "DeviceID": "BAT0",
                "DesignCapacity": 50000,
                "FullChargeCapacity": 45000,
                "EstimatedChargeRemaining": 90,
                "BatteryStatus": 2,  # charging
            }
            return CommandResult(args=args, returncode=0, stdout=json.dumps(data), stderr="", duration_seconds=0.05)

        collector = WindowsCollector(executor=mock_executor)
        battery = collector.collect_battery()

        self.assertIsNotNone(battery)
        self.assertEqual(battery["health_pct"], 90.0)
        self.assertEqual(battery["design_capacity_mwh"], 50000)
        self.assertEqual(battery["full_charge_capacity_mwh"], 45000)
        self.assertTrue(battery["is_charging"])
        self.assertEqual(battery["source"], "windows-cim:Win32_Battery")

    def test_collect_system(self):
        def mock_executor(args, timeout):
            cmd_str = " ".join(args)
            if "Win32_ComputerSystem " in cmd_str or "Win32_ComputerSystem |" in cmd_str:
                data = {"Manufacturer": "Dell Inc.", "Model": "XPS 13 9310"}
            else:
                data = {"SMBIOSBIOSVersion": "2.3.1", "ReleaseDate": "2023-08-15"}
            return CommandResult(args=args, returncode=0, stdout=json.dumps(data), stderr="", duration_seconds=0.05)

        collector = WindowsCollector(executor=mock_executor)
        sys_info = collector.collect_system()

        self.assertEqual(sys_info["vendor"], "Dell Inc.")
        self.assertEqual(sys_info["model"], "XPS 13 9310")
        self.assertEqual(sys_info["bios_version"], "2.3.1")

    def test_collect_cpu(self):
        def mock_executor(args, timeout):
            data = {
                "Name": "11th Gen Intel(R) Core(TM) i7-1165G7",
                "NumberOfCores": 4,
                "NumberOfLogicalProcessors": 8,
                "MaxClockSpeed": 2800,
                "Architecture": 9,  # x86_64
            }
            return CommandResult(args=args, returncode=0, stdout=json.dumps(data), stderr="", duration_seconds=0.05)

        collector = WindowsCollector(executor=mock_executor)
        cpu = collector.collect_cpu()

        self.assertEqual(cpu["cores"], 4)
        self.assertEqual(cpu["threads"], 8)
        self.assertEqual(cpu["architecture"], "x86_64")
        self.assertIn("i7-1165G7", cpu["model"])

    def test_collect_memory(self):
        def mock_executor(args, timeout):
            data = {
                "TotalVisibleMemorySize": 16670868,  # in KB (~16 GB)
                "FreePhysicalMemory": 8000000,
            }
            return CommandResult(args=args, returncode=0, stdout=json.dumps(data), stderr="", duration_seconds=0.05)

        collector = WindowsCollector(executor=mock_executor)
        mem = collector.collect_memory()

        self.assertIsNotNone(mem["total_bytes"])
        self.assertGreater(mem["total_bytes"], 15 * 1024 * 1024 * 1024)

    def test_collect_thermals_kelvin_conversion(self):
        def mock_executor(args, timeout):
            # 3232 tenths of Kelvin = 323.2 K = 50.0 °C
            data = [
                {"InstanceName": "ACPI\\ThermalZone\\TZ01", "CurrentTemperature": 3232},
                {"InstanceName": "ACPI\\ThermalZone\\TZ02", "CurrentTemperature": 3182},  # 45.0 °C
            ]
            return CommandResult(args=args, returncode=0, stdout=json.dumps(data), stderr="", duration_seconds=0.05)

        collector = WindowsCollector(executor=mock_executor)
        thermals = collector.collect_thermals()

        self.assertEqual(thermals["max_temp_c"], 50.0)
        self.assertEqual(thermals["average_temp_c"], 47.5)
        self.assertEqual(len(thermals["zones"]), 2)

    def test_collect_handles_command_failure_gracefully(self):
        def mock_failing_executor(args, timeout):
            return CommandResult(args=args, returncode=1, stdout="", stderr="Access Denied", duration_seconds=0.01)

        collector = WindowsCollector(executor=mock_failing_executor)
        self.assertIsNone(collector.collect_battery())
        thermals = collector.collect_thermals()
        self.assertEqual(thermals["zones"], [])
        self.assertIsNone(thermals["max_temp_c"])


if __name__ == "__main__":
    unittest.main()
