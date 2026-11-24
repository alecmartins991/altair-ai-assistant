"""Child-only native audio entry point. No Qt or main application imports."""
import contextlib
import faulthandler
import io
import json
import sys
import time
from pathlib import Path

from altair.core.audio_isolation import LOG_FILE, record


def execute(action, payload):
    if action == "capture":
        from altair.core.audio_core import _ouvir_microfone_impl
        return _ouvir_microfone_impl()
    if action not in {"speak", "save"}:
        raise ValueError("Invalid action")
    from altair.core.voice import ElevenLabsVoice
    cfg = payload["config"]
    voice = ElevenLabsVoice(
        api_key=cfg.get("eleven_api_key", ""),
        voice_id=cfg.get("eleven_voice_id", ""),
        model_id=cfg.get("eleven_model_id", "eleven_multilingual_v2"),
        fallback_voice=None,
    )
    text = voice._normalizar_texto_fala(payload["text"])
    if not text:
        return None
    if action == "save":
        return voice.save_to_file(text, payload["path"])
    import pygame
    audio = voice._sintetizar_mp3(text)
    if not audio:
        raise RuntimeError("Empty audio")
    pygame.mixer.music.load(io.BytesIO(audio), "mp3")
    try:
        pygame.mixer.music.play()
        while pygame.mixer.music.get_busy():
            time.sleep(0.05)
    finally:
        pygame.mixer.music.stop()
        pygame.mixer.music.unload()
        pygame.mixer.quit()
    return None


def main():
    LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
    with LOG_FILE.open("a", encoding="utf-8") as log:
        faulthandler.enable(file=log, all_threads=True)
        try:
            payload = json.load(sys.stdin)
            with contextlib.redirect_stdout(io.StringIO()):
                result = {"ok": True, "value": execute(sys.argv[1], payload)}
        except Exception as exc:
            record("child", type(exc).__name__)
            result = {"ok": False, "error": type(exc).__name__}
        finally:
            faulthandler.disable()
        print(json.dumps(result, ensure_ascii=True), flush=True)


if __name__ == "__main__":
    main()
