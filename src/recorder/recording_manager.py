import datetime
import logging
import os
import re
import signal
import subprocess
import sys
import threading
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from src.audio.voice_isolator import VoiceIsolator

logger = logging.getLogger("RecordingManager")

@dataclass
class RecordingStats:
    is_recording: bool = False
    duration_seconds: float = 0.0
    file_size_bytes: int = 0
    file_size_formatted: str = "0.0 MB"
    output_path: str = ""
    current_fps: float = 0.0
    written_frames: int = 0

class RecordingManager:
    """
    Studio-Grade Video and Multi-Track Audio Recording Engine:
    - Records Game Screen Video (Direct Window / Display)
    - Records Game Audio + Friends Voice Call (from PipeWire BGMI_Audio_Sink.monitor)
    - Records Player's Microphone (from default / ALSA internal mic)
    - Automatically builds synchronized Multi-Track MP4:
        • Stream 1: Master Mix (Game + Friends + My Mic) [Default Stereo]
        • Stream 2: Game & Friends Audio Only
        • Stream 3: My Microphone Only
    """
    def __init__(self, output_dir: Optional[str] = None):
        self.output_dir = Path(output_dir or (Path.home() / "Videos" / "Recordings")).expanduser()
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.process: Optional[subprocess.Popen] = None
        self.current_recording_path: Optional[Path] = None
        self.stats = RecordingStats()
        self._monitor_thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()
        self._start_time: float = 0.0

    def find_window_geometry(self, window_title: str = "Garuda Stream Mirror") -> Optional[Tuple[int, int, int, int]]:
        """
        Locates the X11/Xwayland geometry (X, Y, Width, Height) of the game mirror window.
        """
        try:
            res = subprocess.run(
                ["xwininfo", "-name", window_title],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                timeout=2.0
            )
            if res.returncode == 0:
                out = res.stdout
                x_match = re.search(r"Absolute upper-left X:\s+(-?[0-9]+)", out)
                y_match = re.search(r"Absolute upper-left Y:\s+(-?[0-9]+)", out)
                w_match = re.search(r"Width:\s+([0-9]+)", out)
                h_match = re.search(r"Height:\s+([0-9]+)", out)

                if x_match and y_match and w_match and h_match:
                    x = max(0, int(x_match.group(1)))
                    y = max(0, int(y_match.group(1)))
                    w = int(w_match.group(1))
                    h = int(h_match.group(1))
                    # Ensure width and height are even numbers for x264
                    w = w - (w % 2)
                    h = h - (h % 2)
                    return x, y, w, h
        except Exception as e:
            logger.debug(f"xwininfo lookup error: {e}")
        return None

    def start_recording(
        self,
        game_sink: str = "BGMI_Audio_Sink",
        mic_source: str = "default",
        game_volume: float = 1.0,
        mic_volume: float = 1.0,
        include_mic: bool = True,
        multi_track: bool = True,
        filename_prefix: str = "GameRecording",
        krisp_denoiser: bool = True,
        rnnoise_model: str = "bd.rnnn",
        wind_cut_hz: int = 125,
        air_cut_hz: int = 11500
    ) -> Tuple[bool, str, Optional[str]]:
        if self.is_recording():
            return True, "Recording is already active", str(self.current_recording_path)

        now_str = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        output_filename = f"{filename_prefix}_{now_str}.mp4"
        self.current_recording_path = self.output_dir / output_filename

        # 1. Determine Video Capture Source (Cross-Platform)
        is_windows = sys.platform == "win32"
        cmd = ["ffmpeg", "-y"]

        if is_windows:
            logger.info("Windows detected: using gdigrab desktop capture")
            cmd.extend([
                "-f", "gdigrab",
                "-draw_mouse", "0",
                "-framerate", "60",
                "-i", "desktop"
            ])
        else:
            display = os.environ.get("DISPLAY", ":0.0")
            geom = self.find_window_geometry("Garuda Stream Mirror")
            if geom:
                x, y, w, h = geom
                logger.info(f"Locking recording to window geometry: {w}x{h}+{x}+{y}")
                cmd.extend([
                    "-f", "x11grab",
                    "-draw_mouse", "0",
                    "-video_size", f"{w}x{h}",
                    "-framerate", "60",
                    "-i", f"{display}+{x},{y}"
                ])
            else:
                logger.info(f"Mirror window not found; recording full display {display}")
                cmd.extend([
                    "-f", "x11grab",
                    "-draw_mouse", "0",
                    "-framerate", "60",
                    "-i", display
                ])

        # 2. Audio Input 1: Game & Friends Sound (PipeWire / Pulse)
        game_pulse_input = f"{game_sink}.monitor"
        cmd.extend([
            "-f", "pulse",
            "-i", game_pulse_input
        ])

        # 3. Audio Input 2: Player Microphone (if enabled)
        if include_mic:
            mic_input = "default" if mic_source == "default" else mic_source
            cmd.extend([
                "-f", "pulse",
                "-i", mic_input
            ])

            # Multi-Stage Voice & Air Noise Separation DSP
            mic_chain = VoiceIsolator.build_filter_chain(
                mic_volume=mic_volume,
                wind_cut_hz=wind_cut_hz,
                air_cut_hz=air_cut_hz,
                enable_krisp=krisp_denoiser,
                rnnoise_model=rnnoise_model,
                gate_threshold=0.007
            )

            # Filter Complex: Noise Suppression, Noise Gate & Multi-Track Split
            cmd.extend([
                "-filter_complex",
                f"[1:a]highpass=f=40,volume={game_volume:.2f},asplit=2[a_game_mix][a_game_out];"
                f"[2:a]{mic_chain},asplit=2[a_mic_mix][a_mic_out];"
                f"[a_game_mix][a_mic_mix]amix=inputs=2:duration=first:dropout_transition=2[a_master]"
            ])

            if multi_track:
                # Video + Denoised Master Mix + Isolated Game + Denoised Mic
                cmd.extend([
                    "-map", "0:v",
                    "-map", "[a_master]",
                    "-map", "[a_game_out]",
                    "-map", "[a_mic_out]",
                    "-metadata:s:a:0", "title=Master Mix (Game + Friends + My Mic)",
                    "-metadata:s:a:1", "title=Game & Friends Audio",
                    "-metadata:s:a:2", "title=My Microphone (AI Voice Isolated & Air Cleaned)",
                    "-disposition:a:0", "default"
                ])
            else:
                # Video + Denoised Master Mix only
                cmd.extend([
                    "-map", "0:v",
                    "-map", "[a_master]",
                    "-metadata:s:a:0", "title=Master Mix (Game + Friends + My Mic)",
                    "-disposition:a:0", "default"
                ])
        else:
            # Game sound & friends only
            cmd.extend([
                "-filter_complex", f"[1:a]volume={game_volume:.2f}[a_game]",
                "-map", "0:v",
                "-map", "[a_game]",
                "-metadata:s:a:0", "title=Game & Friends Audio",
                "-disposition:a:0", "default"
            ])

        # 4. Encoders & MP4 Container Optimizations
        cmd.extend([
            "-c:v", "libx264",
            "-preset", "veryfast",
            "-crf", "21",
            "-pix_fmt", "yuv420p",
            "-c:a", "aac",
            "-b:a", "192k",
            "-movflags", "+faststart",
            str(self.current_recording_path)
        ])

        try:
            logger.info(f"Starting studio recording subprocess: {' '.join(cmd)}")
            self._stop_event.clear()
            self._start_time = time.time()
            self.process = subprocess.Popen(
                cmd,
                stdin=subprocess.PIPE,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                start_new_session=True
            )

            self.stats.is_recording = True
            self.stats.output_path = str(self.current_recording_path)

            self._monitor_thread = threading.Thread(target=self._monitor_stats, daemon=True)
            self._monitor_thread.start()

            return True, "Recording started", str(self.current_recording_path)
        except Exception as e:
            logger.error(f"Failed to start recording: {e}")
            self.stats.is_recording = False
            return False, str(e), None

    def _monitor_stats(self):
        while not self._stop_event.is_set():
            if not self.process or self.process.poll() is not None:
                self.stats.is_recording = False
                break

            self.stats.duration_seconds = time.time() - self._start_time
            if self.current_recording_path and self.current_recording_path.exists():
                try:
                    size = self.current_recording_path.stat().st_size
                    self.stats.file_size_bytes = size
                    mb = size / (1024 * 1024)
                    self.stats.file_size_formatted = f"{mb:.1f} MB"
                except Exception:
                    pass

            time.sleep(0.5)

    def is_recording(self) -> bool:
        return self.process is not None and self.process.poll() is None

    def stop_recording(self) -> Tuple[bool, str, Optional[str]]:
        if self.process is None:
            return False, "No active recording to stop", None

        self._stop_event.set()
        logger.info("Stopping recording process cleanly...")

        try:
            # If still running, send 'q' to stdin for graceful FFmpeg finalization
            if self.process.poll() is None:
                if self.process.stdin:
                    try:
                        self.process.stdin.write(b"q")
                        self.process.stdin.flush()
                        self.process.stdin.close()
                    except Exception:
                        pass

                # Wait for clean exit
                try:
                    self.process.wait(timeout=3.5)
                except subprocess.TimeoutExpired:
                    # Send SIGINT if still running
                    self.process.send_signal(signal.SIGINT)
                    self.process.wait(timeout=2.0)
        except Exception as e:
            logger.warning(f"Error during recording process shutdown: {e}")
            try:
                self.process.kill()
            except Exception:
                pass

        self.stats.is_recording = False
        saved_path = str(self.current_recording_path)
        self.process = None

        if self.current_recording_path and self.current_recording_path.exists():
            final_size_mb = self.current_recording_path.stat().st_size / (1024 * 1024)
            msg = f"Recording saved ({final_size_mb:.1f} MB): {self.current_recording_path.name}"
            logger.info(msg)
            return True, msg, saved_path

        return False, "Recording process terminated but output file was not found", None
