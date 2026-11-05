#!/usr/bin/env bash
# ============================================================================
# Aegis Laptop Diagnostics - Zero-Trace USB Portable Launcher (Linux)
# ============================================================================
# Runs directly from USB drive with zero installation and zero disk trace.
# All inspection histories and HTML reports are written to this USB drive.
#
# 100% offline, local-only, zero network requests, zero telemetry.
# ============================================================================
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
export PYTHONPATH="$SCRIPT_DIR/src:$PYTHONPATH"
export XFLASH_PORTABLE=1
export AEGIS_PORTABLE=1

# Detect Python 3
PYTHON_BIN=""
if command -v python3 >/dev/null 2>&1; then
    PYTHON_BIN="python3"
elif command -v python >/dev/null 2>&1; then
    PYTHON_BIN="python"
fi

if [ -z "$PYTHON_BIN" ]; then
    echo "Error: Python 3.10+ is required to run Aegis Laptop Diagnostics." >&2
    exit 1
fi

echo "[Aegis] Starting zero-trace portable diagnostics from USB..."
echo "[Aegis] Reports directory: $SCRIPT_DIR/aegis_reports/"
echo "[Aegis] SQLite database:   $SCRIPT_DIR/aegis_data/inspections.sqlite3"

exec "$PYTHON_BIN" -m laptop_inspector.cli serve --portable "$@"
