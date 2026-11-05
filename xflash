#!/usr/bin/env python3
"""Xflash Diagnostics - Direct Root Launcher.

Usage:
  python3 run.py                  # Starts dashboard on http://127.0.0.1:8080
  python3 run.py --port 8080      # Starts dashboard on custom port
  python3 run.py analyze <file>   # Runs command-line analysis
"""
from __future__ import annotations

import sys
from pathlib import Path

# Automatically inject src into sys.path
_SRC_DIR = Path(__file__).resolve().parent / "src"
if str(_SRC_DIR) not in sys.path:
    sys.path.insert(0, str(_SRC_DIR))

from laptop_inspector.cli import main

if __name__ == "__main__":
    args = sys.argv[1:]
    # If invoked directly with no args or just port flags, default to serve
    if not args:
        args = ["serve"]
    elif args[0].startswith("--port") or args[0].startswith("-p") or args[0] in ("--portable", "--no-browser"):
        args = ["serve"] + args

    sys.exit(main(args))
