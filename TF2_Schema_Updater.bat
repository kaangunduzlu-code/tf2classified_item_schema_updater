@echo off
title TF2 Classified Item Schema Updater
color 0A

echo ========================================
echo   TF2 Classified Schema Updater
echo ========================================
echo.

REM Check if Python is installed
echo Checking for Python installation...
python --version 2>&1
if errorlevel 1 (
    echo.
    echo [ERROR] Python is not installed or not in PATH!
    echo.
    echo Please install Python from: https://www.python.org/downloads/
    echo Make sure to check "Add Python to PATH" during installation.
    echo.
    echo If Python IS installed, try adding it to PATH manually.
    echo.
    pause
    exit /b 1
)

echo Python found!
echo.

REM Check if requests module is installed
echo Checking for required packages...
python -c "import requests" >nul 2>&1
if errorlevel 1 (
    echo requests package not found.
    echo Installing required Python package: requests
    echo.
    python -m pip install requests
    if errorlevel 1 (
        echo.
        echo [ERROR] Failed to install requests package.
        echo Please try manually running: pip install requests
        echo.
        pause
        exit /b 1
    )
    echo.
    echo requests package installed successfully!
    echo.
) else (
    echo All required packages found!
    echo.
)

REM Check if Python script exists
if not exist "%~dp0tf2_schema_updater.py" (
    echo.
    echo [ERROR] tf2_schema_updater.py not found!
    echo Make sure both .bat and .py files are in the same folder.
    echo.
    pause
    exit /b 1
)

REM Run the Python script
echo Starting TF2 Classified Schema Updater...
echo.
python "%~dp0tf2_schema_updater.py"

REM Always pause at the end so window stays open
echo.
echo ========================================
pause
