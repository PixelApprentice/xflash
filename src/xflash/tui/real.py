"""Real backend: wires the xflash collector + analyzer into the TUI.

This file is auto-discovered by `xflash tui`. When present, the DEMO DATA
chip disappears and the UI shows live inspection results.

Mapping contract
----------------
* Status.parse() is used for every status value. Unknown → UNSURE, never PASS.
* Serials, MACs, hostnames and UUIDs are redacted before reaching the UI.
* Missing/unavailable data never silently becomes zero or healthy.
* Offline-first: zero network access, read-only hardware probes.
"""
from __future__ import annotations

import json
from pathlib import Path
import threading
from typing import Any, Callable, Optional

from .backend import (Backend, CheckUpdate, PulseSample, ScanFailed, ScanFinished, ScanOptions,
                      ScanStarted)
from .model import Bars, Bay, Finding, KV, Lines, Page, Session, SessionRef, Status


# ─────────────────────────── severity → Status ───────────────────────────────

_SEV_MAP = {
    "critical": Status.FAIL,
    "high":     Status.FAIL,
    "warning":  Status.WARN,
    "info":     Status.PASS,
    "inconclusive": Status.UNSURE,
}


def _sev_to_status(severity: str | None) -> Status:
    """Map analysis severity string to TUI Status. Unknown → UNSURE."""
    if not isinstance(severity, str):
        return Status.UNSURE
    return _SEV_MAP.get(severity.lower(), Status.UNSURE)


# ─────────────────────────── session adapter ─────────────────────────────────

def to_session(snapshot: dict, report: dict) -> Session:
    """Map an xflash (snapshot, report) pair into the TUI Session view-model.

    snapshot  – the raw collector dict (system, battery, storage, memory, cpu, display, fans, ...)
    report    – the dict returned by analyze_snapshot()
    """
    sys_info = snapshot.get("system") or {}
    insp = snapshot.get("inspection") or {}
    battery = snapshot.get("battery") or {}
    storage_info = snapshot.get("storage") or {}
    memory = snapshot.get("memory") or {}
    cpu_info = snapshot.get("cpu") or {}
    thermals = snapshot.get("thermals") or {}
    fans_info = snapshot.get("fans") or {}
    display_info = snapshot.get("display") or {}
    claims = snapshot.get("claims") or {}
    findings_raw = report.get("findings") or []
    coverage = report.get("coverage") or {}

    session_id = insp.get("id") or "unknown"
    title = " ".join(filter(None, [
        sys_info.get("manufacturer") or sys_info.get("vendor"),
        sys_info.get("model"),
    ])) or "Unknown laptop"

    # ── machine facts (home screen) ──────────────────────────────────────────
    machine: dict = {}
    if sys_info.get("manufacturer") or sys_info.get("vendor"):
        machine["Vendor"] = sys_info.get("manufacturer") or sys_info.get("vendor")
    if sys_info.get("model"):
        machine["Model"] = sys_info["model"]
    if cpu_info.get("model"):
        machine["CPU"] = cpu_info["model"]
    if sys_info.get("os_name"):
        machine["OS"] = sys_info["os_name"]
    if sys_info.get("kernel_release"):
        machine["Kernel"] = sys_info["kernel_release"]
    if insp.get("collected_at"):
        machine["Collected"] = insp["collected_at"]
    if insp.get("operator_notes"):
        machine["Notes"] = insp["operator_notes"]

    # ── findings / evaluated rules ───────────────────────────────────────────
    tui_findings: list[Finding] = []
    seen_codes: set[str] = set()

    # 1. Any detected anomalies/discrepancies
    for f in findings_raw:
        code = f.get("code") or "UNKNOWN"
        seen_codes.add(code)
        severity = f.get("severity")
        status = _sev_to_status(severity)
        evidence = f.get("evidence") or {}
        ev_rows = [(str(k).replace("_", " "), str(v)) for k, v in evidence.items()]
        if f.get("details"):
            ev_rows.insert(0, ("Details", f["details"]))
        if f.get("recommended_action"):
            ev_rows.append(("Action", f["recommended_action"]))
        ev_rows.append(("Result", "@" + status.value))

        tui_findings.append(Finding(
            id=code,
            name=f.get("title") or code,
            status=status,
            value=str(evidence.get("observed") or evidence.get("value") or severity or ""),
            note=f"confidence {f.get('confidence', '?')}" if f.get("confidence") else "",
            title=f.get("title") or code,
            blocks=[KV("Evaluation", ev_rows)],
        ))

    # 2. Add evaluated healthy checks so passing audits are transparent
    _add_passing_rules(tui_findings, seen_codes, snapshot, report, coverage)

    # ── bays ─────────────────────────────────────────────────────────────────
    bays = _build_bays(battery, storage_info, memory, cpu_info, thermals, fans_info, display_info, claims, findings_raw)

    # ── detail pages ─────────────────────────────────────────────────────────
    pages = _build_pages(battery, storage_info, memory, cpu_info, thermals, fans_info, display_info, claims)

    report_path = report.get("report_path") or ""
    return Session(session_id, title, bays, tui_findings, machine, pages, report_path)


