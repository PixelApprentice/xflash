"""Pure, offline anomaly analysis for normalized laptop snapshots.

This module deliberately does not call the OS, execute commands, or access the network.
Collector adapters are separate future work.
"""
from __future__ import annotations

from typing import Any
import math

SEVERITY_RANK = {"info": 0, "inconclusive": 1, "warning": 2, "high": 3, "critical": 4}


def _finite_number(value: Any) -> bool:
    """Return True for finite JSON-style numbers, excluding booleans."""
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value)


def validate_snapshot_shape(snapshot: Any) -> list[str]:
    """Validate structural types before rule evaluation; values can still be unavailable."""
    errors: list[str] = []
    if not isinstance(snapshot, dict):
        return ["top-level JSON value must be an object"]
    for key in ("inspection", "system", "claims", "battery", "storage", "memory"):
        value = snapshot.get(key)
        if value is None:
            continue
        if key == "storage":
            if not isinstance(value, dict):
                errors.append("'storage' must be an object or null")
            else:
                devices = value.get("devices", [])
                if not isinstance(devices, list):
                    errors.append("'storage.devices' must be an array")
                elif any(not isinstance(device, dict) for device in devices):
                    errors.append("each item in 'storage.devices' must be an object")
        elif not isinstance(value, dict):
            errors.append(f"'{key}' must be an object or null")
    return errors


def _finding(
    *, code: str, severity: str, component: str, title: str, details: str,
    evidence: dict[str, Any], action: str, confidence: str = "medium",
    source: str | None = None,
) -> dict[str, Any]:
    return {
        "code": code,
        "severity": severity,
        "component": component,
        "title": title,
        "details": details,
        "evidence": evidence,
        "recommended_action": action,
        "confidence": confidence,
        "source": source,
    }


