@echo off
setlocal enabledelayedexpansion
:: ============================================================================
:: Xflash - Zero-Trace USB Portable Launcher (Windows 8, 10, 11)
:: ============================================================================
:: Runs directly from USB drive with zero installation and zero disk trace.
:: All inspection histories and HTML reports are written to this USB drive.
::
:: 100% offline, local-only, zero network requests, zero telemetry.
:: ============================================================================

title Xflash Laptop Diagnostics [USB Portable Mode]
cd /d "%~dp0"

:: Set PYTHONPATH so no pip install or system modification is required
set "PYTHONPATH=%~dp0src;%~dp0;%PYTHONPATH%"
set "XFLASH_PORTABLE=1"
set "AEGIS_PORTABLE=1"

set "PY_CMD="

:: 1. Check for bundled portable Python on USB stick
if exist "%~dp0python\python.exe" (
    set "PY_CMD=%~dp0python\python.exe"
    goto :Launch
)
if exist "%~dp0runtime\bin\python.exe" (
    set "PY_CMD=%~dp0runtime\bin\python.exe"
    goto :Launch
)

:: 2. Check for python in system PATH
where python >nul 2>nul
if %ERRORLEVEL% equ 0 (
    set "PY_CMD=python"
    goto :Launch
)

:: 3. Check for Python launcher (py.exe)
where py >nul 2>nul
if %ERRORLEVEL% equ 0 (
    set "PY_CMD=py -3"
    goto :Launch
)

:: 4. Check standard Windows user install locations (Windows 10/11 Microsoft Store & Python.org)
for /d %%D in ("%LOCALAPPDATA%\Programs\Python\Python3*") do (
    if exist "%%D\python.exe" (
        set "PY_CMD=%%D\python.exe"
        goto :Launch
    )
)
if exist "%LOCALAPPDATA%\Microsoft\WindowsApps\python.exe" (
    set "PY_CMD=%LOCALAPPDATA%\Microsoft\WindowsApps\python.exe"
    goto :Launch
)

:: 5. Check standard system-wide install locations (Windows 8/10/11)
for /d %%D in ("C:\Program Files\Python3*") do (
    if exist "%%D\python.exe" (
        set "PY_CMD=%%D\python.exe"
        goto :Launch
    )
)
for /d %%D in ("C:\Python3*") do (
    if exist "%%D\python.exe" (
        set "PY_CMD=%%D\python.exe"
        goto :Launch
    )
)

:NotFound
echo.
echo ============================================================================
echo [Xflash] Python 3.10+ was not automatically detected on this Windows PC.
echo.
echo Options to run Xflash on this laptop:
echo   1. Install Python 3 from https://www.python.org/downloads/ (Check "Add to PATH")
echo   2. Or copy the Windows Python Embeddable ZIP (from python.org) into:
echo      %~dp0python\
echo ============================================================================
echo.
pause
exit /b 1

:Launch
echo [Xflash] Found Python interpreter: !PY_CMD!
echo [Xflash] Starting zero-trace portable diagnostics on http://127.0.0.1:8080 ...
start "" !PY_CMD! -m laptop_inspector.cli serve --portable
timeout /t 2 /nobreak >nul
start "" http://127.0.0.1:8080
exit /b 0
