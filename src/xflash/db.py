"""Offline SQLite database layer for inspection session persistence.

This module provides deterministic local storage for sessions, claims,
findings, manual test results, and test coverage matrices with zero external dependencies.
"""
from __future__ import annotations

import json
import os
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Generator


def _iso_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def get_portable_dir() -> Path:
    """Return the base directory for portable mode (where .portable or repository root is located)."""
    env_dir = os.environ.get("XFLASH_PORTABLE_DIR") or os.environ.get("AEGIS_PORTABLE_DIR")
    if env_dir:
        return Path(env_dir).resolve()

    current = Path(__file__).resolve().parent
    for parent in [current, current.parent, current.parent.parent, current.parent.parent.parent]:
        if (parent / ".portable").is_file() or (parent / "autorun.inf").is_file():
            return parent

    return Path.cwd().resolve()


def is_portable_mode() -> bool:
    """Return True if portable mode is requested via env, flag, or marker file."""
    if os.environ.get("XFLASH_PORTABLE") in ("1", "true", "yes", "on"):
        return True
    if os.environ.get("AEGIS_PORTABLE") in ("1", "true", "yes", "on"):
        return True
    if os.environ.get("LAPTOP_INSPECTOR_PORTABLE") in ("1", "true", "yes", "on"):
        return True
    portable_marker = get_portable_dir() / ".portable"
    return portable_marker.is_file()


def get_default_db_path(portable: bool | None = None) -> Path:
    """Resolve database path depending on portable vs normal system mode."""
    if portable is None:
        portable = is_portable_mode()

    if portable:
        p_dir = get_portable_dir()
        if (p_dir / "aegis_data" / "inspections.sqlite3").is_file() and not (p_dir / "xflash_data" / "inspections.sqlite3").is_file():
            return p_dir / "aegis_data" / "inspections.sqlite3"
        return p_dir / "xflash_data" / "inspections.sqlite3"

    # Normal mode: platform standard app data
    if os.name == "nt":
        base = Path(os.environ.get("LOCALAPPDATA", Path.home() / "AppData" / "Local"))
        return base / "xflash" / "inspections.sqlite3"
    return Path.home() / ".local" / "share" / "xflash" / "inspections.sqlite3"


def get_reports_dir(portable: bool | None = None) -> Path:
    """Return the directory where generated inspection reports are saved."""
    if portable is None:
        portable = is_portable_mode()

    if portable:
        p_dir = get_portable_dir()
        if (p_dir / "aegis_reports").is_dir() and not (p_dir / "xflash_reports").is_dir():
            p = p_dir / "aegis_reports"
        else:
            p = p_dir / "xflash_reports"
    else:
        p = Path.home() / "Documents" / "Xflash_Reports"
    p.mkdir(parents=True, exist_ok=True)
    return p


DEFAULT_DB_PATH = get_default_db_path(portable=False)


