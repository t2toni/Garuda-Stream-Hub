import logging
import threading
from PyQt6.QtCore import Qt, QTimer, pyqtSignal, QObject
from PyQt6.QtWidgets import (
    QApplication, QFrame, QHBoxLayout, QLabel, QMainWindow, QPushButton,
    QScrollArea, QSplitter, QVBoxLayout, QWidget
)

from ..core.config import StreamConfig, PipelineState
from ..core.orchestrator import PipelineOrchestrator, TelemetrySnapshot
from .master_button import MasterActionButton
from .telemetry_hud import TelemetryHUD
from .pipeline_visualizer import PipelineVisualizer
from .overrides_drawer import OverridesDrawer
from .recording_bar import RecordingBar
from .styles import STYLESHEET

logger = logging.getLogger("MainWindow")

class BridgeSignals(QObject):
    step_updated = pyqtSignal(int, str, bool)
    state_changed = pyqtSignal(PipelineState)
    telemetry_updated = pyqtSignal(TelemetrySnapshot)

class MainWindow(QMainWindow):
    """
    Garuda Linux One-Tap Stream Pipeline Production Dashboard.
    Combines neon aesthetic, master 1-tap button, live telemetry, and developer controls.
    """
    def __init__(self, orchestrator: PipelineOrchestrator):
        super().__init__()
        self.orchestrator = orchestrator
        self.setWindowTitle("Garuda Stream Hub — One-Tap Android Ultra-Low Latency Engine")
        self.resize(1120, 720)
        self.setMinimumSize(960, 640)

        self.setStyleSheet(STYLESHEET)

        # Thread-safe Qt Signal Bridge
        self.bridge = BridgeSignals()
        self.bridge.step_updated.connect(self._on_step_updated)
        self.bridge.state_changed.connect(self._on_state_changed)
        self.bridge.telemetry_updated.connect(self._on_telemetry_updated)

        # Wire orchestrator callbacks to signal bridge
        self.orchestrator.on_step_updated = lambda s, m, ok: self.bridge.step_updated.emit(s, m, ok)
        self.orchestrator.on_state_changed = lambda st: self.bridge.state_changed.emit(st)
        self.orchestrator.on_telemetry_updated = lambda t: self.bridge.telemetry_updated.emit(t)

        self._build_ui()

    def _build_ui(self):
        central = QWidget(self)
        self.setCentralWidget(central)

        root_layout = QVBoxLayout(central)
        root_layout.setContentsMargins(20, 16, 20, 16)
        root_layout.setSpacing(14)

        # --- 1. Top Header Bar ---
        header_bar = QHBoxLayout()
        header_bar.setContentsMargins(0, 0, 0, 0)

        title_box = QVBoxLayout()
        title_box.setSpacing(2)

        lbl_title = QLabel("GARUDA STREAM HUB")
        lbl_title.setObjectName("appTitle")

        lbl_subtitle = QLabel("ULTRA-LOW LATENCY MOBILE STREAMING HUB • ARCH / GARUDA LINUX & ANDROID")
        lbl_subtitle.setObjectName("appSubtitle")

        title_box.addWidget(lbl_title)
        title_box.addWidget(lbl_subtitle)

        self.lbl_badge = QLabel("IDLE • READY FOR INITIALIZATION")
        self.lbl_badge.setStyleSheet(
            "background-color: rgba(65, 72, 104, 0.4); color: #7aa2f7; "
            "border: 1px solid rgba(122, 162, 247, 0.4); border-radius: 6px; "
            "padding: 6px 12px; font-weight: 700; font-size: 11px; letter-spacing: 0.8px;"
        )

        header_bar.addLayout(title_box)
        header_bar.addStretch()
        header_bar.addWidget(self.lbl_badge)

        root_layout.addLayout(header_bar)

        # --- 2. Main Work Area (Left: Master Button & Visualizer, Right: Telemetry HUD) ---
        body_layout = QHBoxLayout()
        body_layout.setSpacing(16)

        # Left Column: Command & Orchestration
        left_col = QVBoxLayout()
        left_col.setSpacing(14)

        # Master Button Card
        btn_card = QFrame()
        btn_card.setProperty("class", "glassCard")
        btn_card_layout = QVBoxLayout(btn_card)
        btn_card_layout.setContentsMargins(18, 20, 18, 20)
        btn_card_layout.setSpacing(8)

        btn_caption = QLabel("MASTER ACTION CONTROLLER")
        btn_caption.setStyleSheet("color: #7aa2f7; font-weight: 800; font-size: 11px; letter-spacing: 1px;")
        btn_caption.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.btn_master = MasterActionButton()
        self.btn_master.clicked.connect(self._on_master_clicked)

        btn_card_layout.addWidget(btn_caption)
        btn_card_layout.addWidget(self.btn_master, alignment=Qt.AlignmentFlag.AlignCenter)

        left_col.addWidget(btn_card)

        # Studio Multi-Track Recording Bar
        self.recording_bar = RecordingBar(self.orchestrator.config)
        self.recording_bar.record_requested.connect(self._on_record_requested)
        self.recording_bar.mic_mute_toggled.connect(self._on_mic_mute_toggled)
        left_col.addWidget(self.recording_bar)

        # Pipeline Execution Visualizer
        self.visualizer = PipelineVisualizer()
        left_col.addWidget(self.visualizer)
        left_col.addStretch()

        body_layout.addLayout(left_col, stretch=5)

        # Right Column: Telemetry Sidebar
        right_col = QVBoxLayout()
        right_col.setSpacing(14)

        self.telemetry_hud = TelemetryHUD()
        right_col.addWidget(self.telemetry_hud)
        right_col.addStretch()

        body_layout.addLayout(right_col, stretch=4)

        root_layout.addLayout(body_layout, stretch=1)

        # --- 3. Collapsible Overrides Drawer ---
        self.btn_drawer_toggle = QPushButton("▼ ADVANCED OVERRIDES & DEVELOPER TUNING")
        self.btn_drawer_toggle.setObjectName("drawerToggle")
        self.btn_drawer_toggle.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_drawer_toggle.clicked.connect(self._toggle_drawer)

        root_layout.addWidget(self.btn_drawer_toggle)

        self.overrides_drawer = OverridesDrawer(self.orchestrator.config)
        root_layout.addWidget(self.overrides_drawer)

    def _toggle_drawer(self):
        is_visible = self.overrides_drawer.isVisible()
        self.overrides_drawer.setVisible(not is_visible)
        if not is_visible:
            self.btn_drawer_toggle.setText("▲ ADVANCED OVERRIDES & DEVELOPER TUNING")
        else:
            self.btn_drawer_toggle.setText("▼ ADVANCED OVERRIDES & DEVELOPER TUNING")

    def _on_master_clicked(self):
        if self.orchestrator.state in (PipelineState.IDLE, PipelineState.ERROR):
            # Run initialization in background thread
            threading.Thread(target=self.orchestrator.initialize_pipeline, daemon=True).start()
        elif self.orchestrator.state == PipelineState.ACTIVE:
            # Teardown in background thread
            threading.Thread(target=self.orchestrator.teardown_pipeline, daemon=True).start()

    def _on_step_updated(self, step: int, msg: str, ok: bool):
        self.visualizer.update_step(step, msg, ok)

    def _on_state_changed(self, state: PipelineState):
        self.btn_master.set_pipeline_state(state)
        if state == PipelineState.IDLE:
            self.lbl_badge.setText("IDLE • READY FOR INITIALIZATION")
            self.lbl_badge.setStyleSheet(
                "background-color: rgba(65, 72, 104, 0.4); color: #7aa2f7; "
                "border: 1px solid rgba(122, 162, 247, 0.4); border-radius: 6px; padding: 6px 12px; font-weight: 700;"
            )
        elif state == PipelineState.INITIALIZING:
            self.lbl_badge.setText("INITIALIZING PIPELINE...")
            self.lbl_badge.setStyleSheet(
                "background-color: rgba(224, 175, 104, 0.2); color: #e0af68; "
                "border: 1px solid rgba(224, 175, 104, 0.6); border-radius: 6px; padding: 6px 12px; font-weight: 700;"
            )
        elif state == PipelineState.ACTIVE:
            dev_str = self.orchestrator.latest_telemetry.active_device_serial
            mode = "WI-FI 6" if self.orchestrator.latest_telemetry.is_wireless else "USB 3.2"
            self.lbl_badge.setText(f"LIVE • {mode} ({dev_str})")
            self.lbl_badge.setStyleSheet(
                "background-color: rgba(0, 255, 157, 0.2); color: #00ff9d; "
                "border: 1px solid rgba(0, 255, 157, 0.6); border-radius: 6px; padding: 6px 12px; font-weight: 700;"
            )
        elif state == PipelineState.ERROR:
            self.lbl_badge.setText("ERROR DETECTED")
            self.lbl_badge.setStyleSheet(
                "background-color: rgba(247, 118, 142, 0.2); color: #f7768e; "
                "border: 1px solid rgba(247, 118, 142, 0.6); border-radius: 6px; padding: 6px 12px; font-weight: 700;"
            )
        elif state == PipelineState.TEARING_DOWN:
            self.lbl_badge.setText("TEARING DOWN...")
            self.lbl_badge.setStyleSheet(
                "background-color: rgba(154, 165, 206, 0.2); color: #9aa5ce; "
                "border: 1px solid rgba(154, 165, 206, 0.4); border-radius: 6px; padding: 6px 12px; font-weight: 700;"
            )

    def _on_record_requested(self, start: bool):
        if start:
            threading.Thread(target=self.orchestrator.start_recording, daemon=True).start()
        else:
            threading.Thread(target=self.orchestrator.stop_recording, daemon=True).start()

    def _on_mic_mute_toggled(self, muted: bool):
        self.orchestrator.audio.set_source_mute(self.orchestrator.config.recording.mic_source, muted)

    def _on_telemetry_updated(self, snapshot: TelemetrySnapshot):
        self.telemetry_hud.update_telemetry(snapshot)
        self.recording_bar.update_telemetry(snapshot)

    def closeEvent(self, event):
        if self.orchestrator.state == PipelineState.ACTIVE:
            logger.info("Window closing, triggering pipeline teardown...")
            self.orchestrator.teardown_pipeline()
        event.accept()
