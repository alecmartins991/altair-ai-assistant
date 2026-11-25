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

def test_stereo_only_device(monkeypatch):
    import sys, types, threading, time
    from altair.core import live_capture as capture
    clock=[100.]; opened=[]; events=[]
    monkeypatch.setattr(capture,'time',types.SimpleNamespace(monotonic=lambda:clock[0]))
    monkeypatch.setitem(sys.modules,'altair.core.local_voice',types.SimpleNamespace(warm_live_model=lambda:'fake', live_transcribe=lambda audio,final=False:'Teste estéreo'))
    def check(channels,samplerate,**kwargs):
        if (channels,samplerate)!=(2,48000):raise ValueError('stereo only')
    class Stream:
        def __init__(self,callback,blocksize,samplerate,channels,**kwargs):
            opened.append((channels,samplerate));self.cb=callback;self.n=blocksize;self.stop=threading.Event()
        def __enter__(self):
            def feed():
                for level in [.0001]*15+[.03]*90+[.0001]*80:
                    if self.stop.is_set():break
                    clock[0]+=.02
                    wave=(level*np.sin(2*np.pi*200*np.arange(self.n)/48000)).astype(np.float32)
                    self.cb(np.stack([wave,wave],axis=1),self.n,None,None)
                    time.sleep(.001)
            self.thread=threading.Thread(target=feed);self.thread.start();return self
        def __exit__(self,*args):self.stop.set();self.thread.join()
    monkeypatch.setitem(sys.modules,'sounddevice',types.SimpleNamespace(check_input_settings=check,query_devices=lambda **kwargs:{'default_samplerate':48000,'max_input_channels':2,'name':'Stereo test'},InputStream=Stream))
    assert capture.live_capture(lambda k,v:events.append((k,v)))=='Teste estéreo'
    assert opened==[(2,48000)] and ('device','Stereo test') in events
