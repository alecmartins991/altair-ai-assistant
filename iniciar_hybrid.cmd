@echo off
cd /d "%~dp0"
set "ALTAIR_USER_DATA_DIR=%LOCALAPPDATA%\Altair-Hybrid"
set "ALTAIR_HYBRID_FIRST_RUN=1"
if not exist ".venv\Scripts\python.exe" (
  echo Execute instalar_hybrid.cmd primeiro.
  pause
  exit /b 1
)
".venv\Scripts\python.exe" run_altair.py
if errorlevel 1 pause
