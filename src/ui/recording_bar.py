import os
import subprocess
from pathlib import Path
from PyQt6.QtCore import Qt, QTimer, pyqtSignal
from PyQt6.QtGui import QColor, QFont, QLinearGradient, QPainter, QPen, QBrush
from PyQt6.QtWidgets import (
    QFrame, QHBoxLayout, QLabel, QPushButton, QSlider, QVBoxLayout, QWidget
)

from ..core.config import StreamConfig
from ..core.orchestrator import TelemetrySnapshot

class RecordButton(QPushButton):
    """
    Animated pulsing red recording action button.
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumSize(180, 48)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self._is_recording = False
        self._glow_alpha = 150
        self._pulse_direction = 1

        self._timer = QTimer(self)
        self._timer.timeout.connect(self._animate_pulse)
        self._timer.start(40)

        self._update_label()

    def set_recording(self, recording: bool):
        self._is_recording = recording
        self._update_label()
        self.update()

    def _update_label(self):
        if self._is_recording:
            self.setText("⏹ STOP RECORDING")
        else:
            self.setText("🔴 START RECORDING")

    def _animate_pulse(self):
        if self._is_recording:
            self._glow_alpha += 8 * self._pulse_direction
            if self._glow_alpha >= 250:
                self._glow_alpha = 250
                self._pulse_direction = -1
            elif self._glow_alpha <= 90:
                self._glow_alpha = 90
                self._pulse_direction = 1
            self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        rect = self.rect().adjusted(2, 2, -2, -2)
        radius = 10.0

        if self._is_recording:
            glow_color = QColor(255, 0, 70, self._glow_alpha)
            border_color = QColor(255, 50, 90)
            bg_color = QColor(60, 10, 20, 230)
        else:
            glow_color = QColor(247, 118, 142, 60)
            border_color = QColor(247, 118, 142)
            bg_color = QColor(36, 40, 59, 220)

        # Outer Glow
        glow_pen = QPen(glow_color, 4.0)
        painter.setPen(glow_pen)
        painter.drawRoundedRect(rect.adjusted(1, 1, -1, -1), radius, radius)

        # Background
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QBrush(bg_color))
        painter.drawRoundedRect(rect, radius, radius)

        # Border
        painter.setPen(QPen(border_color, 1.8))
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawRoundedRect(rect, radius, radius)

        # Text
        painter.setPen(QColor(255, 255, 255))
        font = QFont("JetBrains Mono", 11, QFont.Weight.Bold)
        painter.setFont(font)
        painter.drawText(rect, Qt.AlignmentFlag.AlignCenter, self.text())

class RecordingBar(QFrame):
    """
    Studio Recording Control Bar:
    - Master Record Toggle Button
    - Live Duration & File Size telemetry
    - Real-Time Volume Sliders for Game/Friends & My Mic
    - Quick-access button to Recordings folder
    """
    record_requested = pyqtSignal(bool)
    mic_volume_changed = pyqtSignal(float)
    game_volume_changed = pyqtSignal(float)
    mic_mute_toggled = pyqtSignal(bool)

    def __init__(self, config: StreamConfig, parent=None):
        super().__init__(parent)
        self.config = config
        self.setProperty("class", "glassCard")
        self.setFixedHeight(74)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(14, 8, 14, 8)
        layout.setSpacing(14)

        # 1. Master Record Button
        self.btn_record = RecordButton(self)
        self.btn_record.clicked.connect(self._on_record_clicked)
        layout.addWidget(self.btn_record)

        # 2. Recording Status & Telemetry
        v_info = QVBoxLayout()
        v_info.setSpacing(2)
        v_info.setContentsMargins(0, 0, 0, 0)

        self.lbl_status = QLabel("STANDBY")
        self.lbl_status.setStyleSheet("color: #7aa2f7; font-weight: 800; font-size: 11px;")

        self.lbl_duration_size = QLabel("⏱ 00:00:00  •  💾 0.0 MB")
        self.lbl_duration_size.setStyleSheet("color: #9aa5ce; font-size: 11px;")

        v_info.addWidget(self.lbl_status)
        v_info.addWidget(self.lbl_duration_size)
        layout.addLayout(v_info)

        layout.addSpacing(10)

        # 3. Audio Mixing Sliders: Game & Friends Volume
        v_game = QVBoxLayout()
        v_game.setSpacing(2)
        v_game.setContentsMargins(0, 0, 0, 0)
        self.lbl_game_vol = QLabel("🔊 GAME & FRIENDS: 100%")
        self.lbl_game_vol.setStyleSheet("color: #00f0ff; font-size: 10px; font-weight: 700;")
        self.slider_game_vol = QSlider(Qt.Orientation.Horizontal)
        self.slider_game_vol.setRange(0, 150)
        self.slider_game_vol.setValue(int(self.config.recording.game_volume * 100))
        self.slider_game_vol.setFixedWidth(130)
        self.slider_game_vol.valueChanged.connect(self._on_game_slider_changed)
        v_game.addWidget(self.lbl_game_vol)
        v_game.addWidget(self.slider_game_vol)
        layout.addLayout(v_game)

        # 4. Audio Mixing Sliders: Player Mic Volume
        v_mic = QVBoxLayout()
        v_mic.setSpacing(2)
        v_mic.setContentsMargins(0, 0, 0, 0)
        self.lbl_mic_vol = QLabel(f"🎙️ MY MIC: {int(self.config.recording.mic_volume * 100)}%")
        self.lbl_mic_vol.setStyleSheet("color: #00ff9d; font-size: 10px; font-weight: 700;")
        self.slider_mic_vol = QSlider(Qt.Orientation.Horizontal)
        self.slider_mic_vol.setRange(0, 150)
        self.slider_mic_vol.setValue(int(self.config.recording.mic_volume * 100))
        self.slider_mic_vol.setFixedWidth(130)
        self.slider_mic_vol.valueChanged.connect(self._on_mic_slider_changed)
        v_mic.addWidget(self.lbl_mic_vol)
        v_mic.addWidget(self.slider_mic_vol)
        layout.addLayout(v_mic)

        # 5. Mic Mute Toggle & Noise Gate Badge
        self.btn_mic_mute = QPushButton("🎙️ MIC ON")
        self.btn_mic_mute.setCheckable(True)
        self.btn_mic_mute.setFixedHeight(34)
        self.btn_mic_mute.setStyleSheet("font-size: 11px; padding: 4px 10px; color: #00ff9d;")
        self.btn_mic_mute.toggled.connect(self._on_mic_mute_toggled)
        layout.addWidget(self.btn_mic_mute)

        self.lbl_noise_badge = QLabel("🛡️ AI VOICE SEPARATOR & AIR FILTER ACTIVE")
        self.lbl_noise_badge.setStyleSheet(
            "background: rgba(0, 255, 157, 0.12); color: #00ff9d; "
            "border: 1px solid rgba(0, 255, 157, 0.45); border-radius: 6px; "
            "padding: 5px 9px; font-size: 10px; font-weight: 800; letter-spacing: 0.5px;"
        )
        layout.addWidget(self.lbl_noise_badge)

        layout.addStretch()

        # 6. Open Recordings Folder Button
        self.btn_folder = QPushButton("📂 RECORDINGS")
        self.btn_folder.setFixedHeight(34)
        self.btn_folder.setStyleSheet("font-size: 11px; padding: 4px 12px; color: #7aa2f7;")
        self.btn_folder.clicked.connect(self._open_folder)
        layout.addWidget(self.btn_folder)

    def _on_record_clicked(self):
        is_rec = self.btn_record._is_recording
        self.record_requested.emit(not is_rec)

    def _on_game_slider_changed(self, val: int):
        self.lbl_game_vol.setText(f"🔊 GAME & FRIENDS: {val}%")
        factor = val / 100.0
        self.config.recording.game_volume = factor
        self.config.save()
        self.game_volume_changed.emit(factor)

    def _on_mic_slider_changed(self, val: int):
        self.lbl_mic_vol.setText(f"🎙️ MY MIC: {val}%")
        factor = val / 100.0
        self.config.recording.mic_volume = factor
        self.config.save()
        self.mic_volume_changed.emit(factor)

    def _on_mic_mute_toggled(self, checked: bool):
        if checked:
            self.btn_mic_mute.setText("🔇 MIC MUTED")
            self.btn_mic_mute.setStyleSheet("color: #f7768e; border-color: #f7768e; font-size: 11px; padding: 4px 10px;")
        else:
            self.btn_mic_mute.setText("🎙️ MIC ON")
            self.btn_mic_mute.setStyleSheet("color: #00ff9d; border-color: #00ff9d; font-size: 11px; padding: 4px 10px;")
        self.mic_mute_toggled.emit(checked)

    def _open_folder(self):
        folder = Path(self.config.recording.output_dir).expanduser()
        folder.mkdir(parents=True, exist_ok=True)
        try:
            subprocess.Popen(["xdg-open", str(folder)])
        except Exception:
            pass

    def update_telemetry(self, t: TelemetrySnapshot):
        self.btn_record.set_recording(t.is_recording)
        if t.is_recording:
            self.lbl_status.setText("● RECORDING (MULTI-TRACK)")
            self.lbl_status.setStyleSheet("color: #ff0055; font-weight: 800; font-size: 11px;")

            total_sec = int(t.recording_duration_s)
            hrs = total_sec // 3600
            mins = (total_sec % 3600) // 60
            secs = total_sec % 60
            dur_str = f"{hrs:02d}:{mins:02d}:{secs:02d}"

            self.lbl_duration_size.setText(f"⏱ {dur_str}  •  💾 {t.recording_file_size}")
        else:
            self.lbl_status.setText("STANDBY")
            self.lbl_status.setStyleSheet("color: #7aa2f7; font-weight: 800; font-size: 11px;")
            self.lbl_duration_size.setText("⏱ 00:00:00  •  💾 0.0 MB")
