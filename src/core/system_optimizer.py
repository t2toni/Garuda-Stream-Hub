import logging
import os
import shutil
import subprocess
from typing import Optional, Tuple

logger = logging.getLogger("SystemOptimizer")

# Attempt native C++ extension import
try:
    import sys
    sys.path.append(os.path.join(os.path.dirname(__file__), "..", "native"))
    import stream_native
    HAVE_NATIVE = True
except Exception as e:
    logger.warning(f"Native C++ module not available in system_optimizer: {e}")
    HAVE_NATIVE = False

class SystemOptimizer:
    """
    Automates Linux OS optimizations:
    - Process priority overrides (renice) for rendering & OBS
    - Kernel v4l2loopback module verification & loading
    - Scheduler status inspection
    """
    @staticmethod
    def elevate_priority(pid: int, desired_nice: int = -10) -> Tuple[bool, int, str]:
        """
        Attempts to elevate process priority using native C++ API or POSIX setpriority.
        Returns: (success: bool, effective_nice: int, message: str)
        """
        if HAVE_NATIVE:
            try:
                ok, eff_nice, err = stream_native.elevate_process_priority(pid, desired_nice)
                if ok:
                    return True, eff_nice, f"Elevated PID {pid} to nice {eff_nice}"
                else:
                    return False, eff_nice, f"Priority adjustment restricted ({err}), effective nice: {eff_nice}"
            except Exception as e:
                logger.debug(f"Native elevate failed: {e}")

        # Fallback to python os.setpriority on POSIX systems
        if hasattr(os, "setpriority") and hasattr(os, "PRIO_PROCESS"):
            try:
                os.setpriority(os.PRIO_PROCESS, pid, desired_nice)
                eff_nice = os.getpriority(os.PRIO_PROCESS, pid)
                return True, eff_nice, f"Elevated PID {pid} to nice {eff_nice}"
            except PermissionError:
                try:
                    # Fallback to nice 0 (highest unprivileged standard priority)
                    os.setpriority(os.PRIO_PROCESS, pid, 0)
                    eff_nice = os.getpriority(os.PRIO_PROCESS, pid)
                    return False, eff_nice, f"Root required for nice {desired_nice}; set to unprivileged maximum {eff_nice}"
                except Exception as e:
                    return False, 0, str(e)
            except Exception as e:
                return False, 0, str(e)

        return False, 0, "Priority elevation not supported on this platform"

    @staticmethod
    def is_v4l2loopback_loaded() -> bool:
        try:
            with open("/proc/modules", "r") as f:
                for line in f:
                    if line.startswith("v4l2loopback"):
                        return True
        except Exception:
            pass
        return False

    @staticmethod
    def load_v4l2loopback(video_nr: int = 10, label: str = "GarudaStreamCam") -> Tuple[bool, str]:
        if SystemOptimizer.is_v4l2loopback_loaded():
            return True, "v4l2loopback is already loaded"

        if not shutil.which("pkexec"):
            return False, "pkexec is not available to load kernel module"

        cmd = [
            "pkexec", "modprobe", "v4l2loopback",
            "devices=1",
            f"video_nr={video_nr}",
            f'card_label="{label}"',
            "exclusive_caps=1"
        ]
        try:
            res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=15.0)
            if res.returncode == 0:
                return True, f"Loaded v4l2loopback as /dev/video{video_nr}"
            return False, f"Failed to load module: {res.stderr.strip()}"
        except Exception as e:
            return False, str(e)
