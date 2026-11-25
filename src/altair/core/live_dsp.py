"""Conservative local speech gating and stationary-noise attenuation (NumPy only)."""
import numpy as np


class VoiceGate:
    def __init__(self, threshold=.00165):
        self.threshold = float(threshold)
        self.floor = .00025
        self.noise_power = None
        self.window = np.hanning(320).astype(np.float32)
        self.frames = 0

    def analyze(self, frame):
        x = np.asarray(frame, dtype=np.float32).reshape(-1)
        x = x - np.mean(x)
        level = float(np.sqrt(np.mean(x*x)))
        # Do not adapt upward during actual speech. Learn only low-level background.
        gate = max(self.threshold, min(.018, self.floor * 2.6))
        speech = level > gate
        if not speech:
            self.floor = .97*self.floor + .03*level
            power = np.abs(np.fft.rfft(x*self.window))**2
            self.noise_power = power if self.noise_power is None else .94*self.noise_power + .06*power
            self.frames += 1
        return level, speech

    def clean(self, samples):
        """Spectral attenuation using overlapping frames; never discard quiet speech."""
        x = np.asarray(samples, dtype=np.float32).reshape(-1)
        if self.noise_power is None or self.frames < 8 or len(x) < 320:
            return x.copy()
        # Keep an attenuation floor to avoid erasing consonants or quiet voices.
        pad = 320
        data = np.pad(x, (pad, pad))
        result = np.zeros(len(data), dtype=np.float32)
        weight = np.zeros(len(data), dtype=np.float32)
        for start in range(0, len(data)-319, 160):
            spectrum = np.fft.rfft(data[start:start+320]*self.window)
            power = np.abs(spectrum)**2
            gain = np.sqrt(np.clip(1.0 - 1.3*self.noise_power/(power+1e-10), .25, 1.0))
            result[start:start+320] += np.fft.irfft(spectrum*gain, n=320).astype(np.float32)*self.window
            weight[start:start+320] += self.window**2
        return (result[pad:pad+len(x)] / np.maximum(weight[pad:pad+len(x)], 1e-6)).astype(np.float32)


def pause_seconds(partial, configured=.8):
    """A modest grace period for unfinished Portuguese phrases."""
    import re
    base = max(.55, min(1.2, float(configured)))
    tail = str(partial or '').rstrip()
    words = re.findall(r'[^\W\d_]+', tail.lower())
    if tail.endswith((',', '...', ':')) or (words and words[-1] in {'e','que','porque','mas','pra','para','de','o','a','um','uma','então','tipo','como','se'}):
        return max(base, 1.2)
    return base
