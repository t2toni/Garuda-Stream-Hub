import sys
import unittest
from pathlib import Path

PROJECT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_DIR))

from src.android.discovery import DeviceDiscoveryManager, AndroidDevice
from src.android.telemetry import DeviceTelemetryReader, DeviceMetrics

class TestAndroidComponents(unittest.TestCase):
    def test_device_discovery(self):
        mgr = DeviceDiscoveryManager()
        devices = mgr.list_devices()
        self.assertIsInstance(devices, list)
        for dev in devices:
            self.assertIsInstance(dev, AndroidDevice)
            self.assertTrue(dev.is_connected)

    def test_auto_handshake(self):
        mgr = DeviceDiscoveryManager()
        devices = mgr.list_devices()
        if not devices:
            self.skipTest("No Android devices connected for live handshake test")

        ok, target, is_wireless, msg = mgr.auto_handshake()
        self.assertTrue(ok)
        self.assertIsNotNone(target)
        self.assertIsInstance(msg, str)

if __name__ == "__main__":
    unittest.main()
