@echo off
REM ============================================================
REM   SonicSentinel AI - one-click launcher
REM   Double-click this file to start the web application.
REM ============================================================
title SonicSentinel AI
cd /d "%~dp0"

echo ============================================================
echo    SonicSentinel AI  -  starting up...
echo ============================================================
echo.

REM --- 1. Locate a Python interpreter ---------------------------------
REM Prefer this machine's prepared venv, then a local .venv, then system Python.
set "PY="
if exist "D:\sonicsentinel_env\venv\Scripts\python.exe" set "PY=D:\sonicsentinel_env\venv\Scripts\python.exe"
if not defined PY if exist ".venv\Scripts\python.exe" set "PY=.venv\Scripts\python.exe"
if not defined PY (
    where python >nul 2>nul && set "PY=python"
)
if not defined PY (
    echo [ERROR] Python was not found.
    echo Please install Python 3.11+ and run: python -m venv .venv
    echo Then: .venv\Scripts\pip install -r requirements.txt
    echo.
    pause
    exit /b 1
)
echo Using Python: %PY%
echo.

REM --- 2. First-run setup: create local venv + install deps if needed ---
if "%PY%"=="python" (
    if not exist ".venv\Scripts\python.exe" (
        echo No virtual environment found. Creating one now ^(first run^)...
        python -m venv .venv
        set "PY=.venv\Scripts\python.exe"
        echo Installing dependencies ^(this can take a few minutes^)...
        ".venv\Scripts\python.exe" -m pip install --upgrade pip
        ".venv\Scripts\python.exe" -m pip install -r requirements.txt
    )
)

REM --- 3. Make sure Flask is available --------------------------------
"%PY%" -c "import flask" 1>nul 2>nul
if errorlevel 1 (
    echo Installing project dependencies...
    "%PY%" -m pip install -r requirements.txt
)

REM --- 4. Open the browser shortly after the server starts ------------
start "" cmd /c "timeout /t 4 >nul & start http://127.0.0.1:5000"

REM --- 5. Launch the web app ------------------------------------------
echo.
echo Launching SonicSentinel at http://127.0.0.1:5000
echo Demo login:  admin@sonicsentinel.ai / admin
echo Press CTRL+C in this window to stop the server.
echo ============================================================
echo.
"%PY%" webapp\app.py

echo.
echo Server stopped.
pause
