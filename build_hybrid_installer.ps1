$ErrorActionPreference = 'Stop'
Set-Location $PSScriptRoot
$Python = Join-Path $PSScriptRoot '.venv\Scripts\python.exe'
if (-not (Test-Path $Python)) { throw 'Execute instalar_hybrid.cmd primeiro.' }
& $Python -m pip install PyInstaller
if ($LASTEXITCODE -ne 0) { throw 'Falha ao instalar PyInstaller.' }
# Refresh the old bundled wheels before packaging so OAuth/Qt dependencies are present.
& (Join-Path $PSScriptRoot 'installer\build_offline_bundle.ps1')
& (Join-Path $PSScriptRoot 'installer\build_installer.ps1')
if (-not (Test-Path (Join-Path $PSScriptRoot 'dist\AltairInstaller.exe'))) {
    throw 'O executável não foi gerado.'
}
Write-Host 'Executável: dist\AltairInstaller.exe'
Write-Host 'O download do modelo Whisper ainda é feito pelo scripts\setup_voice.ps1.'
