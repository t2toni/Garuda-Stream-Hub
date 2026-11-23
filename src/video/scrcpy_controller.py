import logging
import os
import re
import subprocess
import threading
from typing import Dict, List, Optional, Tuple

logger = logging.getLogger("ScrcpyController")

class ScrcpyController:
    """
    Spawns and manages low-latency scrcpy streaming engine:
    - H.265 / HEVC Qualcomm Hardware Encoder (c2.qti.hevc.encoder)
    - Opus 48kHz audio forwarding routed strictly to BGMI_Audio_Sink
    - Real-time FPS telemetry capture via --print-fps
    - Tight buffer control (15ms video buffer, 20ms audio buffer)
    """
    def __init__(self, scrcpy_path: str = "scrcpy"):
        self.scrcpy_path = scrcpy_path
        self.process: Optional[subprocess.Popen] = None
        self._fps_thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()
        self.current_fps: float = 0.0
        self.last_log_line: str = ""

    def build_command(
        self,
        serial: str,
        video_codec: str = "h265",
        video_encoder: str = "c2.qti.hevc.encoder",
        bitrate_mbps: int = 16,
        max_fps: int = 60,
        video_buffer_ms: int = 15,
        audio_codec: str = "opus",
        audio_source: str = "playback",
        audio_buffer_ms: int = 20,
        v4l2_sink: Optional[str] = None,
        max_size: int = 0,
        extra_args: Optional[List[str]] = None
    ) -> List[str]:
        cmd = [
            self.scrcpy_path,
            "-s", serial,
            f"--video-codec={video_codec}",
            f"--video-bit-rate={bitrate_mbps}M",
            f"--max-fps={max_fps}",
            f"--video-buffer={video_buffer_ms}",
            f"--audio-codec={audio_codec}",
            f"--audio-source={audio_source}",
            f"--audio-buffer={audio_buffer_ms}",
            "--print-fps",
            '--window-title=Garuda Stream Mirror'
        ]

        if video_encoder and video_encoder != "auto":
            cmd.append(f"--video-encoder={video_encoder}")

        if max_size > 0:
            cmd.append(f"--max-size={max_size}")

        if v4l2_sink and os.path.exists(v4l2_sink):
            cmd.append(f"--v4l2-sink={v4l2_sink}")

        if extra_args:
            cmd.extend(extra_args)

        return cmd

    def _monitor_output(self, proc: subprocess.Popen) -> None:
        # scrcpy prints FPS like: "INFO: 60.1 fps" or "60.0 fps"
        fps_pattern = re.compile(r"([0-9]+\.[0-9]+)\s+fps", re.IGNORECASE)
        try:
            for line in iter(proc.stdout.readline, ''):
                if self._stop_event.is_set():
                    break
                line_str = line.strip()
                if line_str:
                    self.last_log_line = line_str
                    match = fps_pattern.search(line_str)
                    if match:
                        try:
                            self.current_fps = float(match.group(1))
                        except ValueError:
                            pass
        except Exception as e:
            logger.debug(f"Output monitor ended: {e}")

    def start(
        self,
        serial: str,
        pulse_sink: str = "BGMI_Audio_Sink",
        video_codec: str = "h265",
        video_encoder: str = "c2.qti.hevc.encoder",
        bitrate_mbps: int = 16,
        max_fps: int = 60,
        video_buffer_ms: int = 15,
        audio_codec: str = "opus",
        audio_source: str = "playback",
        audio_buffer_ms: int = 20,
        v4l2_sink: Optional[str] = None,
        max_size: int = 0
    ) -> Tuple[bool, str]:
        if self.is_alive():
            return True, "Scrcpy pipeline is already running"

        cmd = self.build_command(
            serial=serial,
            video_codec=video_codec,
            video_encoder=video_encoder,
            bitrate_mbps=bitrate_mbps,
            max_fps=max_fps,
            video_buffer_ms=video_buffer_ms,
            audio_codec=audio_codec,
            audio_source=audio_source,
            audio_buffer_ms=audio_buffer_ms,
            v4l2_sink=v4l2_sink,
            max_size=max_size
        )

        env = os.environ.copy()
        if pulse_sink:
            # Route all SDL / PipeWire audio from scrcpy directly into virtual sink!
            env["PULSE_SINK"] = pulse_sink
            env["PIPEWIRE_NODE"] = pulse_sink

        try:
            logger.info(f"Launching scrcpy command: {' '.join(cmd)}")
            self._stop_event.clear()
            self.process = subprocess.Popen(
                cmd,
                env=env,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1
            )

            self._fps_thread = threading.Thread(target=self._monitor_output, args=(self.process,), daemon=True)
            self._fps_thread.start()

            return True, "Scrcpy stream engine launched successfully"
        except Exception as e:
            logger.error(f"Failed to launch scrcpy: {e}")
            return False, str(e)

    def is_alive(self) -> bool:
        return self.process is not None and self.process.poll() is None

    def get_pid(self) -> Optional[int]:
        if self.process and self.is_alive():
            return self.process.pid
        return None

    def stop(self) -> None:
        self._stop_event.set()
        if self.process and self.process.poll() is None:
            try:
                self.process.terminate()
                self.process.wait(timeout=2.0)
            except Exception:
                try:
                    self.process.kill()
                except Exception:
                    pass
        self.process = None
        self.current_fps = 0.0