def analyze_battery(battery: dict[str, Any] | None) -> tuple[list[dict[str, Any]], bool]:
    findings: list[dict[str, Any]] = []
    if not battery:
        return ([ _finding(
            code="BATTERY_DATA_UNAVAILABLE", severity="inconclusive", component="battery",
            title="Battery health could not be evaluated",
            details="No battery measurements were supplied. This is not a pass.", evidence={},
            action="Collect a native battery report or record why the battery interface is unavailable.",
            confidence="low",
        ) ], False)

    design = battery.get("design_capacity_mwh")
    full = battery.get("full_charge_capacity_mwh")
    cycles = battery.get("cycle_count")
    source = battery.get("source")

    if (
        not _finite_number(design)
        or not _finite_number(full)
        or design <= 0
        or full < 0
    ):
        findings.append(_finding(
            code="BATTERY_CAPACITY_INVALID_OR_MISSING", severity="inconclusive", component="battery",
            title="Battery capacity data is missing or invalid",
            details="Design and full-charge capacity must be valid non-negative measurements, with design capacity greater than zero.",
            evidence={"design_capacity_mwh": design, "full_charge_capacity_mwh": full},
            action="Repeat collection using a supported native interface; preserve the raw values and source.",
            confidence="low", source=source,
        ))
        return findings, False

    evidence = {
        "design_capacity_mwh": design,
        "full_charge_capacity_mwh": full,
        "cycle_count": cycles,
    }
    health = full / design * 100.0
    degradation = 100.0 - health
    evidence["health_percent"] = round(health, 2)
    evidence["degradation_percent"] = round(degradation, 2)

    if full == 0:
        findings.append(_finding(
            code="BATTERY_CAPACITY_DEPLETED", severity="critical", component="battery",
            title="Reported full-charge capacity is zero",
            details="The battery controller reports 0 mWh full-charge capacity. The battery may be completely dead, disconnected, or failing to communicate.",
            evidence=evidence,
            action="Inspect the physical battery for swelling, check whether the laptop operates on battery power alone, and recheck connections.",
            confidence="high", source=source,
        ))
        return findings, True

    # Validate cycle count
    valid_cycles = False
    if cycles is not None:
        if isinstance(cycles, bool) or not isinstance(cycles, int):
            findings.append(_finding(
                code="BATTERY_CYCLE_COUNT_INVALID", severity="warning", component="battery",
                title="Reported battery cycle count is not a valid integer",
                details=f"Controller reported cycle count of {cycles!r}. Value must be an integer.",
                evidence={"cycle_count": cycles},
                action="Verify cycle count from an alternate native interface.",
                confidence="medium", source=source,
            ))
        elif cycles < 0:
            findings.append(_finding(
                code="BATTERY_CYCLE_COUNT_INVALID", severity="warning", component="battery",
                title="Reported battery cycle count is negative",
                details=f"Controller reported invalid negative cycle count of {cycles}.",
                evidence={"cycle_count": cycles},
                action="Verify cycle count from an alternate native interface and check power supply firmware.",
                confidence="medium", source=source,
            ))
        elif cycles > 10000:
            findings.append(_finding(
                code="BATTERY_CYCLE_COUNT_IMPLAUSIBLE", severity="warning", component="battery",
                title="Reported battery cycle count is implausibly high",
                details=f"Controller reported {cycles} cycles. This likely indicates an uninitialized register or reporting bug.",
                evidence={"cycle_count": cycles},
                action="Inspect raw sysfs/WMI registers; do not rely on this cycle count.",
                confidence="medium", source=source,
            ))
        else:
            valid_cycles = True

    # Some battery controllers can report a value above design due to rounding,
    # replacement packs, calibration, or firmware-specific semantics. Do not
    # describe it as >100% physical health without qualification.
    if health > 110.0:
        findings.append(_finding(
            code="BATTERY_CAPACITY_IMPLAUSIBLE", severity="warning", component="battery",
            title="Reported full-charge capacity is implausibly above design capacity",
            details=f"Reported capacity is {health:.1f}% of design capacity. This may reflect a replacement pack, controller/reporting semantics, or bad data.",
            evidence=evidence,
            action="Recollect from a second supported interface and verify battery identity; do not use this value as a precise health score.",
            confidence="medium", source=source,
        ))
        return findings, True
    if health > 100.0:
        findings.append(_finding(
            code="BATTERY_CAPACITY_ABOVE_DESIGN", severity="info", component="battery",
            title="Reported capacity is slightly above design capacity",
            details=f"Reported full-charge capacity is {health:.1f}% of design. Small excesses can arise from estimation, rounding, or replacement/controller details.",
            evidence=evidence,
            action="Record the raw values and repeat if the result affects the purchase decision.",
            confidence="low", source=source,
        ))

    if degradation >= 40.0:
        severity = "high"
        title = "Very high reported battery capacity loss"
    elif degradation >= 30.0:
        severity = "high"
        title = "High reported battery capacity loss"
    elif degradation >= 20.0:
        severity = "warning"
        title = "Battery capacity degradation merits review"
    else:
        severity = None
        title = ""

    if severity:
        findings.append(_finding(
            code="BATTERY_CAPACITY_DEGRADATION", severity=severity, component="battery",
            title=title,
            details=f"Full-charge capacity is {health:.1f}% of design capacity ({degradation:.1f}% lower). Capacity is an estimate and depends on battery/controller reporting.",
            evidence=evidence,
            action="Ask whether the battery was replaced; compare native OS and firmware values, check runtime under a repeatable workload, and inspect for swelling. Do not treat this measurement alone as proof of fraud.",
            confidence="medium", source=source,
        ))

    if degradation >= 20.0 and valid_cycles and 0 <= cycles <= 50:
        findings.append(_finding(
            code="LOW_CYCLES_HIGH_DEGRADATION", severity="warning", component="battery",
            title="Low reported cycle count conflicts with substantial capacity loss",
            details=f"The controller reports {cycles} cycles but estimated capacity loss is {degradation:.1f}%. Possible explanations include an aged/replacement battery, cycle counter reset, storage/temperature exposure, calibration, or inaccurate firmware data.",
            evidence=evidence,
            action="Investigate battery age and identity, repeat the reading, and perform a real runtime check. Treat as a discrepancy, not evidence of seller misconduct by itself.",
            confidence="medium", source=source,
        ))
    return findings, True


