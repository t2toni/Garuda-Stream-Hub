import json
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

PROJECT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_DIR))

from src.obs.scene_injector import OBSSceneInjector

class TestOBSSceneInjector(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.obs_dir = Path(self.temp_dir) / "obs-studio"
        self.scenes_dir = self.obs_dir / "basic" / "scenes"
        self.scenes_dir.mkdir(parents=True, exist_ok=True)

        # Seed sample scene
        sample_scene = {
            "name": "Untitled",
            "current_scene": "Scene 1",
            "sources": [
                {
                    "name": "Scene 1",
                    "id": "scene",
                    "settings": {
                        "id_counter": 0,
                        "items": []
                    }
                }
            ]
        }
        with open(self.scenes_dir / "Untitled.json", "w", encoding="utf-8") as f:
            json.dump(sample_scene, f, indent=2)

        self.injector = OBSSceneInjector(config_dir=self.obs_dir)

    def tearDown(self):
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_inject_sources(self):
        ok, msg = self.injector.inject_pipeline_sources(sink_name="TEST_SINK", v4l2_device="/dev/video10")
        self.assertTrue(ok)

        # Verify modified JSON
        with open(self.scenes_dir / "Untitled.json", "r", encoding="utf-8") as f:
            data = json.load(f)

        sources = data["sources"]
        source_names = [s["name"] for s in sources]
        self.assertIn("BGMI Audio Stream (Isolated)", source_names)
        self.assertIn("Android Mobile Video", source_names)

        # Check backup created
        backups = list(self.scenes_dir.glob("*.bak.*"))
        self.assertGreater(len(backups), 0)

if __name__ == "__main__":
    unittest.main()
