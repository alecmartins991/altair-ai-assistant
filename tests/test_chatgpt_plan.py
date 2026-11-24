"""Offline unit tests for the ChatGPT plan adapter (no real account or network)."""
import json
import time
from unittest.mock import Mock, patch

import pytest

from altair.core.chatgpt_plan import ChatGPTSession, ChatGPTPlanLLM, PlanError, PERMISSION, _parse_stream


def events(*items):
    return ["data: " + json.dumps(item) for item in items]


def test_stream_requires_completion():
    assert _parse_stream(events(
        {"type": "response.output_text.delta", "delta": "Olá"},
        {"type": "response.output_text.delta", "delta": "!"},
        {"type": "response.completed"},
    )) == "Olá!"


@pytest.mark.parametrize("kind", ["response.failed", "response.incomplete", "error"])
def test_stream_failure(kind):
    with pytest.raises(PlanError):
        _parse_stream(events({"type": "response.output_text.delta", "delta": "parcial"},
                             {"type": kind}))


def test_interrupted_stream():
    with pytest.raises(PlanError):
        _parse_stream(events({"type": "response.output_text.delta", "delta": "parcial"}))


def test_identity_is_not_plan_permission(tmp_path):
    session = ChatGPTSession(tmp_path)
    session.save({"access_token": "test", "scopes": ["openid"]})
    assert not session.authorized()
    with patch("altair.core.chatgpt_plan.require_external_services_allowed"):
        with pytest.raises(PlanError):
            session.access_token()


def test_refresh_rotates_credentials(tmp_path):
    session = ChatGPTSession(tmp_path)
    session.save({"client_id": "oaiapp_test", "subject": "one", "access_token": "old",
                  "refresh_token": "old_refresh", "expires_at": 0, "scopes": [PERMISSION]})
    with patch("altair.core.chatgpt_plan.require_external_services_allowed"), patch(
        "altair.core.chatgpt_plan._post_token",
        return_value={"access_token": "new", "refresh_token": "new_refresh", "expires_in": 3600,
                      "scope": PERMISSION},
    ) as refresh:
        assert session.access_token() == "new"
        assert refresh.call_args.args[0]["client_id"] == "oaiapp_test"
    assert session.load()["refresh_token"] == "new_refresh"


def test_memory_isolated_by_registration(tmp_path):
    session = ChatGPTSession(tmp_path)
    session.save({"client_id": "a", "subject": "one"})
    session.save_memory({"enabled": True, "context": "private"})
    session.save({"client_id": "b", "subject": "one"})
    assert session.memory() == {}
    session.save({"client_id": "a", "subject": "one"})
    assert session.memory()["context"] == "private"


def test_only_official_stream_endpoint(tmp_path):
    session = ChatGPTSession(tmp_path)
    session.save({"client_id": "a", "subject": "one", "access_token": "test",
                  "expires_at": time.time() + 600, "scopes": [PERMISSION]})
    llm = ChatGPTPlanLLM("model", session=session)
    response = Mock(ok=True)
    response.__enter__ = Mock(return_value=response)
    response.__exit__ = Mock(return_value=False)
    response.iter_lines.return_value = events({"type": "response.output_text.delta", "delta": "OK"},
                                             {"type": "response.completed"})
    with patch("altair.core.chatgpt_plan.require_external_services_allowed"), patch(
        "altair.core.chatgpt_plan.requests.post", return_value=response
    ) as post:
        assert llm._chat(model="model", messages=[{"role": "system", "content": "rules"},
                                                 {"role": "user", "content": "test"}]) == "OK"
        assert post.call_args.args[0] == "https://api.openai.com/v1/responses"
        params = post.call_args.kwargs
        assert params["allow_redirects"] is False
        assert params["json"]["store"] is False
        assert params["json"]["stream"] is True
        assert params["json"]["instructions"] == "rules"
        assert "temperature" not in params["json"]
        assert params["headers"]["Authorization"] == "Bearer test"
