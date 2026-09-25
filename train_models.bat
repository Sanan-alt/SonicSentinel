@echo off
REM ============================================================
REM   SonicSentinel AI - train the models (one click)
REM   Runs: organize -> extract features -> train both models.
REM   Only needed once, or after you add new audio to Dataset\.
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

echo [1/3] Organising dataset ^(dedup + stratified split^)...
"%PY%" src\organize.py
if errorlevel 1 goto :fail

echo.
echo [2/3] Extracting acoustic features ^(+ augmentation^)...
"%PY%" src\extract_features.py
if errorlevel 1 goto :fail

echo.
echo [3/3] Training Python model + GTM-substitute...
"%PY%" src\train.py
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
