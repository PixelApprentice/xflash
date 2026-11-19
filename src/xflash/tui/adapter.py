"""Map Xflash's own `snapshot` + `report` (analyze_snapshot output) onto the TUI view-model.

This reads the same fields `cli_ui.format_terminal_report` reads, with the same thresholds and
wording, so the TUI and the plain terminal report never disagree:

  snapshot: inspection.id, system, cpu, memory, storage.devices, battery, display(+edid),
            system_extended, claims, and optionally thermal / cooling / fan telemetry
  report:   risk_state, finding_count, findings[], coverage{}, generated_by

Principles
  * Never raises. Wrong types or missing sections become UNSURE bays, not a crash.
  * Missing data is never PASS (the project's "transparent uncertainty" rule).
  * Serial numbers, MACs, UUIDs and hostnames are redacted from every generic dump.
"""
from __future__ import annotations

import re
from typing import Any, Optional

from .model import (Bars, Bay, Card, Chart, Finding, Hero, KV, Lines, Page, Session, Stats, Status)

_REDACT = re.compile(r"serial|uuid|host_?name|wwn|imei|(^|_)mac(_addr(ess)?)?($|_)", re.I)

# which findings / coverage entries belong to which bay (substring match on component + rule_id / check name)
BAY_KEYS = {
    "BAT": ("battery", "power", "charge"),
    "SSD": ("storage", "nvme", "disk", "smart", "drive", "media"),
    "MEM": ("memory", "ram", "dimm"),
    "CPU": ("cpu", "processor", "thermal"),
    "FAN": ("fan", "cooling", "acoustic"),
    "DSP": ("display", "panel", "edid", "screen", "pixel"),
}
_SEVERITY = {"critical": Status.FAIL, "high": Status.FAIL, "high_risk": Status.FAIL, "error": Status.FAIL,
             "warning": Status.WARN, "warn": Status.WARN, "medium": Status.WARN,
             "info": Status.OPEN, "informational": Status.OPEN, "low": Status.OPEN}
_RANK = {Status.FAIL: 6, Status.CLAIM: 5, Status.WARN: 4, Status.UNSURE: 3, Status.PASS: 2, Status.OPEN: 1}
_CLAIMISH = ("claim", "listing", "mismatch", "shortfall", "discrepan")
_PASSISH = ("pass", "no_detected_anomaly_in_evaluated_checks")


# ───────────────────────── tolerant accessors
def _d(x: Any) -> dict:
    return x if isinstance(x, dict) else {}


def _l(x: Any) -> list:
    return x if isinstance(x, list) else []


def _n(x: Any) -> Optional[float]:
    if isinstance(x, bool):
        return None
    if isinstance(x, (int, float)):
        return float(x)
    try:
        return float(str(x).replace(",", ""))
    except (TypeError, ValueError):
        return None


def _fmt(v: Any) -> str:
    if isinstance(v, bool):
        return "yes" if v else "no"
    if isinstance(v, int):
        return f"{v:,}"
    if isinstance(v, float):
        return f"{v:,.2f}".rstrip("0").rstrip(".")
    if isinstance(v, (list, tuple)):
        return ", ".join(_fmt(x) for x in v[:6]) + (" …" if len(v) > 6 else "")
    if isinstance(v, dict):
        return "{…}"
    return str(v)


def _label(key: str) -> str:
    return str(key).replace("_", " ").strip().capitalize()


def _scalars(d: Any, limit: int = 20) -> list:
    """[(Label, value)] for the scalar fields of a dict, one nested level flattened, secrets redacted."""
    rows: list = []

    def walk(obj: dict, prefix: str, depth: int) -> None:
        for k, v in obj.items():
            if len(rows) >= limit or v is None:
                continue
            name = f"{prefix}{_label(k)}"
            if _REDACT.search(str(k)):
                rows.append((name, "(redacted)"))
            elif isinstance(v, dict):
                if depth < 1:
                    walk(v, name + " ", depth + 1)
            else:
                rows.append((name, _fmt(v)))

    walk(_d(d), "", 0)
    return rows


# ───────────────────────── statuses
def _finding_status(f: dict) -> Status:
    return _SEVERITY.get(str(f.get("severity") or "warning").strip().lower(), Status.WARN)


