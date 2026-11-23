from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QCheckBox, QComboBox, QFormLayout, QFrame, QGridLayout, QHBoxLayout,
    QLabel, QLineEdit, QPushButton, QSlider, QVBoxLayout, QWidget
)

from ..core.config import StreamConfig
from ..core.system_optimizer import SystemOptimizer
from ..obs.scene_injector import OBSSceneInjector

class OverridesDrawer(QFrame):
    """
    Hidden expandable developer drawer for fine-tuning bitrates, codecs, ports,
    and launching OBS Studio / V4L2 loopback modules.
    """
    config_changed = pyqtSignal()

    def __init__(self, config: StreamConfig, parent=None):
        super().__init__(parent)
        self.config = config
        self.setProperty("class", "glassCard")
        self.setVisible(False) # Collapsed by default

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(16, 14, 16, 14)
        main_layout.setSpacing(12)

        title = QLabel("DEVELOPER OVERRIDES & HARDWARE TUNING")
        title.setStyleSheet("color: #00f0ff; font-weight: 800; font-size: 12px; letter-spacing: 1px;")
        main_layout.addWidget(title)

        grid = QGridLayout()
        grid.setHorizontalSpacing(16)
        grid.setVerticalSpacing(10)

        # 1. Video Bitrate
        self.lbl_bitrate = QLabel(f"Video Bitrate: {self.config.video.bitrate_mbps} Mbps")
        self.lbl_bitrate.setStyleSheet("color: #c0caf5; font-size: 11px;")
        self.slider_bitrate = QSlider(Qt.Orientation.Horizontal)
        self.slider_bitrate.setRange(4, 32)
        self.slider_bitrate.setValue(self.config.video.bitrate_mbps)
        self.slider_bitrate.valueChanged.connect(self._on_bitrate_changed)

        grid.addWidget(self.lbl_bitrate, 0, 0)
        grid.addWidget(self.slider_bitrate, 0, 1)

        # 2. Video Codec
        lbl_v_codec = QLabel("Video Codec:")
        lbl_v_codec.setStyleSheet("color: #c0caf5; font-size: 11px;")
        self.combo_v_codec = QComboBox()
        self.combo_v_codec.addItems(["h265", "h264", "av1"])
        self.combo_v_codec.setCurrentText(self.config.video.codec)
        self.combo_v_codec.currentTextChanged.connect(self._on_v_codec_changed)

        grid.addWidget(lbl_v_codec, 1, 0)
        grid.addWidget(self.combo_v_codec, 1, 1)

        # 3. Audio Codec & Capture Source Mode
        lbl_a_codec = QLabel("Audio Codec:")
        lbl_a_codec.setStyleSheet("color: #c0caf5; font-size: 11px;")
        self.combo_a_codec = QComboBox()
        self.combo_a_codec.addItems(["opus", "aac", "raw"])
        self.combo_a_codec.setCurrentText(self.config.audio.codec)
        self.combo_a_codec.currentTextChanged.connect(self._on_a_codec_changed)

        grid.addWidget(lbl_a_codec, 2, 0)
        grid.addWidget(self.combo_a_codec, 2, 1)

        lbl_a_source = QLabel("Audio Capture Mode:")
        lbl_a_source.setStyleSheet("color: #c0caf5; font-size: 11px;")
        self.combo_a_source = QComboBox()
        self.combo_a_source.addItems(["voice-performance", "output", "playback"])
        self.combo_a_source.setCurrentText(self.config.audio.audio_source)
        self.combo_a_source.currentTextChanged.connect(self._on_a_source_changed)

        grid.addWidget(lbl_a_source, 3, 0)
        grid.addWidget(self.combo_a_source, 3, 1)

        # 4. Video Buffer (ms)
        self.lbl_v_buffer = QLabel(f"Video Buffer: {self.config.video.video_buffer_ms} ms")
        self.lbl_v_buffer.setStyleSheet("color: #c0caf5; font-size: 11px;")
        self.slider_v_buffer = QSlider(Qt.Orientation.Horizontal)
        self.slider_v_buffer.setRange(0, 80)
        self.slider_v_buffer.setValue(self.config.video.video_buffer_ms)
        self.slider_v_buffer.valueChanged.connect(self._on_v_buffer_changed)

        grid.addWidget(self.lbl_v_buffer, 4, 0)
        grid.addWidget(self.slider_v_buffer, 4, 1)

        # 5. Multi-Track & V4L2 Options
        self.chk_multitrack = QCheckBox("Multi-Track Audio Recording (Master Mix + Game/Friends + My Mic)")
        self.chk_multitrack.setChecked(self.config.recording.multi_track)
        self.chk_multitrack.toggled.connect(self._on_multitrack_toggled)

        self.chk_v4l2 = QCheckBox("Enable V4L2 Virtual Camera (/dev/video10)")
        self.chk_v4l2.setChecked(self.config.video.use_v4l2)
        self.chk_v4l2.toggled.connect(self._on_v4l2_toggled)

        grid.addWidget(self.chk_multitrack, 5, 0, 1, 2)
        grid.addWidget(self.chk_v4l2, 6, 0, 1, 2)

        # 6. Target Game Packages
        lbl_pkg = QLabel("Target Games:")
        lbl_pkg.setStyleSheet("color: #c0caf5; font-size: 11px;")
        self.txt_pkg = QLineEdit(", ".join(self.config.android.compile_packages))
        self.txt_pkg.setPlaceholderText("com.pubg.imobile, com.dts.freefiremax")
        self.txt_pkg.textChanged.connect(self._on_pkg_changed)

        grid.addWidget(lbl_pkg, 7, 0)
        grid.addWidget(self.txt_pkg, 7, 1)

        main_layout.addLayout(grid)

        # Utility Buttons Row
        btn_row = QHBoxLayout()
        btn_row.setSpacing(10)

        self.btn_obs = QPushButton("Launch OBS Studio")
        self.btn_obs.clicked.connect(self._launch_obs)

        self.btn_v4l2 = QPushButton("Load v4l2loopback")
        self.btn_v4l2.clicked.connect(self._load_v4l2)

        self.lbl_status = QLabel("")
        self.lbl_status.setStyleSheet("color: #7aa2f7; font-size: 11px;")

        btn_row.addWidget(self.btn_obs)
        btn_row.addWidget(self.btn_v4l2)
        btn_row.addWidget(self.lbl_status)
        btn_row.addStretch()

        main_layout.addLayout(btn_row)

    def _on_bitrate_changed(self, val: int):
        self.config.video.bitrate_mbps = val
        self.lbl_bitrate.setText(f"Video Bitrate: {val} Mbps")
        self.config.save()
        self.config_changed.emit()

    def _on_v_codec_changed(self, text: str):
        self.config.video.codec = text
        self.config.save()
        self.config_changed.emit()

    def _on_a_codec_changed(self, text: str):
        self.config.audio.codec = text
        self.config.save()
        self.config_changed.emit()

    def _on_a_source_changed(self, text: str):
        self.config.audio.audio_source = text
        self.config.save()
        self.config_changed.emit()

    def _on_multitrack_toggled(self, checked: bool):
        self.config.recording.multi_track = checked
        self.config.save()
        self.config_changed.emit()

    def _on_v_buffer_changed(self, val: int):
        self.config.video.video_buffer_ms = val
        self.lbl_v_buffer.setText(f"Video Buffer: {val} ms")
        self.config.save()
        self.config_changed.emit()

    def _on_v4l2_toggled(self, checked: bool):
        self.config.video.use_v4l2 = checked
        self.config.save()
        self.config_changed.emit()

    def _on_pkg_changed(self, text: str):
        pkgs = [p.strip() for p in text.split(",") if p.strip()]
        self.config.android.compile_packages = pkgs
        self.config.save()
        self.config_changed.emit()

    def _launch_obs(self):
        obs = OBSSceneInjector()
        ok, msg = obs.launch_obs()
        self.lbl_status.setText(msg)

    def _load_v4l2(self):
        ok, msg = SystemOptimizer.load_v4l2loopback()
        self.lbl_status.setText(msg)
        if ok:
            self.chk_v4l2.setChecked(True)
