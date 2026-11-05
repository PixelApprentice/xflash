"""Local HTTP server and REST API for the Laptop Buyer Kit dashboard."""
from __future__ import annotations

import json
import mimetypes
import os
import sys
from http import HTTPStatus
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, urlparse

from ..analysis import analyze_snapshot
from ..collectors.linux import LinuxCollector
from ..db import Database, DEFAULT_DB_PATH, get_default_db_path, get_reports_dir, is_portable_mode
from ..report import to_html, to_json

STATIC_DIR = Path(__file__).parent / "static"


class InspectorRequestHandler(SimpleHTTPRequestHandler):
    """Custom HTTP handler serving the dashboard SPA and local JSON REST APIs."""

    def __init__(self, *args: Any, db: Database | None = None, portable: bool | None = None, **kwargs: Any) -> None:
        self.portable = portable
        if db is not None:
            self.db = db
        else:
            self.db = Database(get_default_db_path(portable=self.portable))
        super().__init__(*args, directory=str(STATIC_DIR), **kwargs)

    def _send_json(self, data: Any, status: HTTPStatus = HTTPStatus.OK) -> None:
        body = json.dumps(data, ensure_ascii=False, indent=2).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Cache-Control", "no-cache, no-store, must-revalidate")
        self.end_headers()
        self.wfile.write(body)

    def _send_error_json(self, message: str, status: HTTPStatus = HTTPStatus.BAD_REQUEST) -> None:
        self._send_json({"error": message, "status": status.value}, status=status)

    def _read_body_json(self) -> dict[str, Any] | None:
        try:
            length = int(self.headers.get("Content-Length", "0"))
            if length <= 0:
                return {}
            raw = self.rfile.read(length).decode("utf-8")
            return json.loads(raw)
        except (ValueError, json.JSONDecodeError):
            return None

    def do_OPTIONS(self) -> None:
        self.send_response(HTTPStatus.NO_CONTENT)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, DELETE, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    def do_GET(self) -> None:
        parsed = urlparse(self.path)
        path = parsed.path.rstrip("/")

        if path == "/api/health":
            is_portable = is_portable_mode() if self.portable is None else self.portable
            self._send_json({
                "status": "healthy",
                "application": "Xflash Diagnostics",
                "version": "3.0.0",
                "offline_mode": True,
                "portable_mode": is_portable,
                "db_path": str(self.db.db_path),
                "reports_dir": str(get_reports_dir(portable=is_portable)),
            })
            return

        if path == "/api/probe":
            try:
                collector = LinuxCollector()
                specs = collector.probe_host_specs()
                self._send_json(specs)
            except Exception as exc:
                self._send_error_json(f"Hardware probe failed: {exc}", HTTPStatus.INTERNAL_SERVER_ERROR)
            return

        if path == "/api/ports":
            try:
                collector = LinuxCollector()
                ports = collector.collect_ports()
                self._send_json(ports)
            except Exception as exc:
                self._send_error_json(f"Port query failed: {exc}", HTTPStatus.INTERNAL_SERVER_ERROR)
            return

        if path == "/api/network":
            try:
                collector = LinuxCollector()
                net = collector.collect_network()
                self._send_json(net)
            except Exception as exc:
                self._send_error_json(f"Network query failed: {exc}", HTTPStatus.INTERNAL_SERVER_ERROR)
            return

        if path == "/api/system/extended":
            try:
                collector = LinuxCollector()
                sysext = collector.collect_system_extended()
                self._send_json(sysext)
            except Exception as exc:
                self._send_error_json(f"System extended probe failed: {exc}", HTTPStatus.INTERNAL_SERVER_ERROR)
            return

        if path == "/api/fans":
            try:
                collector = LinuxCollector()
                fans = collector.collect_fans()
                self._send_json(fans)
            except Exception as exc:
                self._send_error_json(f"Fan query failed: {exc}", HTTPStatus.INTERNAL_SERVER_ERROR)
            return

        if path == "/api/fan/profiles":
            try:
                collector = LinuxCollector()
                profiles = collector.get_fan_profiles()
                self._send_json(profiles)
            except Exception as exc:
                self._send_error_json(f"Fan profile query failed: {exc}", HTTPStatus.INTERNAL_SERVER_ERROR)
            return

        if path == "/api/sessions":
            sessions = self.db.list_sessions(limit=100)
            self._send_json({"sessions": sessions})
            return

        if path.startswith("/api/sessions/"):
            session_id = path[len("/api/sessions/"):]
            session = self.db.get_session(session_id)
            if not session:
                self._send_error_json("Session not found", HTTPStatus.NOT_FOUND)
                return
            self._send_json(session)
            return

        if path.startswith("/api/export/"):
            parts = path.strip("/").split("/")
            # format: /api/export/<id>/<html|json>
            if len(parts) == 4 and parts[3] in ("html", "json"):
                session_id = parts[2]
                export_format = parts[3]
                session = self.db.get_session(session_id)
                if not session:
                    self._send_error_json("Session not found", HTTPStatus.NOT_FOUND)
                    return
                report = session["report"]
                if export_format == "html":
                    content = to_html(report).encode("utf-8")
                    mime = "text/html; charset=utf-8"
                else:
                    content = to_json(report).encode("utf-8")
                    mime = "application/json; charset=utf-8"

                self.send_response(HTTPStatus.OK)
                self.send_header("Content-Type", mime)
                self.send_header("Content-Length", str(len(content)))
                self.send_header("Content-Disposition", f'attachment; filename="report-{session_id}.{export_format}"')
                self.end_headers()
                self.wfile.write(content)
                return

        # Serve static assets or fallback to index.html for SPA
        file_path = STATIC_DIR / parsed.path.lstrip("/")
        if file_path.is_file():
            super().do_GET()
        else:
            # Fallback to index.html
            index_file = STATIC_DIR / "index.html"
            if index_file.is_file():
                content = index_file.read_bytes()
                self.send_response(HTTPStatus.OK)
                self.send_header("Content-Type", "text/html; charset=utf-8")
                self.send_header("Content-Length", str(len(content)))
                self.end_headers()
                self.wfile.write(content)
            else:
                self.send_error(HTTPStatus.NOT_FOUND, "Static index file not found")

    def do_POST(self) -> None:
        parsed = urlparse(self.path)
        path = parsed.path.rstrip("/")

        body = self._read_body_json()
        if body is None:
            self._send_error_json("Invalid JSON payload", HTTPStatus.BAD_REQUEST)
            return

        if path == "/api/benchmark/cpu-pulse":
            try:
                import time, math
                collector = LinuxCollector()
                t_start = collector.collect_thermals()
                initial_max = t_start.get("max_temp_c") if isinstance(t_start, dict) else 45.0
                if initial_max is None:
                    initial_max = 45.0

                start_time = time.time()
                iterations = 0
                while time.time() - start_time < 5.0:
                    for _ in range(50000):
                        math.sqrt(12345.6789)
                    iterations += 50000

                t_end = collector.collect_thermals()
                peak_max = t_end.get("max_temp_c") if isinstance(t_end, dict) else (initial_max or 50.0)
                if peak_max is None:
                    peak_max = initial_max
                rise = max(0.0, round(peak_max - initial_max, 1))

                self._send_json({
                    "duration_seconds": 5.0,
                    "initial_temp_c": initial_max,
                    "peak_temp_c": peak_max,
                    "temp_rise_c": rise,
                    "thermal_ramp_rate": round(rise / 5.0, 2),
                    "throttle_detected": peak_max >= 95.0,
                    "status": "PASS — Normal Cooling Dissipation" if peak_max < 90 else "WARNING — High Thermal Rise",
                    "iterations_completed": iterations,
                })
            except Exception as exc:
                self._send_error_json(f"Thermal pulse failed: {exc}", HTTPStatus.INTERNAL_SERVER_ERROR)
            return

        if path == "/api/fan/profile":
            profile = body.get("profile")
            if not profile or not isinstance(profile, str):
                self._send_error_json("Payload must contain a string 'profile'", HTTPStatus.BAD_REQUEST)
                return
            try:
                collector = LinuxCollector()
                res = collector.set_fan_profile(profile)
                if res.get("success"):
                    self._send_json(res)
                else:
                    self._send_error_json(res.get("error", "Failed to switch fan profile"), HTTPStatus.BAD_REQUEST)
            except Exception as exc:
                self._send_error_json(f"Fan profile switch failed: {exc}", HTTPStatus.INTERNAL_SERVER_ERROR)
            return

        if path == "/api/export/portable":
            session_id = body.get("session_id")
            if not session_id:
                self._send_error_json("Missing 'session_id'", HTTPStatus.BAD_REQUEST)
                return
            session = self.db.get_session(session_id)
            if not session:
                self._send_error_json("Session not found", HTTPStatus.NOT_FOUND)
                return
            report = session["report"]
            is_portable = is_portable_mode() if self.portable is None else self.portable
            reports_dir = get_reports_dir(portable=is_portable)
            html_path = reports_dir / f"inspection-{session_id}.html"
            json_path = reports_dir / f"inspection-{session_id}.json"
            html_path.write_text(to_html(report), encoding="utf-8")
            json_path.write_text(to_json(report), encoding="utf-8")
            self._send_json({
                "success": True,
                "session_id": session_id,
                "html_file": html_path.name,
                "json_file": json_path.name,
                "directory": str(reports_dir),
            })
            return

        if path == "/api/inspect/live":
            claims = body.get("claims") or {}
            operator_notes = body.get("operator_notes")

            try:
                collector = LinuxCollector()
                snapshot = collector.collect_snapshot(claims=claims)
                report = analyze_snapshot(snapshot)
                session_id = self.db.save_session(snapshot, report, operator_notes=operator_notes)
                full_record = self.db.get_session(session_id)
                self._send_json(full_record, status=HTTPStatus.CREATED)
            except Exception as exc:
                self._send_error_json(f"Live collection failed: {exc}", HTTPStatus.INTERNAL_SERVER_ERROR)
            return

        if path == "/api/inspect/snapshot":
            snapshot = body.get("snapshot")
            operator_notes = body.get("operator_notes")
            if not isinstance(snapshot, dict):
                self._send_error_json("Payload must contain a 'snapshot' object", HTTPStatus.BAD_REQUEST)
                return

            try:
                report = analyze_snapshot(snapshot)
                session_id = self.db.save_session(snapshot, report, operator_notes=operator_notes)
                full_record = self.db.get_session(session_id)
                self._send_json(full_record, status=HTTPStatus.CREATED)
            except Exception as exc:
                self._send_error_json(f"Analysis failed: {exc}", HTTPStatus.BAD_REQUEST)
            return

        if path.startswith("/api/sessions/") and path.endswith("/manual"):
            # format: /api/sessions/<id>/manual
            parts = path.strip("/").split("/")
            if len(parts) == 4:
                session_id = parts[2]
                check_name = body.get("check_name")
                status = body.get("status")
                notes = body.get("notes")

                if not check_name or not status:
                    self._send_error_json("Missing 'check_name' or 'status'", HTTPStatus.BAD_REQUEST)
                    return

                session = self.db.get_session(session_id)
                if not session:
                    self._send_error_json("Session not found", HTTPStatus.NOT_FOUND)
                    return

                self.db.record_manual_check(session_id, check_name, status, notes)
                updated = self.db.get_manual_checks(session_id)
                self._send_json({"manual_checks": updated})
                return

        self._send_error_json("Unknown endpoint", HTTPStatus.NOT_FOUND)

    def do_DELETE(self) -> None:
        parsed = urlparse(self.path)
        path = parsed.path.rstrip("/")

        if path.startswith("/api/sessions/"):
            session_id = path[len("/api/sessions/"):]
            deleted = self.db.delete_session(session_id)
            if not deleted:
                self._send_error_json("Session not found", HTTPStatus.NOT_FOUND)
                return
            self._send_json({"success": True, "id": session_id})
            return

        self._send_error_json("Unknown endpoint", HTTPStatus.NOT_FOUND)