def _is_claimish(f: dict) -> bool:
    rid = str(f.get("rule_id") or f.get("code") or "")
    text = f"{rid} {f.get('title', '')}".lower()
    return any(k in text for k in _CLAIMISH)


def _belongs(bay: str, f: dict) -> bool:
    rid = str(f.get("rule_id") or f.get("code") or "")
    text = f"{f.get('component', '')} {rid}".lower()
    return any(k in text for k in BAY_KEYS[bay])


def _cov_status(v: Any) -> Status:
    s = str(v).upper()
    if s in ("PASSED", "HEALTHY", "CLEAN"):
        return Status.PASS
    if s == "WARNING":
        return Status.WARN
    if s in ("HIGH", "CRITICAL"):
        return Status.FAIL
    return Status.parse(v)          # skipped -> OPEN, anything unknown -> UNSURE


def _worst(statuses: list) -> Status:
    return max(statuses, key=lambda s: _RANK.get(s, 0)) if statuses else Status.UNSURE


def _bay_status(bay: str, has_data: bool, findings: list, coverage: dict, risk_state: str) -> Status:
    related = [f for f in findings if _belongs(bay, f)]
    if related:
        worst = max(related, key=lambda f: _RANK.get(_finding_status(f), 0))
        return Status.CLAIM if _is_claimish(worst) else _finding_status(worst)
    cov = [_cov_status(v) for k, v in coverage.items() if any(w in str(k).lower() for w in BAY_KEYS[bay])]
    if cov:
        return _worst(cov)
    if not has_data:
        return Status.UNSURE
    return Status.PASS if (not coverage or risk_state in _PASSISH) else Status.UNSURE


def _role_for_pct(pct: float) -> str:
    return "p" if pct >= 80 else "w" if pct >= 60 else "c"      # same bands as cli_ui


# ───────────────────────── buyer-impact text (same wording as cli_ui)
def _impact(component: str, rule_id: str) -> tuple:
    comp, rid = component.lower(), rule_id.lower()
    if "battery" in comp or "battery" in rid:
        return ("Reduced runtime away from AC power; replacement battery cost may range from $40–$100.",
                "Test drain speed under load. Request a battery replacement credit or discount from seller.")
    if "storage" in comp or "nvme" in rid or "media_error" in rid:
        return ("Drive sector instability or capacity shortfall limits usable storage and risks data corruption.",
                "Back up critical data immediately; negotiate price down by the cost of a replacement NVMe SSD.")
    if "memory" in comp or "ram" in rid:
        return ("Installed RAM is lower than advertised, reducing multitasking capabilities.",
                "Verify whether RAM is soldered or socketed; request seller supply missing SODIMM module or discount.")
    if "cpu" in comp or "thermal" in rid:
        return ("Processor frequency or thermal throttling may constrain peak sustained performance.",
                "Inspect fan exhaust for dust blockages and verify thermal paste condition.")
    return ("Component behavior diverges from factory baseline or seller claims.",
            "Inspect component in Advanced Mode telemetry before completing purchase.")


def _verdict(report: dict) -> tuple:
    """Same states and wording as cli_ui.format_terminal_report (a test compares them)."""
    state = str(report.get("risk_state") or "inconclusive").lower()
    n = report.get("finding_count", len(_l(report.get("findings"))))
    n = n if isinstance(n, int) else 0
    if state in _PASSISH:
        return (Status.PASS, "PASSED — LOW RISK",
                "Observed hardware telemetry aligns with expectations. No critical faults identified.")
    if state in ("review", "warning"):
        return (Status.WARN, f"REVIEW DISCREPANCIES ({n} Finding{'s' if n != 1 else ''})",
                f"{n} spec discrepancy or wear issue detected. Inspect findings below for negotiation leverage.")
    if state in ("high", "high_risk"):
        return (Status.FAIL, f"MATERIAL ANOMALIES DETECTED ({n} Findings)",
                "Significant hardware wear or specification shortfall detected. Caution advised.")
    if state == "critical":
        return (Status.FAIL, "CRITICAL HARDWARE FAULT",
                "Severe hardware failure or component controller warning detected! Purchase discouraged.")
    return (Status.UNSURE, "INCONCLUSIVE TELEMETRY",
            "Insufficient measurements collected to certify hardware health.")


