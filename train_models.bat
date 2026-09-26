@echo off
REM ============================================================
REM   SonicSentinel AI - build / rebuild the models (one click)
REM   Detects new audio in Dataset\, cleans + organizes, extracts
REM   features, and trains both models. Safe to run any time.
REM ============================================================
title SonicSentinel AI - Training
cd /d "%~dp0"

set "PY="
if exist "D:\sonicsentinel_env\venv\Scripts\python.exe" set "PY=D:\sonicsentinel_env\venv\Scripts\python.exe"
if not defined PY if exist ".venv\Scripts\python.exe" set "PY=.venv\Scripts\python.exe"
if not defined PY (
    where python >nul 2>nul && set "PY=python"
)
if not defined PY (
    echo [ERROR] Python not found. Install Python 3.11+ first.
    pause
    exit /b 1
)

echo ============================================================
echo    SonicSentinel AI - building models
echo    Using Python: %PY%
echo ============================================================
echo.

REM Smart pipeline: rebuilds dataset+features only if the data changed,
REM then always retrains. Use "train_models.bat force" to force a full rebuild.
if /I "%~1"=="force" (
    "%PY%" src\run_pipeline.py --force
) else (
    "%PY%" src\run_pipeline.py
)
if errorlevel 1 goto :fail

echo.
echo ============================================================
echo    Training complete. You can now run start_sonicsentinel.bat
echo ============================================================
pause
exit /b 0

:fail
echo.
echo [ERROR] A step failed. Check the messages above.
pause
exit /b 1
