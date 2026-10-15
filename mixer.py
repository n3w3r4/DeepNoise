"""Suppression level as a dry/wet blend: out = (100 - level)/100 * dry + level/100 * wet.

Blending in the time domain, so the dry
signal is delayed by the plugin latency to stay aligned with the wet signal.
"""

import numpy as np


class DryWetMixer:
    def __init__(self, level=100.0, delay_samples=0):
        self.level = level
        self.delay = np.zeros(delay_samples, np.float32)

    @property
    def wet_gain(self):
        return min(max(self.level, 0.0), 100.0) / 100.0

    def mix_aligned(self, dry, wet):
        """Blend two already time-aligned signals."""
        a = self.wet_gain
        return (1 - a) * dry + a * wet

    def mix_block(self, dry, wet):
        """Blend one live block, delaying dry by the configured latency."""
        if len(self.delay):
            buf = np.concatenate([self.delay, dry])
            dry, self.delay = buf[: len(dry)], buf[len(dry) :]
        return self.mix_aligned(dry, wet)


class NoiseGate:
    """Downward gate: attenuates blocks quieter than threshold_db.

    Opens fast (attack ~10 ms) when the block level crosses threshold_db, stays open for
    `hold` seconds after the last loud block (so pauses between words don't make the
    residual noise pump in and out), then closes over the release time towards floor_db.
    The gain is ramped inside each block to avoid clicks. threshold_db=None disables it.
    Used both for the pause gate and, with a calibrated threshold, for distant voices.
    """

    def __init__(self, threshold_db=None, floor_db=-40.0, hold=0.25, release=0.150, block=480, rate=48_000):
        self.threshold_db = threshold_db
        self.floor = 10 ** (floor_db / 20)
        self.gain = 1.0
        block_s = block / rate
        self.hold_blocks = int(round(hold / block_s))
        self.hold_left = 0
        self.attack = 1 - np.exp(-block_s / 0.010)
        self.release = 1 - np.exp(-block_s / release)

    def process(self, x):
        if self.threshold_db is None:
            return x
        level_db = 10 * np.log10(np.mean(x**2) + 1e-12)
        if level_db >= self.threshold_db:
            self.hold_left = self.hold_blocks
            target = 1.0
        elif self.hold_left > 0:
            self.hold_left -= 1
            target = 1.0
        else:
            target = self.floor
        coeff = self.attack if target > self.gain else self.release
        new_gain = self.gain + coeff * (target - self.gain)
        ramp = np.linspace(self.gain, new_gain, len(x), dtype=np.float32)
        self.gain = new_gain
        return x * ramp


class HighPass:
    """4th-order Butterworth high-pass applied before denoising, for desk thumps, stand
    vibration and handling noise (energy below ~100 Hz that DeepFilterNet leaves in).
    Keeps filter state across blocks; cutoff_hz=None disables it."""

    def __init__(self, cutoff_hz=80.0, rate=48_000, order=4):
        self.rate, self.order = rate, order
        self.set_cutoff(cutoff_hz)

    def set_cutoff(self, cutoff_hz):
        from scipy.signal import butter, sosfilt_zi

        self.cutoff_hz = cutoff_hz
        if cutoff_hz is None:
            self.sos = None
            return
        self.sos = butter(self.order, cutoff_hz, btype="highpass", fs=self.rate, output="sos")
        self.zi = sosfilt_zi(self.sos) * 0.0

    def process(self, x):
        if self.sos is None:
            return x
        from scipy.signal import sosfilt

        y, self.zi = sosfilt(self.sos, x, zi=self.zi)
        return y.astype(np.float32)
