"""Terminal UI formatter for Xflash CLI diagnostics.

Provides clean, workshop-bench ASCII/ANSI output with 3-part finding cards,
spec reconciliation tables, and offline verification status.
"""
from __future__ import annotations

import os
import sys
from typing import Any


def _supports_color() -> bool:
    """Return True if the current stdout environment supports ANSI colors."""
    if "NO_COLOR" in os.environ or os.environ.get("TERM") == "dumb":
        return False
    return hasattr(sys.stdout, "isatty") and sys.stdout.isatty()


class Ansi:
    RESET = "\033[0m"
    BOLD = "\033[1m"
    DIM = "\033[2m"
    ITALIC = "\033[3m"
    UNDERLINE = "\033[4m"

    # Foreground colors
    BLACK = "\033[30m"
    RED = "\033[31m"
    GREEN = "\033[32m"
    YELLOW = "\033[33m"
    BLUE = "\033[34m"
    MAGENTA = "\033[35m"
    CYAN = "\033[36m"
    WHITE = "\033[37m"

    # Bright foreground
    BRIGHT_RED = "\033[91m"
    BRIGHT_GREEN = "\033[92m"
    BRIGHT_YELLOW = "\033[93m"
    BRIGHT_BLUE = "\033[94m"
    BRIGHT_CYAN = "\033[96m"
    BRIGHT_WHITE = "\033[97m"

    # Backgrounds
    BG_RED = "\033[41m"
    BG_GREEN = "\033[42m"
    BG_YELLOW = "\033[43m"
    BG_BLUE = "\033[44m"
    BG_DARK = "\033[48;5;236m"