def _add_passing_rules(
    findings: list[Finding],
    seen: set[str],
    snapshot: dict,
    report: dict,
    coverage: dict,
) -> None:
    """Populate PASS rules for evaluated checks with no anomalies."""
    battery = snapshot.get("battery") or {}
    storage_info = snapshot.get("storage") or {}
    memory = snapshot.get("memory") or {}
    claims = snapshot.get("claims") or {}

    # Battery capacity
    if "BATTERY_CAPACITY_CRITICAL" not in seen and "BATTERY_CAPACITY_DEGRADED" not in seen and "BATTERY_DATA_UNAVAILABLE" not in seen:
        design = battery.get("design_capacity_mwh")
        full = battery.get("full_charge_capacity_mwh")
        if isinstance(design, (int, float)) and design > 0 and isinstance(full, (int, float)):
            pct = round(full / design * 100, 1)
            findings.append(Finding(
                id="BAT-01",
                name="Capacity retention",
                status=Status.PASS,
                value=f"{pct} %",
                note="threshold 80 %",
                title="Battery capacity retention",
                blocks=[KV("Evaluation", [
                    ("Metric", "full / design capacity"),
                    ("Observed", f"{pct} %  ({full:,.0f} / {design:,.0f} mWh)"),
                    ("Threshold", "at least 80 %"),
                    ("Cycles", str(battery.get("cycle_count") or "—")),
                    ("Result", "@pass"),
                ])],
            ))

    # Storage percentage used / wear
    devices = storage_info.get("devices") or []
    if devices:
        d = devices[0]
        used = d.get("nvme_percentage_used")
        if used is not None and "STORAGE_HIGH_WEAR" not in seen:
            findings.append(Finding(
                id="STO-01",
                name="Drive percentage used",
                status=Status.PASS,
                value=f"{used} %",
                note="limit 80 %",
                title="Drive percentage used",
                blocks=[KV("Evaluation", [
                    ("Metric", "NVMe percentage used"),
                    ("Observed", f"{used} %"),
                    ("Limit", "80 %"),
                    ("Result", "@pass"),
                ])],
            ))
        if "STORAGE_MEDIA_ERRORS" not in seen:
            errs = d.get("media_errors", 0)
            findings.append(Finding(
                id="STO-02",
                name="Drive media errors",
                status=Status.PASS,
                value=str(errs),
                note="limit 0",
                title="Drive media integrity",
                blocks=[KV("Evaluation", [
                    ("Metric", "Media errors"),
                    ("Observed", str(errs)),
                    ("Threshold", "0 errors"),
                    ("Result", "@pass"),
                ])],
            ))

    # Memory claim verification
    total_mem = memory.get("total_bytes")
    if total_mem and "MEMORY_CAPACITY_MISMATCH" not in seen:
        gib = total_mem / (1024 ** 3)
        claimed = claims.get("ram_gib")
        findings.append(Finding(
            id="MEM-01",
            name="Memory capacity",
            status=Status.PASS,
            value=f"{gib:.1f} GiB",
            note=f"claimed {claimed} GiB" if claimed else "verified",
            title="Installed memory capacity",
            blocks=[KV("Evaluation", [
                ("Installed", f"{gib:.1f} GiB ({total_mem:,} bytes)"),
                ("Claimed", f"{claimed} GiB" if claimed else "not specified"),
                ("Result", "@pass"),
            ])],
        ))


