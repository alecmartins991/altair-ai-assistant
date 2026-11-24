"""Hybrid tests that do not contact OpenAI or access real microphones."""
from unittest.mock import Mock, patch
import json
import subprocess

import pytest

from altair.core import audio_core
from altair.core import local_voice
from altair.core import companion_tools
from altair.core.chatgpt_plan import ChatGPTPlanLLM, PlanError, ChatGPTSession


def test_offline_stt_never_falls_back(monkeypatch, tmp_path):
    monkeypatch.setenv("ALTAIR_STT_MODE", "local")
    monkeypatch.setenv("ALTAIR_WHISPER_PATH", str(tmp_path))
    monkeypatch.setattr(audio_core, "_remote_stt_enabled", lambda: pytest.fail("remote STT accessed"))
    assert not audio_core._stt_enabled()
    (tmp_path / "model.bin").write_bytes(b"fixture")
    assert audio_core._stt_enabled()


def test_local_whisper_requires_download(monkeypatch, tmp_path):
    monkeypatch.setenv("ALTAIR_WHISPER_PATH", str(tmp_path))
    with pytest.raises(RuntimeError, match="Whisper"):
        local_voice.transcribe_local(None)


def test_invalid_image_never_sent():
    llm = ChatGPTPlanLLM("example", session=Mock())
    with patch.object(llm, "_request_response") as request:
        with pytest.raises(PlanError):
            llm.analyze_image(b"not-a-png", "What?")
        request.assert_not_called()


def test_screenshot_uses_explicit_image_and_no_storage():
    llm = ChatGPTPlanLLM("example", session=Mock())
    with patch.object(llm, "_request_response", return_value="ok") as request:
        assert llm.analyze_image(b"\x89PNG\r\n\x1a\nfixture", "What?") == "ok"
        body = request.call_args.args[0]
        assert body["store"] is False
        assert body["stream"] is True
        assert body["input"][0]["content"][1]["type"] == "input_image"


def test_incomplete_refresh_record_rejected():
    with pytest.raises(PlanError):
        ChatGPTSession._record({"expires_in": 300}, {"access_token": "stale"})


def test_git_is_readonly(tmp_path):
    result = subprocess.CompletedProcess([], 0, stdout="sample", stderr="")
    with patch.object(companion_tools.shutil, "which", return_value="git"), patch.object(
        companion_tools.subprocess, "run", return_value=result
    ) as run:
        companion_tools.git_summary(tmp_path)
        commands = [call.args[0] for call in run.call_args_list]
        assert [cmd[7] for cmd in commands] == ["rev-parse", "status", "log", "diff"]
        assert all("shell" not in call.kwargs or call.kwargs["shell"] is False for call in run.call_args_list)
