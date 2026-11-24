"""Progressive local recognition; native audio and inference stay in the child."""
import os
import time
import queue
import threading
from collections import deque
from concurrent.futures import ThreadPoolExecutor
import numpy as np

RATE = 16000
BLOCK = 320


def live_capture(emit):
    import sounddevice as sd
    from altair.core.local_voice import live_transcribe, warm_live_model
    from altair.core.audio_isolation import record
    # Warm only once, before the microphone opens. Keep the model in this worker.
    emit("phase", "Preparando reconhecimento…")
    model = warm_live_model()
    emit("phase", "Ouvindo • " + model)
    frames = queue.Queue(maxsize=500)
    overflow = threading.Event()
    pre = deque(maxlen=15)
    noise = 0.0005
    threshold = min(.025, max(.0007, float(os.getenv("ALTAIR_MIC_THRESHOLD", ".003")) * .55))
    audio = []
    started = None
    last_voice = None
    last_partial = ""
    partial_at = 0
    partial_n = 0
    future = None
    first_level = 0
    last_level = 0
    heard = 0
    start = time.monotonic()

    def callback(indata, count, info, status):
        try:
            frames.put_nowait((time.monotonic(), indata[:, 0].copy()))
        except queue.Full:
            overflow.set()

    def submit(executor, samples, final):
        return executor.submit(live_transcribe, np.concatenate(samples), final=final)

    def collect():
        nonlocal future, last_partial
        if future is not None and future.done():
            last_partial = future.result().strip()
            future = None
            if last_partial:
                emit("partial", last_partial)

    with ThreadPoolExecutor(max_workers=1) as executor:
        with sd.InputStream(samplerate=RATE, channels=1, dtype="float32", blocksize=BLOCK, callback=callback):
            while True:
                collect()
                if overflow.is_set():
                    raise RuntimeError("Microphone buffer overflow")
                try:
                    now, frame = frames.get(timeout=.1)
                except queue.Empty:
                    if time.monotonic() - start > 12 and started is None:
                        return ""
                    continue
                level = float(np.sqrt(np.mean(frame * frame)))
                if now - last_level >= .08:
                    emit("level", level)
                    last_level = now
                gate = max(threshold, min(.025, noise * 2.8))
                if started is None:
                    pre.append(frame)
                    if level > gate:
                        heard += 1
                    else:
                        heard = 0
                        noise = noise * .98 + min(level, .008) * .02
                    if heard >= 3:
                        started = last_voice = now
                        audio.extend(pre)
                        pre.clear()
                        emit("phase", "Transcrevendo sua fala…")
                    elif now - start > 12:
                        return ""
                    continue
                audio.append(frame)
                if level > gate:
                    last_voice = now
                # Re-decode snapshots while speaking; never enqueue stale partials.
                if future is None and now - started >= .65 and now - partial_at >= .65 and len(audio) > partial_n + 20:
                    partial_n = len(audio)
                    partial_at = now
                    future = submit(executor, list(audio), False)
                pause = .70
                if last_partial.rstrip().endswith((",", "...", ":")) or last_partial.lower().split()[-1:] in (["e"], ["que"], ["porque"], ["mas"], ["pra"], ["de"]):
                    pause = 1.15
                if now - last_voice >= pause or now - started >= 35:
                    break
        emit("level", 0.0)
        emit("phase", "Concluindo transcrição…")
        if future is not None:
            last_partial = future.result().strip()
        # Last partial often already covers the whole speech; otherwise finalize once.
        voiced_n = max(0, len(audio) - int((now - last_voice) * RATE / BLOCK))
        if last_partial and partial_n >= voiced_n and partial_n > 0:
            result = last_partial
        else:
            result = submit(executor, audio, True).result().strip()
        record("live-stt", "ms=" + str(int((time.monotonic()-now)*1000)))
        return result
