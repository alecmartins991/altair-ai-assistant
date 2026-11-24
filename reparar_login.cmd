@echo off
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (
  echo Ambiente do Altair nao encontrado. Use instalar_hybrid.cmd uma vez.
  pause
  exit /b 1
)
set "ALTAIR_USER_DATA_DIR=%LOCALAPPDATA%\Altair-Hybrid"
set "PYTHONPATH=%~dp0src"
".venv\Scripts\python.exe" -m pip install --upgrade "PyJWT[crypto]>=2.10,<3" "requests>=2.31,<3" certifi
if errorlevel 1 goto fail
".venv\Scripts\python.exe" -c "import jwt; from cryptography.hazmat.primitives.asymmetric import rsa; from altair.core.secure_storage import protect_secret, unprotect_secret; assert hasattr(jwt, 'PyJWK'); v=protect_secret('altair-diagnostic'); assert v.startswith('dpapi:') and unprotect_secret(v)=='altair-diagnostic'; print('JWT, criptografia e armazenamento Windows: OK')"
if errorlevel 1 goto fail
".venv\Scripts\python.exe" -m compileall -q src
if errorlevel 1 goto fail
echo Reparo concluido. Abra iniciar_hybrid.cmd e tente entrar novamente.
pause
exit /b 0
:fail
echo Reparo falhou. Confira a mensagem acima, sem compartilhar tokens ou chaves.
pause
exit /b 1
