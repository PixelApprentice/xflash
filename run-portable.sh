#!/usr/bin/env bash
# ============================================================================
# Xflash Laptop Diagnostics - Zero-Trace USB Portable Launcher (Linux)
# ============================================================================
# Compatible with: Ubuntu, Debian, Arch Linux, Fedora, openSUSE, Pop!_OS, Mint
# Runs directly from USB drive with zero installation and zero disk trace.
# All inspection histories and HTML reports are written to this USB drive.
#
# 100% offline, local-only, zero network requests, zero telemetry.
# ============================================================================
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
export PYTHONPATH="$SCRIPT_DIR/src:$SCRIPT_DIR:$PYTHONPATH"
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
    echo "============================================================================" >&2
    echo "[ERROR] Python 3.10+ is required to run Xflash Laptop Diagnostics." >&2
    echo "Please install Python using your distribution package manager:" >&2
    echo "  Ubuntu/Debian:  sudo apt install python3 python3-pip" >&2
    echo "  Arch Linux:     sudo pacman -S python" >&2
    echo "  Fedora/RHEL:    sudo dnf install python3" >&2
    echo "============================================================================" >&2
    exit 1
fi

echo "[Xflash] Starting zero-trace portable diagnostics from USB..."
echo "[Xflash] Reports directory: $SCRIPT_DIR/aegis_reports/"
echo "[Xflash] SQLite database:   $SCRIPT_DIR/aegis_data/inspections.sqlite3"

exec "$PYTHON_BIN" -m laptop_inspector.cli serve --portable "$@"
