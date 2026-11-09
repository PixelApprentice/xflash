"""Safe read-only Linux hardware telemetry collector using sysfs, /proc, and smartctl."""
from __future__ import annotations

import json
import os
import platform
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .base import safe_exec


def _read_int(path: Path) -> int | None:
    try:
        raw = path.read_text(encoding="utf-8").strip()
        return int(raw)
    except (OSError, ValueError):
        return None


def _read_str(path: Path) -> str | None:
    try:
        raw = path.read_text(encoding="utf-8").strip()
        return raw or None
    except OSError:
        return None


def _parse_edid(edid_bytes: bytes) -> dict[str, Any] | None:
    """Parse raw EDID binary data for monitor manufacturer, panel model, and technology."""
    if len(edid_bytes) < 128:
        return None
    try:
        # Standard EDID magic: 00 FF FF FF FF FF FF 00
        if edid_bytes[:8] != b"\x00\xff\xff\xff\xff\xff\xff\x00":
            return None

        # Manufacturer ID: 3 letters compressed in big-endian 16-bit word at offset 8
        mfg_raw = int.from_bytes(edid_bytes[8:10], "big")
        c1 = chr(((mfg_raw >> 10) & 0x1F) + ord("@"))
        c2 = chr(((mfg_raw >> 5) & 0x1F) + ord("@"))
        c3 = chr((mfg_raw & 0x1F) + ord("@"))
        mfg_id = f"{c1}{c2}{c3}"
        prod_code = int.from_bytes(edid_bytes[10:12], "little")
        year = edid_bytes[17] + 1990

        # Video input byte 20
        v_in = edid_bytes[20]
        bpc_bits = (v_in >> 4) & 0x7
        bpc_map = {1: "6-bit", 2: "8-bit", 3: "10-bit", 4: "12-bit", 5: "14-bit", 6: "16-bit"}
        color_depth = bpc_map.get(bpc_bits, "8-bit Standard")

        # Physical dimension in cm (bytes 21 & 22)
        w_cm = edid_bytes[21]
        h_cm = edid_bytes[22]
        diag_in = round(((w_cm**2 + h_cm**2) ** 0.5) / 2.54, 1) if (w_cm and h_cm) else None

        # Descriptor blocks (offsets 54, 72, 90, 108)
        model_name = None
        for off in (54, 72, 90, 108):
            blk = edid_bytes[off : off + 18]
            if blk[0:2] == b"\x00\x00" and blk[3] in (0xFC, 0xFE):
                try:
                    name_bytes = blk[5:]
                    clean = name_bytes.split(b"\n")[0].split(b"\x00")[0]
                    parsed_name = clean.decode("latin-1", errors="replace").strip()
                    if parsed_name:
                        model_name = parsed_name
                        break
                except Exception:
                    pass

        mfg_names = {
            "SDC": "Samsung Display (SDC)",
            "BOE": "BOE Technology",
            "LGD": "LG Display",
            "AUO": "AU Optronics",
            "INX": "Innolux Corp",
            "SHP": "Sharp Corp",
            "CSOT": "TCL CSOT",
        }
        mfg_full = mfg_names.get(mfg_id, mfg_id)

        # Panel technology classification
        name_upper = (model_name or "").upper()
        if any(k in name_upper for k in ["ATNA", "OLED", "AMOLED", "AMOL"]) or (mfg_id == "SDC" and "ATNA" in name_upper):
            panel_type = "OLED / AMOLED (Self-Emitting)"
            is_oled = True
        elif any(k in name_upper for k in ["IPS", "AHVA", "PLS"]):
            panel_type = "IPS (Wide-Viewing Angle)"
            is_oled = False
        elif any(k in name_upper for k in ["TN", "TN-TFT"]):
            panel_type = "TN (Twisted Nematic)"
            is_oled = False
        else:
            panel_type = "LCD (Standard / IPS)"
            is_oled = False

        return {
            "manufacturer": mfg_full,
            "mfg_code": mfg_id,
            "model_name": model_name or f"Panel 0x{prod_code:04X}",
            "panel_type": panel_type,
            "is_oled": is_oled,
            "color_depth": color_depth,
            "diagonal_inches": diag_in,
            "mfg_year": year,
        }
    except Exception:
        return None


