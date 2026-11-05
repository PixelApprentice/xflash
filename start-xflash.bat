@echo off
setlocal
:: ============================================================================
:: Xflash - Zero-Trace USB Portable Launcher (Windows)
:: ============================================================================
:: Runs directly from USB drive with zero installation and zero disk trace.
:: All inspection histories and HTML reports are written to this USB drive.
::
:: 100% offline, local-only, zero network requests, zero telemetry.
:: ============================================================================

title Xflash Laptop Diagnostics [USB Portable Mode]
cd /d "%~dp0"

:: Set PYTHONPATH so no pip install or system modification is required
set "PYTHONPATH=%~dp0src;%PYTHONPATH%"
set "XFLASH_PORTABLE=1"
set "AEGIS_PORTABLE=1"

:: Check for python in system PATH
where python >nul 2>nul
if %ERRORLEVEL% equ 0 (
    echo [Xflash] Starting zero-trace portable diagnostics on http://127.0.0.1:8080 ...
    start "" python -m laptop_inspector.cli serve --portable
    timeout /t 1 /nobreak >nul
    start "" http://127.0.0.1:8080
    exit /b 0
)

:: Check for py launcher
where py >nul 2>nul
if %ERRORLEVEL% equ 0 (
    echo [Aegis] Starting zero-trace portable diagnostics via py launcher...
    start "" py -m laptop_inspector.cli serve --portable
    timeout /t 1 /nobreak >nul
    start "" http://127.0.0.1:8080
    exit /b 0
)

:: Check for bundled embeddable python if present on USB
if exist "%~dp0python\python.exe" (
    echo [Aegis] Starting via bundled portable Python...
    start "" "%~dp0python\python.exe" -m laptop_inspector.cli serve --portable
    timeout /t 1 /nobreak >nul
    start "" http://127.0.0.1:8080
    exit /b 0
)

echo.
echo ============================================================================
echo [ERROR] Python 3.10+ was not found on this system.
echo.
echo Aegis is an open-source diagnostics suite requiring Python.
echo Please install Python from https://www.python.org/downloads/
echo or place Windows embeddable Python into: %~dp0python\
echo ============================================================================
echo.
pause
exit /b 1
