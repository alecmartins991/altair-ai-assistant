"""Audio process isolation and privacy-safe diagnostics for the desktop launcher."""
import datetime
import os
import json
import subprocess
import sys
import threading
import time
from pathlib import Path

from altair.paths import APP_DATA_ROOT

DEVICE_LOCK = threading.Lock()
SPEECH_PENDING = threading.Event()
_speech_lock = threading.Lock()
LOG_FILE = APP_DATA_ROOT / "logs" / "audio-stability.log"


def record(stage, detail=""):
    # Callers pass fixed stage names, exception types or exit codes only.
    try:
        LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
        with LOG_FILE.open("a", encoding="utf-8") as stream:
            stream.write(f"{datetime.datetime.now().isoformat(timespec='seconds')} {stage} {detail}\n")
    except OSError:
        pass


class AudioFailure(RuntimeError):
    pass


def run_worker(action, payload, cancel=None, timeout=120):
    """Run native audio in a disposable process; never put credentials in argv."""
    if getattr(sys, "frozen", False):
        raise AudioFailure("Este modo de áudio requer a instalação Python do Altair Hybrid.")
    if cancel and cancel():
        return None
    env = os.environ.copy()
    root = str(Path(__file__).resolve().parents[2])
    env["PYTHONPATH"] = root + os.pathsep + env.get("PYTHONPATH", "")
    env["PYTHONIOENCODING"] = "utf-8"
    env["PYGAME_HIDE_SUPPORT_PROMPT"] = "1"
    record(action, "start")
    process = subprocess.Popen(
        [sys.executable, "-m", "altair.core.audio_worker", action],
        stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
        env=env, creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
    )
    deadline = time.monotonic() + timeout
    data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    try:
        while True:
            if cancel and cancel():
                record(action, "cancelled")
                return None
            if time.monotonic() >= deadline:
                raise AudioFailure("Tempo limite do processo de áudio.")
            try:
                output, _ = process.communicate(input=data, timeout=0.2)
                break
            except subprocess.TimeoutExpired:
                data = None
        if process.returncode:
            record(action, f"exit={process.returncode}")
            raise AudioFailure(f"Processo de áudio falhou (código {process.returncode}). Veja audio-stability.log.")
        try:
            result = json.loads(output.decode("utf-8"))
        except (ValueError, UnicodeError):
            raise AudioFailure("Resposta inválida do processo de áudio.") from None
        if not isinstance(result, dict) or result.get("ok") is not True:
            kind = result.get("error", "AudioFailure") if isinstance(result, dict) else "AudioFailure"
            record(action, "worker error")
            raise AudioFailure(f"Falha de áudio ({kind}). Veja audio-stability.log.")
        record(action, "ok")
        return result.get("value")
    finally:
        if process.poll() is None:
            process.kill()
            process.communicate()


class IsolatedVoice:
    """Serialize speech and pause capture; local System.Speech already uses a child."""
    def __init__(self, config):
        self.config = dict(config)
        self._cancel = threading.Event()
        self._local = None
        if config.get("provider") == "windows_local":
            from altair.core.local_voice import WindowsLocalVoice
            self._local = WindowsLocalVoice()

    def speak(self, text):
        if not str(text).strip():
            return
        with _speech_lock:
            self._cancel.clear()
            SPEECH_PENDING.set()
            try:
                with DEVICE_LOCK:
                    if self._cancel.is_set():
                        return
                    record("speech", "start")
                    if self._local:
                        self._local.speak(text)
                    else:
                        run_worker("speak", {"config": self.config, "text": str(text)},
                                   cancel=self._cancel.is_set, timeout=180)
                    record("speech", "ok")
            except Exception as exc:
                record("speech", type(exc).__name__)
                raise AudioFailure("Não foi possível reproduzir a voz. Consulte audio-stability.log.") from None
            finally:
                SPEECH_PENDING.clear()

    def stop(self):
        self._cancel.set()
        if self._local:
            self._local.stop()

    def save_to_file(self, text, path):
        if self._local:
            return self._local.save_to_file(text, path)
        return run_worker("save", {"config": self.config, "text": str(text), "path": str(path)}, timeout=180)
