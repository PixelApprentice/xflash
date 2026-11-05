"""Command-line entry point for Xflash Laptop Diagnostics."""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Any

from .analysis import analyze_snapshot
from .cli_ui import format_terminal_report
from .report import to_html, to_json
from .web.server import run_server


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="xflash",
        description="Xflash: Check before you pay. Offline-first laptop hardware diagnostics, discrepancy detection, and buyer assurance.",
    )
    subparsers = parser.add_subparsers(dest="subcommand", help="Sub-commands")

    # 1. Scan / Inspect Command (Live Terminal Diagnostics)
    scan_parser = subparsers.add_parser("scan", aliases=["inspect", "check"], help="Run live hardware inspection directly in the terminal")
    scan_parser.add_argument("snapshot", nargs="?", type=Path, help="Optional snapshot JSON file (default: live probe of current laptop hardware)")
    scan_parser.add_argument("--claim-model", help="Seller's advertised laptop model (e.g. 'ThinkPad T14 Gen 2')")
    scan_parser.add_argument("--claim-ram", type=float, help="Seller's advertised RAM in GiB (e.g. 16)")
    scan_parser.add_argument("--claim-storage", type=float, help="Seller's advertised storage in GB (e.g. 512)")
    scan_parser.add_argument("--claim-cpu", help="Seller's advertised CPU spec (e.g. 'Intel Core i7')")
    scan_parser.add_argument("--claim-price", type=float, help="Listing asking price in local currency")
    scan_parser.add_argument("--url", help="Marketplace listing URL or memo (stored locally, zero network lookup)")
    scan_parser.add_argument("--format", choices=("terminal", "json", "html"), default="terminal", help="Output display format (default: terminal)")
    scan_parser.add_argument("--output", "-o", type=Path, help="Write report to specified output file")
    scan_parser.add_argument("--export-html", type=Path, help="Additionally export an offline HTML report to file")
    scan_parser.add_argument("--export-json", type=Path, help="Additionally export an offline JSON report to file")
    scan_parser.add_argument("--save-db", action="store_true", help="Save inspection session into local SQLite database")
    scan_parser.add_argument("--no-color", action="store_true", help="Disable ANSI color output in terminal")
    scan_parser.add_argument("--portable", action="store_true", help="Run in zero-trace portable USB mode")

    # 2. Serve Command (Local Offline Web Dashboard)
    serve_parser = subparsers.add_parser("serve", help="Launch local offline web dashboard & REST server")
    serve_parser.add_argument("--host", default="127.0.0.1", help="Host interface to bind (default: 127.0.0.1)")
    serve_parser.add_argument("--port", type=int, default=8080, help="Port to listen on (default: 8080)")
    serve_parser.add_argument("--portable", action="store_true", help="Run in zero-trace portable USB mode (stores DB on current drive)")
    serve_parser.add_argument("--no-browser", action="store_true", help="Do not automatically launch web browser on startup")

    # 3. Analyze Command (Snapshot File Analysis)
    analyze_parser = subparsers.add_parser("analyze", help="Analyze a pre-recorded snapshot JSON file")
    analyze_parser.add_argument("snapshot", type=Path, help="Input snapshot JSON file")
    analyze_parser.add_argument("--format", choices=("terminal", "json", "html"), default="terminal", help="Report format (default: terminal)")
    analyze_parser.add_argument("--output", "-o", type=Path, help="Output file; defaults to stdout")
    analyze_parser.add_argument("--no-color", action="store_true", help="Disable ANSI color output")
    analyze_parser.add_argument("--save-db", action="store_true", help="Save session to local SQLite database")

    # Global flags
    parser.add_argument("--portable", action="store_true", help="Run in zero-trace portable USB mode")
    parser.add_argument("--no-browser", action="store_true", help="Do not automatically launch web browser on startup")

    # Backwards compatibility flags for `xflash <snapshot.json>`
    parser.add_argument("legacy_snapshot", nargs="?", type=Path, help=argparse.SUPPRESS)
    parser.add_argument("--format", choices=("terminal", "json", "html"), default="terminal", help=argparse.SUPPRESS)
    parser.add_argument("--output", type=Path, help=argparse.SUPPRESS)

    return parser


def _collect_live_or_fallback(claims: dict[str, Any]) -> dict[str, Any]:
    """Collect live system snapshot via LinuxCollector, falling back gracefully if unavailable."""
    try:
        from .collectors.linux import LinuxCollector
        collector = LinuxCollector()
        return collector.collect_snapshot(claims=claims)
    except Exception as exc:
        import platform
        print(f"Notice: Live collector encountered: {exc}. Using base platform inventory.", file=sys.stderr)
        return {
            "inspection": {"id": "LIVE-PROBE-001"},
            "system": {
                "vendor": platform.node(),
                "model": platform.machine(),
                "os_name": platform.system(),
                "kernel_release": platform.release(),
            },
            "claims": claims,
        }


