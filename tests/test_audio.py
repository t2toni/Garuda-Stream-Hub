import shutil
import sys
import unittest
from pathlib import Path

PROJECT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_DIR))

from src.audio.pipewire_manager import PipeWireManager
from src.audio.voice_isolator import VoiceIsolator

try:
    import numpy as np
    HAVE_NUMPY = True
except ImportError:
    HAVE_NUMPY = False
    np = None

HAVE_PACTL = shutil.which("pactl") is not None

class TestPipeWireManager(unittest.TestCase):
    def setUp(self):
        self.mgr = PipeWireManager()

    def test_get_default_sink(self):
        if not HAVE_PACTL:
            self.skipTest("pactl is not available in test environment")
        sink = self.mgr.get_default_sink()
        self.assertIsNotNone(sink)
        self.assertIsInstance(sink, str)

    def test_virtual_sink_lifecycle(self):
        if not HAVE_PACTL:
            self.skipTest("pactl is not available in test environment")
        test_sink = "TEST_BGMI_Audio_Sink"
        ok, mod_id, msg = self.mgr.create_virtual_sink(sink_name=test_sink)
        self.assertTrue(ok)
        self.assertTrue(self.mgr.sink_exists(test_sink))

        # Check teardown
        teardown_res = self.mgr.teardown()
        self.assertTrue(len(teardown_res) > 0)
        self.assertFalse(self.mgr.sink_exists(test_sink))

    def test_krisp_denoiser_lifecycle(self):
        if not HAVE_PACTL:
            self.skipTest("pactl is not available in test environment")
        ok, msg = self.mgr.start_krisp_denoiser(vad_threshold=50.0)
        self.assertTrue(ok)
        self.assertTrue(self.mgr.is_krisp_active())

        # Stop Krisp
        stop_ok = self.mgr.stop_krisp_denoiser()
        self.assertTrue(stop_ok)
        self.assertFalse(self.mgr.is_krisp_active())

    def test_voice_isolator_filter_chain(self):
        chain = VoiceIsolator.build_filter_chain(
            mic_volume=0.85,
            wind_cut_hz=125,
            air_cut_hz=11500,
            enable_krisp=True
        )
        self.assertIn("highpass=f=125:poles=2", chain)
        self.assertIn("lowpass=f=11500:poles=2", chain)
        self.assertIn("arnndn=", chain)
        self.assertIn("agate=", chain)
        self.assertIn("volume=0.85", chain)

    def test_voice_isolator_dsp(self):
        if not HAVE_NUMPY:
            self.skipTest("numpy is not installed in test environment")
        sr = 48000
        noise = np.random.normal(0, 0.05, sr)
        cleaned = VoiceIsolator.separate_noise_from_audio(noise, sample_rate=sr, wind_cut_hz=125)
        self.assertEqual(len(cleaned), sr)
        self.assertLess(np.std(cleaned), np.std(noise))

if __name__ == "__main__":
    unittest.main()
