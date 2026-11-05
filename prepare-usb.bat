@echo off
:: ============================================================================
:: Prepare 100% Self-Contained USB Stick for Used Laptop Shop Inspections
:: ============================================================================
cd /d "%~dp0"
python tools\prepare_offline_usb.py --target "%~dp0" %*
if %ERRORLEVEL% neq 0 (
    pause
)