def analyze_storage(storage: dict[str, Any] | None, claims: dict[str, Any] | None = None) -> tuple[list[dict[str, Any]], bool]:
    findings: list[dict[str, Any]] = []
    claims = claims or {}
    devices = (storage or {}).get("devices", [])
    if not isinstance(devices, list) or not devices:
        return ([ _finding(
            code="STORAGE_DATA_UNAVAILABLE", severity="inconclusive", component="storage",
            title="No storage health data was collected",
            details="No storage devices were included in the snapshot. A missing device can mean unsupported hardware, controller mode, permission denial, or a collection error.",
            evidence={},
            action="Re-run inventory with a supported storage interface and document whether the device is behind RAID/RST/USB bridges.",
            confidence="low",
        ) ], False)

    evaluated = False

    # A capacity claim can only be checked safely when the snapshot identifies
    # a single drive corresponding to that claim. Multi-drive systems need a
    # future explicit target/role mapping rather than silently summing devices.
    claimed_gb = claims.get("storage_capacity_gb")
    if claimed_gb is not None:
        if not _finite_number(claimed_gb) or claimed_gb <= 0:
            findings.append(_finding(
                code="STORAGE_CLAIM_INVALID", severity="inconclusive", component="storage",
                title="Advertised storage capacity claim is invalid",
                details="The claim must be a positive number of decimal GB.",
                evidence={"claimed_storage_capacity_gb": claimed_gb},
                action="Correct the claimed capacity and rerun comparison.", confidence="low",
            ))
        elif len(devices) != 1:
            findings.append(_finding(
                code="STORAGE_CLAIM_COMPARISON_AMBIGUOUS", severity="inconclusive", component="storage",
                title="Storage capacity claim could not be mapped to one drive",
                details="The snapshot has multiple or no drive records, so the claimed capacity cannot safely be assigned without an explicit internal-drive mapping.",
                evidence={"claimed_storage_capacity_gb": claimed_gb, "device_count": len(devices)},
                action="Identify which detected drive(s) are internal and which drive the listing describes; then compare at the physical-drive level.", confidence="low",
            ))
        else:
            capacity_bytes = devices[0].get("capacity_bytes") if isinstance(devices[0], dict) else None
            if not _finite_number(capacity_bytes) or capacity_bytes <= 0:
                findings.append(_finding(
                    code="STORAGE_CAPACITY_DATA_UNAVAILABLE", severity="inconclusive", component="storage",
                    title="Storage capacity claim could not be verified",
                    details="No valid physical-device capacity was supplied for the single reported drive.",
                    evidence={"claimed_storage_capacity_gb": claimed_gb, "capacity_bytes": capacity_bytes},
                    action="Collect the full physical drive capacity through the device/controller interface; do not compare the partition's free space to advertised drive capacity.", confidence="low", source=devices[0].get("source"),
                ))
            else:
                observed_gb = capacity_bytes / 1_000_000_000
                ratio = observed_gb / claimed_gb
                cap_ev = {"claimed_storage_capacity_gb": claimed_gb, "observed_storage_capacity_gb": round(observed_gb, 3), "capacity_bytes": capacity_bytes}
                evaluated = True
                if ratio < 0.90:
                    findings.append(_finding(
                        code="STORAGE_CAPACITY_CLAIM_MISMATCH", severity="high", component="storage",
                        title="Detected drive capacity is materially below the listing claim",
                        details=f"Controller-reported physical capacity is {observed_gb:.2f} decimal GB versus a claim of {claimed_gb:.2f} GB. Ensure this is the correct internal drive and the claim refers to physical capacity rather than a volume.",
                        evidence=cap_ev, action="Verify the drive identity/model and inspect model-specific capacity; counterfeit or replaced capacity is one possibility, not a conclusion.", confidence="medium", source=devices[0].get("source"),
                    ))
                elif ratio < 0.95:
                    findings.append(_finding(
                        code="STORAGE_CAPACITY_SMALL_MISMATCH", severity="warning", component="storage",
                        title="Detected drive capacity is below the listing claim",
                        details=f"Controller-reported physical capacity is {observed_gb:.2f} decimal GB versus a claim of {claimed_gb:.2f} GB. The configured 5% tolerance has been exceeded.",
                        evidence=cap_ev, action="Confirm decimal GB vs GiB, physical drive vs partition, and the exact model/variant before deciding.", confidence="low", source=devices[0].get("source"),
                    ))

    for idx, drive in enumerate(devices):
        if not isinstance(drive, dict):
            continue
        model = drive.get("model") or f"Storage device {idx + 1}"
        source = drive.get("source")
        ev = {k: drive.get(k) for k in (
            "model", "protocol", "nvme_percentage_used", "nvme_critical_warning",
            "media_errors", "reallocated_sectors", "pending_sectors", "uncorrectable_errors",
            "self_test_status", "power_on_hours", "capacity_bytes"
        ) if k in drive}
        if len(ev) > 0:
            evaluated = True

        percent_used = drive.get("nvme_percentage_used")
        if _finite_number(percent_used):
            if percent_used < 0:
                findings.append(_finding(
                    code="STORAGE_DATA_INVALID", severity="warning", component="storage",
                    title=f"{model}: invalid negative NVMe percentage used",
                    details=f"The controller reported {percent_used}% of rated endurance used, which is invalid.",
                    evidence=ev, action="Check nvme-cli/smartctl version and raw NVMe SMART log output.",
                    confidence="medium", source=source,
                ))
            elif percent_used >= 100:
                findings.append(_finding(
                    code="NVME_RATED_ENDURANCE_REACHED", severity="high", component="storage",
                    title=f"{model}: reported NVMe endurance usage is at or above 100%",
                    details=f"The controller reports {percent_used}% of rated endurance used. This is not a deterministic prediction of imminent failure, but warrants detailed review.",
                    evidence=ev, action="Capture the full NVMe health/error logs and run a supported non-destructive self-test; make a backup before further testing.",
                    confidence="medium", source=source,
                ))
            elif percent_used >= 80:
                findings.append(_finding(
                    code="NVME_HIGH_ENDURANCE_USAGE", severity="warning", component="storage",
                    title=f"{model}: high reported NVMe endurance usage",
                    details=f"The controller reports {percent_used}% of rated endurance used. Interpret according to the drive vendor's specification.",
                    evidence=ev, action="Review remaining spare, media errors, critical warnings, workload, and vendor documentation.",
                    confidence="medium", source=source,
                ))

        critical_warning = drive.get("nvme_critical_warning")
        if isinstance(critical_warning, int) and not isinstance(critical_warning, bool):
            if critical_warning < 0:
                findings.append(_finding(
                    code="STORAGE_DATA_INVALID", severity="warning", component="storage",
                    title=f"{model}: invalid negative NVMe critical warning bitmask",
                    details=f"The raw critical-warning value is {critical_warning}, which is not a valid unsigned byte.",
                    evidence=ev, action="Capture raw smartctl/nvme logs.",
                    confidence="medium", source=source,
                ))
            elif critical_warning != 0:
                decoded_flags = []
                if critical_warning & (1 << 0):
                    decoded_flags.append("available_spare_below_threshold")
                if critical_warning & (1 << 1):
                    decoded_flags.append("temperature_threshold_exceeded")
                if critical_warning & (1 << 2):
                    decoded_flags.append("nvm_subsystem_reliability_degraded")
                if critical_warning & (1 << 3):
                    decoded_flags.append("media_read_only")
                if critical_warning & (1 << 4):
                    decoded_flags.append("volatile_memory_backup_failed")
                if critical_warning & (1 << 5):
                    decoded_flags.append("persistent_memory_region_degraded")
                ev_with_decoded = dict(ev)
                ev_with_decoded["decoded_flags"] = decoded_flags
                flags_desc = ", ".join(decoded_flags) or "unknown flags"
                findings.append(_finding(
                    code="NVME_CRITICAL_WARNING", severity="high", component="storage",
                    title=f"{model}: NVMe controller reports a critical warning",
                    details=f"The raw controller critical-warning value is {critical_warning} ({flags_desc}). Individual bits have defined meanings; retain the raw log for interpretation.",
                    evidence=ev_with_decoded, action="Stop routine stress testing; capture the full health log and prioritize data backup and drive replacement assessment.",
                    confidence="high", source=source,
                ))

        for field, code, label in (
            ("media_errors", "STORAGE_MEDIA_ERRORS", "media/data-integrity errors"),
            ("reallocated_sectors", "STORAGE_REALLOCATED_SECTORS", "reallocated sectors"),
            ("pending_sectors", "STORAGE_PENDING_SECTORS", "pending/unstable sectors"),
            ("uncorrectable_errors", "STORAGE_UNCORRECTABLE_ERRORS", "uncorrectable errors"),
        ):
            value = drive.get(field)
            if _finite_number(value):
                if value < 0:
                    findings.append(_finding(
                        code="STORAGE_DATA_INVALID", severity="warning", component="storage",
                        title=f"{model}: invalid negative counter for {label}",
                        details=f"The controller data reports negative value ({value}) for {label}. Sensor or driver output is corrupt.",
                        evidence=ev, action="Verify raw SMART/NVMe attribute values and driver status.", confidence="medium", source=source,
                    ))
                elif value > 0:
                    findings.append(_finding(
                        code=code, severity="warning" if field in ("media_errors", "reallocated_sectors") else "high",
                        component="storage", title=f"{model}: nonzero {label} counter",
                        details=f"The supplied controller data reports {value} {label}. Counter meaning and historical semantics depend on drive protocol/vendor; this reading alone may not show whether the issue is active or increasing.",
                        evidence=ev, action="Capture detailed SMART/NVMe logs, repeat after an interval if safe, and run a supported read-only/self-test. Avoid write tests on a seller's disk.",
                        confidence="medium", source=source,
                    ))

        self_test = drive.get("self_test_status")
        if isinstance(self_test, str) and self_test.lower() in {"failed", "failure", "completed_with_error", "aborted_by_host"}:
            findings.append(_finding(
                code="STORAGE_SELF_TEST_NOT_CLEAN", severity="high", component="storage",
                title=f"{model}: storage self-test did not complete cleanly",
                details=f"Reported self-test status: {self_test}.", evidence=ev,
                action="Review the device-specific test log and decide whether to replace the drive; do not run destructive tests.",
                confidence="high", source=source,
            ))
    return findings, evaluated