def format_terminal_report(snapshot: dict[str, Any], report: dict[str, Any], use_color: bool | None = None) -> str:
    """Format snapshot measurements and pure analysis findings into an ANSI terminal report."""
    if use_color is None:
        use_color = _supports_color()

    def c(code: str, text: str) -> str:
        return f"{code}{text}{Ansi.RESET}" if use_color else text

    lines: list[str] = []
    width = 78

    # 1. Header Banner
    lines.append(c(Ansi.BRIGHT_BLUE, "┌" + "─" * (width - 2) + "┐"))
    title_text = "  XFLASH HARDWARE ASSURANCE v3.0 — WORKSHOP-BENCH"
    tagline_text = "  Check before you pay · 100% Offline Inspection"
    lines.append(c(Ansi.BRIGHT_BLUE, "│") + c(Ansi.BOLD + Ansi.BRIGHT_WHITE, f"{title_text:<{width - 2}}") + c(Ansi.BRIGHT_BLUE, "│"))
    lines.append(c(Ansi.BRIGHT_BLUE, "│") + c(Ansi.CYAN, f"{tagline_text:<{width - 2}}") + c(Ansi.BRIGHT_BLUE, "│"))
    lines.append(c(Ansi.BRIGHT_BLUE, "└" + "─" * (width - 2) + "┘"))
    lines.append("")

    # 2. Overall Verdict Banner
    risk_state = (report.get("risk_state") or "inconclusive").lower()
    finding_count = report.get("finding_count", 0)

    if risk_state in ("pass", "no_detected_anomaly_in_evaluated_checks"):
        badge = c(Ansi.BOLD + Ansi.BRIGHT_GREEN, "✔ VERDICT: PASSED — LOW RISK")
        verdict_desc = "Observed hardware telemetry aligns with expectations. No critical faults identified."
    elif risk_state in ("review", "warning"):
        badge = c(Ansi.BOLD + Ansi.BRIGHT_YELLOW, f"⚠ VERDICT: REVIEW DISCREPANCIES ({finding_count} Finding{'s' if finding_count != 1 else ''})")
        verdict_desc = f"{finding_count} spec discrepancy or wear issue detected. Inspect findings below for negotiation leverage."
    elif risk_state in ("high", "high_risk"):
        badge = c(Ansi.BOLD + Ansi.BRIGHT_RED, f"✖ VERDICT: MATERIAL ANOMALIES DETECTED ({finding_count} Findings)")
        verdict_desc = "Significant hardware wear or specification shortfall detected. Caution advised."
    elif risk_state == "critical":
        badge = c(Ansi.BOLD + Ansi.RED, "⛔ VERDICT: CRITICAL HARDWARE FAULT")
        verdict_desc = "Severe hardware failure or component controller warning detected! Purchase discouraged."
    else:
        badge = c(Ansi.BOLD + Ansi.YELLOW, "⁇ VERDICT: INCONCLUSIVE TELEMETRY")
        verdict_desc = "Insufficient measurements collected to certify hardware health."

    lines.append(f"  {badge}")
    lines.append(f"  {c(Ansi.DIM, verdict_desc)}")
    lines.append("")

    # 3. Spec Reconciliation Table (Observed vs Claimed)
    lines.append(c(Ansi.BOLD, "  ■ HARDWARE SPECIFICATIONS & RECONCILIATION"))
    lines.append(c(Ansi.DIM, "  " + "─" * (width - 4)))

    system = snapshot.get("system") or {}
    cpu = snapshot.get("cpu") or {}
    memory = snapshot.get("memory") or {}
    storage = snapshot.get("storage") or {}
    battery = snapshot.get("battery") or {}
    display = snapshot.get("display") or {}
    claims = snapshot.get("claims") or {}

    # Model
    obs_model = f"{system.get('vendor', '')} {system.get('model', '')}".strip() or "Unknown Model"
    claim_model = claims.get("model") or "(None entered)"
    lines.append(f"  {c(Ansi.CYAN, 'Model:'):<18} {obs_model}")
    if claims.get("model"):
        import re
        norm_obs = re.sub(r"[^a-zA-Z0-9]+", " ", obs_model.lower()).split()
        norm_claim = re.sub(r"[^a-zA-Z0-9]+", " ", str(claims["model"]).lower()).split()
        is_match = all(token in norm_obs for token in norm_claim) if norm_claim else False
        match_str = c(Ansi.GREEN, "✔ Match") if is_match else c(Ansi.YELLOW, "≠ Discrepancy")
        lines.append(f"  {c(Ansi.DIM, 'Claimed Model:'):<18} {claim_model}  [{match_str}]")

    # CPU
    obs_cpu = cpu.get("model") or "Unknown CPU"
    cores = cpu.get("cores")
    threads = cpu.get("threads")
    core_str = f" ({cores}C/{threads}T)" if cores and threads else ""
    lines.append(f"  {c(Ansi.CYAN, 'CPU:'):<18} {obs_cpu}{core_str}")

    # Memory
    mem_bytes = memory.get("total_bytes")
    mem_gib = memory.get("total_gib") or ((mem_bytes / (1024**3)) if mem_bytes else None)
    claim_ram = claims.get("ram_gib")
    obs_ram_str = f"{mem_gib:.1f} GiB" if mem_gib is not None else "Unknown"
    if claim_ram is not None and mem_gib is not None:
        ram_delta = mem_gib - claim_ram
        if abs(ram_delta) <= 1.2:
            ram_match = c(Ansi.GREEN, f"✔ Verified against {claim_ram:g} GiB claimed")
        else:
            ram_match = c(Ansi.BRIGHT_RED, f"✖ Shortfall! Claimed {claim_ram:g} GiB (delta: {ram_delta:+.1f} GiB)")
        lines.append(f"  {c(Ansi.CYAN, 'Memory (RAM):'):<18} {obs_ram_str}  [{ram_match}]")
    else:
        lines.append(f"  {c(Ansi.CYAN, 'Memory (RAM):'):<18} {obs_ram_str}")

    # Storage
    disks = storage.get("devices") or []
    if disks:
        primary_disk = disks[0]
        disk_model = primary_disk.get("model") or "Primary Disk"
        cap_bytes = primary_disk.get("capacity_bytes")
        cap_gb = (cap_bytes / 1e9) if cap_bytes else None
        disk_proto = (primary_disk.get("protocol") or "storage").upper()
        cap_str = f"{cap_gb:.0f} GB" if cap_gb else "Unknown size"

        claim_storage = claims.get("storage_capacity_gb")
        if claim_storage is not None and cap_gb is not None:
            storage_delta = cap_gb - claim_storage
            if abs(storage_delta) <= (claim_storage * 0.1):
                storage_match = c(Ansi.GREEN, f"✔ Verified against {claim_storage:g} GB claimed")
            else:
                storage_match = c(Ansi.BRIGHT_YELLOW, f"≠ Discrepancy! Claimed {claim_storage:g} GB")
            lines.append(f"  {c(Ansi.CYAN, 'Storage:'):<18} {disk_model} ({cap_str} · {disk_proto})  [{storage_match}]")
        else:
            lines.append(f"  {c(Ansi.CYAN, 'Storage:'):<18} {disk_model} ({cap_str} · {disk_proto})")

        # NVMe Health
        used_pct = primary_disk.get("nvme_percentage_used")
        media_errors = primary_disk.get("media_errors")
        poh = primary_disk.get("power_on_hours")
        spare = primary_disk.get("available_spare")

        health_details = []
        if used_pct is not None:
            health_details.append(f"Wear: {used_pct}% used")
        if spare is not None:
            health_details.append(f"Spare: {spare}%")
        if media_errors is not None:
            err_color = Ansi.BRIGHT_RED if media_errors > 0 else Ansi.GREEN
            health_details.append(c(err_color, f"Media Errors: {media_errors}"))
        if poh is not None:
            health_details.append(f"Runtime: {poh} hrs (~{poh // 24} days)")

        if health_details:
            lines.append(f"  {c(Ansi.DIM, '  └─ Disk Health:'):<18} {', '.join(health_details)}")
    else:
        lines.append(f"  {c(Ansi.CYAN, 'Storage:'):<18} {c(Ansi.YELLOW, 'No storage telemetry collected')}")

    # Battery
    design = battery.get("design_capacity_mwh")
    full = battery.get("full_charge_capacity_mwh")
    cycles = battery.get("cycle_count")
    status = battery.get("status") or "Unknown"

    if design and full:
        health_pct = min(100.0, (full / design) * 100.0)
        h_color = Ansi.GREEN if health_pct >= 80 else (Ansi.YELLOW if health_pct >= 60 else Ansi.BRIGHT_RED)
        cycle_str = f" · {cycles} cycles" if cycles is not None else ""
        lines.append(f"  {c(Ansi.CYAN, 'Battery:'):<18} {c(h_color, f'{health_pct:.1f}% Health')} ({full:,.0f} / {design:,.0f} mWh{cycle_str}) [{status}]")
    elif full:
        lines.append(f"  {c(Ansi.CYAN, 'Battery:'):<18} Full: {full:,.0f} mWh (Design capacity unrecorded) [{status}]")
    else:
        lines.append(f"  {c(Ansi.CYAN, 'Battery:'):<18} {c(Ansi.DIM, 'No battery detected (Desktop or AC-only)')}")

    # Display & Panel Technology
    res = display.get("resolution") or "Unknown resolution"
    edid = display.get("edid") or {}
    panel_tech = edid.get("panel_type") or display.get("panel_type") or "LCD"
    mfg = edid.get("manufacturer")
    mfg_str = f" · {mfg}" if mfg else ""
    diag = edid.get("diagonal_inches")
    diag_str = f" · {diag:.1f}\"" if diag else ""
    depth = edid.get("color_depth")
    depth_str = f" · {depth}" if depth else ""
    lines.append(f"  {c(Ansi.CYAN, 'Display:'):<18} {res} · {c(Ansi.BOLD, panel_tech)}{diag_str}{depth_str}{mfg_str}")

    # OS & Clean Reinstall Resale Detection
    system_ext = snapshot.get("system_extended") or {}
    boot_firmware = system_ext.get("boot_firmware") or "Unknown"
    pt_scheme = system_ext.get("partition_table") or "Unknown"
    os_name = system_ext.get("os_pretty_name") or system_ext.get("os_name") or system.get("os_name", "Linux")
    refurb_status = system_ext.get("refurbish_status")

    os_line = f"{os_name} ({boot_firmware} · {pt_scheme})"
    if refurb_status:
        is_wipe = system_ext.get("is_recent_wipe", False)
        wipe_tag = c(Ansi.BRIGHT_YELLOW, f"[{refurb_status}]") if is_wipe else c(Ansi.DIM, f"[{refurb_status}]")
        lines.append(f"  {c(Ansi.CYAN, 'OS & Resale Wipe:'):<18} {os_line} {wipe_tag}")
    else:
        lines.append(f"  {c(Ansi.CYAN, 'OS Environment:'):<18} {os_line}")

    lines.append("")

    # 4. Findings Breakdown (3-Part Workshop-Bench Structure)
    findings = report.get("findings") or []
    if findings:
        lines.append(c(Ansi.BOLD, f"  ■ DETECTED HARDWARE FINDINGS ({len(findings)})"))
        lines.append(c(Ansi.DIM, "  " + "─" * (width - 4)))

        for idx, f in enumerate(findings, 1):
            sev = (f.get("severity") or "warning").upper()
            rule_id = f.get("rule_id", "finding")
            component = (f.get("component") or "hardware").upper()

            if sev == "CRITICAL":
                sev_badge = c(Ansi.BOLD + Ansi.RED, f"[{sev}]")
            elif sev == "HIGH":
                sev_badge = c(Ansi.BOLD + Ansi.BRIGHT_RED, f"[{sev}]")
            elif sev == "WARNING":
                sev_badge = c(Ansi.BOLD + Ansi.BRIGHT_YELLOW, f"[{sev}]")
            else:
                sev_badge = c(Ansi.CYAN, f"[{sev}]")

            explanation = f.get("details") or f.get("explanation") or "Discrepancy noted."
            rule_action = f.get("action")

            # Construct 3-part finding tiers
            # Tier 1: What's Wrong
            tier1 = explanation

            # Tier 2: Why It Matters (Buyer Impact)
            if "battery" in component.lower() or "battery" in rule_id.lower():
                tier2 = "Reduced runtime away from AC power; replacement battery cost may range from $40–$100."
                fallback_tier3 = "Test drain speed under load. Request a battery replacement credit or discount from seller."
            elif "storage" in component.lower() or "nvme" in rule_id.lower() or "media_error" in rule_id.lower():
                tier2 = "Drive sector instability or capacity shortfall limits usable storage and risks data corruption."
                fallback_tier3 = "Back up critical data immediately; negotiate price down by the cost of a replacement NVMe SSD."
            elif "memory" in component.lower() or "ram" in rule_id.lower():
                tier2 = "Installed RAM is lower than advertised, reducing multitasking capabilities."
                fallback_tier3 = "Verify whether RAM is soldered or socketed; request seller supply missing SODIMM module or discount."
            elif "cpu" in component.lower() or "thermal" in rule_id.lower():
                tier2 = "Processor frequency or thermal throttling may constrain peak sustained performance."
                fallback_tier3 = "Inspect fan exhaust for dust blockages and verify thermal paste condition."
            else:
                tier2 = "Component behavior diverges from factory baseline or seller claims."
                fallback_tier3 = "Inspect component in Advanced Mode telemetry before completing purchase."

            tier3 = rule_action or fallback_tier3

            evidence = f.get("evidence") or {}
            ev_pairs = [f"{k}={v}" for k, v in list(evidence.items())[:3]]
            ev_str = ", ".join(ev_pairs) if ev_pairs else "rule_check"

            lines.append(f"  {idx}. {sev_badge} {c(Ansi.BOLD + Ansi.BRIGHT_WHITE, f.get('title') or rule_id.replace('_', ' ').title())} ({component})")
            lines.append(f"     {c(Ansi.CYAN, '1. What’s Wrong:')}  {tier1}")
            lines.append(f"     {c(Ansi.YELLOW, '2. Why It Matters:')} {tier2}")
            lines.append(f"     {c(Ansi.GREEN, '3. Action:')}         {tier3}")
            lines.append(f"     {c(Ansi.DIM, f'Evidence: {ev_str}')}")
            lines.append("")
    else:
        lines.append(c(Ansi.BOLD + Ansi.GREEN, "  ✔ NO HARDWARE FINDINGS"))
        lines.append(f"  {c(Ansi.DIM, 'All evaluated rules returned clean telemetry within expected factory tolerances.')}")
        lines.append("")

    # 5. Coverage Matrix
    coverage = report.get("coverage") or {}
    if coverage:
        lines.append(c(Ansi.BOLD, "  ■ EVALUATION COVERAGE MATRIX"))
        lines.append(c(Ansi.DIM, "  " + "─" * (width - 4)))
        cov_items = []
        for check_name, status in coverage.items():
            st_upper = str(status).upper()
            if st_upper in ("PASSED", "HEALTHY", "CLEAN"):
                cov_str = c(Ansi.GREEN, f"✔ {check_name}")
            elif st_upper in ("WARNING", "HIGH", "CRITICAL"):
                cov_str = c(Ansi.YELLOW, f"⚠ {check_name}")
            else:
                cov_str = c(Ansi.DIM, f"• {check_name} ({status})")
            cov_items.append(cov_str)

        # Chunk into rows of 3
        for i in range(0, len(cov_items), 3):
            chunk = cov_items[i : i + 3]
            lines.append("  " + "    ".join(chunk))
        lines.append("")

    # 6. Session Footer
    insp_id = (snapshot.get("inspection") or {}).get("id") or "INSPECT-LIVE"
    lines.append(c(Ansi.DIM, f"  Session ID: {insp_id} · Generated by {report.get('generated_by', 'xflash/3.0.0')}"))
    lines.append(c(Ansi.DIM, "  Guarantees: 100% offline · Read-only inspection · Zero host telemetry"))
    lines.append(c(Ansi.BRIGHT_BLUE, "─" * width))

    return "\n".join(lines)
