import logging
import re
import subprocess
from dataclasses import dataclass
from typing import Optional, Tuple

logger = logging.getLogger("AndroidTelemetry")

@dataclass
class DeviceMetrics:
    temperature_c: float = 0.0
    battery_level: int = 100
    is_charging: bool = False
    wifi_ssid: str = "N/A"
    wifi_rssi_dbm: int = -99
    wifi_link_speed_mbps: int = 0
    wifi_frequency_mhz: int = 0
    wifi_standard: str = "N/A"
    is_wireless: bool = False

class DeviceTelemetryReader:
    def __init__(self, serial: str, adb_path: str = "adb"):
        self.serial = serial
        self.adb_path = adb_path
        self._cached_metrics = DeviceMetrics()

    def _adb_shell(self, cmd_args: list, timeout: float = 3.0) -> Tuple[int, str]:
        try:
            full_cmd = [self.adb_path, "-s", self.serial, "shell"] + cmd_args
            proc = subprocess.run(full_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=timeout)
            return proc.returncode, proc.stdout.strip()
        except Exception as e:
            return -1, str(e)

    def fetch_metrics(self) -> DeviceMetrics:
        metrics = DeviceMetrics()
        metrics.is_wireless = ":" in self.serial

        # 1. Fetch Battery & Temperature
        code, out = self._adb_shell(["dumpsys", "battery"])
        if code == 0 and out:
            # Temperature is reported in tenths of a degree Celsius (e.g., 330 = 33.0 C)
            temp_match = re.search(r"temperature:\s*([0-9]+)", out)
            if temp_match:
                metrics.temperature_c = round(float(temp_match.group(1)) / 10.0, 1)

            level_match = re.search(r"level:\s*([0-9]+)", out)
            if level_match:
                metrics.battery_level = int(level_match.group(1))

            status_match = re.search(r"status:\s*([0-9]+)", out)
            if status_match:
                # 2 = CHARGING, 5 = FULL
                metrics.is_charging = status_match.group(1) in ("2", "5")
        else:
            # Fallback to sysfs thermal zone
            code, out = self._adb_shell(["cat", "/sys/class/thermal/thermal_zone0/temp"])
            if code == 0 and out.isdigit():
                metrics.temperature_c = round(float(out) / 1000.0, 1)

        # 2. Fetch Wi-Fi Details
        code, out = self._adb_shell(["dumpsys", "wifi"])
        if code == 0 and out:
            ssid_match = re.search(r'mWifiInfo\s+SSID:\s*"([^"]+)"', out)
            if ssid_match:
                metrics.wifi_ssid = ssid_match.group(1)

            rssi_match = re.search(r"RSSI:\s*(-?[0-9]+)", out)
            if rssi_match:
                metrics.wifi_rssi_dbm = int(rssi_match.group(1))

            speed_match = re.search(r"Link speed:\s*([0-9]+)Mbps", out)
            if speed_match:
                metrics.wifi_link_speed_mbps = int(speed_match.group(1))

            freq_match = re.search(r"Frequency:\s*([0-9]+)MHz", out)
            if freq_match:
                metrics.wifi_frequency_mhz = int(freq_match.group(1))

            std_match = re.search(r"Wi-Fi standard:\s*([^\s,]+)", out)
            if std_match:
                metrics.wifi_standard = std_match.group(1)

        self._cached_metrics = metrics
        return metrics
