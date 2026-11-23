from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QFrame, QGridLayout, QHBoxLayout, QLabel, QVBoxLayout, QWidget
)

from ..core.orchestrator import TelemetrySnapshot

class MetricCard(QFrame):
    def __init__(self, title: str, unit: str = "", default_val: str = "--", parent=None):
        super().__init__(parent)
        self.setProperty("class", "glassCard")
        self.setMinimumHeight(76)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 10, 12, 10)
        layout.setSpacing(4)

        self.lbl_title = QLabel(title)
        self.lbl_title.setProperty("class", "metricTitle")

        val_layout = QHBoxLayout()
        val_layout.setSpacing(4)
        val_layout.setContentsMargins(0, 0, 0, 0)

        self.lbl_val = QLabel(default_val)
        self.lbl_val.setProperty("class", "metricValue")

        self.lbl_unit = QLabel(unit)
        self.lbl_unit.setProperty("class", "metricUnit")
        self.lbl_unit.setAlignment(Qt.AlignmentFlag.AlignBottom | Qt.AlignmentFlag.AlignLeft)

        val_layout.addWidget(self.lbl_val)
        val_layout.addWidget(self.lbl_unit)
        val_layout.addStretch()

        layout.addWidget(self.lbl_title)
        layout.addLayout(val_layout)

    def set_value(self, val: str, color_hex: str = "#00f0ff"):
        self.lbl_val.setText(val)
        self.lbl_val.setStyleSheet(f"color: {color_hex};")

class TelemetryHUD(QWidget):
    """
    Telemetry Dashboard displaying real-time stream vitals:
    FPS, Audio Delay, Battery Temp, Wi-Fi RSSI, Pings, Jitter Buffer.
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(10)

        header = QLabel("LIVE TELEMETRY")
        header.setStyleSheet("color: #7aa2f7; font-weight: 800; font-size: 11px; letter-spacing: 1px;")
        layout.addWidget(header)

        grid = QGridLayout()
        grid.setSpacing(10)

        self.card_fps = MetricCard("VIDEO FRAMERATE", "FPS", "0.0")
        self.card_audio = MetricCard("AUDIO DELAY", "ms", "12.5")
        self.card_temp = MetricCard("DEVICE THERMAL", "°C", "--")
        self.card_wifi = MetricCard("WI-FI 6 LINK", "Mbps", "--")
        self.card_ping = MetricCard("DEVICE RTT", "ms", "--")
        self.card_cdn = MetricCard("INGEST PING", "ms", "--")
        self.card_jitter = MetricCard("NETWORK JITTER", "ms", "0.0")
        self.card_buffer = MetricCard("ADAPTIVE BUFFER", "ms", "15")

        grid.addWidget(self.card_fps, 0, 0)
        grid.addWidget(self.card_audio, 0, 1)
        grid.addWidget(self.card_temp, 1, 0)
        grid.addWidget(self.card_wifi, 1, 1)
        grid.addWidget(self.card_ping, 2, 0)
        grid.addWidget(self.card_cdn, 2, 1)
        grid.addWidget(self.card_jitter, 3, 0)
        grid.addWidget(self.card_buffer, 3, 1)

        layout.addLayout(grid)

    def update_telemetry(self, t: TelemetrySnapshot):
        # FPS
        fps_str = f"{t.fps:.1f}" if t.fps > 0 else "0.0"
        fps_color = "#00ff9d" if t.fps >= 55.0 else ("#e0af68" if t.fps >= 30.0 else "#7aa2f7")
        self.card_fps.set_value(fps_str, fps_color)

        # Audio Delay
        audio_str = f"{t.audio_delay_ms:.1f}"
        audio_color = "#00ff9d" if t.audio_delay_ms <= 20.0 else "#e0af68"
        self.card_audio.set_value(audio_str, audio_color)

        # Device Temperature
        if t.device_temp_c > 0:
            temp_str = f"{t.device_temp_c:.1f}"
            temp_color = "#00ff9d" if t.device_temp_c < 38.0 else ("#e0af68" if t.device_temp_c < 43.0 else "#f7768e")
            self.card_temp.set_value(temp_str, temp_color)
        else:
            self.card_temp.set_value("--", "#565f89")

        # Wi-Fi Link Speed / RSSI
        if t.wifi_link_speed_mbps > 0:
            wifi_str = f"{t.wifi_link_speed_mbps} ({t.wifi_rssi_dbm}dBm)"
            self.card_wifi.set_value(wifi_str, "#00f0ff")
        elif t.is_wireless:
            self.card_wifi.set_value(f"{t.wifi_rssi_dbm} dBm", "#7aa2f7")
        else:
            self.card_wifi.set_value("USB 3.2", "#bb9af7")

        # Device Ping
        if t.device_ping_ms > 0:
            ping_color = "#00ff9d" if t.device_ping_ms < 20.0 else ("#e0af68" if t.device_ping_ms < 50.0 else "#f7768e")
            self.card_ping.set_value(f"{t.device_ping_ms:.1f}", ping_color)
        else:
            self.card_ping.set_value("<1.0" if not t.is_wireless else "--", "#bb9af7")

        # CDN Ingest Ping
        if t.cdn_ping_ms > 0:
            cdn_color = "#00ff9d" if t.cdn_ping_ms < 40.0 else "#e0af68"
            self.card_cdn.set_value(f"{t.cdn_ping_ms:.1f}", cdn_color)
        else:
            self.card_cdn.set_value("--", "#565f89")

        # Jitter & Buffer
        self.card_jitter.set_value(f"{t.jitter_ms:.1f}", "#7aa2f7")
        self.card_buffer.set_value(f"{t.recommended_buffer_ms}", "#00ff9d" if t.recommended_buffer_ms <= 20 else "#e0af68")
