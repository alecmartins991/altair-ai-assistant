$ErrorActionPreference = 'Stop'
Set-Location $PSScriptRoot
$Python = Join-Path $PSScriptRoot '.venv\Scripts\python.exe'
if (-not (Test-Path $Python)) { throw 'Execute instalar_hybrid.cmd primeiro.' }
$env:PYTHONPATH = Join-Path $PSScriptRoot 'src'
$env:ALTAIR_USER_DATA_DIR = Join-Path $env:TEMP ('Altair-Hybrid-Test-' + [guid]::NewGuid().ToString())
try {
    & $Python -m pip install pytest
    if ($LASTEXITCODE -ne 0) { throw 'Falha ao instalar pytest.' }
    & $Python -m pytest tests/test_chatgpt_plan.py tests/test_hybrid_desktop.py tests/test_chatgpt_login_regression.py tests/test_audio_isolation.py tests/test_neural_voice.py tests/test_live_conversation.py tests/test_live_capture.py -q
    if ($LASTEXITCODE -ne 0) { throw 'Testes falharam.' }
} finally {
    if (Test-Path $env:ALTAIR_USER_DATA_DIR) {
        Remove-Item -LiteralPath $env:ALTAIR_USER_DATA_DIR -Recurse -Force
    }
}
