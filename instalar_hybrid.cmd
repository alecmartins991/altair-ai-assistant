@echo off
cd /d "%~dp0"
powershell.exe -NoProfile -ExecutionPolicy RemoteSigned -File "%~dp0install_hybrid.ps1"
if errorlevel 1 echo Instalacao falhou. Leia o erro acima.
pause
