#!/usr/bin/env bash
# ============================================================================
# Prepare 100% Self-Contained USB Stick for Used Laptop Shop Inspections
# ============================================================================
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
python3 "$SCRIPT_DIR/tools/prepare_offline_usb.py" --target "$SCRIPT_DIR" "$@"
