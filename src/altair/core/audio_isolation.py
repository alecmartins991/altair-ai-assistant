"""Audio process isolation and privacy-safe diagnostics for the desktop launcher."""
import atexit
import queue
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


class ResidentWorker:
    """Keep a model warm in its own process. Cancellation kills only that worker."""
    def __init__(self):
        self.lock = threading.Lock()
        self.process = None
        self.responses = None
        self.settings = None
        atexit.register(self.close)

    def close(self):
        p, self.process = self.process, None
        if p is not None:
            try:
                if p.poll() is None:
                    p.kill()
                p.wait(timeout=3)
            except (OSError, subprocess.TimeoutExpired):
                pass
            finally:
                for stream in (p.stdin, p.stdout):
                    try:
                        stream.close()
                    except (OSError, ValueError):
                        pass

    def _start(self, settings):
        self.close()
        env = os.environ.copy()
        env["PYTHONPATH"] = str(Path(__file__).resolve().parents[2]) + os.pathsep + env.get("PYTHONPATH", "")
        env["PYTHONIOENCODING"] = "utf-8"
        env["PYGAME_HIDE_SUPPORT_PROMPT"] = "1"
        env["HF_HUB_OFFLINE"] = "1"
        self.process = subprocess.Popen([sys.executable, "-m", "altair.core.audio_worker", "resident"],
            stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
            env=env, creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
        self.settings = settings
        responses = self.responses = queue.Queue()
        p = self.process
        def reader():
            try:
                for line in iter(p.stdout.readline, b""):
                    responses.put(line)
            except (OSError, ValueError):
                pass
            finally:
                responses.put(None)
        threading.Thread(target=reader, daemon=True).start()

    def call(self, action, payload, cancel=None, timeout=120, on_event=None):
        if getattr(sys, "frozen", False):
            raise AudioFailure("Use a instalação Python do Altair Hybrid.")
        with self.lock:
            if cancel and cancel():
                return None
            settings = tuple(sorted((k, v) for k, v in os.environ.items()
                if k.startswith(("ALTAIR_STT_", "ALTAIR_WHISPER_", "ALTAIR_MIC_", "ALTAIR_EXTERNAL_SERVICES_"))))
            try:
                if self.process is None or self.process.poll() is not None or self.settings != settings:
                    self._start(settings)
                self.process.stdin.write((json.dumps({"action": action, "payload": payload}, ensure_ascii=True) + "\n").encode("ascii"))
                self.process.stdin.flush()
                deadline = time.monotonic() + timeout
                cancel_deadline = None
                while True:
                    if cancel and cancel():
                        if action != "live_capture":
                            self.close()
                            return None
                        if cancel_deadline is None:
                            self.process.stdin.write(b'{"action":"cancel"}\n')
                            self.process.stdin.flush()
                            cancel_deadline = time.monotonic() + 1.0
                    if cancel_deadline is not None and time.monotonic() >= cancel_deadline:
                        self.close()
                        return None
                    if time.monotonic() >= deadline:
                        raise AudioFailure("Tempo limite de áudio.")
                    try:
                        line = self.responses.get(timeout=0.1)
                    except queue.Empty:
                        continue
                    if line is None:
                        raise AudioFailure("Processo de áudio encerrou inesperadamente.")
                    result = json.loads(line)
                    if "event" in result:
                        if on_event and cancel_deadline is None:
                            on_event(result["event"], result.get("value"))
                        continue
                    if cancel_deadline is not None:
                        return None
                    if result.get("ok") is not True:
                        raise AudioFailure("Falha no áudio (" + str(result.get("error", "AudioFailure")) + ").")
                    return result.get("value")
            except Exception as exc:
                record(action, type(exc).__name__)
                self.close()
                raise AudioFailure("Falha no processo de áudio. Consulte audio-stability.log.") from None


CAPTURE_WORKER = ResidentWorker()
KOKORO_WORKER = ResidentWorker()


class IsolatedVoice:
    """Serialize speech and pause capture; local System.Speech already uses a child."""
    def __init__(self, config):
        self.config = dict(config)
        self._cancel = threading.Event()
        self._local = None
        if config.get("provider") == "windows_local":
            from altair.core.local_voice import WindowsLocalVoice
            self._local = WindowsLocalVoice()

    def speak(self, text, cancelled=None):
        if not str(text).strip():
            return
        def stopped():
            return self._cancel.is_set() or (cancelled is not None and cancelled())
        with _speech_lock:
            if cancelled is not None and cancelled():
                return
            self._cancel.clear()
            SPEECH_PENDING.set()
            try:
                with DEVICE_LOCK:
                    if stopped():
                        return
                    record("speech", "start")
                    if self._local:
                        self._local.speak(text)
                    elif self.config.get("provider") == "kokoro_local":
                        KOKORO_WORKER.call("speak", {"config": self.config, "text": str(text)},
                                           cancel=stopped, timeout=180)
                    else:
                        run_worker("speak", {"config": self.config, "text": str(text)},
                                   cancel=stopped, timeout=180)
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
        if self.config.get("provider") == "kokoro_local":
            return KOKORO_WORKER.call("save", {"config": self.config, "text": str(text), "path": str(path)}, timeout=180)
        return run_worker("save", {"config": self.config, "text": str(text), "path": str(path)}, timeout=180)