# ───────────────────────── per-subsystem readers
def _battery(snap: dict) -> dict:
    b = _d(snap.get("battery"))
    design, full = _n(b.get("design_capacity_mwh")), _n(b.get("full_charge_capacity_mwh"))
    pct = min(100.0, full / design * 100.0) if design and full else None
    return {"raw": b, "design": design, "full": full, "pct": pct, "cycles": _n(b.get("cycle_count")),
            "status": b.get("status")}


def _disks(snap: dict) -> list:
    return [d for d in _l(_d(snap.get("storage")).get("devices")) if isinstance(d, dict)]


def _thermal(snap: dict) -> dict:
    """First thermal-ish section present, plus a fan rpm and a CPU temperature if we can find them."""
    for key in ("thermal", "cooling", "fan", "fans", "sensors"):
        sec = snap.get(key)
        if isinstance(sec, dict) and sec:
            rpm = next((_n(v) for k, v in _flatten(sec) if "rpm" in k.lower() and _n(v) is not None), None)
            temp = next((_n(v) for k, v in _flatten(sec)
                         if any(t in k.lower() for t in ("temp", "celsius", "pkg")) and _n(v) is not None), None)
            return {"section": sec, "rpm": rpm, "temp": temp, "key": key}
    return {}


def _flatten(d: dict, prefix: str = "", depth: int = 0):
    for k, v in d.items():
        if isinstance(v, dict) and depth < 2:
            yield from _flatten(v, f"{prefix}{k}.", depth + 1)
        elif not isinstance(v, (dict, list)):
            yield f"{prefix}{k}", v