def analyze_memory(memory: dict[str, Any] | None, claims: dict[str, Any] | None) -> tuple[list[dict[str, Any]], bool]:
    findings: list[dict[str, Any]] = []
    memory = memory or {}
    claims = claims or {}
    observed_bytes = memory.get("total_bytes")
    claimed_gib = claims.get("ram_gib")
    if claimed_gib is None:
        return findings, False
    if (
        not _finite_number(observed_bytes)
        or observed_bytes <= 0
    ):
        findings.append(_finding(
            code="RAM_DATA_UNAVAILABLE", severity="inconclusive", component="memory",
            title="RAM claim could not be checked",
            details="The seller's claimed RAM quantity was supplied, but the detected memory total is missing or invalid.",
            evidence={"claimed_ram_gib": claimed_gib},
            action="Collect system memory inventory and confirm whether memory is soldered or hidden by firmware/OS limitations.",
            confidence="low", source=memory.get("source"),
        ))
        return findings, False
    if (
        not _finite_number(claimed_gib)
        or claimed_gib <= 0
    ):
        findings.append(_finding(
            code="RAM_CLAIM_INVALID", severity="inconclusive", component="memory",
            title="Advertised RAM claim is invalid", details="Claimed RAM must be a positive number of GiB.",
            evidence={"claimed_ram_gib": claimed_gib}, action="Correct the listing/specification input and rerun comparison.", confidence="low"
        ))
        return findings, False

    observed_gib = observed_bytes / (1024 ** 3)
    delta_ratio = observed_gib / claimed_gib
    evidence = {"claimed_ram_gib": claimed_gib, "observed_ram_gib": round(observed_gib, 3), "observed_bytes": observed_bytes}
    if delta_ratio < 0.90:
        findings.append(_finding(
            code="RAM_CLAIM_MISMATCH", severity="high", component="memory",
            title="Detected RAM is materially below the advertised quantity",
            details=f"Detected {observed_gib:.2f} GiB versus claimed {claimed_gib:.2f} GiB. Confirm whether the listing means installed, usable, or shared memory.",
            evidence=evidence, action="Cross-check BIOS/UEFI and OS inventory, reserve/shared memory, module layout, and model-specific maximum configuration.",
            confidence="medium", source=memory.get("source"),
        ))
    elif delta_ratio < 0.98:
        findings.append(_finding(
            code="RAM_CLAIM_SMALL_MISMATCH", severity="warning", component="memory",
            title="Detected RAM is somewhat below the advertised quantity",
            details=f"Detected {observed_gib:.2f} GiB versus claimed {claimed_gib:.2f} GiB; units and reserved memory may explain part of the difference.",
            evidence=evidence, action="Confirm the specification unit and compare with BIOS and module-level data if available.",
            confidence="low", source=memory.get("source"),
        ))
    return findings, True


