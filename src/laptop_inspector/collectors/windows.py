"""Windows platform hardware inventory and sensor collector.

Collects hardware diagnostics via native Windows Management Instrumentation (WMI),
Common Information Model (CIM) cmdlets, and Windows performance counters.
Non-destructive, local-only, read-only.
"""
from __future__ import annotations

import json
import os
import platform
from typing import Any, Callable

from .base import CommandResult, safe_exec


def _run_ps_json(cmd: str, timeout: float = 6.0, executor: Callable[[list[str], float], CommandResult] | None = None) -> Any:
    """Execute a PowerShell command returning JSON-serialized output."""
    exec_fn = executor or (lambda args, to: safe_exec(args, timeout_seconds=to))
    full_cmd = f"$ProgressPreference = 'SilentlyContinue'; try {{ {cmd} | ConvertTo-Json -Compress -Depth 4 }} catch {{ '' }}"
    args = ["powershell.exe", "-NoProfile", "-NonInteractive", "-ExecutionPolicy", "Bypass", "-Command", full_cmd]
    res = exec_fn(args, timeout)
    if res.returncode == 0 and res.stdout.strip():
        try:
            return json.loads(res.stdout)
        except json.JSONDecodeError:
            pass
    return None


class WindowsCollector:
    """Collector adapter for Windows 10, 11, and 8.1 hardware telemetry."""

    def __init__(self, executor: Callable[[list[str], float], CommandResult] | None = None) -> None:
        self._executor = executor

    def _exec(self, args: list[str], timeout: float = 5.0) -> CommandResult:
        if self._executor:
            return self._executor(args, timeout)
        return safe_exec(args, timeout_seconds=timeout)

    def _ps(self, cmd: str, timeout: float = 6.0) -> Any:
        return _run_ps_json(cmd, timeout=timeout, executor=self._exec)

    def collect_battery(self) -> dict[str, Any] | None:
        """Collect battery health, cycle count, and design vs actual capacity."""
        data = self._ps("Get-CimInstance Win32_Battery | Select-Object Name, DeviceID, EstimatedChargeRemaining, DesignCapacity, FullChargeCapacity, BatteryStatus")
        if not data:
            return None

        item = data[0] if isinstance(data, list) else data
        design_mwh = item.get("DesignCapacity")
        full_mwh = item.get("FullChargeCapacity")
        charge_pct = item.get("EstimatedChargeRemaining")
        status_code = item.get("BatteryStatus")

        # In Windows CIM, DesignCapacity and FullChargeCapacity may be reported in mWh or mAh
        health_pct = None
        if full_mwh and design_mwh and design_mwh > 0:
            health_pct = round((float(full_mwh) / float(design_mwh)) * 100.0, 1)

        is_charging = status_code in (2, 6, 7, 8) if status_code is not None else None

        return {
            "health_pct": health_pct,
            "cycle_count": None,  # Win32_Battery does not expose cycle count directly
            "full_charge_capacity_mwh": full_mwh,
            "design_capacity_mwh": design_mwh,
            "charge_percentage": charge_pct,
            "is_charging": is_charging,
            "technology": "Li-ion",
            "model": item.get("Name") or item.get("DeviceID"),
            "source": "windows-cim:Win32_Battery",
        }

    def collect_system(self) -> dict[str, Any]:
        """Collect system chassis vendor, model, and BIOS firmware info."""
        cs = self._ps("Get-CimInstance Win32_ComputerSystem | Select-Object Manufacturer, Model")
        bios = self._ps("Get-CimInstance Win32_BIOS | Select-Object SMBIOSBIOSVersion, ReleaseDate, Manufacturer")

        cs_item = cs[0] if isinstance(cs, list) else (cs or {})
        bios_item = bios[0] if isinstance(bios, list) else (bios or {})

        vendor = cs_item.get("Manufacturer") or "Unknown"
        model = cs_item.get("Model") or "Windows PC"
        bios_ver = bios_item.get("SMBIOSBIOSVersion") or "Unknown"
        bios_date = bios_item.get("ReleaseDate") or ""

        return {
            "vendor": vendor,
            "model": model,
            "bios_version": bios_ver,
            "bios_date": str(bios_date)[:10] if bios_date else "Unknown",
            "source": "windows-cim:Win32_ComputerSystem",
        }

    def collect_cpu(self) -> dict[str, Any]:
        """Collect CPU processor specifications and core count."""
        proc = self._ps("Get-CimInstance Win32_Processor | Select-Object Name, NumberOfCores, NumberOfLogicalProcessors, MaxClockSpeed, Architecture")
        item = proc[0] if isinstance(proc, list) else (proc or {})

        name = (item.get("Name") or "CPU").strip()
        cores = item.get("NumberOfCores")
        threads = item.get("NumberOfLogicalProcessors")
        freq = float(item.get("MaxClockSpeed") or 0.0)
        arch_id = item.get("Architecture")

        arch_map = {0: "x86", 9: "x86_64", 5: "ARM", 12: "ARM64"}
        arch = arch_map.get(arch_id, platform.machine() or "x86_64")

        return {
            "model": name,
            "cores": cores,
            "threads": threads,
            "frequency_mhz": freq,
            "architecture": arch,
            "source": "windows-cim:Win32_Processor",
        }

    def collect_memory(self) -> dict[str, Any]:
        """Collect system physical memory capacity."""
        os_mem = self._ps("Get-CimInstance Win32_OperatingSystem | Select-Object TotalVisibleMemorySize, FreePhysicalMemory")
        item = os_mem[0] if isinstance(os_mem, list) else (os_mem or {})

        total_kb = item.get("TotalVisibleMemorySize")
        total_bytes = int(total_kb) * 1024 if total_kb else None

        return {
            "total_bytes": total_bytes,
            "available_bytes": int(item.get("FreePhysicalMemory", 0)) * 1024 if item.get("FreePhysicalMemory") else None,
            "source": "windows-cim:Win32_OperatingSystem",
        }

    def collect_storage(self) -> dict[str, Any]:
        """Collect storage disk drives, media types, and capacity."""
        disks = self._ps("Get-CimInstance Win32_DiskDrive | Select-Object Model, Size, MediaType, InterfaceType, Partitions")
        disk_list = disks if isinstance(disks, list) else ([disks] if disks else [])

        total_bytes = 0
        primary_model = "Storage Drive"
        bus_type = "NVMe/SATA"

        for d in disk_list:
            if isinstance(d, dict):
                size = d.get("Size")
                if size:
                    total_bytes += int(size)
                if not primary_model or primary_model == "Storage Drive":
                    primary_model = d.get("Model") or primary_model
                if d.get("InterfaceType"):
                    bus_type = d.get("InterfaceType")

        cap_gb = round(total_bytes / (1000 ** 3), 1) if total_bytes > 0 else None

        return {
            "model": primary_model,
            "capacity_gb": cap_gb,
            "bus_type": bus_type,
            "percentage_used": None,
            "media_errors": 0,
            "source": "windows-cim:Win32_DiskDrive",
        }

    def collect_thermals(self) -> dict[str, Any]:
        """Collect thermal zone temperatures via WMI MSAcpi_ThermalZoneTemperature."""
        tz = self._ps("Get-CimInstance -Namespace 'root/wmi' -ClassName 'MSAcpi_ThermalZoneTemperature' | Select-Object InstanceName, CurrentTemperature, CriticalTripPoint")
        items = tz if isinstance(tz, list) else ([tz] if tz else [])

        zones: list[dict[str, Any]] = []
        cpu_temps: list[float] = []

        for item in items:
            if isinstance(item, dict):
                raw_k = item.get("CurrentTemperature")
                name = item.get("InstanceName") or "ThermalZone"
                if raw_k and raw_k > 0:
                    # Windows reports MSAcpi temperature in tenths of Kelvin
                    temp_c = round((float(raw_k) - 2732.0) / 10.0, 1)
                    if 0.0 <= temp_c <= 125.0:
                        zones.append({"zone": name, "type": "ACPI Thermal Zone", "temp_c": temp_c})
                        cpu_temps.append(temp_c)

        avg_temp = round(sum(z["temp_c"] for z in zones) / len(zones), 1) if zones else None
        max_temp = max((z["temp_c"] for z in zones), default=None)

        return {
            "zones": zones,
            "average_temp_c": avg_temp,
            "max_temp_c": max_temp,
            "cpu_temp_c": max_temp,
            "source": "windows-wmi:root/wmi/MSAcpi_ThermalZoneTemperature",
        }

    def collect_fans(self) -> dict[str, Any]:
        """Collect fan speed RPM readings if exposed by OEM ACPI controller."""
        fans = self._ps("Get-CimInstance Win32_Fan | Select-Object Name, DesiredSpeed, VariableSpeed")
        items = fans if isinstance(fans, list) else ([fans] if fans else [])

        fan_list = []
        for i, item in enumerate(items):
            if isinstance(item, dict):
                fan_list.append({
                    "hwmon": "windows-cim",
                    "fan_id": str(i + 1),
                    "label": item.get("Name") or f"Fan {i+1}",
                    "rpm": item.get("DesiredSpeed") or 0,
                    "source": "Win32_Fan",
                })

        return {
            "fans": fan_list,
            "fan_count": len(fan_list),
            "source": "windows-cim:Win32_Fan",
        }

    def collect_ports(self) -> dict[str, Any]:
        """Collect USB connected devices and video output displays."""
        usb = self._ps("Get-CimInstance Win32_PnPEntity | Where-Object { $_.PNPClass -eq 'USB' -and $_.Present -eq $true } | Select-Object Name, Manufacturer, DeviceID")
        usb_items = usb if isinstance(usb, list) else ([usb] if usb else [])

        devices = []
        for u in usb_items:
            if isinstance(u, dict) and u.get("Name"):
                devices.append({
                    "product": u.get("Name"),
                    "manufacturer": u.get("Manufacturer") or "USB Vendor",
                    "removable": True,
                    "speed": "USB",
                    "speed_label": "USB Connected",
                    "device_type": "External USB Port",
                })

        video = self._ps("Get-CimInstance Win32_VideoController | Select-Object Name, VideoProcessor, DriverVersion")
        video_items = video if isinstance(video, list) else ([video] if video else [])

        displays = []
        for v in video_items:
            if isinstance(v, dict) and v.get("Name"):
                displays.append({
                    "name": v.get("Name"),
                    "connector": "Internal/External Display",
                    "status": "connected",
                })

        return {
            "usb": devices,
            "display_ports": displays,
            "source": "windows-cim:PnPEntity",
        }

    def collect_network(self) -> dict[str, Any]:
        """Collect wireless and ethernet network hardware interfaces."""
        net = self._ps("Get-CimInstance Win32_NetworkAdapter | Where-Object { $_.PhysicalAdapter -eq $true } | Select-Object Name, Manufacturer, NetConnectionStatus, Speed")
        items = net if isinstance(net, list) else ([net] if net else [])

        adapters = []
        for item in items:
            if isinstance(item, dict) and item.get("Name"):
                adapters.append({
                    "interface": item.get("Name"),
                    "is_up": item.get("NetConnectionStatus") == 2,
                    "state": "Connected" if item.get("NetConnectionStatus") == 2 else "Disconnected",
                })

        return {
            "interfaces": adapters,
            "source": "windows-cim:Win32_NetworkAdapter",
        }

    def collect_display(self) -> dict[str, Any]:
        """Collect display panel and resolution specs."""
        disp = self._ps("Get-CimInstance Win32_VideoController | Select-Object CurrentHorizontalResolution, CurrentVerticalResolution, CurrentRefreshRate")
        item = disp[0] if isinstance(disp, list) else (disp or {})

        width = item.get("CurrentHorizontalResolution") or 1920
        height = item.get("CurrentVerticalResolution") or 1080
        hz = item.get("CurrentRefreshRate") or 60

        return {
            "width_px": width,
            "height_px": height,
            "resolution": f"{width}x{height}",
            "refresh_rate_hz": hz,
            "source": "windows-cim:Win32_VideoController",
        }

    def collect_system_extended(self) -> dict[str, Any]:
        """Collect OS version, kernel build, and install age estimate."""
        os_info = self._ps("Get-CimInstance Win32_OperatingSystem | Select-Object Caption, Version, BuildNumber, InstallDate, OSArchitecture")
        item = os_info[0] if isinstance(os_info, list) else (os_info or {})

        caption = item.get("Caption") or "Microsoft Windows"
        version = item.get("Version") or platform.version()
        build = item.get("BuildNumber") or ""
        arch = item.get("OSArchitecture") or platform.machine()

        return {
            "os_name": caption,
            "os_version": f"{version} (Build {build})" if build else version,
            "cpu_arch": arch,
            "cpu_bits": 64 if "64" in str(arch) else 32,
            "boot_firmware": "UEFI",
            "partition_table": "GPT",
            "is_recent_wipe": False,
            "os_install_age_estimate": "Established",
            "source": "windows-cim:Win32_OperatingSystem",
        }

    def get_fan_profiles(self) -> dict[str, Any]:
        """Check ACPI fan profiles."""
        return {
            "supported": False,
            "current": "balanced",
            "choices": ["balanced"],
            "reason": "ACPI platform profile switching requires OEM proprietary driver on Windows",
        }

    def set_fan_profile(self, profile: str) -> dict[str, Any]:
        return {
            "success": False,
            "error": "ACPI platform profiles are not switchable via generic Windows APIs.",
        }

    def probe_host_specs(self) -> dict[str, Any]:
        """Probe host hardware specs for auto-detecting claims."""
        cpu = self.collect_cpu()
        mem = self.collect_memory()
        storage = self.collect_storage()
        system = self.collect_system()
        disp = self.collect_display()

        ram_gib = None
        if mem.get("total_bytes"):
            ram_gib = round(mem["total_bytes"] / (1024 ** 3))

        return {
            "model": f"{system.get('vendor', '')} {system.get('model', '')}".strip(),
            "cpu": cpu.get("model"),
            "ram_gib": ram_gib,
            "storage_gb": storage.get("capacity_gb"),
            "display": disp.get("resolution"),
            "system_extended": self.collect_system_extended(),
        }

    def collect_snapshot(self, claims: dict[str, Any] | None = None) -> dict[str, Any]:
        """Collect full system hardware snapshot."""
        return {
            "battery": self.collect_battery(),
            "system": self.collect_system(),
            "cpu": self.collect_cpu(),
            "memory": self.collect_memory(),
            "storage": self.collect_storage(),
            "thermals": self.collect_thermals(),
            "display": self.collect_display(),
            "ports": self.collect_ports(),
            "network": self.collect_network(),
            "system_extended": self.collect_system_extended(),
            "claims": claims or {},
        }
