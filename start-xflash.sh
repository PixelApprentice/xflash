#!/usr/bin/env bash
# ============================================================================
# Xflash Laptop Diagnostics - Linux Quick Launcher
# ============================================================================
# Check before you pay · Zero-install standalone USB launcher
# ============================================================================
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
exec "$SCRIPT_DIR/run-portable.sh" "$@"