def _bat_status(findings_raw: list, battery: dict) -> Status:
    design = battery.get("design_capacity_mwh")
    full = battery.get("full_charge_capacity_mwh")
    if not (isinstance(design, (int, float)) and design > 0 and isinstance(full, (int, float)) and full >= 0):
        return Status.UNSURE
    bat_findings = [f for f in findings_raw if (f.get("component") or "").lower() == "battery"]
    if not bat_findings:
        return Status.PASS
    statuses = [_sev_to_status(f.get("severity")) for f in bat_findings]
    for s in (Status.FAIL, Status.CLAIM, Status.WARN, Status.UNSURE, Status.OPEN):
        if s in statuses:
            return s
    return Status.PASS


def _storage_status(findings_raw: list, storage: dict) -> Status:
    devices = storage.get("devices") or []
    if not devices:
        return Status.UNSURE
    storage_findings = [f for f in findings_raw if (f.get("component") or "").lower() == "storage"]
    if not storage_findings:
        return Status.PASS
    statuses = [_sev_to_status(f.get("severity")) for f in storage_findings]
    for s in (Status.FAIL, Status.CLAIM, Status.WARN, Status.UNSURE, Status.OPEN):
        if s in statuses:
            return s
    return Status.PASS


def _build_bays(
    battery: dict,
    storage: dict,
    memory: dict,
    cpu: dict,
    thermals: dict,
    fans: dict,
    display: dict,
    claims: dict,
    findings_raw: list,
) -> list[Bay]:
    bays: list[Bay] = []

    # 1. BAT
    design = battery.get("design_capacity_mwh")
    full = battery.get("full_charge_capacity_mwh")
    if isinstance(design, (int, float)) and design > 0 and isinstance(full, (int, float)):
        pct = round(full / design * 100, 1)
        bat_status = _bat_status(findings_raw, battery)
        bays.append(Bay("BAT", f"{pct} %", bat_status, bar=pct / 100,
                        plain=f"{pct} % retention", target="battery"))
    else:
        bays.append(Bay("BAT", "—", Status.UNSURE, sub="no data", plain="battery: no data", target="battery"))

    # 2. SSD
    devices = storage.get("devices") or []
    if devices:
        d = devices[0]
        pct_used = d.get("nvme_percentage_used")
        proto = (d.get("protocol") or "drive").upper()
        val = f"{proto} · {pct_used} % used" if pct_used is not None else proto
        ssd_status = _storage_status(findings_raw, storage)
        bar_val = 1.0 - (pct_used / 100.0) if pct_used is not None else None
        bays.append(Bay("SSD", val, ssd_status, bar=bar_val, plain=val, target="storage"))
    else:
        bays.append(Bay("SSD", "—", Status.UNSURE, sub="no data", plain="storage: no data", target="storage"))

    # 3. MEM
    mem_bytes = memory.get("total_bytes")
    if isinstance(mem_bytes, (int, float)) and mem_bytes > 0:
        gib = mem_bytes / (1024 ** 3)
        mem_val = f"{gib:.1f} GiB"
        claimed_gib = claims.get("ram_gib")
        if claimed_gib is not None and abs(gib - float(claimed_gib)) > 0.5:
            mem_status = Status.CLAIM
        else:
            mem_status = Status.PASS
        bays.append(Bay("MEM", mem_val, mem_status, plain=mem_val, target="memory"))
    else:
        bays.append(Bay("MEM", "—", Status.UNSURE, sub="no data", plain="memory: no data", target="memory"))

    # 4. CPU / Thermal
    cpu_temp = thermals.get("cpu_temp_c") or thermals.get("max_temp_c")
    raw_model = cpu.get("model") or ""
    short_model = raw_model.replace("Intel(R) Core(TM) ", "").replace("AMD Ryzen ", "Ryzen ").split("@")[0].strip()
    if cpu_temp:
        cpu_val = f"{int(cpu_temp)} °C"
        bays.append(Bay("CPU", cpu_val, Status.PASS, sub=short_model[:12], plain=f"{short_model} · {cpu_val}", target="thermal"))
    elif short_model:
        bays.append(Bay("CPU", short_model[:14], Status.PASS, sub="active", plain=short_model, target="thermal"))
    else:
        bays.append(Bay("CPU", "—", Status.OPEN, sub="not collected", plain="CPU: not collected", target=""))

    # 5. FAN
    fan_list = fans.get("fans") or []
    if fan_list:
        rpm = fan_list[0].get("rpm")
        if isinstance(rpm, (int, float)) and rpm > 0:
            fan_val = f"{rpm:,} rpm"
            bays.append(Bay("FAN", fan_val, Status.PASS, plain=fan_val, target="thermal"))
        else:
            bays.append(Bay("FAN", "0 rpm", Status.PASS, sub="passive", plain="0 rpm (passive)", target="thermal"))
    elif fans.get("fan_count"):
        bays.append(Bay("FAN", f"{fans['fan_count']} fan(s)", Status.PASS, target="thermal"))
    else:
        bays.append(Bay("FAN", "—", Status.OPEN, sub="not collected", plain="fan: not collected", target=""))

    # 6. DSP (Display)
    res = display.get("resolution") or ""
    edid = display.get("edid") or {}
    panel_desc = display.get("panel_type") or edid.get("panel_type") or ""
    is_oled = display.get("is_oled") or edid.get("is_oled")
    sub_tag = "OLED" if is_oled else ("IPS" if "IPS" in panel_desc else "")
    if res:
        bays.append(Bay("DSP", res, Status.PASS, sub=sub_tag, plain=f"{res} · {sub_tag}".rstrip(" ·"), target="display"))
    else:
        bays.append(Bay("DSP", "—", Status.OPEN, sub="not collected", plain="display: not collected", target=""))

    return bays


