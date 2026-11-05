#!/usr/bin/env bash
# ============================================================================
# Xflash Laptop Diagnostics - Linux USB Auto-Start Prompt Handler
# ============================================================================
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
exec "$SCRIPT_DIR/run-portable.sh" "$@"