class Database:
    def __init__(self, db_path: str | Path | None = None) -> None:
        if db_path is None or str(db_path) == ":memory:":
            self.db_path = ":memory:"
        else:
            self.db_path = Path(db_path).resolve()
            self.db_path.parent.mkdir(parents=True, exist_ok=True)
            self.db_path = str(self.db_path)

        self._init_db()

    @contextmanager
    def _connection(self) -> Generator[sqlite3.Connection, None, None]:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON;")
        if self.db_path != ":memory:":
            conn.execute("PRAGMA journal_mode = WAL;")
        try:
            with conn:
                yield conn
        finally:
            conn.close()

    def _init_db(self) -> None:
        with self._connection() as conn:
            conn.executescript("""
            CREATE TABLE IF NOT EXISTS sessions (
                id TEXT PRIMARY KEY,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                operator_notes TEXT,
                risk_state TEXT NOT NULL,
                finding_count INTEGER NOT NULL,
                system_model TEXT,
                platform TEXT,
                snapshot_json TEXT NOT NULL,
                report_json TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS claims (
                session_id TEXT PRIMARY KEY REFERENCES sessions(id) ON DELETE CASCADE,
                model TEXT,
                ram_gib REAL,
                storage_capacity_gb REAL,
                cpu_model TEXT,
                gpu_model TEXT,
                display_resolution TEXT
            );

            CREATE TABLE IF NOT EXISTS findings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT NOT NULL REFERENCES sessions(id) ON DELETE CASCADE,
                code TEXT NOT NULL,
                severity TEXT NOT NULL,
                component TEXT NOT NULL,
                title TEXT NOT NULL,
                details TEXT NOT NULL,
                evidence_json TEXT,
                recommended_action TEXT,
                confidence TEXT,
                source TEXT
            );

            CREATE TABLE IF NOT EXISTS coverage (
                session_id TEXT NOT NULL REFERENCES sessions(id) ON DELETE CASCADE,
                check_name TEXT NOT NULL,
                status TEXT NOT NULL,
                PRIMARY KEY (session_id, check_name)
            );

            CREATE TABLE IF NOT EXISTS manual_checks (
                session_id TEXT NOT NULL REFERENCES sessions(id) ON DELETE CASCADE,
                check_name TEXT NOT NULL,
                status TEXT NOT NULL,
                notes TEXT,
                checked_at TEXT NOT NULL,
                PRIMARY KEY (session_id, check_name)
            );

            CREATE INDEX IF NOT EXISTS idx_sessions_created ON sessions(created_at DESC);
            CREATE INDEX IF NOT EXISTS idx_findings_session ON findings(session_id);
            """)

    def save_session(
        self,
        snapshot: dict[str, Any],
        report: dict[str, Any],
        operator_notes: str | None = None,
    ) -> str:
        session_id = (
            (snapshot.get("inspection") or {}).get("id")
            or report.get("inspection_id")
            or f"INSP-{int(datetime.now(timezone.utc).timestamp())}"
        )
        system = snapshot.get("system") or {}
        claims = snapshot.get("claims") or {}
        now = _iso_now()

        system_model = system.get("model") or system.get("product_name")
        platform = system.get("platform") or system.get("os_name")

        with self._connection() as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO sessions (
                    id, created_at, updated_at, operator_notes,
                    risk_state, finding_count, system_model, platform,
                    snapshot_json, report_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    session_id,
                    now,
                    now,
                    operator_notes,
                    report.get("risk_state", "unknown"),
                    report.get("finding_count", len(report.get("findings", []))),
                    system_model,
                    platform,
                    json.dumps(snapshot, ensure_ascii=False),
                    json.dumps(report, ensure_ascii=False),
                ),
            )

            # Insert/replace claims
            if claims:
                conn.execute(
                    """
                    INSERT OR REPLACE INTO claims (
                        session_id, model, ram_gib, storage_capacity_gb,
                        cpu_model, gpu_model, display_resolution
                    ) VALUES (?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        session_id,
                        claims.get("model"),
                        claims.get("ram_gib"),
                        claims.get("storage_capacity_gb"),
                        claims.get("cpu_model"),
                        claims.get("gpu_model"),
                        claims.get("display_resolution"),
                    ),
                )

            # Insert findings (replace existing for session)
            conn.execute("DELETE FROM findings WHERE session_id = ?", (session_id,))
            for f in report.get("findings", []):
                conn.execute(
                    """
                    INSERT INTO findings (
                        session_id, code, severity, component, title,
                        details, evidence_json, recommended_action,
                        confidence, source
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        session_id,
                        f.get("code", "UNKNOWN"),
                        f.get("severity", "info"),
                        f.get("component", "unknown"),
                        f.get("title", ""),
                        f.get("details", ""),
                        json.dumps(f.get("evidence", {}), ensure_ascii=False),
                        f.get("recommended_action", ""),
                        f.get("confidence", "medium"),
                        f.get("source"),
                    ),
                )

            # Insert coverage
            coverage = report.get("coverage", {})
            conn.execute("DELETE FROM coverage WHERE session_id = ?", (session_id,))
            for check_name, status in coverage.items():
                conn.execute(
                    "INSERT INTO coverage (session_id, check_name, status) VALUES (?, ?, ?)",
                    (session_id, check_name, status),
                )

        return session_id

    def get_session(self, session_id: str) -> dict[str, Any] | None:
        with self._connection() as conn:
            sess_row = conn.execute("SELECT * FROM sessions WHERE id = ?", (session_id,)).fetchone()
            if not sess_row:
                return None

            claims_row = conn.execute("SELECT * FROM claims WHERE session_id = ?", (session_id,)).fetchone()
            findings_rows = conn.execute("SELECT * FROM findings WHERE session_id = ?", (session_id,)).fetchall()
            coverage_rows = conn.execute("SELECT * FROM coverage WHERE session_id = ?", (session_id,)).fetchall()
            manual_rows = conn.execute("SELECT * FROM manual_checks WHERE session_id = ?", (session_id,)).fetchall()

            claims = dict(claims_row) if claims_row else {}
            if "session_id" in claims:
                del claims["session_id"]

            findings = []
            for fr in findings_rows:
                findings.append({
                    "id": fr["id"],
                    "code": fr["code"],
                    "severity": fr["severity"],
                    "component": fr["component"],
                    "title": fr["title"],
                    "details": fr["details"],
                    "evidence": json.loads(fr["evidence_json"] or "{}"),
                    "recommended_action": fr["recommended_action"],
                    "confidence": fr["confidence"],
                    "source": fr["source"],
                })

            coverage = {cr["check_name"]: cr["status"] for cr in coverage_rows}
            manual_checks = {
                mr["check_name"]: {
                    "status": mr["status"],
                    "notes": mr["notes"],
                    "checked_at": mr["checked_at"],
                }
                for mr in manual_rows
            }

            return {
                "id": sess_row["id"],
                "created_at": sess_row["created_at"],
                "updated_at": sess_row["updated_at"],
                "operator_notes": sess_row["operator_notes"],
                "risk_state": sess_row["risk_state"],
                "finding_count": sess_row["finding_count"],
                "system_model": sess_row["system_model"],
                "platform": sess_row["platform"],
                "snapshot": json.loads(sess_row["snapshot_json"]),
                "report": json.loads(sess_row["report_json"]),
                "claims": claims,
                "findings": findings,
                "coverage": coverage,
                "manual_checks": manual_checks,
            }

    def list_sessions(self, limit: int = 50, offset: int = 0) -> list[dict[str, Any]]:
        with self._connection() as conn:
            rows = conn.execute(
                """
                SELECT id, created_at, operator_notes, risk_state, finding_count, system_model, platform
                FROM sessions
                ORDER BY created_at DESC
                LIMIT ? OFFSET ?
                """,
                (limit, offset),
            ).fetchall()
            return [dict(r) for r in rows]

    def record_manual_check(
        self,
        session_id: str,
        check_name: str,
        status: str,
        notes: str | None = None,
    ) -> None:
        now = _iso_now()
        with self._connection() as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO manual_checks (
                    session_id, check_name, status, notes, checked_at
                ) VALUES (?, ?, ?, ?, ?)
                """,
                (session_id, check_name, status, notes, now),
            )
            conn.execute("UPDATE sessions SET updated_at = ? WHERE id = ?", (now, session_id))

    def get_manual_checks(self, session_id: str) -> dict[str, dict[str, Any]]:
        with self._connection() as conn:
            rows = conn.execute(
                "SELECT check_name, status, notes, checked_at FROM manual_checks WHERE session_id = ?",
                (session_id,),
            ).fetchall()
            return {
                r["check_name"]: {
                    "status": r["status"],
                    "notes": r["notes"],
                    "checked_at": r["checked_at"],
                }
                for r in rows
            }

    def delete_session(self, session_id: str) -> bool:
        with self._connection() as conn:
            cursor = conn.execute("DELETE FROM sessions WHERE id = ?", (session_id,))
            return cursor.rowcount > 0
