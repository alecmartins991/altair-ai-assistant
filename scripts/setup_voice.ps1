param([string]$Python = "", [switch]$SkipModel)
$ErrorActionPreference = 'Stop'
$Root = Split-Path -Parent $PSScriptRoot
if (-not $Python) { $Python = Join-Path $Root '.venv\Scripts\python.exe' }
if (-not (Test-Path $Python)) { throw 'Instale primeiro o Altair com instalar_hybrid.cmd.' }
$env:PYTHONPATH = Join-Path $Root 'src'
if (-not $env:ALTAIR_USER_DATA_DIR) {
    $env:ALTAIR_USER_DATA_DIR = Join-Path $env:LOCALAPPDATA 'Altair-Hybrid'
}
& $Python -m pip install -r (Join-Path $Root 'requirements-voice-local.txt')
if ($LASTEXITCODE -ne 0) { throw 'Falha ao instalar Whisper.' }
if (-not $SkipModel) {
    # Explicit initial download. Runtime uses local_files_only=True.
    & $Python -c "from huggingface_hub import snapshot_download; from altair.core.local_voice import whisper_path; p=whisper_path(); p.mkdir(parents=True, exist_ok=True); snapshot_download('Systran/faster-whisper-base', local_dir=str(p)); print(p)"
    if ($LASTEXITCODE -ne 0) { throw 'Falha ao baixar modelo Whisper. Execute novamente.' }
}
Write-Host 'Voz local preparada. Escolha windows_local e local no Altair.'
