param([string]$Python = "", [switch]$SkipModel, [ValidateSet("base","small","large-v3-turbo")][string]$Whisper = "base")
$ErrorActionPreference = 'Stop'
$Root = Split-Path -Parent $PSScriptRoot
if (-not $Python) { $Python = Join-Path $Root '.venv\Scripts\python.exe' }
if (-not (Test-Path $Python)) { throw 'Instale primeiro o Altair com instalar_hybrid.cmd.' }
$env:PYTHONPATH = Join-Path $Root 'src'
if (-not $env:ALTAIR_USER_DATA_DIR) {
    $env:ALTAIR_USER_DATA_DIR = Join-Path $env:LOCALAPPDATA 'Altair-Hybrid'
}
& $Python -m pip install -r (Join-Path $Root 'requirements-voice-local.txt')
if ($LASTEXITCODE -ne 0) { throw 'Falha ao instalar dependencias de voz.' }
if (-not $SkipModel) {
    & $Python -m altair.core.download_neural_voice --whisper $Whisper
    if ($LASTEXITCODE -ne 0) { throw 'Falha no download ou validacao dos modelos. Execute novamente.' }
}
Write-Host 'Voz local preparada. Abra o Altair e escolha kokoro_local e o modelo Whisper instalado.'
