"""Offline preflight. Does not read credentials or contact ChatGPT."""
import importlib.util
import json
import sys
from pathlib import Path


def main():
    from altair.paths import APP_DATA_ROOT, DATA_DIR
    from altair.core.local_voice import whisper_path
    problems = []
    print("Altair Live - diagnóstico local")
    for name in ("PyQt5", "numpy", "sounddevice", "faster_whisper", "ctranslate2"):
        if importlib.util.find_spec(name) is None:
            problems.append("Dependência ausente: " + name)
        else:
            print("OK:", name)
    installed = [name for name in ("small", "base", "large-v3-turbo")
                 if (whisper_path(name) / "model.bin").is_file()]
    print("Whisper instalado:", ", ".join(installed) or "nenhum")
    if not installed:
        problems.append("Execute atualizar_voz.cmd para instalar modelos locais.")
    # Read only the voice provider name, never print other settings or keys.
    provider = "windows_local"
    try:
        provider = json.loads((DATA_DIR / "json" / "voice_config.json").read_text(encoding="utf-8")).get("provider", provider)
    except (OSError, ValueError, AttributeError):
        pass
    if provider == "kokoro_local":
        from altair.core.neural_voice import ready
        if not ready() or importlib.util.find_spec("kokoro_onnx") is None:
            problems.append("Kokoro não está completo. Execute atualizar_voz.cmd.")
        else:
            print("OK: arquivos do Kokoro")
    try:
        import sounddevice as sd
        info = sd.query_devices(kind="input")
        print("Entrada padrão:", info["name"])
        usable = False
        for rate, channels in ((16000, 1), (int(info["default_samplerate"]), 1), (int(info["default_samplerate"]), 2)):
            try:
                sd.check_input_settings(samplerate=rate, channels=channels, dtype="float32")
                print("OK: formato de entrada", rate, "Hz,", channels, "canal(is)")
                usable = True
                break
            except Exception:
                continue
        if not usable:
            problems.append("Nenhum formato de entrada compatível.")
    except Exception as exc:
        problems.append("Entrada de áudio indisponível: " + type(exc).__name__)
    print("Log local:", APP_DATA_ROOT / "logs" / "audio-stability.log")
    if problems:
        for problem in problems:
            print("ATENÇÃO:", problem)
        return 1
    print("Pré-checagem concluída. Não testa fala real, síntese ou conexão com ChatGPT.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
