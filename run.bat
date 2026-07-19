@echo off
:: -----------------------------------------------------------------
::  CandyBarV2 — Windows launcher
::  Usage:  run.bat  (double-click or run from terminal)
:: -----------------------------------------------------------------
setlocal
cd /d "%~dp0"

set PYTHON=venv\Scripts\python.exe
set PIP=venv\Scripts\pip.exe
set RCC=venv\Scripts\pyside6-rcc.exe

:: ── 1. Create venv if missing ─────────────────────────────────
if not exist "%PYTHON%" (
    echo [run] Creating virtual environment...
    python -m venv venv
    if errorlevel 1 (
        echo [run] ERROR: Failed to create virtual environment.
        echo [run] Make sure Python 3.10+ is installed and on your PATH.
        pause
        exit /b 1
    )
)

:: ── 2. Install / sync dependencies ───────────────────────────
echo [run] Checking dependencies...
"%PIP%" install -q -r requirements.txt
if errorlevel 1 (
    echo [run] ERROR: Dependency installation failed.
    pause
    exit /b 1
)

:: ── 3. Compile QRC resources ──────────────────────────────────
if exist "%RCC%" (
    echo [run] Compiling Qt resources...
    "%RCC%" app/imports/resource.qrc -o app/imports/resource_rc.py
    if errorlevel 1 (
        echo [run] WARNING: Resource compilation failed, continuing anyway.
    )
) else (
    echo [run] Warning: pyside6-rcc not found, skipping compilation.
)

:: ── 4. Launch ─────────────────────────────────────────────────
echo [run] Starting CandyBarV2...
"%PYTHON%" main.py

endlocal
