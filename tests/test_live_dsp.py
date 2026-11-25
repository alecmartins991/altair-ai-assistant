import numpy as np
from altair.core.live_dsp import VoiceGate, pause_seconds

def test_dc_not_speech():
    gate=VoiceGate()
    for _ in range(50):
        level,speech=gate.analyze(np.full(320,.02,dtype=np.float32))
        assert not speech and level<1e-7

def test_quiet_speech_detected():
    gate=VoiceGate(); t=np.arange(320)/16000
    for _ in range(20): gate.analyze(.0002*np.sin(2*np.pi*60*t))
    assert gate.analyze(.004*np.sin(2*np.pi*220*t))[1]

def test_noise_filter_attenuates_stationary_noise():
    gate=VoiceGate(); t=np.arange(320)/16000
    noise=.001*np.sin(2*np.pi*100*t)
    for _ in range(20): gate.analyze(noise)
    x=np.tile(noise,50).astype(np.float32); y=gate.clean(x)
    assert len(y)==len(x) and np.isfinite(y).all()
    assert np.sqrt(np.mean(y*y))<.85*np.sqrt(np.mean(x*x))

def test_clean_speech_no_profile_is_unchanged():
    gate=VoiceGate(); x=np.random.default_rng(0).normal(0,.02,1600).astype(np.float32)
    np.testing.assert_array_equal(gate.clean(x),x)

def test_pause_for_incomplete_phrase():
    assert pause_seconds('Eu queria que',.7)>pause_seconds('Tudo certo.',.7)
    assert pause_seconds('então,',.7)>=1.2
