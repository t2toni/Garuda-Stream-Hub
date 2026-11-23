import subprocess
import sys
import tempfile
import time
import unittest
from pathlib import Path

PROJECT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_DIR))

from src.recorder.recording_manager import RecordingManager, RecordingStats
from src.audio.pipewire_manager import PipeWireManager

class TestRecordingManager(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.recorder = RecordingManager(output_dir=self.temp_dir)
        self.audio = PipeWireManager()

    def test_recorder_initial_state(self):
        self.assertFalse(self.recorder.is_recording())
        self.assertEqual(self.recorder.stats.duration_seconds, 0.0)

    def test_short_recording_session(self):
        # 1. Create test virtual sink
        test_sink = "REC_TEST_SINK"
        ok, _, _ = self.audio.create_virtual_sink(sink_name=test_sink)
        self.assertTrue(ok)

        # 2. Start recording
        start_ok, start_msg, rec_path = self.recorder.start_recording(
            game_sink=test_sink,
            mic_source="default",
            include_mic=True,
            multi_track=True,
            filename_prefix="TestRec"
        )
        self.assertTrue(start_ok)
        self.assertTrue(self.recorder.is_recording())
        self.assertIsNotNone(rec_path)

        # Let it record for 1.5 seconds
        time.sleep(1.5)

        # 3. Stop recording
        stop_ok, stop_msg, saved_path = self.recorder.stop_recording()
        self.assertTrue(stop_ok)
        self.assertFalse(self.recorder.is_recording())
        self.assertTrue(Path(saved_path).exists())
        self.assertGreater(Path(saved_path).stat().st_size, 0)

        # 4. Probe the recorded file with ffprobe to verify streams!
        probe_cmd = [
            "ffprobe", "-v", "error",
            "-show_entries", "stream=index,codec_type,codec_name:stream_tags=title",
            "-of", "csv=p=0",
            saved_path
        ]
        probe_res = subprocess.run(probe_cmd, stdout=subprocess.PIPE, text=True)
        probe_out = probe_res.stdout

        # Verify video and audio streams exist
        self.assertIn("video", probe_out)
        self.assertIn("audio", probe_out)

        # Clean audio sink
        self.audio.teardown()

if __name__ == "__main__":
    unittest.main()
