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
    cfg = payload["config"]
    if cfg.get("provider") == "kokoro_local":
        from altair.core import neural_voice
        args = (payload["text"], cfg.get("kokoro_voice", "pm_alex"), cfg.get("kokoro_speed", "1.0"))
        if action == "save":
            return neural_voice.save(*args, payload["path"])
        return neural_voice.play(*args)
    from altair.core.voice import ElevenLabsVoice
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
    if not pygame.mixer.get_init():
        pygame.mixer.init()
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


def _reply(action, payload):
    try:
        with contextlib.redirect_stdout(io.StringIO()):
            return {"ok": True, "value": execute(action, payload)}
    except Exception as exc:
        record("child", type(exc).__name__)
        return {"ok": False, "error": type(exc).__name__}


def main():
    LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
    with LOG_FILE.open("a", encoding="utf-8") as log:
        faulthandler.enable(file=log, all_threads=True)
        try:
            if sys.argv[1] == "resident":
                for line in sys.stdin:
                    req = json.loads(line)
                    print(json.dumps(_reply(req["action"], req["payload"]), ensure_ascii=True), flush=True)
            else:
                print(json.dumps(_reply(sys.argv[1], json.load(sys.stdin)), ensure_ascii=True), flush=True)
        finally:
            faulthandler.disable()


if __name__ == "__main__":
    main()
