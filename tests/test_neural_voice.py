"""Neural voice regression tests without actual models or network."""
from unittest.mock import patch, Mock
import queue
import pytest
from altair.core import neural_voice, local_voice, audio_isolation


def test_voice_chunks_preserve_portuguese():
    parts = list(neural_voice.chunks("Olá, tudo bem? Eu sou o Altair. " + "Uma frase longa. " * 40))
    assert parts[0] == "Olá, tudo bem?"
    assert all(len(part) <= 180 for part in parts)


def test_model_selection(tmp_path, monkeypatch):
    monkeypatch.delenv("ALTAIR_WHISPER_PATH", raising=False)
    monkeypatch.setattr(local_voice, "APP_DATA_ROOT", tmp_path)
    assert local_voice.whisper_path("large-v3-turbo").name == "whisper-large-v3-turbo"
    assert local_voice.whisper_path("base").name == "whisper-base"


def test_kokoro_provider_isolated():
    voice = audio_isolation.IsolatedVoice({"provider":"kokoro_local", "kokoro_voice":"pf_dora"})
    with patch.object(audio_isolation.KOKORO_WORKER, "call") as call:
        voice.speak("Olá")
        assert call.call_args.args[0] == "speak"
        assert call.call_args.args[1]["config"]["kokoro_voice"] == "pf_dora"
    assert not audio_isolation.SPEECH_PENDING.is_set()


def test_resident_recovers_from_worker_exit():
    worker = audio_isolation.ResidentWorker()
    proc = Mock()
    proc.poll.return_value = 1
    def start(settings):
        worker.process = proc
        worker.responses = queue.Queue()
        worker.responses.put(None)
        worker.settings = settings
    with patch.object(worker, "_start", side_effect=start):
        with pytest.raises(audio_isolation.AudioFailure):
            worker.call("capture", {})
    assert worker.process is None
