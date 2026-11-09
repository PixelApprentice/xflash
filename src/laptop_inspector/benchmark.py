"""Thermal and cooling pulse benchmark module.

Safely tests CPU thermal dissipation and fan response under a 5-second bounded workload.
Cross-platform: runs on Linux, Windows, and macOS without root/admin privileges.
Enforces non-destructive, read-only integer/float arithmetic calculations.
"""
from __future__ import annotations

import math
import os
import subprocess
import sys
import time
from typing import Any


def _get_current_cpu_temp(collector: Any) -> float | None:
    """Read current CPU temperature from collector with tolerant fallbacks."""
    if collector is None:
        return None
    try:
        thermals = collector.collect_thermals()
        if not isinstance(thermals, dict):
            return None
        # Prefer direct CPU package temperature if reported
        if "cpu_temp_c" in thermals and thermals["cpu_temp_c"] is not None:
            return float(thermals["cpu_temp_c"])
        # Next check max_temp_c
        if "max_temp_c" in thermals and thermals["max_temp_c"] is not None:
            return float(thermals["max_temp_c"])
        # Next check average_temp_c
        if "average_temp_c" in thermals and thermals["average_temp_c"] is not None:
            return float(thermals["average_temp_c"])
    except Exception:
        pass
    return None


def _get_current_fan_rpm(collector: Any) -> int | None:
    """Read current maximum fan RPM from collector if supported."""
    if collector is None:
        return None
    try:
        fans_data = collector.collect_fans()
        if isinstance(fans_data, dict):
            fans = fans_data.get("fans", [])
            rpms = [f.get("rpm", 0) for f in fans if isinstance(f, dict) and f.get("rpm")]
            if rpms:
                return max(rpms)
    except Exception:
        pass
    return None


def run_cpu_pulse(
    duration_seconds: float = 5.0,
    collector: Any = None,
    worker_count: int | None = None,
) -> dict[str, Any]:
    """Execute a 5-second bounded CPU thermal dissipation test.

    Spawns worker child processes performing non-destructive arithmetic calculations
    to safely generate load across CPU cores, while dynamically sampling thermal sensors
    to measure peak rise and ramp rate.
    """
    duration = max(1.0, min(10.0, float(duration_seconds)))
    if worker_count is None:
        cpu_count = os.cpu_count() or 2
        # Use between 2 and 4 worker processes to distribute load across cores safely
        workers = max(2, min(cpu_count, 4))
    else:
        workers = max(1, min(worker_count, 8))

    initial_temp = _get_current_cpu_temp(collector)
    initial_fan = _get_current_fan_rpm(collector)

    # Subprocess payload: small bounded arithmetic loop
    worker_script = (
        f"import time, math; "
        f"end = time.time() + {duration:.2f}; "
        f"x = 1.0; "
        f"while time.time() < end: "
        f"    for _ in range(25000): "
        f"        x = math.sin(x) * 1.0001 + 0.123; "
    )

    procs: list[subprocess.Popen] = []
    try:
        for _ in range(workers):
            p = subprocess.Popen(
                [sys.executable, "-c", worker_script],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            procs.append(p)
    except Exception:
        pass

    samples: list[float] = []
    fan_samples: list[int] = []
    if initial_temp is not None:
        samples.append(initial_temp)
    if initial_fan is not None:
        fan_samples.append(initial_fan)

    start_time = time.time()
    deadline = start_time + duration

    # Sample sensors dynamically every 250ms during pulse
    while time.time() < deadline:
        time.sleep(0.25)
        cur_t = _get_current_cpu_temp(collector)
        if cur_t is not None:
            samples.append(cur_t)
        cur_fan = _get_current_fan_rpm(collector)
        if cur_fan is not None:
            fan_samples.append(cur_fan)

    # Ensure all worker processes have exited cleanly
    for p in procs:
        try:
            p.wait(timeout=1.5)
        except Exception:
            try:
                p.kill()
            except Exception:
                pass

    elapsed = round(time.time() - start_time, 2)
    final_temp = _get_current_cpu_temp(collector)
    if final_temp is not None:
        samples.append(final_temp)

    # Compute metrics
    if samples:
        init_t = samples[0]
        peak_t = max(samples)
        min_t = min(samples)
        temp_rise = max(0.0, round(peak_t - init_t, 1))
        ramp_rate = round(temp_rise / elapsed, 2)
        sensor_available = True
    else:
        # Transparent reporting when sensors not exposed (e.g. virtual machine / locked EC)
        init_t = 45.0
        peak_t = 45.0
        temp_rise = 0.0
        ramp_rate = 0.0
        sensor_available = False

    peak_fan = max(fan_samples) if fan_samples else initial_fan
    fan_rise = (peak_fan - initial_fan) if (peak_fan and initial_fan) else 0

    throttle_detected = peak_t >= 95.0

    if not sensor_available:
        verdict = "INCONCLUSIVE — Thermal sensors not exposed by firmware"
    elif throttle_detected:
        verdict = "WARNING — Thermal throttling threshold reached (>=95°C)"
    elif temp_rise >= 25.0:
        verdict = "WARNING — Rapid thermal rise (Check thermal paste and vents)"
    elif temp_rise >= 1.5:
        verdict = "PASS — Normal heatsink dissipation with active heat transfer"
    else:
        verdict = "PASS — Low thermal rise; heatsink operating efficiently"

    return {
        "duration_seconds": elapsed,
        "worker_count": workers,
        "initial_temp_c": init_t,
        "peak_temp_c": peak_t,
        "temp_rise_c": temp_rise,
        "thermal_ramp_rate": ramp_rate,
        "initial_fan_rpm": initial_fan,
        "peak_fan_rpm": peak_fan,
        "fan_rpm_rise": fan_rise,
        "sensor_available": sensor_available,
        "throttle_detected": throttle_detected,
        "status": verdict,
    }
