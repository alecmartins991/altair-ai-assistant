"""Offline voice: Whisper from a preinstalled model and Windows System.Speech.

No network access during inference; the model is downloaded separately by the owner.
"""
import os
import subprocess
import threading
import time
from pathlib import Path

from altair.paths import APP_DATA_ROOT

_model = None
_model_path = None
_model_lock = threading.Lock()


WHISPER_MODELS = {"base": "whisper-base", "small": "whisper-small", "large-v3-turbo": "whisper-large-v3-turbo"}
_model_device = None


def whisper_path(model=None):
    model = model or os.getenv("ALTAIR_WHISPER_MODEL", "large-v3-turbo")
    return Path(os.getenv("ALTAIR_WHISPER_PATH", str(APP_DATA_ROOT / "models" / WHISPER_MODELS.get(model, WHISPER_MODELS["large-v3-turbo"]))))


def local_stt_ready():
    return (whisper_path() / "model.bin").is_file()


def transcribe_local(audio, language="pt"):
    global _model, _model_path, _model_device
    path = whisper_path()
    if not local_stt_ready():
        raise RuntimeError("Modelo Whisper selecionado ausente. Execute atualizar_voz.cmd.")
    import numpy as np
    from altair.core.audio_isolation import record
    device = os.getenv("ALTAIR_WHISPER_DEVICE", "cpu")
    if device not in ("cpu", "cuda"):
        device = "cpu"
    audio = np.asarray(audio, dtype=np.float32).flatten()
    if audio.size < 3200:
        return ""
    # Remove DC offset and normalize quiet microphones without clipping.
    audio = audio - np.mean(audio)
    peak = float(np.max(np.abs(audio)))
    if peak < 0.0005:
        return ""
    audio = np.clip(audio * min(5.0, 0.85 / peak), -1.0, 1.0)
    with _model_lock:
        if _model is None or _model_path != path or _model_device != device:
            from faster_whisper import WhisperModel
            _model = WhisperModel(str(path), device=device, compute_type="int8_float16" if device == "cuda" else "int8",
                                  cpu_threads=min(6, os.cpu_count() or 4), local_files_only=True)
            _model_path, _model_device = path, device
        terms = os.getenv("ALTAIR_WHISPER_TERMS", "Altair, ChatGPT, GitHub, Lovable, Codex")[:300]
        segments, _ = _model.transcribe(audio, language="pt" if language in ("pt", "pt-BR", "pt-br") else language,
            task="transcribe", beam_size=5, vad_filter=True,
            vad_parameters={"min_silence_duration_ms": 500, "speech_pad_ms": 350},
            condition_on_previous_text=False, hotwords=terms or None,
            no_speech_threshold=0.6, temperature=0.0)
        result = " ".join(segment.text.strip() for segment in segments).strip()
        record("whisper", "ok")
        return result


_live_model = None
_live_name = None

def warm_live_model():
    global _live_model, _live_name
    if _live_model is not None:
        return _live_name
    from faster_whisper import WhisperModel
    import ctranslate2
    chosen = os.getenv("ALTAIR_WHISPER_MODEL", "base")
    device = os.getenv("ALTAIR_WHISPER_DEVICE", "cpu")
    # Respect selected quality when real-time decoding is feasible. Measure the
    # warm model on a synthetic sample; this measures speed, not speech accuracy.
    candidates = []
    if device == "cuda":
        try:
            if ctranslate2.get_cuda_device_count() > 0:
                candidates.append((chosen, "cuda"))
        except Exception:
            pass
    candidates.extend((name, "cpu") for name in (chosen, "small", "base", "large-v3-turbo"))
    available = [(name, dev) for name, dev in dict.fromkeys(candidates) if (whisper_path(name) / "model.bin").is_file()]
    from altair.core.audio_isolation import record
    for index, (name, dev) in enumerate(available):
        path = whisper_path(name)
        if not (path / "model.bin").is_file():
            continue
        try:
            model = WhisperModel(str(path), device=dev, compute_type="int8_float16" if dev == "cuda" else "int8",
                                 cpu_threads=min(6, os.cpu_count() or 4), local_files_only=True)
            import numpy as np
            segments, _ = model.transcribe(np.zeros(8000, dtype=np.float32), language="pt", beam_size=1, vad_filter=False)
            list(segments)
            # Avoid silent quality downgrades: only fall back if selected
            # decoder cannot keep up, and report the actual model in the UI.
            sample = (.025 * np.sin(2 * np.pi * 220 * np.arange(16000) / 16000)).astype(np.float32)
            start = time.monotonic()
            segments, _ = model.transcribe(sample, language="pt", beam_size=1, vad_filter=False)
            list(segments)
            elapsed = time.monotonic() - start
            record("live-model", name + "/" + dev + " benchmark_ms=" + str(int(elapsed * 1000)))
            if elapsed > 1.2 and index + 1 < len(available):
                # Only downgrade to a smaller model, not a slower GPU fallback.
                smaller = {"large-v3-turbo": 3, "small": 2, "base": 1}
                if any(smaller.get(n, 0) < smaller.get(name, 0) for n, _ in available[index+1:]):
                    del model
                    continue
            _live_model, _live_name = model, name + " / " + dev.upper()
            return _live_name
        except Exception as exc:
            record("live-model", name + "/" + dev + " " + type(exc).__name__)
            continue
    raise RuntimeError("Nenhum modelo Whisper local utilizável")


def live_transcribe(audio, final=False):
    import numpy as np
    warm_live_model()
    audio = np.asarray(audio, dtype=np.float32).flatten()
    if audio.size < 3200:
        return ""
    audio = audio - np.mean(audio)
    peak = float(np.max(np.abs(audio)))
    if peak < .0005:
        return ""
    audio = np.clip(audio * min(4., .8 / peak), -1., 1.)
    segments, _ = _live_model.transcribe(audio, language="pt", task="transcribe",
        beam_size=2 if final else 1, best_of=1, temperature=0., condition_on_previous_text=False,
        vad_filter=final, vad_parameters={"min_speech_duration_ms": 120, "min_silence_duration_ms": 300, "speech_pad_ms": 250} if final else None, no_speech_threshold=.65,
        hotwords=os.getenv("ALTAIR_WHISPER_TERMS", "Altair, ChatGPT, GitHub, Lovable, Codex")[:300] or None)
    return " ".join(s.text.strip() for s in segments if s.no_speech_prob < .8).strip()


class WindowsLocalVoice:
    """Use installed Windows voices; text is passed via stdin, never as shell code."""
    def __init__(self, language="pt-BR"):
        self.language = language
        self._lock = threading.Lock()
        self._process = None
        self._voice_lock = threading.Lock()
        self._interrupted = False

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
                self._interrupted = False
                self._process = proc
            try:
                proc.communicate(str(text).encode("utf-8"), timeout=180)
                if proc.returncode != 0 and not self._interrupted:
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
                self._interrupted = True
                self._process.kill()

    def save_to_file(self, texto, caminho_arquivo):
        # System.Speech writes WAV; callers must convert other formats separately.
        if Path(caminho_arquivo).suffix.lower() != ".wav":
            raise ValueError("A voz local salva somente arquivos .wav.")
        self._run(texto, caminho_arquivo)
        return str(caminho_arquivo)