def _run_scan_command(args: argparse.Namespace) -> int:
    """Execute live or snapshot terminal hardware scan."""
    claims: dict[str, Any] = {}
    if getattr(args, "claim_model", None):
        claims["model"] = args.claim_model
    if getattr(args, "claim_ram", None) is not None:
        claims["ram_gib"] = args.claim_ram
    if getattr(args, "claim_storage", None) is not None:
        claims["storage_capacity_gb"] = args.claim_storage
    if getattr(args, "claim_cpu", None):
        claims["cpu"] = args.claim_cpu
    if getattr(args, "claim_price", None) is not None:
        claims["price"] = args.claim_price
    if getattr(args, "url", None):
        claims["listing_url"] = args.url

    snapshot_path = getattr(args, "snapshot", None)
    if snapshot_path:
        try:
            with snapshot_path.open("r", encoding="utf-8") as handle:
                snapshot = json.load(handle)
            if not isinstance(snapshot, dict):
                raise ValueError("Top-level JSON value must be an object")
            if claims:
                snapshot["claims"] = {**(snapshot.get("claims") or {}), **claims}
        except (OSError, json.JSONDecodeError, ValueError) as exc:
            print(f"error: unable to read snapshot file: {exc}", file=sys.stderr)
            return 2
    else:
        snapshot = _collect_live_or_fallback(claims)

    try:
        report = analyze_snapshot(snapshot)
    except Exception as exc:
        print(f"error: hardware analysis failed: {exc}", file=sys.stderr)
        return 2

    # Save to SQLite database if requested
    is_portable = getattr(args, "portable", False)
    if getattr(args, "save_db", False) or is_portable:
        try:
            from .db import Database, get_default_db_path
            db = Database(get_default_db_path(portable=is_portable))
            db.save_session(snapshot, report, operator_notes="CLI Inspection")
        except Exception as exc:
            print(f"Notice: SQLite persistence skipped ({exc})", file=sys.stderr)

    # Handle output exports
    if getattr(args, "export_html", None):
        try:
            html_content = to_html(report)
            args.export_html.parent.mkdir(parents=True, exist_ok=True)
            args.export_html.write_text(html_content, encoding="utf-8")
            print(f"✔ HTML report exported to: {args.export_html}", file=sys.stderr)
        except OSError as exc:
            print(f"error exporting HTML: {exc}", file=sys.stderr)

    if getattr(args, "export_json", None):
        try:
            json_content = to_json(report)
            args.export_json.parent.mkdir(parents=True, exist_ok=True)
            args.export_json.write_text(json_content, encoding="utf-8")
            print(f"✔ JSON report exported to: {args.export_json}", file=sys.stderr)
        except OSError as exc:
            print(f"error exporting JSON: {exc}", file=sys.stderr)

    # Format primary output
    report_format = getattr(args, "format", "terminal")
    use_color = not getattr(args, "no_color", False)

    if report_format == "html":
        output = to_html(report)
    elif report_format == "json":
        output = to_json(report)
    else:
        output = format_terminal_report(snapshot, report, use_color=use_color)

    output_path = getattr(args, "output", None)
    if output_path:
        try:
            output_path.parent.mkdir(parents=True, exist_ok=True)
            output_path.write_text(output, encoding="utf-8")
            print(f"✔ Report written to: {output_path}")
        except OSError as exc:
            print(f"error writing output: {exc}", file=sys.stderr)
            return 2
    else:
        print(output)

    # Exit code reflects findings: 0 if passed/clean, 1 if high risk/critical anomalies detected
    return 1 if report.get("risk_state") in ("high", "high_risk", "critical") else 0


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)

    is_portable = getattr(args, "portable", False)
    no_browser = getattr(args, "no_browser", False)

    if args.subcommand in ("scan", "inspect", "check"):
        return _run_scan_command(args)

    if args.subcommand == "serve":
        run_server(
            host=args.host,
            port=args.port,
            portable=is_portable,
            open_browser=not no_browser,
        )
        return 0

    if args.subcommand == "analyze":
        return _run_scan_command(args)

    # Legacy syntax: `xflash <snapshot.json>`
    snapshot_path = getattr(args, "snapshot", None) or args.legacy_snapshot
    if snapshot_path:
        args.snapshot = snapshot_path
        return _run_scan_command(args)

    # If no subcommand provided: default to launching dashboard
    print("No subcommand specified. Starting local workshop dashboard on http://127.0.0.1:8080 ...")
    print("Tip: Run 'xflash scan' for instant live terminal hardware inspection.")
    run_server(
        host="127.0.0.1",
        port=8080,
        portable=is_portable,
        open_browser=not no_browser,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
