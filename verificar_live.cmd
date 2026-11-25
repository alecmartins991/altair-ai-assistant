@echo off
cd /d "%~dp0"
set "ALTAIR_USER_DATA_DIR=%LOCALAPPDATA%\Altair-Hybrid"
set "PYTHONPATH=%~dp0src"
if not exist ".venv\Scripts\python.exe" (
  echo Instale primeiro com instalar_hybrid.cmd.
  pause
  exit /b 1
)
".venv\Scripts\python.exe" -m compileall -q src
if errorlevel 1 (
  echo Erro de sintaxe encontrado. Nao inicie esta versao.
  pause
  exit /b 1
)
".venv\Scripts\python.exe" -m altair.core.live_preflight
set "RESULT=%ERRORLEVEL%"
pause
exit /b %RESULT%
