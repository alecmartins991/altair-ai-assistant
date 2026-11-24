"""Live regression checks with fake LLM and no actual account or microphone."""
import json
import threading
from unittest.mock import Mock
import pytest
from altair.core.chatgpt_plan import _parse_stream, PlanError
from altair.core.live_conversation import answer_turn, explicit_command, SpeechBuffer


def test_parse_stream_emits_deltas_before_completion():
    deltas = []
    def source():
        yield 'data: ' + json.dumps({"type":"response.output_text.delta","delta":"Olá. "})
        assert deltas == ["Olá. "]
        yield 'data: ' + json.dumps({"type":"response.output_text.delta","delta":"Tudo bem?"})
        yield 'data: {"type":"response.completed"}'
    assert _parse_stream(source(), deltas.append) == "Olá. Tudo bem?"
    assert deltas == ["Olá. ", "Tudo bem?"]


def test_cancelled_sse_does_not_return_stale_answer():
    with pytest.raises(PlanError) as exc:
        _parse_stream(['data: {"type":"response.completed"}'], cancelled=lambda: True)
    assert exc.value.code == "live_cancelled"


def test_live_conversation_does_not_call_command_router():
    spoken = []
    progress = []
    history = []
    started = threading.Event()
    command = Mock()
    class FakeLLM:
        def live_answer(self, text, context, emit, cancelled):
            emit("Tudo bem. ")
            assert started.wait(2), "Speech did not start before response completed"
            emit("Como posso ajudar?")
            return "Tudo bem. Como posso ajudar?"
    def speak(part):
        spoken.append(part)
        started.set()
    answer, streamed = answer_turn(FakeLLM(), "E aí, tudo certo?", history, speak, progress.append, lambda: False, command)
    assert streamed and answer == history[-1]["content"]
    assert spoken == ["Tudo bem.", "Como posso ajudar?"]
    assert progress[-1] == answer
    command.assert_not_called()


def test_explicit_command_retains_existing_service():
    command = Mock(return_value={"visual":"Aberto", "fala":"Pronto."})
    spoke = []
    assert explicit_command("Altair, abra o navegador")
    assert not explicit_command("Você sabe como abrir o navegador?")
    assert answer_turn(Mock(), "abra o navegador", [], spoke.append, lambda x: None, lambda: False, command) == ("Aberto", False)
    command.assert_called_once_with("abra o navegador")
    assert spoke == ["Pronto."]


def test_cancelled_buffer_never_plays_queued_text():
    cancelled = threading.Event()
    cancelled.set()
    speak = Mock()
    buffer = SpeechBuffer(speak, cancelled.is_set)
    buffer.push("Resposta antiga.")
    buffer.finish()
    speak.assert_not_called()
