"""Exercise cancellation and streaming independently of the network/account."""
import threading
import time
import pytest
from altair.core.chatgpt_plan import ChatGPTPlanLLM, PlanError


def test_live_network_cancel_does_not_wait_for_socket(monkeypatch):
    llm = ChatGPTPlanLLM("fake")
    release, entered, cancelled = threading.Event(), threading.Event(), threading.Event()
    def block(payload, emit, cancel):
        entered.set()
        release.wait(3)
        emit("old")
        return "old"
    monkeypatch.setattr(llm, "_request_response", block)
    def cancel():
        if entered.wait(1):
            cancelled.set()
    thread = threading.Thread(target=cancel)
    thread.start()
    seen = []
    start = time.monotonic()
    try:
        with pytest.raises(PlanError) as exc:
            llm._live_request({}, seen.append, cancelled.is_set)
        assert exc.value.code == "live_cancelled"
        assert time.monotonic() - start < .5
        assert not seen
    finally:
        release.set()
        thread.join()


def test_live_network_delivers_ordered_deltas(monkeypatch):
    llm = ChatGPTPlanLLM("fake")
    seen = []
    def source(payload, emit, cancel):
        emit("Olá. ")
        emit("Tudo bem?")
        return "Olá. Tudo bem?"
    monkeypatch.setattr(llm, "_request_response", source)
    assert llm._live_request({}, seen.append, lambda: False) == "Olá. Tudo bem?"
    assert seen == ["Olá. ", "Tudo bem?"]


def test_live_network_error_propagates(monkeypatch):
    llm = ChatGPTPlanLLM("fake")
    def fail(*args):
        raise RuntimeError("network")
    monkeypatch.setattr(llm, "_request_response", fail)
    with pytest.raises(RuntimeError, match="network"):
        llm._live_request({}, lambda x: None, lambda: False)
