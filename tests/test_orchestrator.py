import sys
import unittest
from pathlib import Path

PROJECT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_DIR))

from src.core.config import StreamConfig, PipelineState
from src.core.orchestrator import PipelineOrchestrator

class TestPipelineOrchestrator(unittest.TestCase):
    def setUp(self):
        self.config = StreamConfig()
        self.orchestrator = PipelineOrchestrator(self.config)

    def test_validate_dependencies(self):
        ok, missing = self.orchestrator.validate_dependencies()
        self.assertTrue(ok)
        self.assertEqual(missing, [])

    def test_initial_state(self):
        self.assertEqual(self.orchestrator.state, PipelineState.IDLE)
        self.assertEqual(len(self.orchestrator.step_statuses), 5)

if __name__ == "__main__":
    unittest.main()
