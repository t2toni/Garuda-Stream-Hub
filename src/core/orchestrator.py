import logging
import os
import shutil
import threading
import time
from dataclasses import dataclass
from typing import Callable, Dict, List, Optional, Tuple

from .config import StreamConfig, PipelineState, ConnectionMode
from .system_optimizer import SystemOptimizer
from ..android.discovery import DeviceDiscoveryManager
from ..android.optimizer import DeviceOptimizer
from ..android.telemetry import DeviceTelemetryReader, DeviceMetrics
from ..audio.pipewire_manager import PipeWireManager
from ..video.scrcpy_controller import ScrcpyController
from ..video.adaptive_buffer import AdaptiveBufferController
from ..obs.scene_injector import OBSSceneInjector
from ..recorder.recording_manager import RecordingManager, RecordingStats

# Attempt native C++ extension import
try:
    import sys
    sys.path.append(os.path.join(os.path.dirname(__file__), "..", "native"))
    import stream_native
    HAVE_NATIVE = True
except Exception:
    HAVE_NATIVE = False

class PythonJitterCalculator:
    """Pure-Python fallback when native C++ module is unavailable."""
    def __init__(self, window_size: int = 30):
        self.window_size = window_size
        self.samples: List[float] = []
        self.jitter_estimate = 0.0
        self.last_rtt = -1.0
        self.lock = threading.Lock()

    def add_sample(self, rtt_ms: float) -> None:
        if rtt_ms < 0.0:
            return
        with self.lock:
            self.samples.append(rtt_ms)
            if len(self.samples) > self.window_size:
                self.samples.pop(0)
            if self.last_rtt >= 0.0:
                d = abs(rtt_ms - self.last_rtt)
                self.jitter_estimate += (d - self.jitter_estimate) / 16.0
            else:
                self.jitter_estimate = 0.0
            self.last_rtt = rtt_ms

    def get_jitter_ms(self) -> float:
        with self.lock:
            return self.jitter_estimate

    def get_recommended_buffer_ms(self) -> int:
        with self.lock:
            buf = 15 + int(round(self.jitter_estimate * 2.0))
            return max(15, min(100, buf))

    def reset(self) -> None:
        with self.lock:
            self.samples.clear()
            self.jitter_estimate = 0.0
            self.last_rtt = -1.0

def python_ping_host(host: str, port: int, timeout_ms: int = 400) -> float:
    """Cross-platform socket ping fallback."""
    import socket
    start = time.perf_counter()
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(timeout_ms / 1000.0)
        sock.connect((host, port))
        sock.close()
        return (time.perf_counter() - start) * 1000.0
    except Exception:
        return -1.0

logger = logging.getLogger("PipelineOrchestrator")

@dataclass
class TelemetrySnapshot:
    state: PipelineState = PipelineState.IDLE
    fps: float = 0.0
    audio_delay_ms: float = 0.0
    device_temp_c: float = 0.0
    device_battery_pct: int = 100
    wifi_rssi_dbm: int = -99
    wifi_link_speed_mbps: int = 0
    wifi_ssid: str = "N/A"
    is_wireless: bool = False
    device_ping_ms: float = 0.0
    cdn_ping_ms: float = 0.0
    jitter_ms: float = 0.0
    recommended_buffer_ms: int = 15
    quality_tier: str = "HIGH"
    active_device_serial: str = "None"
    scrcpy_pid: Optional[int] = None
    step_statuses: Dict[int, str] = None
    is_recording: bool = False
    recording_duration_s: float = 0.0
    recording_file_size: str = "0.0 MB"
    recording_path: str = ""