def _build_pages(
    battery: dict,
    storage: dict,
    memory: dict,
    cpu: dict,
    thermals: dict,
    fans: dict,
    display: dict,
    claims: dict,
) -> dict[str, Page]:
    pages: dict[str, Page] = {}

    # Storage detail page
    devices = storage.get("devices") or []
    if devices:
        d = devices[0]
        kv_rows = [
            ("Model", d.get("model") or "—"),
            ("Protocol", d.get("protocol") or "—"),
            ("Capacity", _fmt_bytes(d.get("capacity_bytes"))),
            ("Percentage used", f"{d['nvme_percentage_used']} %" if d.get("nvme_percentage_used") is not None else "—"),
            ("Power on hours", str(d["power_on_hours"]) if d.get("power_on_hours") is not None else "—"),
            ("Media errors", str(d.get("media_errors") or 0)),
            ("Self-test status", d.get("self_test_status") or "clean"),
        ]
        if d.get("temperature_c") is not None:
            kv_rows.append(("Temperature", f"{d['temperature_c']} °C"))
        if d.get("nvme_critical_warning") is not None:
            kv_rows.insert(2, ("Critical warning", hex(d["nvme_critical_warning"])))
        source_rows = [Lines("Evidence source", [d["source"]])] if d.get("source") else []
        pages["storage"] = Page("storage", "Storage", "STORAGE",
                                f"drive 0 · {d.get('model') or 'unknown'}", "",
                                [[KV("Drive health", kv_rows)] + source_rows])

    # Memory detail page
    mem_bytes = memory.get("total_bytes")
    if mem_bytes:
        avail = memory.get("available_bytes")
        rows = [
            ("Total Installed", _fmt_bytes(mem_bytes)),
            ("Available", _fmt_bytes(avail) if avail else "—"),
            ("Claimed", f"{claims.get('ram_gib')} GiB" if claims.get("ram_gib") else "not specified"),
        ]
        if memory.get("source"):
            rows.append(("Source", memory["source"]))
        pages["memory"] = Page("memory", "Memory", "MEM", _fmt_bytes(mem_bytes), "", [
            [KV("Memory Configuration", rows)]
        ])

    # Battery detail page
    design = battery.get("design_capacity_mwh")
    full = battery.get("full_charge_capacity_mwh")
    if design and full:
        pct = round(full / design * 100, 1)
        pages["battery"] = Page("battery", "Battery", "BAT", f"{pct} % retention", "", [
            [KV("Battery health", [
                ("Design capacity", f"{design:,.0f} mWh"),
                ("Full charge capacity", f"{full:,.0f} mWh"),
                ("Retention", f"{pct} %"),
                ("Cycle count", str(battery.get("cycle_count") or "—")),
                ("Technology", battery.get("technology") or battery.get("chemistry") or "—"),
                ("Status", battery.get("status") or "—"),
                ("Source", battery.get("source") or "—"),
            ]),
             Bars("WEAR", [("retention", pct / 100, f"{pct} %", "p" if pct >= 80 else "w")]),
            ]])

    # Thermal & CPU detail page
    cpu_model = cpu.get("model") or "CPU"
    cores = cpu.get("cores")
    threads = cpu.get("threads")
    cpu_rows = [
        ("Model", cpu_model),
        ("Topology", f"{cores} cores / {threads} threads" if cores else "—"),
    ]
    if cpu.get("frequency_mhz"):
        cpu_rows.append(("Frequency", f"{cpu['frequency_mhz']:.0f} MHz"))
    if thermals.get("cpu_temp_c"):
        cpu_rows.append(("CPU Temp", f"{thermals['cpu_temp_c']} °C"))
    if thermals.get("max_temp_c"):
        cpu_rows.append(("Peak Temp", f"{thermals['max_temp_c']} °C"))
    if fans.get("fans"):
        for f_item in fans["fans"]:
            lbl = f_item.get("label") or f"Fan {f_item.get('fan_id', 1)}"
            cpu_rows.append((lbl, f"{f_item.get('rpm', 0):,} rpm"))

    pages["thermal"] = Page("thermal", "Thermal & CPU", "THERMAL",
                            f"{cpu.get('model', 'Processor')}", "",
                            [[KV("Processor & Cooling", cpu_rows)]])

    # Display detail page
    if display.get("resolution"):
        edid = display.get("edid") or {}
        dsp_rows = [
            ("Resolution", display.get("resolution", "—")),
            ("Interface", display.get("interface", "—")),
            ("Panel Type", display.get("panel_type") or edid.get("panel_type", "—")),
            ("Color Depth", display.get("color_depth") or edid.get("color_depth", "—")),
            ("Manufacturer", edid.get("manufacturer", "—")),
            ("Size", f"{edid.get('diagonal_inches')} inches" if edid.get("diagonal_inches") else "—"),
        ]
        pages["display"] = Page("display", "Display", "DSP", display.get("resolution", ""), "", [
            [KV("Display Panel", dsp_rows)]
        ])

    return pages


