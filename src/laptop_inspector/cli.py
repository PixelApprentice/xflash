"""Command-line entry point for Laptop Buyer Kit."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from .analysis import analyze_snapshot
from .report import to_html, to_json
from .web.server import run_server


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="xflash",
        description="Xflash: Check before you pay. Offline-first laptop hardware diagnostics, discrepancy detection, and buyer assurance.",
    )
    subparsers = parser.add_subparsers(dest="subcommand", help="Sub-commands")

    # Serve command: local web dashboard
    serve_parser = subparsers.add_parser("serve", help="Launch local offline web dashboard & REST server")
    serve_parser.add_argument("--host", default="127.0.0.1", help="Host interface to bind (default: 127.0.0.1)")
    serve_parser.add_argument("--port", type=int, default=8080, help="Port to listen on (default: 8080)")
    serve_parser.add_argument("--portable", action="store_true", help="Run in zero-trace portable USB mode (stores DB on current drive)")
    serve_parser.add_argument("--no-browser", action="store_true", help="Do not automatically launch web browser on startup")

    # Analyze command
    analyze_parser = subparsers.add_parser("analyze", help="Analyze a normalized snapshot JSON file")
    analyze_parser.add_argument("snapshot", type=Path, help="Input snapshot JSON file")
    analyze_parser.add_argument("--format", choices=("json", "html"), default="json", help="Report format (default: json)")
    analyze_parser.add_argument("--output", type=Path, help="Output file; defaults to stdout")

    # Global flags
    parser.add_argument("--portable", action="store_true", help="Run in zero-trace portable USB mode")
    parser.add_argument("--no-browser", action="store_true", help="Do not automatically launch web browser on startup")

    # For backwards compatibility with `laptop-inspector <snapshot>`
    parser.add_argument("legacy_snapshot", nargs="?", type=Path, help=argparse.SUPPRESS)
    parser.add_argument("--format", choices=("json", "html"), default="json", help=argparse.SUPPRESS)
    parser.add_argument("--output", type=Path, help=argparse.SUPPRESS)

    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)

    is_portable = getattr(args, "portable", False)
    no_browser = getattr(args, "no_browser", False)

    if args.subcommand == "serve":
        run_server(
            host=args.host,
            port=args.port,
            portable=is_portable,
            open_browser=not no_browser,
        )
        return 0

    snapshot_path = getattr(args, "snapshot", None) or args.legacy_snapshot
    if not snapshot_path:
        # Default to launching dashboard if no arguments provided
        print("No snapshot specified. Starting interactive local dashboard...")
        run_server(
            host="127.0.0.1",
            port=8080,
            portable=is_portable,
            open_browser=not no_browser,
        )
        return 0

    try:
        with snapshot_path.open("r", encoding="utf-8") as handle:
            snapshot = json.load(handle)
        if not isinstance(snapshot, dict):
            raise ValueError("Top-level JSON value must be an object")
    except (OSError, json.JSONDecodeError, ValueError) as exc:
        print(f"error: unable to read snapshot: {exc}", file=sys.stderr)
        return 2

    try:
        report = analyze_snapshot(snapshot)
    except (TypeError, ValueError, AttributeError) as exc:
        print(f"error: snapshot structure is invalid: {exc}", file=sys.stderr)
        return 2

    report_format = getattr(args, "format", "json")
    output = to_html(report) if report_format == "html" else to_json(report)
    output_path = getattr(args, "output", None)

    if output_path:
        try:
            output_path.parent.mkdir(parents=True, exist_ok=True)
            output_path.write_text(output, encoding="utf-8")
        except OSError as exc:
            print(f"error: unable to write report: {exc}", file=sys.stderr)
            return 2
    else:
        sys.stdout.write(output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
