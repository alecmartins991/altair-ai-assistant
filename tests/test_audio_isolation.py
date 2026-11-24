"""Regression tests with no real microphone, network, account, or sound device."""
from unittest.mock import Mock, patch
import subprocess
import pytest

from altair.core import audio_isolation as iso


def test_worker_native_failure_does_not_exit_parent():
    proc = Mock(returncode=3221225477)
    proc.communicate.return_value = (b"", b"")
    proc.poll.return_value = 3221225477
    with patch.object(iso.subprocess, "Popen", return_value=proc):
        with pytest.raises(iso.AudioFailure, match="3221225477"):
            iso.run_worker("capture", {})
    assert not proc.kill.called


def test_worker_timeout_and_cancel():
    proc = Mock(returncode=None)
    proc.communicate.side_effect = [subprocess.TimeoutExpired("child", .2), (b"", b"")]
    proc.poll.return_value = None
    cancel = Mock(side_effect=[False, False, True])
    with patch.object(iso.subprocess, "Popen", return_value=proc):
        assert iso.run_worker("capture", {}, cancel=cancel) is None
    proc.kill.assert_called_once()


def test_voice_lock_released_on_failure():
    voice = iso.IsolatedVoice({"provider": "windows_local"})
    with patch.object(voice._local, "speak", side_effect=RuntimeError("device")):
        with pytest.raises(iso.AudioFailure):
            voice.speak("test")
    assert not iso.SPEECH_PENDING.is_set()
    assert iso.DEVICE_LOCK.acquire(blocking=False)
    iso.DEVICE_LOCK.release()


def test_local_voice_keeps_capture_paused_during_playback():
    voice = iso.IsolatedVoice({"provider": "windows_local"})
    def fake_speak(text):
        assert iso.SPEECH_PENDING.is_set()
        assert iso.DEVICE_LOCK.locked()
    with patch.object(voice._local, "speak", side_effect=fake_speak):
        voice.speak("test")
    assert not iso.SPEECH_PENDING.is_set()
