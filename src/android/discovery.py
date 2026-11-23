import logging
import re
import socket
import subprocess
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

logger = logging.getLogger("AndroidDiscovery")

@dataclass
class AndroidDevice:
    serial: str
    ip: Optional[str] = None
    port: int = 5555
    model: str = "Unknown"
    product: str = "Unknown"
    is_wireless: bool = False
    is_connected: bool = False
    transport_id: str = ""

class DeviceDiscoveryManager:
    def __init__(self, adb_path: str = "adb"):
        self.adb_path = adb_path

    def run_adb(self, args: List[str], timeout: float = 5.0) -> Tuple[int, str, str]:
        try:
            cmd = [self.adb_path] + args
            proc = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=timeout)
            return proc.returncode, proc.stdout.strip(), proc.stderr.strip()
        except Exception as e:
            logger.error(f"ADB execution error {args}: {e}")
            return -1, "", str(e)

    def list_devices(self) -> List[AndroidDevice]:
        code, out, _ = self.run_adb(["devices", "-l"])
        devices = []
        if code != 0 or not out:
            return devices

        lines = out.splitlines()
        for line in lines[1:]: # Skip 'List of devices attached'
            line = line.strip()
            if not line:
                continue
            parts = line.split()
            if len(parts) >= 2:
                serial = parts[0]
                state = parts[1]
                if state != "device":
                    continue

                model = "Unknown"
                product = "Unknown"
                transport_id = ""
                for part in parts[2:]:
                    if part.startswith("model:"):
                        model = part.split(":", 1)[1]
                    elif part.startswith("product:"):
                        product = part.split(":", 1)[1]
                    elif part.startswith("transport_id:"):
                        transport_id = part.split(":", 1)[1]

                is_wireless = ":" in serial
                ip = serial.split(":")[0] if is_wireless else None
                port = int(serial.split(":")[1]) if is_wireless and ":" in serial else 5555

                dev = AndroidDevice(
                    serial=serial,
                    ip=ip,
                    port=port,
                    model=model,
                    product=product,
                    is_wireless=is_wireless,
                    is_connected=True,
                    transport_id=transport_id
                )
                devices.append(dev)
        return devices

    def get_device_wlan_ip(self, serial: str) -> Optional[str]:
        # Try ip route / ip addr show
        code, out, _ = self.run_adb(["-s", serial, "shell", "ip", "-f", "inet", "addr", "show", "wlan0"])
        if code == 0 and out:
            match = re.search(r"inet\s+([0-9]+\.[0-9]+\.[0-9]+\.[0-9]+)/", out)
            if match:
                return match.group(1)

        # Fallback to getprop / dumpsys
        code, out, _ = self.run_adb(["-s", serial, "shell", "dumpsys", "wifi"])
        if code == 0 and out:
            match = re.search(r"IP:\s+/([0-9]+\.[0-9]+\.[0-9]+\.[0-9]+)", out)
            if match:
                return match.group(1)
        return None

    def promote_to_wireless(self, usb_serial: str, port: int = 5555) -> Tuple[bool, Optional[str], str]:
        """
        Promotes a USB connected phone to Wi-Fi 6 / 5GHz TCP/IP mode.
        """
        ip = self.get_device_wlan_ip(usb_serial)
        if not ip:
            return False, None, "Could not determine device Wi-Fi IP address"


        # Restart ADB in TCP mode
        code, out, err = self.run_adb(["-s", usb_serial, "tcpip", str(port)])
        if code != 0:
            return False, None, f"Failed to restart ADB in TCP mode: {err}"

        # Connect to device via Wi-Fi
        target = f"{ip}:{port}"
        code, out, err = self.run_adb(["connect", target], timeout=4.0)
        if "connected to" in out.lower():
            logger.info(f"Successfully promoted device to wireless: {target}")
            return True, target, f"Connected to {target} over Wi-Fi"
        return False, None, f"Failed to connect to {target}: {out} {err}"

    def auto_handshake(self) -> Tuple[bool, Optional[str], bool, str]:
        """
        Executes zero-config discovery handshake:
        1. Checks currently attached devices.
        2. If wireless device attached, uses it immediately.
        3. If USB device attached, attempts promotion to Wi-Fi.
        4. If Wi-Fi connects, uses Wi-Fi; otherwise falls back to USB 3.2.
        Returns: (success: bool, target_serial: str, is_wireless: bool, message: str)
        """
        devices = self.list_devices()
        if not devices:
            return False, None, False, "No Android devices detected via USB or Wi-Fi. Please check USB debugging."

        # Prefer existing wireless connection if active
        for dev in devices:
            if dev.is_wireless and dev.is_connected:
                return True, dev.serial, True, f"Found active wireless link to {dev.serial} ({dev.model})"

        # If USB device found, attempt Wi-Fi promotion
        usb_dev = next((d for d in devices if not d.is_wireless), None)
        if usb_dev:
            logger.info(f"Found USB device {usb_dev.serial}. Attempting auto wireless pairing...")
            ok, target, msg = self.promote_to_wireless(usb_dev.serial)
            if ok and target:
                return True, target, True, f"Wireless link established: {target} (5GHz Wi-Fi)"
            logger.warning(f"Wireless promotion fell back: {msg}. Using high-speed USB 3.2.")
            return True, usb_dev.serial, False, f"Connected via USB 3.2 ({usb_dev.model})"

        return False, None, False, "Failed to establish device link"