def compute_coverage(
    snapshot: dict[str, Any],
    findings: list[dict[str, Any]],
    checks: dict[str, bool],
) -> dict[str, str]:
    """Calculate explicit per-test coverage states.

    Possible states: passed, warning, high, critical, inconclusive, skipped, not_run.
    """
    claims = snapshot.get("claims") or {}
    battery = snapshot.get("battery")
    storage = snapshot.get("storage") or {}
    devices = storage.get("devices") if isinstance(storage, dict) else None

    finding_codes = {f["code"]: f for f in findings}
    coverage: dict[str, str] = {}

    # 1. battery_capacity
    if not checks.get("battery", False):
        coverage["battery_capacity"] = "inconclusive"
    elif "BATTERY_CAPACITY_DEPLETED" in finding_codes:
        coverage["battery_capacity"] = "critical"
    elif "BATTERY_CAPACITY_IMPLAUSIBLE" in finding_codes:
        coverage["battery_capacity"] = "warning"
    elif "BATTERY_CAPACITY_DEGRADATION" in finding_codes:
        coverage["battery_capacity"] = finding_codes["BATTERY_CAPACITY_DEGRADATION"]["severity"]
    else:
        coverage["battery_capacity"] = "passed"

    # 2. battery_cycles
    if not checks.get("battery", False):
        coverage["battery_cycles"] = "skipped"
    elif battery and battery.get("cycle_count") is None:
        coverage["battery_cycles"] = "inconclusive"
    elif any(c in finding_codes for c in ("BATTERY_CYCLE_COUNT_INVALID", "BATTERY_CYCLE_COUNT_IMPLAUSIBLE", "LOW_CYCLES_HIGH_DEGRADATION")):
        coverage["battery_cycles"] = "warning"
    else:
        coverage["battery_cycles"] = "passed"

    # 3. storage_devices
    if not devices or not isinstance(devices, list):
        coverage["storage_devices"] = "inconclusive"
    else:
        coverage["storage_devices"] = "passed"

    # 4. storage_capacity_claim
    if claims.get("storage_capacity_gb") is None:
        coverage["storage_capacity_claim"] = "skipped"
    elif any(c in finding_codes for c in ("STORAGE_CLAIM_INVALID", "STORAGE_CLAIM_COMPARISON_AMBIGUOUS", "STORAGE_CAPACITY_DATA_UNAVAILABLE")):
        coverage["storage_capacity_claim"] = "inconclusive"
    elif "STORAGE_CAPACITY_CLAIM_MISMATCH" in finding_codes:
        coverage["storage_capacity_claim"] = "high"
    elif "STORAGE_CAPACITY_SMALL_MISMATCH" in finding_codes:
        coverage["storage_capacity_claim"] = "warning"
    else:
        coverage["storage_capacity_claim"] = "passed"

    # 5. nvme_endurance
    has_nvme_wear = devices and any(isinstance(d, dict) and "nvme_percentage_used" in d for d in devices)
    if not has_nvme_wear:
        coverage["nvme_endurance"] = "skipped"
    elif any(f["code"] == "STORAGE_DATA_INVALID" and "percentage used" in f["title"] for f in findings):
        coverage["nvme_endurance"] = "inconclusive"
    elif "NVME_RATED_ENDURANCE_REACHED" in finding_codes:
        coverage["nvme_endurance"] = "high"
    elif "NVME_HIGH_ENDURANCE_USAGE" in finding_codes:
        coverage["nvme_endurance"] = "warning"
    else:
        coverage["nvme_endurance"] = "passed"

    # 6. nvme_critical_warning
    has_crit_warn = devices and any(isinstance(d, dict) and "nvme_critical_warning" in d for d in devices)
    if not has_crit_warn:
        coverage["nvme_critical_warning"] = "skipped"
    elif any(f["code"] == "STORAGE_DATA_INVALID" and "critical warning" in f["title"] for f in findings):
        coverage["nvme_critical_warning"] = "inconclusive"
    elif "NVME_CRITICAL_WARNING" in finding_codes:
        coverage["nvme_critical_warning"] = "high"
    else:
        coverage["nvme_critical_warning"] = "passed"

    # 7. storage_integrity
    if not devices:
        coverage["storage_integrity"] = "skipped"
    elif any(c in finding_codes for c in ("STORAGE_UNCORRECTABLE_ERRORS", "STORAGE_PENDING_SECTORS")):
        coverage["storage_integrity"] = "high"
    elif any(c in finding_codes for c in ("STORAGE_MEDIA_ERRORS", "STORAGE_REALLOCATED_SECTORS")):
        coverage["storage_integrity"] = "warning"
    elif any(f["code"] == "STORAGE_DATA_INVALID" and "counter" in f["title"] for f in findings):
        coverage["storage_integrity"] = "inconclusive"
    else:
        coverage["storage_integrity"] = "passed"

    # 8. storage_self_test
    if "STORAGE_SELF_TEST_NOT_CLEAN" in finding_codes:
        coverage["storage_self_test"] = "high"
    elif devices and any(isinstance(d, dict) and str(d.get("self_test_status", "")).lower() in {"passed", "clean", "completed_without_error", "success"} for d in devices):
        coverage["storage_self_test"] = "passed"
    else:
        coverage["storage_self_test"] = "not_run"

    # 9. memory_capacity_claim
    if claims.get("ram_gib") is None:
        coverage["memory_capacity_claim"] = "skipped"
    elif any(c in finding_codes for c in ("RAM_DATA_UNAVAILABLE", "RAM_CLAIM_INVALID")):
        coverage["memory_capacity_claim"] = "inconclusive"
    elif "RAM_CLAIM_MISMATCH" in finding_codes:
        coverage["memory_capacity_claim"] = "high"
    elif "RAM_CLAIM_SMALL_MISMATCH" in finding_codes:
        coverage["memory_capacity_claim"] = "warning"
    else:
        coverage["memory_capacity_claim"] = "passed"

    return coverage