class PipelineOrchestrator:
    """
    Master 1-Tap Streaming Hub Orchestrator.
    Executes and monitors the 5 system phases in parallel / sequential pipeline.
    """
    def __init__(self, config: Optional[StreamConfig] = None):
        self.config = config or StreamConfig.load()
        self.state = PipelineState.IDLE
        self.step_statuses: Dict[int, str] = {
            1: "Pending",
            2: "Pending",
            3: "Pending",
            4: "Pending",
            5: "Pending"
        }

        # Subsystems
        self.discovery = DeviceDiscoveryManager()
        self.audio = PipeWireManager()
        self.scrcpy = ScrcpyController()
        self.adaptive_buffer = AdaptiveBufferController(base_buffer_ms=self.config.video.video_buffer_ms)
        self.obs = OBSSceneInjector()
        self.recorder = RecordingManager(output_dir=self.config.recording.output_dir)
        self.android_optimizer: Optional[DeviceOptimizer] = None
        self.android_telemetry: Optional[DeviceTelemetryReader] = None

        # Telemetry engines (Native C++ with seamless Python fallback)
        if HAVE_NATIVE:
            self.jitter_calc = stream_native.JitterCalculator(window_size=30)
            self._ping_func = stream_native.ping_host
        else:
            self.jitter_calc = PythonJitterCalculator(window_size=30)
            self._ping_func = python_ping_host

        # Telemetry worker
        self._telemetry_thread: Optional[threading.Thread] = None
        self._telemetry_stop = threading.Event()
        self.latest_telemetry = TelemetrySnapshot()

        # Callbacks
        self.on_step_updated: Optional[Callable[[int, str, bool], None]] = None
        self.on_state_changed: Optional[Callable[[PipelineState], None]] = None
        self.on_telemetry_updated: Optional[Callable[[TelemetrySnapshot], None]] = None

    def _set_state(self, new_state: PipelineState) -> None:
        self.state = new_state
        self.latest_telemetry.state = new_state
        if self.on_state_changed:
            self.on_state_changed(new_state)

    def _set_step(self, step: int, msg: str, success: bool = True) -> None:
        self.step_statuses[step] = msg
        logger.info(f"Step {step}: {msg}")
        if self.on_step_updated:
            self.on_step_updated(step, msg, success)

    def validate_dependencies(self) -> Tuple[bool, List[str]]:
        """STEP 1: Dependency Validation (Cross-Platform)"""
        if sys.platform == "win32":
            tools = ["adb", "scrcpy", "ffmpeg"]
        else:
            tools = ["adb", "scrcpy", "pactl", "pw-cli", "ffmpeg"]
        missing = [tool for tool in tools if not shutil.which(tool)]
        if missing:
            return False, missing
        return True, []

    def initialize_pipeline(self) -> Tuple[bool, str]:
        """
        Executes the master 1-tap pipeline initialization across all 5 phases.
        """
        if self.state in (PipelineState.INITIALIZING, PipelineState.ACTIVE):
            return True, "Pipeline already initializing or active"

        self._set_state(PipelineState.INITIALIZING)
        logger.info("Initializing Master Stream Pipeline...")

        # STEP 1: Dependency Check
        ok, missing = self.validate_dependencies()
        if not ok:
            err = f"Missing system dependencies: {', '.join(missing)}"
            self._set_step(1, err, False)
            self._set_state(PipelineState.ERROR)
            return False, err
        self._set_step(1, "All core binaries validated (adb, scrcpy, pipewire, ffmpeg)", True)

        # STEP 2: Network & USB Environment Handshake
        self._set_step(2, "Scanning subnet and querying device...", True)
        handshake_ok, serial, is_wireless, h_msg = self.discovery.auto_handshake()
        if not handshake_ok or not serial:
            err = f"Device handshake failed: {h_msg}"
            self._set_step(2, err, False)
            self._set_state(PipelineState.ERROR)
            return False, err

        self.latest_telemetry.active_device_serial = serial
        self.latest_telemetry.is_wireless = is_wireless
        self.android_optimizer = DeviceOptimizer(serial=serial)
        self.android_telemetry = DeviceTelemetryReader(serial=serial)

        # Android Performance Injection
        opt_results = self.android_optimizer.apply_optimizations(self.config.android.compile_packages)
        self._set_step(2, f"Handshake complete: {serial} ({'Wi-Fi 6' if is_wireless else 'USB 3.2'}). Optimizations injected.", True)

        # STEP 3: Virtual Sound Engine Construction
        self._set_step(3, "Provisioning PipeWire virtual cable & loopback...", True)
        sink_ok, _, sink_msg = self.audio.create_virtual_sink(
            sink_name=self.config.audio.sink_name,
            description=self.config.audio.sink_description
        )
        if not sink_ok:
            err = f"Failed to provision virtual audio: {sink_msg}"
            self._set_step(3, err, False)
            self.teardown_pipeline()
            self._set_state(PipelineState.ERROR)
            return False, err

        # Ensure player's microphone duplex profile is active
        mic_ok, mic_msg = self.audio.ensure_duplex_mic_enabled()
        logger.info(f"Microphone duplex status: {mic_msg}")

        # Setup zero-latency headphone loopback strictly for game audio & teammates
        if self.config.audio.auto_loopback:
            lb_ok, _, lb_msg = self.audio.setup_headphone_loopback(
                game_sink=self.config.audio.sink_name,
                latency_ms=15
            )
            if not lb_ok:
                logger.warning(f"Headphone loopback notice: {lb_msg}")

        # Launch real-time neural Krisp denoiser if enabled
        krisp_status_msg = ""
        if self.config.audio.enable_krisp_denoiser:
            krisp_ok, krisp_msg = self.audio.start_krisp_denoiser(
                vad_threshold=self.config.audio.krisp_vad_threshold
            )
            logger.info(f"Krisp AI Denoiser status: {krisp_msg}")
            if krisp_ok:
                krisp_status_msg = " + Krisp AI Mic Active"

        self._set_step(3, f"Clean Sound Engine Active: Game + Friends ({self.config.audio.sink_name}) to Headphones{krisp_status_msg}", True)

        # STEP 4: Display Casting & Frame Acceleration
        self._set_step(4, "Launching scrcpy H.265 Qualcomm HW stream...", True)
        scrcpy_ok, scrcpy_msg = self.scrcpy.start(
            serial=serial,
            pulse_sink=self.config.audio.sink_name,
            video_codec=self.config.video.codec,
            video_encoder=self.config.video.encoder,
            bitrate_mbps=self.config.video.bitrate_mbps,
            max_fps=self.config.video.max_fps,
            video_buffer_ms=self.config.video.video_buffer_ms,
            audio_codec=self.config.audio.codec,
            audio_source=self.config.audio.audio_source,
            audio_buffer_ms=self.config.audio.audio_buffer_ms,
            v4l2_sink=self.config.video.v4l2_device if self.config.video.use_v4l2 else None,
            max_size=self.config.video.max_size
        )
        if not scrcpy_ok:
            err = f"Failed to start video mirror: {scrcpy_msg}"
            self._set_step(4, err, False)
            self.teardown_pipeline()
            self._set_state(PipelineState.ERROR)
            return False, err

        # Elevate scrcpy priority
        pid = self.scrcpy.get_pid()
        if pid:
            self.latest_telemetry.scrcpy_pid = pid
            SystemOptimizer.elevate_priority(pid, desired_nice=self.config.target_nice)

        self._set_step(4, f"H.265 Video Mirror Active (15ms buffer, PID: {pid})", True)

        # STEP 5: OBS Studio Auto-Hook & Telemetry
        self._set_step(5, "Configuring OBS Studio audio/video sources...", True)
        obs_mic = self.audio.krisp_source_name if self.audio.is_krisp_active() else "default"
        obs_ok, obs_msg = self.obs.inject_pipeline_sources(
            sink_name=self.config.audio.sink_name,
            v4l2_device=self.config.video.v4l2_device if self.config.video.use_v4l2 else None,
            mic_device=obs_mic
        )
        self._set_step(5, f"OBS Hook: {obs_msg}", True)

        # Launch Telemetry Loop
        self._start_telemetry_loop()
        self._set_state(PipelineState.ACTIVE)
        logger.info("Master Stream Pipeline is fully ACTIVE!")
        return True, "Pipeline successfully initialized"

    def _start_telemetry_loop(self) -> None:
        self._telemetry_stop.clear()
        self._telemetry_thread = threading.Thread(target=self._run_telemetry, daemon=True)
        self._telemetry_thread.start()

    def _run_telemetry(self) -> None:
        while not self._telemetry_stop.is_set():
            try:
                # 1. Scrcpy FPS
                self.latest_telemetry.fps = self.scrcpy.current_fps

                # 2. Audio Latency
                self.latest_telemetry.audio_delay_ms = self.audio.get_audio_latency_ms()

                # 3. Android Device Metrics
                if self.android_telemetry:
                    d_metrics = self.android_telemetry.fetch_metrics()
                    self.latest_telemetry.device_temp_c = d_metrics.temperature_c
                    self.latest_telemetry.device_battery_pct = d_metrics.battery_level
                    self.latest_telemetry.wifi_rssi_dbm = d_metrics.wifi_rssi_dbm
                    self.latest_telemetry.wifi_link_speed_mbps = d_metrics.wifi_link_speed_mbps
                    self.latest_telemetry.wifi_ssid = d_metrics.wifi_ssid

                # 4. Latency & Jitter Sentinel
                serial = self.latest_telemetry.active_device_serial
                dev_ip = serial.split(":")[0] if ":" in serial else None
                if dev_ip and self._ping_func:
                    rtt = self._ping_func(dev_ip, 5555, 300)
                    if rtt > 0:
                        self.latest_telemetry.device_ping_ms = round(rtt, 1)
                        if self.jitter_calc:
                            self.jitter_calc.add_sample(rtt)
                            self.latest_telemetry.jitter_ms = round(self.jitter_calc.get_jitter_ms(), 1)
                            self.latest_telemetry.recommended_buffer_ms = self.jitter_calc.get_recommended_buffer_ms()

                # CDN Ingest Ping (Google / YouTube)
                if self._ping_func:
                    cdn_rtt = self._ping_func(self.config.telemetry.cdn_ingest_host, self.config.telemetry.cdn_ingest_port, 400)
                    if cdn_rtt > 0:
                        self.latest_telemetry.cdn_ping_ms = round(cdn_rtt, 1)

                # Recording stats
                self.latest_telemetry.is_recording = self.recorder.is_recording()
                self.latest_telemetry.recording_duration_s = self.recorder.stats.duration_seconds
                self.latest_telemetry.recording_file_size = self.recorder.stats.file_size_formatted
                self.latest_telemetry.recording_path = self.recorder.stats.output_path

                # Quality evaluation
                buf, tier, _ = self.adaptive_buffer.evaluate(
                    self.latest_telemetry.jitter_ms,
                    self.latest_telemetry.device_ping_ms
                )
                self.latest_telemetry.quality_tier = tier

                # Notify UI
                if self.on_telemetry_updated:
                    self.on_telemetry_updated(self.latest_telemetry)

            except Exception as e:
                logger.debug(f"Telemetry cycle error: {e}")

            time.sleep(self.config.telemetry.poll_interval_ms / 1000.0)

    def start_recording(self) -> Tuple[bool, str, Optional[str]]:
        """
        Starts unified video and multi-track audio recording:
        Game screen video + Game audio + Friends voice call + Player mic.
        """
        return self.recorder.start_recording(
            game_sink=self.config.audio.sink_name,
            mic_source=self.config.recording.mic_source,
            game_volume=self.config.recording.game_volume,
            mic_volume=self.config.recording.mic_volume,
            include_mic=self.config.recording.include_mic,
            multi_track=self.config.recording.multi_track,
            filename_prefix="GarudaStream",
            krisp_denoiser=self.config.recording.krisp_ai_denoiser,
            rnnoise_model=self.config.recording.rnnoise_model,
            wind_cut_hz=self.config.recording.wind_cut_hz,
            air_cut_hz=self.config.recording.air_cut_hz
        )

    def stop_recording(self) -> Tuple[bool, str, Optional[str]]:
        """
        Stops active recording cleanly.
        """
        return self.recorder.stop_recording()

    def teardown_pipeline(self) -> List[str]:
        """
        Restores device settings, stops video mirror, unloads audio sinks, finalizes recordings.
        """
        self._set_state(PipelineState.TEARING_DOWN)
        results = []

        # Stop active recording cleanly if in progress
        if self.recorder.is_recording():
            ok, msg, path = self.recorder.stop_recording()
            results.append(f"Recording stopped: {msg}")

        # Stop Telemetry
        self._telemetry_stop.set()
        if self._telemetry_thread and self._telemetry_thread.is_alive():
            self._telemetry_thread.join(timeout=1.0)
        results.append("Telemetry sentinel stopped")

        # Stop Scrcpy
        if self.scrcpy.is_alive():
            self.scrcpy.stop()
            results.append("Scrcpy video engine stopped")

        # Restore Android Settings
        if self.android_optimizer:
            self.android_optimizer.restore_settings()
            results.append("Android device settings restored")

        # Teardown PipeWire Sinks
        audio_res = self.audio.teardown()
        results.extend(audio_res)

        # Reset Steps
        for k in self.step_statuses:
            self.step_statuses[k] = "Pending"
            if self.on_step_updated:
                self.on_step_updated(k, "Pending", True)

        self._set_state(PipelineState.IDLE)
        logger.info("Pipeline teardown completed")
        return results
