"""Live voice turn orchestration. Never execute partial transcripts."""
import re
import threading
import queue
import time
from contextlib import nullcontext
from altair.core.audio_isolation import record


def explicit_command(text):
    # Preserve the existing command service for explicit requests, not casual chat.
    return bool(re.match(r"^\s*(?:altair[\s,]+)?(?:por favor[\s,]+)?(?:abra|abre|abrir|feche|execute|inicie|desligue|ligue|envie|mande|encaminhe|compartilhe|clique|digite|pesquise|procure|busque|calcule|gere|crie|analise|leia|liste|mostre|simule|organize)\b", text, re.I))


class SpeechBuffer:
    """Buffer deltas into speakable phrases without holding up the network."""
    def __init__(self, speak, cancelled):
        self.speak = speak
        self.cancelled = cancelled
        self.pending = ""
        self.aborted = threading.Event()
        self.items = queue.Queue()
        self.thread = threading.Thread(target=self._play, daemon=True, name="altair-live-speech")
        self.thread.start()

    def push(self, delta):
        if self.cancelled():
            return
        self.pending += delta
        while True:
            match = re.search(r"[.!?;:](?:\s+|$)", self.pending)
            if match and self.pending[:match.end()].strip():
                end = match.end()
            elif len(self.pending) >= 110:
                end = self.pending.rfind(" ", 30, 110)
                if end < 0:
                    end = 110
            else:
                break
            part = self.pending[:end].strip()
            self.pending = self.pending[end:]
            if part:
                self.items.put(part)

    def _play(self):
        while True:
            part = self.items.get()
            if part is None or self.cancelled() or self.aborted.is_set():
                return
            try:
                self.speak(part)
            except Exception as exc:
                record("live-playback", type(exc).__name__)
                return

    def finish(self, flush=True):
        if not flush:
            self.aborted.set()
        if flush and self.pending.strip() and not self.cancelled():
            self.items.put(self.pending.strip())
        self.pending = ""
        self.items.put(None)
        self.thread.join()


def answer_turn(llm, text, history, speak, progress, cancelled, command, request_lock=None):
    """One ordinary conversation request, using the approved text account."""
    if explicit_command(text) or not callable(getattr(llm, "live_answer", None)):
        with request_lock if request_lock else nullcontext():
            if cancelled():
                return "", False
            result = command(text)
        if isinstance(result, dict):
            visual, spoken = str(result.get("visual") or ""), str(result.get("fala") or "")
        else:
            visual = spoken = str(result)
        if spoken and not cancelled():
            speak(spoken)
        if visual and not cancelled():
            history.extend([{"role":"user","content":text},{"role":"assistant","content":visual}])
            del history[:-12]
        return visual, False
    started = time.monotonic()
    pieces = []
    speech = SpeechBuffer(speak, cancelled)

    def on_delta(delta):
        if cancelled():
            return
        if not pieces:
            record("live-first-token", "ms=" + str(int((time.monotonic()-started)*1000)))
        pieces.append(delta)
        progress("".join(pieces))
        speech.push(delta)

    try:
        with request_lock if request_lock else nullcontext():
            if cancelled():
                speech.finish(flush=False)
                return "", True
            answer = llm.live_answer(text, history, on_delta, cancelled)
    except Exception:
        speech.finish(flush=False)
        raise
    speech.finish()
    if not cancelled():
        history.extend([{"role":"user","content":text},{"role":"assistant","content":answer}])
        del history[:-12]
    return answer, True
