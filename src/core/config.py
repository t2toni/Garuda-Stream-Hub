from dataclasses import dataclass, field, asdict
from enum import Enum
import json
import os
from pathlib import Path
from typing import List, Optional

class PipelineState(Enum):
    IDLE = "IDLE"
    INITIALIZING = "INITIALIZING"
    ACTIVE = "ACTIVE"
    ERROR = "ERROR"
    TEARING_DOWN = "TEARING_DOWN"

class ConnectionMode(Enum):
    AUTO = "AUTO"
    WIFI = "WIFI"
    USB = "USB"

@dataclass
class VideoConfig:
    codec: str = "h265"                  # h265 (HEVC), h264 (AVC), av1
    encoder: str = "c2.qti.hevc.encoder" # Qualcomm HW encoder or auto
    bitrate_mbps: int = 16               # Default 16 Mbps
    max_fps: int = 60                    # 60 or 120 FPS
    max_size: int = 0                    # 0 = native device resolution, e.g. 1920
    video_buffer_ms: int = 15            # Low-latency target buffer
    v4l2_device: str = "/dev/video10"     # Virtual camera node or auto
    use_v4l2: bool = False               # True if v4l2loopback is active

@dataclass
class AudioConfig:
    codec: str = "raw"                   # raw (uncompressed 48kHz PCM, zero robotic compression artifacts), aac, opus
    audio_source: str = "output"         # output (clean digital game + friends voice call), playback
    audio_buffer_ms: int = 50            # 50ms stable buffer preventing jitter under-runs & time-stretch robotic glitching
    sink_name: str = "BGMI_Audio_Sink"   # Dedicated virtual sink
    sink_description: str = "BGMI_Audio_Sink (Mobile Stream Engine)"
    auto_loopback: bool = True           # Loopback to physical headphones
    duplicate_audio: bool = False        # Duplicate on device
    enable_krisp_denoiser: bool = True   # Real-time neural AI noise suppression (Discord Krisp architecture)
    krisp_vad_threshold: float = 50.0    # Voice activity detection threshold (%)

@dataclass
class RecordingConfig:
    output_dir: str = str(Path.home() / "Videos" / "Recordings")
    record_format: str = "mp4"           # mp4 or mkv
    video_bitrate_mbps: int = 16         # 16 Mbps for crisp 1080p
    audio_bitrate_kbps: int = 192        # 192 kbps per stream
    include_mic: bool = True             # Record player's microphone
    mic_volume: float = 0.85             # 0.85 = 85% clean gain without clipping
    game_volume: float = 1.0             # 1.0 = 100%
    mic_source: str = "default"          # "default" or specific alsa_input...
    multi_track: bool = True             # Multi-track audio (Master, Game, Mic)
    noise_suppression: bool = True       # Active highpass filter
    noise_gate: bool = True              # Noise gate: silences room hiss & fan noise when not speaking
    noise_gate_threshold: float = 0.012  # Musical gate sensitivity threshold
    krisp_ai_denoiser: bool = True       # Discord Krisp-grade neural noise suppression (RNNoise model)
    rnnoise_model: str = "bd.rnnn"       # Model optimized for Voice over Room/Fan noise
    wind_cut_hz: int = 125               # Wind & breath air blast filter frequency (125Hz steep cutoff)
    air_cut_hz: int = 11500              # High-frequency air ventilation hiss cutoff (11.5kHz)

@dataclass
class AndroidOptimizationConfig:
    stay_on_plugged_in: int = 3          # Keep display awake
    disable_low_power: bool = True       # Disable Android battery saver
    enable_game_driver: bool = True      # Enable Android performance driver
    compile_packages: List[str] = field(default_factory=lambda: [
        "com.pubg.imobile",
        "com.dts.freefiremax",
        "com.dts.freefireth"
    ])

@dataclass
class TelemetryConfig:
    poll_interval_ms: int = 500
    ping_timeout_ms: int = 600
    cdn_ingest_host: str = "8.8.8.8"      # Google DNS / YouTube ingest sentinel
    cdn_ingest_port: int = 53

@dataclass
class StreamConfig:
    connection_mode: ConnectionMode = ConnectionMode.AUTO
    device_ip: Optional[str] = None
    device_port: int = 5555
    device_serial: Optional[str] = None
    target_nice: int = -10
    video: VideoConfig = field(default_factory=VideoConfig)
    audio: AudioConfig = field(default_factory=AudioConfig)
    recording: RecordingConfig = field(default_factory=RecordingConfig)
    android: AndroidOptimizationConfig = field(default_factory=AndroidOptimizationConfig)
    telemetry: TelemetryConfig = field(default_factory=TelemetryConfig)

    @classmethod
    def get_config_path(cls) -> Path:
        base = Path(os.environ.get("XDG_CONFIG_HOME", Path.home() / ".config"))
        return base / "garuda_stream_hub" / "settings.json"

    def save(self) -> None:
        path = self.get_config_path()
        path.parent.mkdir(parents=True, exist_ok=True)
        data = asdict(self)
        data["connection_mode"] = self.connection_mode.value
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)

    @classmethod
    def load(cls) -> "StreamConfig":
        path = cls.get_config_path()
        if not path.exists():
            return cls()
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            mode_str = data.get("connection_mode", "AUTO")
            mode = ConnectionMode(mode_str) if mode_str in ConnectionMode._value2member_map_ else ConnectionMode.AUTO
            
            video = VideoConfig(**data.get("video", {}))
            audio = AudioConfig(**data.get("audio", {}))
            recording = RecordingConfig(**data.get("recording", {}))
            android = AndroidOptimizationConfig(**data.get("android", {}))
            telemetry = TelemetryConfig(**data.get("telemetry", {}))
            
            return cls(
                connection_mode=mode,
                device_ip=data.get("device_ip"),
                device_port=data.get("device_port", 5555),
                device_serial=data.get("device_serial"),
                target_nice=data.get("target_nice", -10),
                video=video,
                audio=audio,
                recording=recording,
                android=android,
                telemetry=telemetry
            )
        except Exception:
            return cls()