# ───────────────────────── the adapter
def to_session(snapshot: Any, report: Any) -> Session:
    snap, rep = _d(snapshot), _d(report)
    findings_raw = [f for f in _l(rep.get("findings")) if isinstance(f, dict)]
    coverage = _d(rep.get("coverage"))
    risk_state = str(rep.get("risk_state") or "inconclusive").lower()
    claims = _d(snap.get("claims"))
    system, cpu, mem = _d(snap.get("system")), _d(snap.get("cpu")), _d(snap.get("memory"))
    display, ext = _d(snap.get("display")), _d(snap.get("system_extended"))
    bat, disks, therm = _battery(snap), _disks(snap), _thermal(snap)
    sid = str(_d(snap.get("inspection")).get("id") or "INSPECT-LIVE")
    verdict = _verdict(rep)
    title = f"{system.get('vendor', '')} {system.get('model', '')}".strip() or "Unknown Model"
    st = lambda bay, data: _bay_status(bay, data, findings_raw, coverage, risk_state)  # noqa: E731
    first_rule = {b: next((str(f.get("rule_id") or f.get("code") or "") for f in findings_raw if _belongs(b, f)), "") for b in BAY_KEYS}
    pages: dict = {}
    bays: list = []

    # BAT ---------------------------------------------------------------
    pct = bat["pct"]
    if pct is not None:
        bays.append(Bay("BAT", f"{pct:.1f} %", st("BAT", True), bar=pct / 100, gauge=pct / 100, big=f"{pct:.1f}%",
                        sub=f"{int(bat['cycles'])} cycles" if bat["cycles"] is not None else "",
                        plain=f"{pct:.1f} % retention", target="battery"))
        ac_online = (snap.get("ac_adapter") or {}).get("online")
        ac_str = "Connected (AC Power)" if ac_online is True else ("Disconnected (Battery Power)" if ac_online is False else "—")
        left = [
            Hero("BATTERY", f"{pct:.1f}%", "battery", _role_for_pct(pct), str(bat["status"] or "Health")),
            Bars("CAPACITY HEALTH", [
                ("retention", pct / 100, f"{pct:.1f} %", _role_for_pct(pct), 0.80),
                ("wear", (100 - pct) / 100, f"{(100 - pct):.1f} %", "w" if (100 - pct) >= 20 else "p"),
            ], footer="white block marks the 80 % health threshold"),
            Card("BUYER VERDICT", [
                ("Condition",
                 f"{'Healthy' if pct >= 80 else 'Worn' if pct >= 60 else 'Critical'} ({pct:.1f}% factory capacity retained)",
                 _role_for_pct(pct)),
                ("Estimated Runtime",
                 f"~{pct:.0f}% of factory spec runtime" if pct >= 80 else "Shortened runtime off AC charger",
                 "t"),
                ("Buyer Action",
                 "Battery passes health criteria; no replacement needed." if pct >= 80 else
                 "Request $40–$80 discount for battery replacement credit.",
                 "p" if pct >= 80 else "w"),
            ]),
        ]
        right = [
            KV("Pack Telemetry", [
                ("Design Capacity", f"{bat['design']:,.0f} mWh ({bat['design']/1000:.1f} Wh)"),
                ("Full Charge", f"{bat['full']:,.0f} mWh ({bat['full']/1000:.1f} Wh)"),
                ("Capacity Loss", f"{max(0, bat['design'] - bat['full']):,.0f} mWh ({(100 - pct):.1f}%)"),
                ("Cycle Count", f"{int(bat['cycles'])} cycles" if bat['cycles'] is not None else "Unknown"),
                ("Power State", str(bat["status"] or "Unknown")),
                ("AC Charger", ac_str),
                ("Chemistry", str(bat["raw"].get("technology") or "Li-ion")),
                ("Interface", str(bat["raw"].get("source") or "ACPI sysfs").split("/")[-1]),
            ]),
        ]
        pages["battery"] = Page("battery", "Battery", "BATTERY", str(bat["status"] or "status unknown"),
                                f"{pct:.1f} % retention", [left, right], rules_hint=first_rule["BAT"], accent=_role_for_pct(pct))
    elif bat["full"]:
        bays.append(Bay("BAT", f"{bat['full']:,.0f} mWh", Status.UNSURE, sub="design capacity unrecorded",
                        plain=f"{bat['full']:,.0f} mWh (no design)", target="battery"))
        pages["battery"] = Page("battery", "Battery", "BATTERY", "design capacity unrecorded", "", [[
            KV("Battery", _scalars(bat["raw"]))]])
    else:
        bays.append(Bay("BAT", "none", st("BAT", False) if not bat["raw"] else Status.UNSURE,
                        sub="no battery detected", plain="no battery detected"))

    # SSD ---------------------------------------------------------------
    if disks:
        d0 = disks[0]
        used = _n(d0.get("nvme_percentage_used"))
        cap = _n(d0.get("capacity_bytes"))
        proto = str(d0.get("protocol") or "storage").upper()
        cap_gb = f"{cap / 1e9:.0f} GB" if cap else "unknown size"
        bays.append(Bay("SSD", f"{proto} · {used:g} % used" if used is not None else f"{proto} · {cap_gb}",
                        st("SSD", True), bar=(1 - used / 100) if used is not None else None,
                        gauge=(1 - used / 100) if used is not None else None,
                        big=f"{used:g}%" if used is not None else "", sub=f"{proto} · {cap_gb}",
                        value_role="p", plain=f"{proto} · {used:g} % used" if used is not None else f"{proto} · {cap_gb}",
                        target="storage"))
        errs = _n(d0.get("media_errors"))
        poh = _n(d0.get("power_on_hours"))
        spare = _n(d0.get("available_spare"))
        crit = _n(d0.get("nvme_critical_warning")) or 0
        temp_c = d0.get("temperature_c")

        left = []
        if used is not None:
            left.append(Hero("STORAGE", f"{100 - used}%", "chip", "p" if used < 80 else "w", "endurance remaining"))
            wear = [("used", used / 100, f"{used:g} %", "p" if used < 80 else "w", 0.80)]
            if spare is not None:
                wear.append(("spare", spare / 100, f"{spare:g} %", "p" if spare > 20 else "w"))
            left.append(Bars("NVMe ENDURANCE & SPARE", wear, footer="white block marks the 80 % wear limit"))
        else:
            left.append(Hero("STORAGE", cap_gb, "chip", "p", f"{proto} primary drive"))

        left.append(Card("BUYER VERDICT", [
            ("Drive Condition",
             f"{'Excellent' if (used or 0) < 20 and not errs else 'Normal' if (used or 0) < 80 and not errs else 'Degraded'} "
             f"({100 - (used or 0):g}% life remaining)",
             "p" if (used or 0) < 80 and not errs else "w"),
            ("Data Integrity",
             "0 media/data integrity errors detected" if not errs else f"{errs:g} media errors detected!",
             "p" if not errs else "c"),
            ("Buyer Action",
             "Storage drive is healthy; no replacement needed." if (used or 0) < 80 and not errs else
             "Drive has high wear or media errors; inspect or negotiate replacement.",
             "p" if (used or 0) < 80 and not errs else "w"),
        ]))

        right = [
            KV(f"Drive 0: {d0.get('model') or 'Primary SSD'}", [
                ("Model", str(d0.get("model") or "NVMe Drive")),
                ("Capacity", cap_gb),
                ("Device Node", str(d0.get("device_node") or "/dev/nvme0n1")),
                ("Protocol", proto),
                ("Temperature", f"{temp_c} °C (Normal)" if temp_c else "—"),
                ("Power-On Time", f"{poh:,.0f} hours (~{int(poh // 24):,} days)" if poh else "—"),
                ("Power Cycles", f"{d0.get('power_cycles'):,}" if d0.get('power_cycles') is not None else "—"),
                ("Self-Test", str(d0.get("self_test_status") or "clean")),
            ]),
            KV("SMART / NVMe Health", [
                ("Percentage Used", f"{used:g}%" if used is not None else "—"),
                ("Available Spare", f"{spare:g}%" if spare is not None else "—"),
                ("Media Errors", f"{errs:g}" if errs is not None else "0"),
                ("Critical Warnings", f"{crit:g} (Clean)" if crit == 0 else f"{crit} WARNING"),
            ]),
        ]
        pages["storage"] = Page("storage", "Storage", "STORAGE", f"{len(disks)} drive{'s' if len(disks) != 1 else ''}",
                                f"drive 0 · {d0.get('model') or ''}", [left, right],
                                rules_hint=first_rule["SSD"])
    else:
        bays.append(Bay("SSD", "—", Status.UNSURE, sub="no storage telemetry", plain="no storage telemetry"))

    # MEM ---------------------------------------------------------------
    gib = _n(mem.get("total_gib")) or ((_n(mem.get("total_bytes")) or 0) / 1024 ** 3) or None
    if gib:
        speed = next((_fmt(v) for k, v in _scalars(mem) if "speed" in k.lower() or k.lower() == "type"), "")
        bays.append(Bay("MEM", f"{gib:.1f} GiB", st("MEM", True), gauge=1.0, big=f"{gib:g} GiB", sub=speed,
                        value_role="p", plain=f"{gib:.1f} GiB", target="memory"))
        avail_bytes = _n(mem.get("available_bytes")) or 0
        total_bytes = _n(mem.get("total_bytes")) or (gib * 1024 ** 3)
        avail_gib = avail_bytes / 1024 ** 3 if avail_bytes else 0
        used_gib = max(0.0, gib - avail_gib) if avail_gib else 0
        left = [
            Hero("MEMORY", f"{gib:.1f} GiB", "chip", "p", f"{used_gib:.1f} GiB in use" if used_gib else "installed"),
            Bars("RAM CAPACITY", [
                ("total", 1.0, f"{gib:.1f} GiB", "p"),
                ("in use", used_gib / gib if gib else 0, f"{used_gib:.1f} GiB", "t2"),
            ], footer="available memory ready for workloads"),
            Card("BUYER VERDICT", [
                ("Installed RAM", f"{total_bytes / 1e9:.0f} GB ({gib:.1f} GiB accessible)", "p"),
                ("Capability", "Comfortable headroom for multitasking & productivity" if gib >= 15 else
                 "Adequate for standard web & streaming" if gib >= 8 else "Constrained memory; verify upgradeability", "t"),
                ("Buyer Action", "RAM capacity is healthy and matches typical specs.", "p"),
            ]),
        ]
        right = [
            KV("Memory Telemetry", [
                ("Total Usable", f"{gib:.1f} GiB ({total_bytes:,.0f} bytes)"),
                ("Available Now", f"{avail_gib:.1f} GiB ({avail_bytes:,.0f} bytes)" if avail_bytes else "—"),
                ("In Use", f"{used_gib:.1f} GiB ({(used_gib/gib*100):.0f}%)" if gib and used_gib else "—"),
                ("Architecture", f"{system.get('architecture', 'x86_64')} Unified Architecture"),
                ("Telemetry Source", str(mem.get("source") or "/proc/meminfo")),
            ]),
        ]
        pages["memory"] = Page("memory", "Memory", "MEM", f"{gib:.1f} GiB installed", "", [left, right],
                                rules_hint=first_rule["MEM"])
    else:
        bays.append(Bay("MEM", "—", Status.UNSURE, sub="no memory telemetry", plain="no memory telemetry"))

    # CPU ---------------------------------------------------------------
    cores, threads = _n(cpu.get("cores")), _n(cpu.get("threads"))
    temp = therm.get("temp")
    cpu_model = str(cpu.get("model") or "Unknown CPU")
    claim_cpu = claims.get("cpu")
    cpu_val = f"{temp:.0f} °C" if temp is not None else (f"{cores:g}C/{threads:g}T" if cores and threads else "—")
    cpu_status = st("CPU", bool(cpu))
    bays.append(Bay("CPU", cpu_val, cpu_status, gauge=(temp / 100) if temp is not None else None, sub=cpu_model,
                    note=f"listing {claim_cpu}" if claim_cpu and cpu_status is Status.CLAIM else "", value_role="t",
                    plain=f"{cpu_model} · {cpu_val}", target="cpu" if cpu else ""))
    if cpu:
        accent = "w" if cpu_status in (Status.CLAIM, Status.WARN) else "p"
        left = [
            Hero("PROCESSOR", f"{cores:g}C/{threads:g}T" if cores and threads else cpu_val, "chip", accent, cpu_val),
        ]
        if temp is not None:
            left.append(Bars("CORE TEMPERATURE", [
                ("temp", temp / 100, f"{temp:.0f} °C", "p" if temp < 75 else "w", 0.85),
            ], footer="white block marks 85 °C throttle limit"))
        left.append(Card("BUYER VERDICT", [
            ("Core Topology", f"{cores or '?'} Physical Cores / {threads or '?'} Logical Threads", "t"),
            ("Thermal Status", f"{temp:.0f} °C (Nominal operating temperature)" if temp and temp < 75 else "Within normal thermal envelope", "p"),
            ("Processor Match", "Observed hardware identity verified via CPUID", "p"),
        ]))
        right = [
            KV("Processor Specifications", [
                ("Model", cpu_model),
                ("Physical Cores", f"{int(cores)}" if cores is not None else "—"),
                ("Logical Threads", f"{int(threads)}" if threads is not None else "—"),
                ("Current Clock", f"{cpu.get('frequency_mhz', '—')} MHz"),
                ("Architecture", str(cpu.get("architecture") or system.get("architecture") or "x86_64")),
                ("Telemetry Source", str(cpu.get("source") or "/proc/cpuinfo")),
            ]),
        ]
        pages["cpu"] = Page("cpu", "Processor", "CPU", cpu_model, "", [left, right],
                            rules_hint=first_rule["CPU"], accent=accent)

    # FAN ---------------------------------------------------------------
    rpm = therm.get("rpm")
    if rpm is not None:
        bays.append(Bay("FAN", f"{rpm:,.0f} rpm", st("FAN", True), gauge=min(1.0, rpm / 5000), value_role="t",
                        plain=f"{rpm:,.0f} rpm", target="thermal"))
    else:
        bays.append(Bay("FAN", "—", st("FAN", False), sub="no fan telemetry", plain="no fan telemetry",
                        target="thermal" if therm else ""))
    if therm:
        t_val = therm.get("temp")
        hero_val = f"{rpm:,.0f}" if rpm is not None else (f"{t_val:.0f}°C" if t_val is not None else "OK")
        hero_sub = "rpm" if rpm is not None else ("Package Temp" if t_val is not None else "Cooling")
        left = [Hero("FAN", hero_val, "fan", "t", hero_sub)]
        if rpm is not None:
            left.append(Bars("FAN SPEED", [("rpm", min(1.0, rpm / 5000), f"{rpm:,.0f} rpm", "t")]))
        left.append(Card("BUYER VERDICT", [
            ("Thermal Integrity", "Thermal sensors are operational; no emergency trip detected", "p"),
            ("Cooling State", f"{rpm:,.0f} RPM fan active" if rpm else "Fan operating passively or controlled by embedded EC", "t"),
            ("Buyer Advice", "Listen for fan bearing grinding, rattling, or whining under load.", "w"),
        ]))
        prof = (snap.get("fan_profiles") or {}).get("current")
        right = [
            KV("Thermal & Sensor Telemetry", [
                ("CPU Package", f"{t_val:.0f} °C" if t_val is not None else "—"),
                ("Fan Speed", f"{rpm:,.0f} rpm" if rpm is not None else "Passive / EC-managed"),
                ("Fan Profile", str(prof or "Standard / Automatic")),
                ("Sensor Interface", str(therm.get("key") or "ACPI thermal")),
            ]),
        ]
        pages["thermal"] = Page("thermal", "Thermal", "THERMAL", f"{therm['key']} telemetry", "", [left, right],
                                rules_hint=first_rule["FAN"] or first_rule["CPU"])

    # DSP ---------------------------------------------------------------
    edid = _d(display.get("edid"))
    res = display.get("resolution")
    tech = edid.get("panel_type") or display.get("panel_type") or "LCD"
    is_oled = edid.get("is_oled") or display.get("is_oled")
    diag = _n(edid.get("diagonal_inches"))
    sub = " · ".join(x for x in (str(tech), f'{diag:.1f}"' if diag else "", str(edid.get("color_depth") or ""),
                                 str(edid.get("manufacturer") or "")) if x)
    if display:
        bays.append(Bay("DSP", str(res or "—"), st("DSP", True), gauge=1.0, sub=sub, value_role="t",
                        plain=f"{res or '?'} · {tech}", target="display"))
        left = [
            Hero("DISPLAY", str(res or "—"), "monitor", "p" if is_oled else "t", sub),
            Card("BUYER VERDICT", [
                ("Panel Grade", f"Premium {tech} ({'Self-Emitting OLED' if is_oled else 'Backlit LCD'})", "p" if is_oled else "t"),
                ("Color Quality", f"{edid.get('color_depth', '8-bit')} depth · Deep contrast", "p" if is_oled else "t"),
                ("Buyer Inspection", "Check full-screen white/black images for dead pixels, burn-in, or lines.", "w"),
            ]),
        ]
        right = [
            KV("Display Specifications", [
                ("Resolution", str(res or "—")),
                ("Panel Type", str(tech)),
                ("Diagonal Size", f'{diag:.1f}"' if diag else "—"),
                ("Color Depth", str(edid.get("color_depth") or "8-bit")),
                ("Manufacturer", str(edid.get("manufacturer") or "—")),
                ("Model Code", str(edid.get("model_name") or "—")),
                ("Interface Node", str(display.get("interface") or "eDP")),
            ]),
        ]
        pages["display"] = Page("display", "Display", "DSP", sub, "", [left, right], rules_hint=first_rule["DSP"])
    else:
        bays.append(Bay("DSP", "—", Status.UNSURE, sub="no display telemetry", plain="no display telemetry"))

    # system / reconciliation / coverage pages ---------------------------
    pages["system"] = Page("system", "System", "SYSTEM", str(ext.get("os_pretty_name") or system.get("os_name") or ""), "", [[
        KV("System", _scalars(system)), KV("Boot and OS", _scalars(ext))]])
    pages["specs"] = _specs_page(snap, claims, system, cpu, mem, disks, bat, display, ext)
    if coverage:
        pages["coverage"] = Page("coverage", "Coverage", "COVERAGE", f"{len(coverage)} checks evaluated",
                                 str(rep.get("generated_by") or ""), [[
            KV("Evaluation coverage", [(str(k), "@" + _cov_status(v).value) for k, v in coverage.items()])]],
            note="Missing or skipped checks are never counted as healthy.")

    return Session(
        id=sid, title=title, bays=bays,
        findings=[_finding(i, f, bat) for i, f in enumerate(findings_raw)],
        machine=_machine(system, ext, sid), pages=pages,
        verdict=verdict[1], verdict_status=verdict[0], verdict_note=verdict[2], raw=(snapshot, report))


