from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QFrame, QHBoxLayout, QLabel, QVBoxLayout, QWidget
)

STEP_LABELS = {
    1: "DEPENDENCIES",
    2: "DEVICE HANDSHAKE",
    3: "SOUND ENGINE",
    4: "VIDEO MIRROR",
    5: "OBS STUDIO HOOK"
}

class PipelineStepNode(QFrame):
    def __init__(self, step_num: int, label: str, parent=None):
        super().__init__(parent)
        self.step_num = step_num
        self.setProperty("class", "glassCard")
        self.setFixedHeight(54)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(12, 6, 12, 6)
        layout.setSpacing(10)

        # Status indicator circle
        self.lbl_icon = QLabel("●")
        self.lbl_icon.setStyleSheet("color: #565f89; font-size: 16px;")
        self.lbl_icon.setFixedWidth(20)

        info_layout = QVBoxLayout()
        info_layout.setContentsMargins(0, 0, 0, 0)
        info_layout.setSpacing(2)

        self.lbl_title = QLabel(f"STEP {step_num}: {label}")
        self.lbl_title.setStyleSheet("font-weight: 700; font-size: 11px; color: #7aa2f7;")

        self.lbl_status = QLabel("Pending initialization")
        self.lbl_status.setStyleSheet("font-size: 10px; color: #565f89;")

        info_layout.addWidget(self.lbl_title)
        info_layout.addWidget(self.lbl_status)

        layout.addWidget(self.lbl_icon)
        layout.addLayout(info_layout)
        layout.addStretch()

    def set_status(self, text: str, success: bool = True, in_progress: bool = False):
        self.lbl_status.setText(text)
        if in_progress:
            self.lbl_icon.setText("◐")
            self.lbl_icon.setStyleSheet("color: #e0af68; font-size: 16px;")
            self.lbl_title.setStyleSheet("font-weight: 700; font-size: 11px; color: #e0af68;")
        elif success and text != "Pending":
            self.lbl_icon.setText("✔")
            self.lbl_icon.setStyleSheet("color: #00ff9d; font-size: 16px;")
            self.lbl_title.setStyleSheet("font-weight: 700; font-size: 11px; color: #00ff9d;")
            self.lbl_status.setStyleSheet("font-size: 10px; color: #c0caf5;")
        elif not success:
            self.lbl_icon.setText("✖")
            self.lbl_icon.setStyleSheet("color: #f7768e; font-size: 16px;")
            self.lbl_title.setStyleSheet("font-weight: 700; font-size: 11px; color: #f7768e;")
            self.lbl_status.setStyleSheet("font-size: 10px; color: #f7768e;")
        else:
            self.lbl_icon.setText("●")
            self.lbl_icon.setStyleSheet("color: #565f89; font-size: 16px;")
            self.lbl_title.setStyleSheet("font-weight: 700; font-size: 11px; color: #7aa2f7;")
            self.lbl_status.setStyleSheet("font-size: 10px; color: #565f89;")

class PipelineVisualizer(QWidget):
    """
    Displays real-time execution of the 5 parallel/sequential pipeline phases.
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(6)

        header = QLabel("PIPELINE EXECUTION NODES")
        header.setStyleSheet("color: #7aa2f7; font-weight: 800; font-size: 11px; letter-spacing: 1px;")
        layout.addWidget(header)

        self.nodes = {}
        for num, label in STEP_LABELS.items():
            node = PipelineStepNode(num, label, self)
            self.nodes[num] = node
            layout.addWidget(node)

    def update_step(self, step_num: int, message: str, success: bool = True):
        if step_num in self.nodes:
            in_prog = "..." in message or "Scanning" in message or "Launching" in message or "Provisioning" in message
            self.nodes[step_num].set_status(message, success=success, in_progress=in_prog)

    def reset_all(self):
        for node in self.nodes.values():
            node.set_status("Pending", success=True)
