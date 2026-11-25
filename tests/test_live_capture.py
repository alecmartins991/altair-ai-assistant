"""Microphone simulation: no physical device, Windows or Whisper required."""
import sys
import types
import time
import threading
import numpy as np
import pytest
from altair.core import live_capture as capture


def mock_audio(monkeypatch, levels, rate=16000):
    clock = [100.0]
    finished, stream_calls, decode_calls = [], [], []
    monkeypatch.setattr(capture, "time", types.SimpleNamespace(monotonic=lambda: clock[0]))

    def decode(audio, final=False):
        decode_calls.append((len(audio), final))
        return "Olá, tudo bem?"

    monkeypatch.setitem(sys.modules, "altair.core.local_voice", types.SimpleNamespace(
        warm_live_model=lambda: "fake", live_transcribe=decode))

    def check_input_settings(samplerate, **kwargs):
        if samplerate != rate:
            raise ValueError("wrong rate")

    class Stream:
        def __init__(self, callback, blocksize, samplerate, **kwargs):
            self.callback, self.blocksize = callback, blocksize
            self.stop = threading.Event()
            stream_calls.append(samplerate)

        def __enter__(self):
            def run():
                for level in levels:
                    if self.stop.is_set():
                        break
                    clock[0] += .02
                    self.callback((level*np.sin(2*np.pi*200*np.arange(self.blocksize)/rate)).astype(np.float32).reshape(-1, 1),
                                  self.blocksize, None, None)
                    time.sleep(.001)
            self.thread = threading.Thread(target=run)
            self.thread.start()
            return self

        def __exit__(self, *args):
            self.stop.set()
            self.thread.join()
            finished.append(True)

    monkeypatch.setitem(sys.modules, "sounddevice", types.SimpleNamespace(
        check_input_settings=check_input_settings,
        query_devices=lambda **kwargs: {"default_samplerate": rate}, InputStream=Stream))
    monkeypatch.setenv("ALTAIR_MIC_THRESHOLD", ".003")
    return finished, stream_calls, decode_calls


@pytest.mark.parametrize("rate", [16000, 48000])
def test_progressive_capture_and_final(monkeypatch, rate):
    finished, stream_calls, decode_calls = mock_audio(monkeypatch, [.0001]*15 + [.03]*90 + [.0001]*80, rate)
    events = []
    assert capture.live_capture(lambda k, v: events.append((k, v))) == "Olá, tudo bem?"
    assert stream_calls == [rate] and finished == [True]
    kinds = [k for k, v in events]
    assert "partial" in kinds and "speech_start" in kinds and "level" in kinds
    assert next(i for i, x in enumerate(events) if x[0] == "partial") < next(
        i for i, x in enumerate(events) if x[0] == "phase" and x[1].startswith("Concluindo"))
    assert any(not final for _, final in decode_calls)


def test_capture_cancellation_closes_device(monkeypatch):
    finished, _, _ = mock_audio(monkeypatch, [.03]*500)
    cancel = threading.Event()
    def emit(k, v):
        if k == "speech_start":
            cancel.set()
    assert capture.live_capture(emit, cancel.is_set) == ""
    assert finished == [True]


def test_silent_capture_never_calls_recognizer(monkeypatch):
    finished, _, decoded = mock_audio(monkeypatch, [.0001]*620)
    events = []
    assert capture.live_capture(lambda k, v: events.append((k, v))) == ""
    assert not decoded and finished
    assert any("Sem sinal" in str(v) for k, v in events if k == "phase")
