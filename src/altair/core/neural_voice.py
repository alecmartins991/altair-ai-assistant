"""Local Kokoro ONNX speech; called exclusively in an isolated audio worker."""
import os
import re
from pathlib import Path
from altair.paths import APP_DATA_ROOT

VOICES = {"pm_alex": "Alex", "pm_santa": "Santa", "pf_dora": "Dora"}
_engine = None


def model_dir():
    return APP_DATA_ROOT / "models" / "kokoro-v1"


def ready():
    return all((model_dir() / name).is_file() for name in ("kokoro-v1.0.onnx", "voices-v1.0.bin"))


def chunks(text):
    text = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", str(text))
    text = re.sub(r"[#*_~\x60]", "", text)
    text = re.sub(r"\s+", " ", text).strip()
    for sentence in re.split(r"(?<=[.!?;:])\s+", text):
        words = sentence.split()
        part = ""
        for word in words:
            if len(part) + len(word) > 180 and part:
                yield part
                part = ""
            part = (part + " " + word).strip()
        if part:
            yield part


def synthesize(text, voice="pm_alex", speed=1.0):
    global _engine
    if not ready():
        raise RuntimeError("Kokoro models missing")
    if voice not in VOICES or not 0.75 <= float(speed) <= 1.25:
        raise ValueError("Invalid voice or speed")
    if _engine is None:
        os.environ.setdefault("HF_HUB_OFFLINE", "1")
        from kokoro_onnx import Kokoro
        root = model_dir()
        _engine = Kokoro(str(root / "kokoro-v1.0.onnx"), str(root / "voices-v1.0.bin"))
    for part in chunks(text):
        samples, rate = _engine.create(part, voice=voice, speed=float(speed), lang="pt-br")
        if len(samples):
            yield samples, rate


def play(text, voice, speed):
    import sounddevice as sd
    try:
        for samples, rate in synthesize(text, voice, speed):
            sd.play(samples, rate, blocking=True)
    finally:
        sd.stop()


def save(text, voice, speed, path):
    import numpy as np
    import soundfile as sf
    pieces = list(synthesize(text, voice, speed))
    if not pieces:
        raise RuntimeError("Empty speech")
    rate = pieces[0][1]
    if any(r != rate for _, r in pieces):
        raise RuntimeError("Sample rate mismatch")
    sf.write(str(path), np.concatenate([s for s, _ in pieces]), rate)
    return str(path)
