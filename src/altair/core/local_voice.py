"""Offline voice: Whisper from a preinstalled model and Windows System.Speech.

No network access during inference; the model is downloaded separately by the owner.
"""
import os
import subprocess
import threading
from pathlib import Path

from altair.paths import APP_DATA_ROOT

_model = None
_model_path = None
_model_lock = threading.Lock()


def whisper_path():
    return Path(os.getenv("ALTAIR_WHISPER_PATH", str(APP_DATA_ROOT / "models" / "whisper-base")))


def local_stt_ready():
    return (whisper_path() / "model.bin").is_file()


def transcribe_local(audio, language="pt"):
    global _model, _model_path
    path = whisper_path()
    if not local_stt_ready():
        raise RuntimeError("Modelo Whisper local ausente. Execute setup_voice.ps1 antes de usar o microfone.")
    with _model_lock:
        if _model is None or _model_path != path:
            from faster_whisper import WhisperModel
            _model = WhisperModel(str(path), device="cpu", compute_type="int8", local_files_only=True)
            _model_path = path
        segments, _ = _model.transcribe(audio, language=language or "pt", beam_size=1, vad_filter=True)
        return " ".join(segment.text.strip() for segment in segments).strip()


class WindowsLocalVoice:
    """Use installed Windows voices; text is passed via stdin, never as shell code."""
    def __init__(self, language="pt-BR"):
        self.language = language
        self._lock = threading.Lock()
        self._process = None
        self._voice_lock = threading.Lock()

    def _run(self, text, path=None):
        if os.name != "nt":
            raise RuntimeError("Voz local System.Speech disponível apenas no Windows.")
        if not str(text).strip():
            return
        script = (
            "$ErrorActionPreference='Stop'; "
            "[Console]::InputEncoding=[System.Text.UTF8Encoding]::new($false); "
            "Add-Type -AssemblyName System.Speech; "
            "$s=New-Object System.Speech.Synthesis.SpeechSynthesizer; "
            "try { "
            "$v=$s.GetInstalledVoices() | Where-Object {$_.Enabled -and $_.VoiceInfo.Culture.Name -eq $env:ALTAIR_TTS_LANGUAGE} | Select-Object -First 1; "
            "if ($v) {$s.SelectVoice($v.VoiceInfo.Name)}; "
            "if ($env:ALTAIR_TTS_FILE) {$s.SetOutputToWaveFile($env:ALTAIR_TTS_FILE)}; "
            "$s.Speak([Console]::In.ReadToEnd()) "
            "} finally {$s.Dispose()}"
        )
        env = os.environ.copy()
        env["ALTAIR_TTS_LANGUAGE"] = self.language
        env["ALTAIR_TTS_FILE"] = str(Path(path).resolve()) if path else ""
        with self._voice_lock:
            with self._lock:
                proc = subprocess.Popen(["powershell.exe", "-NoProfile", "-NonInteractive", "-Command", script],
                    stdin=subprocess.PIPE, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                    env=env, creationflags=subprocess.CREATE_NO_WINDOW)
                self._process = proc
            try:
                proc.communicate(str(text).encode("utf-8"), timeout=180)
                if proc.returncode != 0 and proc.returncode != 1:
                    raise RuntimeError("Falha na voz local do Windows.")
            except subprocess.TimeoutExpired:
                proc.kill()
                proc.communicate()
                raise RuntimeError("Tempo limite da voz local.")
            finally:
                with self._lock:
                    if self._process is proc:
                        self._process = None

    def speak(self, texto):
        self._run(texto)

    def stop(self):
        with self._lock:
            if self._process and self._process.poll() is None:
                self._process.kill()

    def save_to_file(self, texto, caminho_arquivo):
        # System.Speech writes WAV; callers must convert other formats separately.
        if Path(caminho_arquivo).suffix.lower() != ".wav":
            raise ValueError("A voz local salva somente arquivos .wav.")
        self._run(texto, caminho_arquivo)
        return str(caminho_arquivo)
