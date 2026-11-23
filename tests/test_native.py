import os
import sys
import unittest
from pathlib import Path

# Add src/native to path
SRC_DIR = Path(__file__).resolve().parent.parent / "src"
NATIVE_DIR = SRC_DIR / "native"
sys.path.insert(0, str(NATIVE_DIR))

try:
    import stream_native
    HAVE_NATIVE = True
except Exception as e:
    HAVE_NATIVE = False

class TestNativeModule(unittest.TestCase):
    def setUp(self):
        if not HAVE_NATIVE:
            self.skipTest("Native C++ module not compiled")

    def test_jitter_calculator(self):
        calc = stream_native.JitterCalculator(window_size=10)
        self.assertEqual(calc.get_jitter_ms(), 0.0)
        self.assertEqual(calc.get_recommended_buffer_ms(), 15)

        # Feed RTT samples
        calc.add_sample(10.0)
        calc.add_sample(12.0)
        calc.add_sample(18.0)
        calc.add_sample(9.0)

        jitter = calc.get_jitter_ms()
        self.assertGreater(jitter, 0.0)
        avg = calc.get_avg_rtt_ms()
        self.assertGreater(avg, 5.0)

        buf = calc.get_recommended_buffer_ms()
        self.assertGreaterEqual(buf, 15)
        self.assertLessEqual(buf, 100)

        calc.reset()
        self.assertEqual(calc.get_jitter_ms(), 0.0)

    def test_process_stats(self):
        pid = os.getpid()
        stats = stream_native.get_process_stats(pid)
        self.assertTrue(stats.is_running)
        self.assertEqual(stats.pid, pid)
        self.assertIn("python", stats.name.lower())
        self.assertGreater(stats.num_threads, 0)
        self.assertGreater(stats.vm_rss_kb, 0)

    def test_ping_host_unreachable(self):
        # Ping non-existent local port
        rtt = stream_native.ping_host("127.0.0.1", 64999, 100)
        self.assertEqual(rtt, -1.0)

if __name__ == "__main__":
    unittest.main()