def create_server(
    host: str = "127.0.0.1",
    port: int = 8080,
    db: Database | None = None,
    portable: bool | None = None,
) -> ThreadingHTTPServer:
    database = db or Database(get_default_db_path(portable=portable))

    def handler_factory(*args: Any, **kwargs: Any) -> InspectorRequestHandler:
        return InspectorRequestHandler(*args, db=database, portable=portable, **kwargs)

    return ThreadingHTTPServer((host, port), handler_factory)


def run_server(
    host: str = "127.0.0.1",
    port: int = 8080,
    db: Database | None = None,
    portable: bool | None = None,
    open_browser: bool = False,
) -> None:
    server = create_server(host=host, port=port, db=db, portable=portable)
    mode_label = "USB ZERO-TRACE PORTABLE" if (is_portable_mode() if portable is None else portable) else "NORMAL SYSTEM"
    print(f"Aegis Laptop Diagnostics [{mode_label}] running locally at: http://{host}:{port}")
    print("Press Ctrl+C to stop.")

    if open_browser:
        import threading
        import webbrowser

        def _open():
            import time
            time.sleep(0.4)
            webbrowser.open(f"http://{host}:{port}")

        threading.Thread(target=_open, daemon=True).start()

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down server cleanly...")
    finally:
        server.server_close()


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Run Xflash local diagnostic server")
    parser.add_argument("--host", default="127.0.0.1", help="Host interface to bind (default: 127.0.0.1)")
    parser.add_argument("--port", type=int, default=8080, help="Port to listen on (default: 8080)")
    parser.add_argument("--portable", action="store_true", help="Run in zero-trace USB portable mode")
    parser.add_argument("--no-browser", action="store_true", help="Do not automatically launch web browser")
    cli_args = parser.parse_args()

    run_server(
        host=cli_args.host,
        port=cli_args.port,
        portable=cli_args.portable,
        open_browser=not cli_args.no_browser,
    )