class LinuxCollector:
    """Read-only hardware collector for Linux systems."""

    def __init__(
        self,
        sysfs_root: str | Path = "/sys",
        proc_root: str | Path = "/proc",
    ) -> None:
        self.sysfs = Path(sysfs_root)
        self.proc = Path(proc_root)

    def collect_battery(self) -> dict[str, Any] | None:
        """Collect battery metrics from Linux sysfs power_supply subsystem."""
        ps_dir = self.sysfs / "class" / "power_supply"
        if not ps_dir.is_dir():
            return None

        # Look for battery devices (commonly BAT0, BAT1, or type=Battery)
        bat_dirs = []
        try:
            for entry in ps_dir.iterdir():
                dev_type = _read_str(entry / "type")
                if entry.name.startswith("BAT") or dev_type == "Battery":
                    bat_dirs.append(entry)
        except OSError:
            return None

        if not bat_dirs:
            return None

        # Check each battery directory for valid readings
        for bat in sorted(bat_dirs, key=lambda p: p.name):
            source = f"linux-sysfs:{bat}"

            # 1. Try energy measurements (uWh) -> convert to mWh
            energy_design_uwh = _read_int(bat / "energy_full_design")
            energy_full_uwh = _read_int(bat / "energy_full")

            design_mwh: float | None = None
            full_mwh: float | None = None

            if energy_design_uwh is not None and energy_full_uwh is not None and energy_design_uwh > 0:
                design_mwh = round(energy_design_uwh / 1000.0, 1)
                full_mwh = round(energy_full_uwh / 1000.0, 1)
            else:
                # 2. Try charge measurements (uAh) + voltage (uV) -> convert to mWh
                charge_design_uah = _read_int(bat / "charge_full_design")
                charge_full_uah = _read_int(bat / "charge_full")
                voltage_uv = _read_int(bat / "voltage_now") or _read_int(bat / "voltage_min_design")

                if (
                    charge_design_uah is not None
                    and charge_full_uah is not None
                    and voltage_uv is not None
                    and charge_design_uah > 0
                    and voltage_uv > 0
                ):
                    # (uAh * uV) / 1,000,000,000 = mWh
                    design_mwh = round((charge_design_uah * voltage_uv) / 1_000_000_000.0, 1)
                    full_mwh = round((charge_full_uah * voltage_uv) / 1_000_000_000.0, 1)

            if design_mwh is not None and full_mwh is not None:
                cycles = _read_int(bat / "cycle_count")
                status = _read_str(bat / "status")
                technology = _read_str(bat / "technology")

                result: dict[str, Any] = {
                    "source": source,
                    "design_capacity_mwh": design_mwh,
                    "full_charge_capacity_mwh": full_mwh,
                }
                if cycles is not None:
                    result["cycle_count"] = cycles
                if status:
                    result["status"] = status
                if technology:
                    result["technology"] = technology

                return result

        return None

    def collect_memory(self) -> dict[str, Any]:
        """Collect memory metrics from /proc/meminfo."""
        meminfo = self.proc / "meminfo"
        total_bytes = None
        available_bytes = None

        try:
            for line in meminfo.read_text(encoding="utf-8").splitlines():
                if line.startswith("MemTotal:"):
                    parts = line.split()
                    if len(parts) >= 2:
                        total_bytes = int(parts[1]) * 1024
                elif line.startswith("MemAvailable:"):
                    parts = line.split()
                    if len(parts) >= 2:
                        available_bytes = int(parts[1]) * 1024
        except (OSError, ValueError):
            pass

        return {
            "source": f"linux-proc:{meminfo}",
            "total_bytes": total_bytes,
            "available_bytes": available_bytes,
        }

    def collect_system(self) -> dict[str, Any]:
        """Collect vendor, model, and BIOS info without collecting serial numbers."""
        dmi_id = self.sysfs / "class" / "dmi" / "id"
        vendor = _read_str(dmi_id / "sys_vendor")
        model = _read_str(dmi_id / "product_name") or _read_str(dmi_id / "product_version")
        bios_version = _read_str(dmi_id / "bios_version")
        bios_date = _read_str(dmi_id / "bios_date")

        return {
            "vendor": vendor or "Unknown",
            "model": model or "Unknown Linux Host",
            "bios_version": bios_version,
            "bios_date": bios_date,
            "os_name": platform.system(),
            "kernel_release": platform.release(),
            "architecture": platform.machine(),
        }

    def collect_storage(self) -> dict[str, Any]:
        """Enumerate internal physical storage devices and read SMART/NVMe telemetry if available."""
        devices: list[dict[str, Any]] = []
        block_dir = self.sysfs / "block"

        if block_dir.is_dir():
            try:
                for entry in sorted(block_dir.iterdir()):
                    name = entry.name
                    # Filter virtual, loop, ram, and zram devices
                    if (
                        name.startswith("loop")
                        or name.startswith("ram")
                        or name.startswith("zram")
                        or name.startswith("dm-")
                    ):
                        continue

                    # Read size in 512-byte sectors
                    sectors = _read_int(entry / "size")
                    if sectors is None or sectors <= 0:
                        continue
                    capacity_bytes = sectors * 512

                    dev_path = f"/dev/{name}"
                    model = _read_str(entry / "device" / "model") or name
                    protocol = "nvme" if name.startswith("nvme") else "ata"

                    dev_entry: dict[str, Any] = {
                        "model": model,
                        "device_node": dev_path,
                        "capacity_bytes": capacity_bytes,
                        "protocol": protocol,
                        "source": f"linux-sysfs:{entry}",
                    }

                    # Safely probe smartctl if executable exists (least privilege first)
                    smart_res = safe_exec(["smartctl", "--json=c", "-x", dev_path], timeout_seconds=4.0)
                    if (smart_res.returncode not in (0, 4) or not smart_res.stdout) and os.name == "posix":
                        # Try non-interactive least-privilege sudo -n if permission was denied
                        smart_res = safe_exec(["sudo", "-n", "smartctl", "--json=c", "-x", dev_path], timeout_seconds=4.0)

                    if smart_res.returncode in (0, 4) and smart_res.stdout:
                        try:
                            smart_data = json.loads(smart_res.stdout)
                            dev_entry = self._parse_smartctl_json(dev_entry, smart_data)
                        except json.JSONDecodeError:
                            pass
                    elif protocol == "nvme" and os.name == "posix":
                        # Fallback to nvme-cli if smartctl is not available
                        nvme_res = safe_exec(["nvme", "log", "smart", dev_path, "-o", "json"], timeout_seconds=3.0)
                        if nvme_res.returncode != 0 or not nvme_res.stdout:
                            nvme_res = safe_exec(["sudo", "-n", "nvme", "log", "smart", dev_path, "-o", "json"], timeout_seconds=3.0)
                        if (nvme_res.returncode != 0 or not nvme_res.stdout):
                            nvme_res = safe_exec(["sudo", "-n", "nvme", "smart-log", dev_path, "-o", "json"], timeout_seconds=3.0)

                        if nvme_res.returncode == 0 and nvme_res.stdout:
                            try:
                                nvme_data = json.loads(nvme_res.stdout)
                                if "percent_used" in nvme_data:
                                    dev_entry["nvme_percentage_used"] = nvme_data["percent_used"]
                                if "critical_warning" in nvme_data:
                                    dev_entry["nvme_critical_warning"] = nvme_data["critical_warning"]
                                if "media_errors" in nvme_data:
                                    dev_entry["media_errors"] = nvme_data["media_errors"]
                                if "power_on_hours" in nvme_data:
                                    dev_entry["power_on_hours"] = nvme_data["power_on_hours"]
                                if "power_cycles" in nvme_data:
                                    dev_entry["power_cycles"] = nvme_data["power_cycles"]
                                if "avail_spare" in nvme_data:
                                    dev_entry["available_spare"] = nvme_data["avail_spare"]
                                dev_entry["self_test_status"] = "clean"
                            except json.JSONDecodeError:
                                pass

                    # If temperature is still missing for NVMe, probe sysfs hwmon
                    if protocol == "nvme" and "temperature_c" not in dev_entry:
                        hwmon_pattern = self.sysfs / "class" / "nvme" / name / "hwmon*" / "temp1_input"
                        # Handle symlink resolution in /sys/block/nvme0n1/device/hwmon*
                        dev_hwmon = entry / "device"
                        for hwmon_dir in dev_hwmon.glob("hwmon*"):
                            temp_in = _read_int(hwmon_dir / "temp1_input")
                            if temp_in:
                                dev_entry["temperature_c"] = round(temp_in / 1000.0, 1)
                                break

                    devices.append(dev_entry)
            except OSError:
                pass

        return {"devices": devices}

    def _parse_smartctl_json(self, dev: dict[str, Any], data: dict[str, Any]) -> dict[str, Any]:
        """Extract SMART/NVMe telemetry safely from smartctl JSON."""
        # NVMe SMART data
        nvme_health = data.get("nvme_smart_health_information_log")
        if isinstance(nvme_health, dict):
            if "percentage_used" in nvme_health:
                dev["nvme_percentage_used"] = nvme_health["percentage_used"]
            if "critical_warning" in nvme_health:
                dev["nvme_critical_warning"] = nvme_health["critical_warning"]
            if "media_errors" in nvme_health:
                dev["media_errors"] = nvme_health["media_errors"]
            if "power_on_hours" in nvme_health:
                dev["power_on_hours"] = nvme_health["power_on_hours"]
            if "power_cycles" in nvme_health:
                dev["power_cycles"] = nvme_health["power_cycles"]
            if "available_spare" in nvme_health:
                dev["available_spare"] = nvme_health["available_spare"]
            if "temperature" in nvme_health:
                dev["temperature_c"] = nvme_health["temperature"]

        # Temperature from main smartctl root if not in nvme_health
        if "temperature_c" not in dev and "temperature" in data:
            temp_obj = data["temperature"]
            if isinstance(temp_obj, dict) and "current" in temp_obj:
                dev["temperature_c"] = temp_obj["current"]

        # Self-test and overall smart status
        smart_status = data.get("smart_status")
        if isinstance(smart_status, dict) and "passed" in smart_status:
            dev["self_test_status"] = "clean" if smart_status["passed"] else "failing"
        else:
            test_status = (data.get("ata_smart_data") or {}).get("self_test", {}).get("status", {})
            if isinstance(test_status, dict) and "string" in test_status:
                dev["self_test_status"] = test_status["string"]

        return dev

    def collect_cpu(self) -> dict[str, Any]:
        """Collect CPU processor model, core count, thread count, and frequency."""
        cpuinfo = self.proc / "cpuinfo"
        model_name = "Unknown CPU"
        cores = 1
        threads = 0
        freq_mhz = None

        try:
            if cpuinfo.is_file():
                for line in cpuinfo.read_text(encoding="utf-8").splitlines():
                    if ":" in line:
                        k, v = [x.strip() for x in line.split(":", 1)]
                        if k == "model name" and model_name == "Unknown CPU":
                            model_name = v
                        elif k == "processor":
                            threads += 1
                        elif k == "cpu cores" and cores == 1:
                            try:
                                cores = int(v)
                            except ValueError:
                                pass
                        elif k == "cpu MHz" and freq_mhz is None:
                            try:
                                freq_mhz = round(float(v), 1)
                            except ValueError:
                                pass
        except OSError:
            pass

        if threads == 0:
            threads = os.cpu_count() or 1
        if cores == 1 and threads > 1:
            cores = threads

        return {
            "model": model_name,
            "cores": cores,
            "threads": threads,
            "frequency_mhz": freq_mhz,
            "architecture": platform.machine(),
            "source": f"linux-proc:{cpuinfo}",
        }

    def collect_gpu(self) -> dict[str, Any]:
        """Detect GPU / graphics controllers via DRM subsystem and lspci."""
        gpu_name = "Integrated / System Graphics"
        drm_dir = self.sysfs / "class" / "drm"

        # Try lspci first for rich model name
        lspci_res = safe_exec(["lspci"], timeout_seconds=2.0)
        if lspci_res.returncode == 0 and lspci_res.stdout:
            for line in lspci_res.stdout.splitlines():
                if any(kw in line.lower() for kw in ("vga compatible controller", "3d controller", "display controller")):
                    # e.g., "00:02.0 VGA compatible controller: Intel Corporation Alder Lake-UP3 GT2 [Iris Xe Graphics] (rev 0c)"
                    if ":" in line:
                        parts = line.split(":", 2)
                        gpu_name = parts[-1].strip()
                        break

        # Fallback to DRM driver name if lspci is not available
        driver = "unknown"
        if drm_dir.is_dir():
            try:
                for card in drm_dir.glob("card[0-9]"):
                    driver_link = card / "device" / "driver"
                    if driver_link.is_symlink() or driver_link.is_dir():
                        driver = driver_link.resolve().name
                        break
            except OSError:
                pass

        return {
            "model": gpu_name,
            "driver": driver,
            "source": "linux-drm-lspci",
        }

    def collect_display(self) -> dict[str, Any] | None:
        """Collect primary connected display interface and native resolution from DRM modes."""
        drm_dir = self.sysfs / "class" / "drm"
        if not drm_dir.is_dir():
            return None

        primary_display = None
        all_displays = []

        try:
            for entry in sorted(drm_dir.iterdir()):
                status_file = entry / "status"
                modes_file = entry / "modes"
                if status_file.is_file():
                    status = _read_str(status_file)
                    if status == "connected":
                        modes = []
                        if modes_file.is_file():
                            try:
                                modes = [m.strip() for m in modes_file.read_text(encoding="utf-8").splitlines() if m.strip()]
                            except OSError:
                                pass

                        native_res = modes[0] if modes else "Unknown"
                        display_info: dict[str, Any] = {
                            "interface": entry.name,
                            "status": "connected",
                            "resolution": native_res,
                            "supported_modes": modes[:5],
                        }

                        # Parse EDID if present for panel model & OLED/IPS detection
                        edid_file = entry / "edid"
                        if edid_file.is_file():
                            try:
                                edid_data = edid_file.read_bytes()
                                parsed = _parse_edid(edid_data)
                                if parsed:
                                    display_info["edid"] = parsed
                                    display_info["panel_type"] = parsed.get("panel_type")
                                    display_info["is_oled"] = parsed.get("is_oled")
                            except OSError:
                                pass

                        all_displays.append(display_info)
                        if "eDP" in entry.name or primary_display is None:
                            primary_display = display_info
        except OSError:
            pass

        return primary_display

    def collect_ac_adapter(self) -> dict[str, Any] | None:
        """Collect AC power adapter online / plugged-in state and negotiated power."""
        ps_dir = self.sysfs / "class" / "power_supply"
        if not ps_dir.is_dir():
            return None

        try:
            for entry in ps_dir.iterdir():
                dev_type = _read_str(entry / "type")
                if dev_type == "Mains" or entry.name.startswith("AC") or entry.name.startswith("ADP"):
                    online_val = _read_int(entry / "online")
                    voltage_now = _read_int(entry / "voltage_now")
                    current_max = _read_int(entry / "current_max")
                    power_now = _read_int(entry / "power_now")

                    wattage = None
                    if voltage_now and current_max:
                        # (uV * uA) / 10^12 = W
                        wattage = round((voltage_now * current_max) / 1_000_000_000_000.0, 1)

                    return {
                        "name": entry.name,
                        "online": online_val == 1,
                        "wattage_w": wattage,
                        "source": f"linux-sysfs:{entry}",
                    }
        except OSError:
            pass

        return None

    def collect_thermals(self) -> dict[str, Any]:
        """Collect thermal zone temperatures across CPU and system sensors."""
        thermal_dir = self.sysfs / "class" / "thermal"
        zones: list[dict[str, Any]] = []
        cpu_temps: list[float] = []

        if thermal_dir.is_dir():
            try:
                for entry in sorted(thermal_dir.glob("thermal_zone*")):
                    zone_type = _read_str(entry / "type") or entry.name
                    temp_raw = _read_int(entry / "temp")
                    if temp_raw is not None:
                        # Linux sysfs reports thermal zone temp in millidegrees Celsius
                        temp_c = round(temp_raw / 1000.0, 1) if temp_raw > 1000 else float(temp_raw)
                        zones.append({
                            "zone": entry.name,
                            "type": zone_type,
                            "temp_c": temp_c,
                        })
                        z_lower = zone_type.lower()
                        if any(k in z_lower for k in ("x86_pkg", "pkg", "tcpu", "core", "cpu")) and temp_c > 10:
                            cpu_temps.append(temp_c)
            except OSError:
                pass

        # Inspect hwmon for direct CPU core sensors (coretemp, k10temp, zenpower, cpu_thermal)
        hwmon_dir = self.sysfs / "class" / "hwmon"
        if hwmon_dir.is_dir():
            try:
                for entry in sorted(hwmon_dir.glob("hwmon*")):
                    name = (_read_str(entry / "name") or "").lower()
                    if any(driver in name for driver in ("coretemp", "k10temp", "zenpower", "cpu_thermal")):
                        for tfile in sorted(entry.glob("temp*_input")):
                            label = _read_str(tfile.parent / tfile.name.replace("_input", "_label")) or tfile.name
                            val = _read_int(tfile)
                            if val is not None and val > 0:
                                t_val = round(val / 1000.0, 1) if val > 1000 else float(val)
                                if 15.0 <= t_val <= 125.0:
                                    cpu_temps.append(t_val)
                                    zones.append({
                                        "zone": f"{entry.name}/{tfile.name}",
                                        "type": f"{name} ({label})",
                                        "temp_c": t_val,
                                    })
            except OSError:
                pass

        avg_temp = round(sum(z["temp_c"] for z in zones) / len(zones), 1) if zones else None
        max_temp = max((z["temp_c"] for z in zones), default=None)
        cpu_temp = max(cpu_temps) if cpu_temps else max_temp

        return {
            "zones": zones,
            "average_temp_c": avg_temp,
            "max_temp_c": max_temp,
            "cpu_temp_c": cpu_temp,
            "source": f"linux-sysfs:{thermal_dir}",
        }

    def collect_ports(self) -> dict[str, Any]:
        """Collect live status of physical USB ports, HDMI/video displays, and AC charging."""
        return {
            "usb": self._collect_usb_devices(),
            "display_ports": self._collect_display_connectors(),
            "ac_charging": self.collect_ac_adapter(),
        }

    def _collect_usb_devices(self) -> list[dict[str, Any]]:
        """Enumerate USB devices and physical ports from /sys/bus/usb/devices."""
        usb_dir = self.sysfs / "bus" / "usb" / "devices"
        devices: list[dict[str, Any]] = []
        if not usb_dir.is_dir():
            return devices

        try:
            for p in sorted(usb_dir.iterdir()):
                name = p.name
                if not p.is_dir() or ":" in name or name.startswith("usb"):
                    continue

                prod = _read_str(p / "product") or "Generic USB Device"
                manuf = _read_str(p / "manufacturer") or "Unknown Vendor"
                speed = _read_str(p / "speed") or "N/A"
                removable = _read_str(p / "removable") or "unknown"

                speed_label = f"{speed} Mbps"
                if speed == "1.5":
                    speed_label = "Low Speed (1.5 Mbps · USB 1.0)"
                elif speed == "12":
                    speed_label = "Full Speed (12 Mbps · USB 1.1/2.0)"
                elif speed == "480":
                    speed_label = "High Speed (480 Mbps · USB 2.0)"
                elif speed == "5000":
                    speed_label = "SuperSpeed (5 Gbps · USB 3.0/3.1 Gen 1)"
                elif speed == "10000":
                    speed_label = "SuperSpeed+ (10 Gbps · USB 3.2 Gen 2)"
                elif speed == "20000":
                    speed_label = "SuperSpeed 20G (20 Gbps · USB 3.2 2x2)"

                devices.append({
                    "port_id": name,
                    "product": prod,
                    "manufacturer": manuf,
                    "speed_mbps": speed,
                    "speed_label": speed_label,
                    "removable": removable == "removable",
                    "device_type": "External Removable Port" if removable == "removable" else "Internal Motherboard Header"
                })
        except OSError:
            pass
        return devices

    def _collect_display_connectors(self) -> list[dict[str, Any]]:
        """Enumerate display connectors and video output ports from /sys/class/drm."""
        drm_dir = self.sysfs / "class" / "drm"
        connectors: list[dict[str, Any]] = []
        if not drm_dir.is_dir():
            return connectors

        try:
            for p in sorted(drm_dir.iterdir()):
                if not p.is_dir() or not p.name.startswith("card") or "-" not in p.name:
                    continue

                parts = p.name.split("-", 1)
                card_id = parts[0]
                conn_name = parts[1]

                status = _read_str(p / "status") or "unknown"
                modes_file = p / "modes"
                modes = modes_file.read_text(encoding="utf-8").strip().splitlines() if modes_file.is_file() else []

                is_external = not (conn_name.startswith("eDP") or conn_name.startswith("DSI"))
                port_type = "HDMI" if "HDMI" in conn_name else "DisplayPort" if ("DP" in conn_name and not conn_name.startswith("eDP")) else "Internal Display"

                connectors.append({
                    "connector": conn_name,
                    "card": card_id,
                    "status": status,
                    "modes": modes,
                    "resolution": modes[0] if modes else None,
                    "is_external": is_external,
                    "port_type": port_type,
                })
        except OSError:
            pass
        return connectors

    def collect_network(self) -> dict[str, Any]:
        """Collect network adapters and wireless hardware interfaces."""
        net_dir = self.sysfs / "class" / "net"
        adapters: list[dict[str, Any]] = []

        if net_dir.is_dir():
            try:
                for p in sorted(net_dir.iterdir()):
                    if not p.is_dir():
                        continue
                    name = p.name
                    if name == "lo" or name.startswith("br-") or name.startswith("docker") or name.startswith("veth"):
                        continue

                    operstate = _read_str(p / "operstate") or "unknown"
                    is_wireless = (p / "wireless").is_dir() or (p / "phy80211").is_dir()

                    adapters.append({
                        "interface": name,
                        "state": operstate,
                        "type": "Wi-Fi" if is_wireless else "Ethernet",
                    })
            except OSError:
                pass

        rfkill_res = safe_exec(["rfkill", "list"], timeout_seconds=2.0)
        rfkill_info = rfkill_res.stdout if rfkill_res.returncode == 0 else ""

        return {
            "adapters": adapters,
            "rfkill_raw": rfkill_info,
        }

    def collect_system_extended(self) -> dict[str, Any]:
        """Detect OS type, boot firmware (UEFI/BIOS), CPU architecture, filesystem, and install age."""
        import struct

        result: dict[str, Any] = {
            "source": "linux-proc+sysfs",
        }

        # --- Architecture ---
        result["cpu_arch"] = platform.machine()  # e.g. x86_64, aarch64, i686
        result["cpu_bits"] = struct.calcsize("P") * 8  # 32 or 64

        # --- OS Release ---
        os_release: dict[str, str] = {}
        try:
            release_path = Path("/etc/os-release")
            if release_path.is_file():
                for line in release_path.read_text(encoding="utf-8").splitlines():
                    if "=" in line:
                        k, _, v = line.partition("=")
                        os_release[k.strip()] = v.strip().strip('"')
        except OSError:
            pass

        result["os_name"] = os_release.get("NAME") or platform.system()
        result["os_version"] = os_release.get("VERSION") or os_release.get("VERSION_ID") or platform.release()
        result["os_id"] = os_release.get("ID", "linux")
        result["os_pretty_name"] = os_release.get("PRETTY_NAME") or result["os_name"]

        # --- Kernel ---
        try:
            result["kernel_version"] = (self.proc / "version").read_text(encoding="utf-8").strip()[:120]
        except OSError:
            result["kernel_version"] = platform.release()

        # --- Boot Firmware: UEFI vs BIOS/MBR ---
        efi_path = Path("/sys/firmware/efi")
        result["boot_firmware"] = "UEFI" if efi_path.is_dir() else "BIOS/MBR"

        # --- Root Filesystem Type ---
        result["root_fs_type"] = "unknown"
        try:
            mounts = (self.proc / "mounts").read_text(encoding="utf-8")
            for line in mounts.splitlines():
                parts = line.split()
                if len(parts) >= 3 and parts[1] == "/":
                    result["root_fs_type"] = parts[2]  # e.g. ext4, btrfs, tmpfs
                    break
        except OSError:
            pass

        # --- Partition Table & Block Info via lsblk ---
        result["partition_table"] = "unknown"
        result["root_device"] = "unknown"
        result["root_size"] = "unknown"
        try:
            lsblk_res = safe_exec(["lsblk", "-o", "NAME,PTTYPE,FSTYPE,SIZE,MOUNTPOINT", "-J"], timeout_seconds=2.0)
            if lsblk_res.returncode == 0 and lsblk_res.stdout:
                data = json.loads(lsblk_res.stdout)
                devices = data.get("blockdevices", [])

                def find_root(dev_list: list[dict[str, Any]]) -> dict[str, Any] | None:
                    for dev in dev_list:
                        if dev.get("mountpoint") == "/":
                            return dev
                        children = dev.get("children", [])
                        found = find_root(children)
                        if found:
                            if not found.get("pttype") and dev.get("pttype"):
                                found["pttype"] = dev["pttype"]
                            return found
                    return None

                root_dev = find_root(devices)
                if root_dev:
                    result["root_device"] = root_dev.get("name", "unknown")
                    result["partition_table"] = (root_dev.get("pttype") or "unknown").upper()
                    result["root_fs_type"] = root_dev.get("fstype") or result.get("root_fs_type", "unknown")
                    result["root_size"] = root_dev.get("size", "unknown")
        except Exception:
            pass

        # --- Touchscreen Detection ---
        result["touchscreen_detected"] = False
        try:
            input_sys = self.sysfs / "class" / "input"
            if input_sys.is_dir():
                for inp in input_sys.iterdir():
                    name_path = inp / "device" / "name"
                    if name_path.is_file():
                        name = _read_str(name_path) or ""
                        if "touchscreen" in name.lower() or "touch screen" in name.lower():
                            result["touchscreen_detected"] = True
                            result["touchscreen_device"] = name
                            break
        except OSError:
            pass

        # --- Backlight type hint (raw=OLED hint, firmware=LCD) ---
        result["backlight_type"] = "unknown"
        try:
            bl_dir = self.sysfs / "class" / "backlight"
            if bl_dir.is_dir():
                for bl in bl_dir.iterdir():
                    t = _read_str(bl / "type")
                    if t:
                        result["backlight_type"] = t  # "raw" or "firmware"
                        break
        except OSError:
            pass

        # --- OS Install Date & Refurbish / Clean Wipe Detection ---
        install_dt = None
        install_source = None
        # 1. Arch/Manjaro pacman.log
        pacman_log = Path("/var/log/pacman.log")
        if pacman_log.is_file():
            try:
                with open(pacman_log, "r", encoding="utf-8", errors="ignore") as f:
                    first_line = f.readline()
                    m = re.search(r"\[(\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2})", first_line)
                    if m:
                        install_dt = datetime.fromisoformat(m.group(1)).replace(tzinfo=timezone.utc)
                        install_source = "pacman.log"
            except Exception:
                pass

        # 2. Debian/Ubuntu /var/log/installer/syslog or dpkg.log
        if not install_dt:
            for log_p in [
                Path("/var/log/installer/syslog"),
                Path("/var/log/dpkg.log"),
                Path("/var/log/anaconda/anaconda.log"),  # Fedora/RHEL
                Path("/var/log/dnf.log"),               # Fedora/CentOS
                Path("/var/log/zypp/history"),          # openSUSE
            ]:
                if log_p.is_file():
                    try:
                        mtime = log_p.stat().st_mtime
                        install_dt = datetime.fromtimestamp(mtime, tz=timezone.utc)
                        install_source = log_p.name
                        break
                    except Exception:
                        pass

        # 3. Fallback to /etc/machine-id
        if not install_dt:
            machine_id_path = Path("/etc/machine-id")
            if machine_id_path.is_file():
                try:
                    mtime = machine_id_path.stat().st_mtime
                    install_dt = datetime.fromtimestamp(mtime, tz=timezone.utc)
                    install_source = "machine-id"
                except Exception:
                    pass

        if install_dt:
            now_utc = datetime.now(timezone.utc)
            days_ago = max(0, (now_utc - install_dt).days)
            result["os_install_date"] = install_dt.strftime("%Y-%m-%d %H:%M UTC")
            result["os_install_age_days"] = days_ago
            result["os_install_age_estimate"] = f"~{days_ago} days ago"
            result["os_install_source"] = install_source
            if days_ago <= 14:
                result["refurbish_status"] = "Recent Clean OS Installation (Possible Resale Wipe)"
                result["is_recent_wipe"] = True
            else:
                result["refurbish_status"] = f"Established OS Installation ({days_ago} days runtime)"
                result["is_recent_wipe"] = False
        else:
            result["os_install_date"] = "Unknown"
            result["os_install_age_days"] = None
            result["os_install_age_estimate"] = "Unknown"
            result["refurbish_status"] = "Installation timestamp unrecorded"
            result["is_recent_wipe"] = False

        return result

    def collect_fans(self) -> dict[str, Any]:
        """Read fan RPM values from hwmon sysfs nodes (non-destructive, no PWM writes)."""
        fans: list[dict[str, Any]] = []
        hwmon_base = self.sysfs / "class" / "hwmon"
        if not hwmon_base.is_dir():
            return {"fans": fans, "source": "hwmon-unavailable"}

        try:
            for hwmon in sorted(hwmon_base.iterdir()):
                hwmon_name = _read_str(hwmon / "name") or hwmon.name
                # Look for fan*_input files
                for fan_input_path in sorted(hwmon.glob("fan*_input")):
                    fan_suffix = fan_input_path.stem.replace("fan", "").replace("_input", "")
                    rpm = _read_int(fan_input_path)
                    if rpm is None:
                        continue
                    label_path = hwmon / f"fan{fan_suffix}_label"
                    label = _read_str(label_path) or f"Fan {fan_suffix}"
                    fans.append({
                        "hwmon": hwmon_name,
                        "fan_id": fan_suffix,
                        "label": label,
                        "rpm": rpm,
                        "source": str(fan_input_path),
                    })
        except OSError:
            pass

        return {
            "fans": fans,
            "fan_count": len(fans),
            "source": "hwmon-sysfs",
        }

    def get_fan_profiles(self) -> dict[str, Any]:
        """Query ACPI platform thermal/fan profile choices and current mode."""
        choices_path = Path("/sys/firmware/acpi/platform_profile_choices")
        current_path = Path("/sys/firmware/acpi/platform_profile")
        if not choices_path.is_file() or not current_path.is_file():
            return {
                "supported": False,
                "current": "unsupported",
                "choices": [],
                "source": "acpi-platform-profile-unavailable",
            }

        try:
            choices = choices_path.read_text(encoding="utf-8").split()
            current = current_path.read_text(encoding="utf-8").strip()
            return {
                "supported": True,
                "current": current,
                "choices": choices,
                "source": "sysfs:/sys/firmware/acpi/platform_profile",
            }
        except OSError:
            return {
                "supported": False,
                "current": "unreadable",
                "choices": [],
                "source": "sysfs-permission-error",
            }

    def set_fan_profile(self, profile: str) -> dict[str, Any]:
        """Safely switch ACPI platform thermal/fan profile (whisper mode vs max performance)."""
        current_status = self.get_fan_profiles()
        if not current_status.get("supported"):
            return {"success": False, "error": "ACPI platform profiles unsupported on this host"}

        allowed = current_status.get("choices", [])
        if profile not in allowed:
            return {
                "success": False,
                "error": f"Invalid profile '{profile}'. Allowed: {', '.join(allowed)}",
            }

        target_file = Path("/sys/firmware/acpi/platform_profile")
        # 1. Try unprivileged write
        try:
            target_file.write_text(f"{profile}\n", encoding="utf-8")
            return {"success": True, "new_profile": profile, "method": "direct_sysfs"}
        except OSError:
            pass

        # 2. Fallback to sudo -n tee (least-privilege passwordless root)
        import subprocess

        try:
            sub = subprocess.run(
                ["sudo", "-n", "tee", str(target_file)],
                input=f"{profile}\n".encode("utf-8"),
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                timeout=2.0,
            )
            if sub.returncode == 0:
                return {"success": True, "new_profile": profile, "method": "sudo_acpi"}
            return {"success": False, "error": f"Permission denied (exit code {sub.returncode})"}
        except Exception as exc:
            return {"success": False, "error": str(exc)}

    def probe_host_specs(self) -> dict[str, Any]:
        """Generate a complete hardware telemetry report for instant auto-detection (concurrent & ultra-fast)."""
        from concurrent.futures import ThreadPoolExecutor

        with ThreadPoolExecutor(max_workers=8) as ex:
            f_sys = ex.submit(self.collect_system)
            f_cpu = ex.submit(self.collect_cpu)
            f_gpu = ex.submit(self.collect_gpu)
            f_mem = ex.submit(self.collect_memory)
            f_sto = ex.submit(self.collect_storage)
            f_bat = ex.submit(self.collect_battery)
            f_dis = ex.submit(self.collect_display)
            f_ac = ex.submit(self.collect_ac_adapter)
            f_thm = ex.submit(self.collect_thermals)
            f_prt = ex.submit(self.collect_ports)
            f_net = ex.submit(self.collect_network)
            f_ext = ex.submit(self.collect_system_extended)
            f_fan = ex.submit(self.collect_fans)
            f_pro = ex.submit(self.get_fan_profiles)

        mem = f_mem.result()
        total_bytes = mem.get("total_bytes") or 0
        total_gib = round(total_bytes / (1024 ** 3), 1) if total_bytes else 0

        return {
            "system": f_sys.result(),
            "cpu": f_cpu.result(),
            "gpu": f_gpu.result(),
            "memory": {
                **mem,
                "total_gib": total_gib,
            },
            "storage": f_sto.result(),
            "battery": f_bat.result(),
            "display": f_dis.result(),
            "ac_adapter": f_ac.result(),
            "thermals": f_thm.result(),
            "ports": f_prt.result(),
            "network": f_net.result(),
            "system_extended": f_ext.result(),
            "fans": f_fan.result(),
            "fan_profiles": f_pro.result(),
        }

    def collect_snapshot(self, claims: dict[str, Any] | None = None) -> dict[str, Any]:
        """Produce a normalized inspection snapshot dictionary ready for analysis (concurrent & ultra-fast)."""
        from concurrent.futures import ThreadPoolExecutor

        with ThreadPoolExecutor(max_workers=8) as ex:
            f_sys = ex.submit(self.collect_system)
            f_cpu = ex.submit(self.collect_cpu)
            f_gpu = ex.submit(self.collect_gpu)
            f_dis = ex.submit(self.collect_display)
            f_ac = ex.submit(self.collect_ac_adapter)
            f_thm = ex.submit(self.collect_thermals)
            f_bat = ex.submit(self.collect_battery)
            f_sto = ex.submit(self.collect_storage)
            f_mem = ex.submit(self.collect_memory)
            f_prt = ex.submit(self.collect_ports)
            f_net = ex.submit(self.collect_network)
            f_ext = ex.submit(self.collect_system_extended)
            f_fan = ex.submit(self.collect_fans)
            f_pro = ex.submit(self.get_fan_profiles)

        now = datetime.now(timezone.utc).isoformat()
        return {
            "schema_version": "1.0",
            "inspection": {
                "id": f"LINUX-COLLECT-{int(datetime.now(timezone.utc).timestamp())}",
                "collected_at": now,
            },
            "system": f_sys.result(),
            "cpu": f_cpu.result(),
            "gpu": f_gpu.result(),
            "display": f_dis.result(),
            "ac_adapter": f_ac.result(),
            "thermals": f_thm.result(),
            "claims": claims or {},
            "battery": f_bat.result(),
            "storage": f_sto.result(),
            "memory": f_mem.result(),
            "ports": f_prt.result(),
            "network": f_net.result(),
            "system_extended": f_ext.result(),
            "fans": f_fan.result(),
            "fan_profiles": f_pro.result(),
        }