def analyze_snapshot(snapshot: dict[str, Any]) -> dict[str, Any]:
    """Analyze a normalized session. This function performs no IO or networking."""
    shape_errors = validate_snapshot_shape(snapshot)
    if shape_errors:
        raise ValueError("Invalid snapshot structure: " + "; ".join(shape_errors))
    findings: list[dict[str, Any]] = []
    checks = {}
    battery_findings, checks["battery"] = analyze_battery(snapshot.get("battery"))
    storage_findings, checks["storage"] = analyze_storage(snapshot.get("storage"), snapshot.get("claims"))
    memory_findings, checks["memory_claim_comparison"] = analyze_memory(snapshot.get("memory"), snapshot.get("claims"))
    findings.extend(battery_findings)
    findings.extend(storage_findings)
    findings.extend(memory_findings)
    findings.sort(key=lambda item: (-SEVERITY_RANK.get(item["severity"], 0), item["component"], item["code"]))

    levels = [f["severity"] for f in findings]
    if "critical" in levels:
        risk_state = "critical"
    elif "high" in levels:
        risk_state = "high_risk"
    elif "warning" in levels:
        risk_state = "review"
    elif any(checks.values()):
        risk_state = "no_detected_anomaly_in_evaluated_checks"
    else:
        risk_state = "insufficient_data"

    coverage = compute_coverage(snapshot, findings, checks)

    return {
        "report_schema_version": "1.0",
        "inspection_id": (snapshot.get("inspection") or {}).get("id"),
        "generated_by": "xflash/3.1.0",
        "risk_state": risk_state,
        "checks_evaluated": checks,
        "coverage": coverage,
        "finding_count": len(findings),
        "findings": findings,
        "limitations": [
            "This report is only as complete as the supplied measurements.",
            "A finding may indicate a discrepancy, not its cause or intent.",
            "No live hardware was accessed by this analysis run.",
        ],
    }
