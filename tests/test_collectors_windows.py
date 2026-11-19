"""Unit tests for the Windows hardware collector with synthetic mock execution."""
import json
import unittest

from xflash.collectors.base import CommandResult
from xflash.collectors.windows import WindowsCollector


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

    def test_collect_battery_with_cycle_count_and_status(self):
        def mock_executor(args, timeout):
            cmd = " ".join(args)
            if "BatteryCycleCount" in cmd:
                return CommandResult(args=args, returncode=0, stdout=json.dumps({"CycleCount": 185}), stderr="", duration_seconds=0.01)
            data = {
                "Name": "Primary Battery",
                "DeviceID": "BAT0",
                "DesignCapacity": 60000,
                "FullChargeCapacity": 54000,
                "EstimatedChargeRemaining": 95,
                "BatteryStatus": 2,  # Not charging (AC connected)
            }
            return CommandResult(args=args, returncode=0, stdout=json.dumps(data), stderr="", duration_seconds=0.01)

        collector = WindowsCollector(executor=mock_executor)
        battery = collector.collect_battery()
        self.assertIsNotNone(battery)
        self.assertEqual(battery["cycle_count"], 185)
        self.assertEqual(battery["status"], "Not charging")
        self.assertEqual(battery["health_pct"], 90.0)

    def test_collect_storage_devices_and_reliability_counters(self):
        def mock_executor(args, timeout):
            cmd = " ".join(args)
            if "MSFT_StorageReliabilityCounter" in cmd:
                data = [{"DeviceId": "0", "Temperature": 38, "PowerOnHours": 4500, "ReadErrorsTotal": 0, "WriteErrorsTotal": 0, "Wear": 8}]
                return CommandResult(args=args, returncode=0, stdout=json.dumps(data), stderr="", duration_seconds=0.01)
            data = [{
                "Model": "SAMSUNG MZVL2512HCJQ-00BL7",
                "Size": 512110190592,
                "InterfaceType": "NVMe",
                "DeviceID": "\\\\.\\PHYSICALDRIVE0",
            }]
            return CommandResult(args=args, returncode=0, stdout=json.dumps(data), stderr="", duration_seconds=0.01)

        collector = WindowsCollector(executor=mock_executor)
        storage = collector.collect_storage()
        self.assertIn("devices", storage)
        self.assertEqual(len(storage["devices"]), 1)
        d = storage["devices"][0]
        self.assertEqual(d["model"], "SAMSUNG MZVL2512HCJQ-00BL7")
        self.assertEqual(d["protocol"], "nvme")
        self.assertEqual(d["nvme_percentage_used"], 8)
        self.assertEqual(d["temperature_c"], 38)
        self.assertEqual(d["power_on_hours"], 4500)
        self.assertEqual(d["media_errors"], 0)

    def test_collect_ac_adapter(self):
        def mock_executor(args, timeout):
            data = {"PowerOnline": True}
            return CommandResult(args=args, returncode=0, stdout=json.dumps(data), stderr="", duration_seconds=0.01)

        collector = WindowsCollector(executor=mock_executor)
        ac = collector.collect_ac_adapter()
        self.assertTrue(ac["online"])
        self.assertEqual(ac["name"], "AC Adapter")

    def test_collect_display_edid_and_diagonal(self):
        def mock_executor(args, timeout):
            cmd = " ".join(args)
            if "WmiMonitorID" in cmd:
                # ASCII for "SDC" and "ATNA56YX03-0"
                data = {
                    "ManufacturerName": [83, 68, 67],
                    "UserFriendlyName": [65, 84, 78, 65, 53, 54, 89, 88, 48, 51, 45, 48],
                }
                return CommandResult(args=args, returncode=0, stdout=json.dumps(data), stderr="", duration_seconds=0.01)
            if "WmiMonitorBasicDisplayParams" in cmd:
                data = {"MaxHorizontalImageSize": 34, "MaxVerticalImageSize": 19}
                return CommandResult(args=args, returncode=0, stdout=json.dumps(data), stderr="", duration_seconds=0.01)
            data = {"CurrentHorizontalResolution": 1920, "CurrentVerticalResolution": 1080, "CurrentRefreshRate": 60}
            return CommandResult(args=args, returncode=0, stdout=json.dumps(data), stderr="", duration_seconds=0.01)

        collector = WindowsCollector(executor=mock_executor)
        disp = collector.collect_display()
        self.assertEqual(disp["resolution"], "1920x1080")
        self.assertEqual(disp["edid"]["manufacturer"], "SDC")
        self.assertEqual(disp["edid"]["model_name"], "ATNA56YX03-0")
        self.assertEqual(disp["edid"]["diagonal_inches"], 15.3)

    def test_windows_snapshot_full_analysis_and_tui_adapter(self):
        from xflash.analysis import analyze_snapshot
        from xflash.tui.adapter import to_session

        def mock_win_exec(args, timeout):
            cmd = " ".join(args)
            if "Win32_Battery" in cmd:
                data = {"Name": "Internal Battery", "DeviceID": "BAT0", "DesignCapacity": 50000, "FullChargeCapacity": 45000, "EstimatedChargeRemaining": 90, "BatteryStatus": 2}
            elif "BatteryCycleCount" in cmd:
                data = {"CycleCount": 120}
            elif "Win32_ComputerSystem " in cmd or "Win32_ComputerSystem |" in cmd:
                data = {"Manufacturer": "Lenovo", "Model": "ThinkPad X1"}
            elif "Win32_BIOS" in cmd:
                data = {"SMBIOSBIOSVersion": "1.30", "ReleaseDate": "2023-01-01"}
            elif "Win32_Processor" in cmd:
                data = {"Name": "12th Gen Intel Core i7", "NumberOfCores": 10, "NumberOfLogicalProcessors": 12, "MaxClockSpeed": 2400, "Architecture": 9}
            elif "Win32_OperatingSystem" in cmd:
                data = {"TotalVisibleMemorySize": 16670868, "FreePhysicalMemory": 8000000, "Caption": "Microsoft Windows 11", "Version": "10.0.22631", "BuildNumber": "22631", "OSArchitecture": "64-bit"}
            elif "Win32_DiskDrive" in cmd:
                data = [{"Model": "NVMe Drive 512GB", "Size": 512110190592, "InterfaceType": "NVMe", "DeviceID": "\\\\.\\PHYSICALDRIVE0"}]
            elif "MSFT_StorageReliabilityCounter" in cmd:
                data = [{"DeviceId": "0", "Temperature": 35, "PowerOnHours": 2000, "ReadErrorsTotal": 0, "WriteErrorsTotal": 0, "Wear": 5}]
            elif "MSAcpi_ThermalZoneTemperature" in cmd:
                data = [{"InstanceName": "TZ0", "CurrentTemperature": 3182}]
            elif "WmiMonitorID" in cmd:
                data = {"ManufacturerName": [76, 71], "UserFriendlyName": [80, 97, 110, 101, 108]}
            elif "WmiMonitorBasicDisplayParams" in cmd:
                data = {"MaxHorizontalImageSize": 31, "MaxVerticalImageSize": 17}
            elif "Win32_VideoController" in cmd:
                data = {"CurrentHorizontalResolution": 1920, "CurrentVerticalResolution": 1080, "CurrentRefreshRate": 60}
            else:
                data = {}
            return CommandResult(args=args, returncode=0, stdout=json.dumps(data), stderr="", duration_seconds=0.01)

        collector = WindowsCollector(executor=mock_win_exec)
        snap = collector.collect_snapshot({"model": "ThinkPad X1", "ram_gib": 16, "storage_capacity_gb": 512})
        rep = analyze_snapshot(snap)
        sess = to_session(snap, rep)

        self.assertIn("ThinkPad X1", sess.title)
        self.assertEqual(sess.verdict_status.value, "pass")
        bay_names = [b.name for b in sess.bays]
        self.assertEqual(bay_names, ["BAT", "SSD", "MEM", "CPU", "FAN", "DSP"])
        # Both BAT and SSD bays must be Status.PASS
        bat_bay = next(b for b in sess.bays if b.name == "BAT")
        ssd_bay = next(b for b in sess.bays if b.name == "SSD")
        self.assertEqual(bat_bay.status.value, "pass")
        self.assertEqual(ssd_bay.status.value, "pass")


if __name__ == "__main__":
    unittest.main()