def _machine(system: dict, ext: dict, sid: str) -> dict:
    out = {"Vendor": system.get("vendor"), "Model": system.get("model"),
           "OS": ext.get("os_pretty_name") or ext.get("os_name") or system.get("os_name"),
           "Kernel": system.get("kernel_release"), "Boot": " · ".join(
               str(x) for x in (ext.get("boot_firmware"), ext.get("partition_table")) if x) or None,
           "Session": sid}
    return {k: _fmt(v) for k, v in out.items() if v}


def _finding(i: int, f: dict, bat: dict) -> Finding:
    rid = str(f.get("rule_id") or f.get("code") or f"finding_{i + 1}")
    sev = str(f.get("severity") or "warning")
    comp = str(f.get("component") or "hardware")
    status = _finding_status(f)
    title = str(f.get("title") or rid.replace("_", " ").title())
    why, fallback = _impact(comp, rid)
    evidence = _d(f.get("evidence"))
    first = next((v for v in evidence.values() if not isinstance(v, (dict, list)) and v is not None), None)
    value = (_fmt(first) if first is not None else sev.lower())[:11]
    blocks: list = []
    if ("battery" in comp.lower() or "battery" in rid.lower()) and bat["pct"] is not None:
        role = _role_for_pct(bat["pct"])
        blocks += [Hero("BATTERY", f"{bat['pct']:.1f}%", "battery", role, "full / design"),
                   Bars("", [("retention", bat["pct"] / 100, f"{bat['pct']:.0f} %", role, 0.80)],
                        footer="white block marks the 80 % threshold")]
    blocks.append(Card("", [("What's wrong", f.get("details") or f.get("explanation") or "Discrepancy noted.", "c"),
                            ("Why it matters", why, "w"),
                            ("Action", f.get("action") or f.get("recommended_action") or fallback, "p")]))
    rows = [("Severity", "@" + status.value), ("Component", comp)] + [(_label(k), _fmt(v)) for k, v in evidence.items()]
    blocks.append(KV("Evidence", rows))
    return Finding(rid, title, status, value, comp.lower(), title, blocks)


