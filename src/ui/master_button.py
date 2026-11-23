from PyQt6.QtCore import Qt, pyqtProperty, pyqtSignal, QTimer
from PyQt6.QtGui import QColor, QFont, QPainter, QLinearGradient, QPen, QBrush
from PyQt6.QtWidgets import QPushButton

from ..core.config import PipelineState

class MasterActionButton(QPushButton):
    """
    Massive, glowing center action button tailored for Garuda Linux aesthetic.
    Supports dynamic glowing animations and multi-state visual transitions.
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumSize(380, 96)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self._state = PipelineState.IDLE
        self._glow_alpha = 180
        self._pulse_direction = 1

        # Pulse timer for breathing neon animation
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._pulse_animation)
        self._timer.start(35) # ~30 FPS pulse

        self._update_text()

    def _pulse_animation(self):
        if self._state == PipelineState.INITIALIZING:
            step = 6
        elif self._state == PipelineState.ACTIVE:
            step = 3
        else:
            step = 2

        self._glow_alpha += step * self._pulse_direction
        if self._glow_alpha >= 240:
            self._glow_alpha = 240
            self._pulse_direction = -1
        elif self._glow_alpha <= 100:
            self._glow_alpha = 100
            self._pulse_direction = 1
        self.update()

    def set_pipeline_state(self, state: PipelineState):
        self._state = state
        self._update_text()
        self.update()

    def _update_text(self):
        if self._state == PipelineState.IDLE:
            self.setText("INITIALIZE STREAM PIPELINE")
        elif self._state == PipelineState.INITIALIZING:
            self.setText("INITIALIZING HARDWARE LINK...")
        elif self._state == PipelineState.ACTIVE:
            self.setText("STREAM PIPELINE ACTIVE\n[ CLICK TO TEARDOWN ]")
        elif self._state == PipelineState.ERROR:
            self.setText("PIPELINE FAILED\n[ CLICK TO RETRY ]")
        elif self._state == PipelineState.TEARING_DOWN:
            self.setText("TEARING DOWN PIPELINE...")

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        rect = self.rect().adjusted(4, 4, -4, -4)
        radius = 16.0

        # Colors based on state
        if self._state == PipelineState.IDLE:
            primary_neon = QColor(0, 240, 255) # Electric Cyan
            secondary_neon = QColor(122, 162, 247) # Tokyo Night Blue
            bg_base = QColor(26, 27, 38, 230)
        elif self._state == PipelineState.INITIALIZING:
            primary_neon = QColor(224, 175, 104) # Amber
            secondary_neon = QColor(255, 158, 100) # Orange
            bg_base = QColor(36, 40, 59, 230)
        elif self._state == PipelineState.ACTIVE:
            primary_neon = QColor(0, 255, 157) # Emerald Green
            secondary_neon = QColor(115, 218, 202) # Soft Aqua
            bg_base = QColor(20, 36, 32, 240)
        elif self._state == PipelineState.ERROR:
            primary_neon = QColor(247, 118, 142) # Crimson Rose
            secondary_neon = QColor(255, 0, 127) # Neon Red
            bg_base = QColor(40, 20, 28, 240)
        else: # Tearing down
            primary_neon = QColor(154, 165, 206)
            secondary_neon = QColor(65, 72, 104)
            bg_base = QColor(26, 27, 38, 230)

        # 1. Outer Glow Shadow
        glow_color = QColor(primary_neon.red(), primary_neon.green(), primary_neon.blue(), int(self._glow_alpha * 0.45))
        glow_pen = QPen(glow_color, 6.0)
        painter.setPen(glow_pen)
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawRoundedRect(rect.adjusted(2, 2, -2, -2), radius, radius)

        # 2. Main Button Background
        bg_gradient = QLinearGradient(0, 0, 0, rect.height())
        bg_gradient.setColorAt(0.0, bg_base.lighter(115))
        bg_gradient.setColorAt(1.0, bg_base)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QBrush(bg_gradient))
        painter.drawRoundedRect(rect, radius, radius)

        # 3. Vivid Border Ring
        border_gradient = QLinearGradient(0, 0, rect.width(), rect.height())
        border_gradient.setColorAt(0.0, primary_neon)
        border_gradient.setColorAt(1.0, secondary_neon)
        border_pen = QPen(QBrush(border_gradient), 2.2)
        painter.setPen(border_pen)
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawRoundedRect(rect, radius, radius)

        # 4. Text Rendering
        painter.setPen(QColor(255, 255, 255))
        font = QFont("JetBrains Mono", 13, QFont.Weight.Bold)
        font.setLetterSpacing(QFont.SpacingType.AbsoluteSpacing, 1.2)
        painter.setFont(font)
        painter.drawText(rect, Qt.AlignmentFlag.AlignCenter, self.text())
