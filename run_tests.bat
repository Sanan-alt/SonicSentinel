@echo off
REM Run the full SonicSentinel validation suite (tests + dataset + SRS audit).
setlocal
cd /d "%~dp0"

set "PY=.venv\Scripts\python.exe"
if not exist "%PY%" set "PY=python"

echo ============================================================
echo  SonicSentinel - full validation suite
echo ============================================================
"%PY%" scripts\run_all_tests.py
echo.
echo Reports written under reports\final\
pause