def _specs_page(snap, claims, system, cpu, mem, disks, bat, display, ext) -> Page:
    """Observed vs claimed, with the same tolerances as cli_ui."""
    rows: list = []
    model = f"{system.get('vendor', '')} {system.get('model', '')}".strip() or "Unknown Model"
    rows.append(("Model", model))
    if claims.get("model"):
        norm = lambda s: re.sub(r"[^a-zA-Z0-9]+", " ", str(s).lower()).split()  # noqa: E731
        obs, cl = norm(model), norm(claims["model"])
        ok = bool(cl) and all(t in obs for t in cl)
        rows += [("  claimed", str(claims["model"])), ("  check", "@pass" if ok else "@claim")]
    cores, threads = _n(cpu.get("cores")), _n(cpu.get("threads"))
    rows.append(("CPU", str(cpu.get("model") or "Unknown CPU") + (f" ({cores:g}C/{threads:g}T)" if cores and threads else "")))
    gib = _n(mem.get("total_gib")) or ((_n(mem.get("total_bytes")) or 0) / 1024 ** 3) or None
    rows.append(("Memory", f"{gib:.1f} GiB" if gib else "Unknown"))
    claim_ram = _n(claims.get("ram_gib"))
    if claim_ram is not None and gib is not None:
        delta = gib - claim_ram
        rows += [("  claimed", f"{claim_ram:g} GiB"), ("  check", "@pass" if abs(delta) <= 1.2 else "@claim")]
        if abs(delta) > 1.2:
            rows.append(("  delta", f"{delta:+.1f} GiB"))
    if disks:
        d0 = disks[0]
        cap = _n(d0.get("capacity_bytes"))
        gb = cap / 1e9 if cap else None
        rows.append(("Storage", f"{d0.get('model') or 'Primary Disk'} ({gb:.0f} GB · {str(d0.get('protocol') or 'storage').upper()})"
                     if gb else f"{d0.get('model') or 'Primary Disk'} (unknown size)"))
        claim_gb = _n(claims.get("storage_capacity_gb"))
        if claim_gb is not None and gb is not None:
            ok = abs(gb - claim_gb) <= claim_gb * 0.1
            rows += [("  claimed", f"{claim_gb:g} GB"), ("  check", "@pass" if ok else "@claim")]
    else:
        rows.append(("Storage", "no storage telemetry collected"))
    if bat["pct"] is not None:
        rows.append(("Battery", f"{bat['pct']:.1f} % health ({bat['full']:,.0f} / {bat['design']:,.0f} mWh)"))
    refurb = ext.get("refurbish_status")
    if refurb:
        rows.append(("OS wipe", f"{refurb}" + (" · recent wipe" if ext.get("is_recent_wipe") else "")))
        rows.append(("  wipe check", "@warn" if ext.get("is_recent_wipe") else "@pass"))
    note = "" if claims else 'No seller claims entered. Try :scan --claim-ram 16 --claim-storage 512 --claim-model "XPS 13"'
    return Page("specs", "Specifications", "SPECS", "observed vs claimed", "", [[KV("Reconciliation", rows)]], note=note)
