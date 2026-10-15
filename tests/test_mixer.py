import unittest
import numpy as np
from mixer import DryWetMixer, NoiseGate, HighPass

class MixerTests(unittest.TestCase):
    def test_delay_continues_across_blocks(self):
        mixer = DryWetMixer(level=0, delay_samples=3)
        np.testing.assert_array_equal(mixer.mix_block(np.array([1, 2]), np.zeros(2)), [0, 0])
        np.testing.assert_array_equal(mixer.mix_block(np.array([3, 4]), np.zeros(2)), [0, 1])
        np.testing.assert_array_equal(mixer.mix_block(np.array([5, 6]), np.zeros(2)), [2, 3])

    def test_gate_holds_between_words_then_closes(self):
        gate = NoiseGate(threshold_db=-20, hold=0.02)
        gate.process(np.ones(480, dtype=np.float32))
        quiet = np.full(480, 0.001, dtype=np.float32)
        for _ in range(2):
            np.testing.assert_allclose(gate.process(quiet), quiet)
        self.assertLess(gate.process(quiet)[-1], quiet[-1])

    def test_highpass_rejects_dc_after_settling(self):
        highpass = HighPass()
        block = np.ones(480, dtype=np.float32)
        for _ in range(100):
            output = highpass.process(block)
        self.assertLess(float(np.max(np.abs(output))), 1e-5)
