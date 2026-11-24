"""Explicit one-time downloads. Never invoked during conversation."""
import argparse
import os
import requests
from faster_whisper.utils import download_model
from altair.core.local_voice import whisper_path
from altair.core.neural_voice import model_dir, synthesize

BASE = "https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files-v1.1/"


def fetch(name):
    target = model_dir() / name
    target.parent.mkdir(parents=True, exist_ok=True)
    if target.is_file() and target.stat().st_size > 1024:
        return
    partial = target.with_suffix(target.suffix + ".part")
    try:
        with requests.get(BASE + name, stream=True, timeout=(20, 120)) as response:
            response.raise_for_status()
            expected = response.headers.get("Content-Length")
            with partial.open("wb") as stream:
                for block in response.iter_content(1024 * 1024):
                    if block:
                        stream.write(block)
            if expected and int(expected) != partial.stat().st_size:
                raise RuntimeError("Incomplete download")
        if partial.stat().st_size < 1024:
            raise RuntimeError("Invalid model file")
        os.replace(partial, target)
    finally:
        partial.unlink(missing_ok=True)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--whisper", choices=["base", "small", "large-v3-turbo"], default="large-v3-turbo")
    args = parser.parse_args()
    print("Baixando Whisper", args.whisper, flush=True)
    download_model(args.whisper, output_dir=str(whisper_path(args.whisper)))
    print("Baixando Kokoro e vozes brasileiras...", flush=True)
    for name in ("kokoro-v1.0.onnx", "voices-v1.0.bin"):
        fetch(name)
    print("Validando sintese neural sem abrir o dispositivo de audio...", flush=True)
    for voice in ("pm_alex", "pm_santa", "pf_dora"):
        if not any(len(samples) > 0 for samples, _ in synthesize("Olá, tudo bem?", voice)):
            raise RuntimeError("Kokoro produced no audio")
    print("Modelos preparados. Selecione kokoro_local e o Whisper instalado no Altair.", flush=True)


if __name__ == "__main__":
    main()
