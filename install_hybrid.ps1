param([switch]$SkipVoice)
$ErrorActionPreference = 'Stop'
$Root = $PSScriptRoot
Set-Location $Root
$env:ALTAIR_USER_DATA_DIR = Join-Path $env:LOCALAPPDATA 'Altair-Hybrid'
$Python = Join-Path $Root '.venv\Scripts\python.exe'
if (-not (Test-Path $Python)) {
    $Launcher = Get-Command py.exe -ErrorAction SilentlyContinue
    if (-not $Launcher) { throw 'Instale Python 3.10 x64 (python.org) e abra o instalador novamente.' }
    & $Launcher.Source -3.10 -m venv (Join-Path $Root '.venv')
    if ($LASTEXITCODE -ne 0) { throw 'Python 3.10 x64 é necessário para este projeto.' }
}
& $Python -m pip install --upgrade pip
if ($LASTEXITCODE -ne 0) { throw 'Falha ao preparar pip.' }
& $Python -m pip install -r (Join-Path $Root 'requirements.txt')
if ($LASTEXITCODE -ne 0) { throw 'Falha ao instalar dependências do Altair.' }
if (-not $SkipVoice) {
    & (Join-Path $Root 'scripts\setup_voice.ps1') -Python $Python
}
$env:PYTHONPATH = Join-Path $Root 'src'
& $Python -m compileall -q (Join-Path $Root 'src')
if ($LASTEXITCODE -ne 0) { throw 'Falha de sintaxe: revise o código antes de abrir.' }
Write-Host 'Instalação concluída. Abra iniciar_hybrid.cmd para executar o Altair.'
