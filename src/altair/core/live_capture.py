"""Progressive local recognition; native audio and inference stay in the child."""
import os
import time
import queue
import threading
from collections import deque
from concurrent.futures import ThreadPoolExecutor
import numpy as np
from altair.core.live_dsp import VoiceGate, pause_seconds

RATE = 16000
BLOCK = 320


def live_capture(emit, cancelled=lambda: False):
    import sounddevice as sd
    from altair.core.local_voice import live_transcribe, warm_live_model
    from altair.core.audio_isolation import record
    # Warm only once, before the microphone opens. Keep the model in this worker.
    emit("phase", "Preparando reconhecimento…")
    model = warm_live_model()
    if cancelled():
        return ""
    # Match the Windows default input format if 16 kHz is not supported.
    rate = RATE
    try:
        sd.check_input_settings(channels=1, dtype="float32", samplerate=rate)
    except Exception:
        rate = int(sd.query_devices(kind="input")["default_samplerate"])
        sd.check_input_settings(channels=1, dtype="float32", samplerate=rate)
    input_block = max(1, int(rate * BLOCK / RATE))
    emit("phase", "Ouvindo • " + model)
    frames = queue.Queue(maxsize=500)
    overflow = threading.Event()
    pre = deque(maxlen=15)
    threshold = min(.025, max(.0007, float(os.getenv("ALTAIR_MIC_THRESHOLD", ".003")) * .55))
    gate = VoiceGate(threshold)
    configured_pause = min(.95, float(os.getenv("ALTAIR_MIC_PAUSE", "1.8")) * .5)
    audio = []
    started = None
    last_voice = None
    last_partial = ""
    partial_at = 0
    partial_n = 0
    future = None
    last_level = 0
    heard = 0
    max_level = 0.0
    start = time.monotonic()
    last_frame = start

    def callback(indata, count, info, status):
        try:
            frames.put_nowait((time.monotonic(), indata[:, 0].copy()))
        except queue.Full:
            overflow.set()

    def submit(executor, samples, final):
        return executor.submit(live_transcribe, gate.clean(np.concatenate(samples)), final=final)

    def collect():
        nonlocal future, last_partial
        if future is not None and future.done():
            last_partial = future.result().strip()
            future = None
            if last_partial:
                emit("partial", last_partial)

    with ThreadPoolExecutor(max_workers=1) as executor:
        with sd.InputStream(samplerate=rate, channels=1, dtype="float32", blocksize=input_block, callback=callback):
            while True:
                if cancelled():
                    return ""
                collect()
                if overflow.is_set():
                    raise RuntimeError("Microphone buffer overflow")
                try:
                    now, frame = frames.get(timeout=.1)
                except queue.Empty:
                    if time.monotonic() - last_frame > 3:
                        raise RuntimeError("Microphone stopped delivering frames")
                    continue
                if rate != RATE or len(frame) != BLOCK:
                    frame = np.interp(np.linspace(0, len(frame)-1, BLOCK), np.arange(len(frame)), frame).astype(np.float32)
                last_frame = now
                level, is_voice = gate.analyze(frame)
                max_level = max(max_level, level)
                if now - last_level >= .08:
                    emit("level", level)
                    last_level = now
                if started is None:
                    pre.append(frame)
                    if is_voice:
                        heard += 1
                    else:
                        heard = 0
                    if heard >= 3:
                        started = last_voice = now
                        audio.extend(pre)
                        pre.clear()
                        emit("speech_start", True)
                        emit("phase", "Transcrevendo sua fala…")
                    elif now - start > 12:
                        if max_level < .0005:
                            emit("phase", "Sem sinal do microfone — confira a entrada padrão do Windows")
                            record("live-mic", "no-signal")
                        return ""
                    continue
                audio.append(frame)
                if is_voice:
                    last_voice = now
                # Re-decode snapshots while speaking; never enqueue stale partials.
                if future is None and now - started >= .65 and now - partial_at >= .65 and len(audio) > partial_n + 20:
                    partial_n = len(audio)
                    partial_at = now
                    future = submit(executor, list(audio), False)
                pause = pause_seconds(last_partial, configured_pause)
                if now - last_voice >= pause or now - started >= 60:
                    break
        emit("level", 0.0)
        if cancelled():
            return ""
        emit("phase", "Concluindo transcrição…")
        if future is not None:
            last_partial = future.result().strip()
        if cancelled():
            return ""
        # Reuse a partial only if it includes all voiced frames plus a short tail.
        voiced_n = max(0, len(audio) - int((now - last_voice) * RATE / BLOCK))
        if last_partial and partial_n >= voiced_n + 15 and partial_n > 0:
            result = last_partial
        else:
            result = submit(executor, audio, True).result().strip()
        if not result:
            emit("phase", "Não consegui entender. Pode repetir?")
        record("live-stt", "ms=" + str(int((time.monotonic()-now)*1000)))
        return "" if cancelled() else result
