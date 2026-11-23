import logging
import subprocess
from typing import Dict, List, Optional, Tuple

logger = logging.getLogger("AndroidOptimizer")

class DeviceOptimizer:
    def __init__(self, serial: str, adb_path: str = "adb"):
        self.serial = serial
        self.adb_path = adb_path
        self._saved_settings: Dict[str, str] = {}

    def _adb_shell(self, cmd_args: List[str], timeout: float = 10.0) -> Tuple[int, str]:
        try:
            full_cmd = [self.adb_path, "-s", self.serial, "shell"] + cmd_args
            proc = subprocess.run(full_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=timeout)
            return proc.returncode, proc.stdout.strip()
        except Exception as e:
            logger.error(f"ADB shell command failed {cmd_args}: {e}")
            return -1, str(e)

    def backup_setting(self, namespace: str, key: str) -> None:
        code, out = self._adb_shell(["settings", "get", namespace, key])
        if code == 0 and out != "null":
            self._saved_settings[f"{namespace}:{key}"] = out

    def apply_optimizations(self, target_packages: Optional[List[str]] = None) -> List[str]:
        """
        Executes performance injection:
        1. Keep screen alive while streaming (stay_on_while_plugged_in = 3).
        2. Toggles battery saver OFF (low_power = 0).
        3. Forces speed compiler optimization for games (com.pubg.imobile, com.dts.freefiremax).
        4. Toggles game mode performance.
        """
        results = []

        # 1. Screen Keep-Alive
        self.backup_setting("global", "stay_on_while_plugged_in")
        code, _ = self._adb_shell(["settings", "put", "global", "stay_on_while_plugged_in", "3"])
        if code == 0:
            results.append("Screen keep-awake engaged (stay_on = 3)")

        # 2. Battery Saver OFF
        self.backup_setting("global", "low_power")
        code, _ = self._adb_shell(["settings", "put", "global", "low_power", "0"])
        if code == 0:
            results.append("Android battery saver disabled (low_power = 0)")

        # 3. Game Driver / High Performance Mode
        code, _ = self._adb_shell(["settings", "put", "global", "game_driver_all_apps", "1"])
        if code == 0:
            results.append("Global Game Driver performance profile active")

        # 4. Target Packages Speed Compilation
        if target_packages:
            # Query installed packages
            code, out = self._adb_shell(["pm", "list", "packages"])
            installed = [line.replace("package:", "").strip() for line in out.splitlines() if line]

            for pkg in target_packages:
                if pkg in installed:
                    # Apply game mode performance
                    self._adb_shell(["cmd", "game", "mode", "performance", pkg])
                    # Execute speed compiler (AOT optimization)
                    logger.info(f"Triggering compiler speed optimization for {pkg}...")
                    c_code, c_out = self._adb_shell(["cmd", "package", "compile", "-m", "speed", pkg], timeout=25.0)
                    if c_code == 0:
                        results.append(f"AOT Speed Compiled: {pkg}")
                    else:
                        results.append(f"Package optimization skipped for {pkg}: {c_out}")

        return results

    def restore_settings(self) -> None:
        """
        Restores settings to their original state prior to stream initialization.
        """
        for composite_key, val in self._saved_settings.items():
            try:
                namespace, key = composite_key.split(":", 1)
                self._adb_shell(["settings", "put", namespace, key, val])
                logger.info(f"Restored setting {namespace} {key} = {val}")
            except Exception as e:
                logger.warning(f"Failed to restore setting {composite_key}: {e}")
        self._saved_settings.clear()
