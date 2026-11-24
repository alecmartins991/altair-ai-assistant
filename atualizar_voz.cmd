@echo off
cd /d "%~dp0"
set "ALTAIR_USER_DATA_DIR=%LOCALAPPDATA%\Altair-Hybrid"
echo Feche o Altair antes de prosseguir.
echo Baixaremos o Whisper Turbo e o Kokoro. Isso pode usar alguns GB de disco.
pause
powershell.exe -NoProfile -ExecutionPolicy RemoteSigned -File "%~dp0scripts\setup_voice.ps1" -Whisper large-v3-turbo
if errorlevel 1 (
  echo Falha ao preparar os modelos. Confira o erro acima.
  pause
  exit /b 1
)
echo Abra iniciar_hybrid.cmd e selecione kokoro_local, local, large-v3-turbo e cpu.
pause