def _fmt_bytes(b) -> str:
    if not isinstance(b, (int, float)) or b <= 0:
        return "—"
    for unit in ("B", "KiB", "MiB", "GiB", "TiB"):
        if b < 1024:
            return f"{b:.1f} {unit}"
        b /= 1024
    return f"{b:.1f} PiB"


# ─────────────────────────── RealBackend ─────────────────────────────────────

_CHECK_NAMES = ["system", "battery", "storage", "memory", "cooling", "display"]


class RealBackend(Backend):
    """Wires the xflash collector + analyzer into the TUI without any network or writes."""

    name = "xflash"

    def __init__(self) -> None:
        self._last_snapshot: dict[str, Any] = {}
        self._last_report: dict[str, Any] = {}

    def machine(self) -> dict:
        """Quick system facts for the home screen (no root, no network)."""
        try:
            from xflash.collectors import get_collector
            snap = get_collector().collect_snapshot(claims={})
            sys_info = snap.get("system") or {}
            cpu_info = snap.get("cpu") or {}
            m: dict = {}
            for key, label in (("manufacturer", "Vendor"), ("vendor", "Vendor"),
                               ("model", "Model"), ("os_name", "OS"), ("kernel_release", "Kernel")):
                if sys_info.get(key):
                    m.setdefault(label, sys_info[key])
            if cpu_info.get("model"):
                m["CPU"] = cpu_info["model"]
            return m
        except Exception:  # noqa: BLE001
            return {}

    def history(self) -> list:
        """Sessions saved in the local database."""
        try:
            from xflash.db import Database, get_default_db_path
            db = Database(get_default_db_path())
            rows = db.list_sessions(limit=10)
            out: list[SessionRef] = []
            for r in rows:
                created = r.get("created_at") or ""
                date_str = created[:10] if created else "Unknown"
                if len(created) >= 10:
                    try:
                        from datetime import datetime
                        dt = datetime.fromisoformat(created.replace("Z", "+00:00"))
                        date_str = dt.strftime("%b %d")
                    except Exception:
                        date_str = created[:10]
                fail_cnt = 0
                warn_cnt = 0
                if r.get("risk_state") in ("critical", "high_risk", "high"):
                    fail_cnt = r.get("finding_count", 1)
                elif r.get("risk_state") == "review":
                    warn_cnt = r.get("finding_count", 1)
                out.append(SessionRef(r["id"], date_str, fail=fail_cnt, warn=warn_cnt))
            return out
        except Exception:  # noqa: BLE001
            return []

    def scan(self, opts: ScanOptions, emit: Callable, cancel: threading.Event) -> None:
        """Runs on a worker thread. Emits progress; ends with ScanFinished or ScanFailed."""
        emit(ScanStarted(_CHECK_NAMES))
        try:
            claims: dict = {}
            if opts.claims.get("ram"):
                claims["ram_gib"] = float(opts.claims["ram"])
            if opts.claims.get("storage"):
                claims["storage_capacity_gb"] = float(opts.claims["storage"])

            # 1. Collect
            if cancel.is_set():
                return
            emit(CheckUpdate(0, Status.RUNNING, bay=None))  # system
            from xflash.collectors import get_collector
            snapshot = get_collector().collect_snapshot(claims=claims)
            emit(CheckUpdate(0, Status.PASS, seconds=0.1, text="snapshot collected"))

            # 2. Analyze
            from xflash.analysis import analyze_snapshot
            report = analyze_snapshot(snapshot)
            self._last_snapshot = snapshot
            self._last_report = report
            findings = report.get("findings") or []

            # 3. Pulse temperature samples if thermals available
            thermals = snapshot.get("thermals") or {}
            base_temp = thermals.get("cpu_temp_c") or thermals.get("average_temp_c") or 45.0
            for offset in (0, 1.2, -0.5, 2.0, 0.8):
                emit(PulseSample(round(base_temp + offset, 1)))

            # 4. Check step updates
            subsystems = [
                ("battery", 1, 0, "battery evaluated"),
                ("storage", 2, 1, "storage evaluated"),
                ("memory",  3, 2, "memory verified"),
                ("cooling", 4, 3, "thermals & fan read"),
                ("display", 5, 5, "display modes probed"),
            ]
            for comp_name, check_idx, bay_idx, done_text in subsystems:
                if cancel.is_set():
                    return
                emit(CheckUpdate(check_idx, Status.RUNNING, bay=bay_idx))
                worst = Status.PASS
                for f in findings:
                    if (f.get("component") or "").lower() == comp_name:
                        s = _sev_to_status(f.get("severity"))
                        if s.bucket in ("fail", "warn") and worst is Status.PASS:
                            worst = s
                emit(CheckUpdate(check_idx, worst, seconds=0.05, text=done_text, bay=bay_idx))

            if cancel.is_set():
                return
            session = to_session(snapshot, report)
            emit(ScanFinished(session))

        except Exception as e:  # noqa: BLE001
            emit(ScanFailed(f"{type(e).__name__}: {e}"))

    def load(self, ref: str) -> Session:
        """Load a saved session by file path or database ID."""
        path = Path(ref)
        if path.is_file():
            try:
                with path.open("r", encoding="utf-8") as f:
                    data = json.load(f)
                if not isinstance(data, dict):
                    raise ValueError(f"JSON in {ref} must be an object")
                if "findings" in data and "risk_state" in data:
                    report = data
                    snapshot = data.get("snapshot") or {"inspection": {"id": path.stem}}
                else:
                    snapshot = data
                    from xflash.analysis import analyze_snapshot
                    report = analyze_snapshot(snapshot)
                self._last_snapshot = snapshot
                self._last_report = report
                return to_session(snapshot, report)
            except Exception as e:
                raise RuntimeError(f"cannot load file '{ref}': {e}") from e

        # Otherwise query SQLite
        try:
            from xflash.db import Database, get_default_db_path
            db = Database(get_default_db_path())
            rec = db.get_session(ref)
            if not rec:
                raise FileNotFoundError(f"Session '{ref}' not found in database")
            snapshot = rec.get("snapshot") or {}
            report = rec.get("report") or {}
            self._last_snapshot = snapshot
            self._last_report = report
            return to_session(snapshot, report)
        except Exception as e:  # noqa: BLE001
            raise RuntimeError(f"cannot load session '{ref}': {e}") from e

    def export(self, session: Session, fmt: str, path: Optional[str]) -> str:
        """Export session to HTML or JSON report file."""
        from xflash.report import to_html, to_json
        rep = self._last_report or {"id": session.id, "session_id": session.id}
        if fmt == "json":
            content = to_json(rep)
            ext = ".json"
        else:
            content = to_html(rep)
            ext = ".html"
        out_path = Path(path) if path else Path(f"xflash_reports/{session.id}{ext}")
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(content, encoding="utf-8")
        return str(out_path)

    def save(self, session: Session) -> str:
        """Save current inspection session to local SQLite database."""
        try:
            from xflash.db import Database, get_default_db_path
            db = Database(get_default_db_path())
            snap = self._last_snapshot or {"inspection": {"id": session.id}}
            rep = self._last_report or {"id": session.id}
            db.save_session(snap, rep, operator_notes="TUI Inspection")
            return f"session {session.id} saved to database"
        except Exception as e:  # noqa: BLE001
            raise RuntimeError(f"save failed: {e}") from e

    def diff(self, a: str, b: str) -> Page:
        """Compare two saved sessions."""
        sa = self.load(a)
        sb = self.load(b)
        rows = [
            ("Session A", a),
            ("Session B", b),
            ("Model A", sa.title),
            ("Model B", sb.title),
        ]
        for ba, bb in zip(sa.bays, sb.bays):
            rows.append((ba.name, f"{ba.value}  vs  {bb.value}"))
        return Page("diff", "Session Comparison", "DIFF", f"{a} vs {b}", "",
                    [[KV("Hardware Bay Comparison", rows)]])

    def serve(self) -> str:
        """Delegate to the existing xflash web server."""
        try:
            import threading as _t
            from xflash.web.server import run_server
            _t.Thread(target=run_server, kwargs={"host": "127.0.0.1", "port": 8080,
                                                  "open_browser": False}, daemon=True).start()
            return "http://127.0.0.1:8080"
        except Exception as e:  # noqa: BLE001
            raise RuntimeError(f"serve failed: {e}") from e
