"""
Garuda Linux Neon Tokyo Night / Dracula Aesthetic Stylesheet.
Engineered for PyQt6 with rich neon accents, glassmorphic cards, and crisp typography.
"""

STYLESHEET = """
QWidget {
    background-color: #16161e;
    color: #c0caf5;
    font-family: 'JetBrains Mono', 'Fira Code', 'Inter', 'Ubuntu', sans-serif;
    font-size: 13px;
    selection-background-color: #7aa2f7;
    selection-color: #1a1b26;
}

QMainWindow {
    background-color: #16161e;
}

/* Glassmorphic Panel / Card Containers */
QFrame.glassCard {
    background-color: rgba(36, 40, 59, 0.75);
    border: 1px solid rgba(122, 162, 247, 0.25);
    border-radius: 12px;
}

QFrame.glassCard:hover {
    border: 1px solid rgba(0, 240, 255, 0.5);
}

/* Header Banner */
QLabel#appTitle {
    font-size: 20px;
    font-weight: 800;
    color: #00f0ff;
    letter-spacing: 1.5px;
}

QLabel#appSubtitle {
    font-size: 11px;
    color: #7aa2f7;
    letter-spacing: 0.5px;
}

/* Telemetry Metric Widgets */
QLabel.metricValue {
    font-size: 22px;
    font-weight: 700;
    color: #00f0ff;
}

QLabel.metricUnit {
    font-size: 11px;
    color: #565f89;
    font-weight: 600;
}

QLabel.metricTitle {
    font-size: 11px;
    font-weight: 600;
    color: #9aa5ce;
    text-transform: uppercase;
    letter-spacing: 0.8px;
}

/* Buttons */
QPushButton {
    background-color: #24283b;
    border: 1px solid #414868;
    border-radius: 8px;
    padding: 8px 16px;
    color: #c0caf5;
    font-weight: 600;
}

QPushButton:hover {
    background-color: #2f354f;
    border: 1px solid #7aa2f7;
    color: #00f0ff;
}

QPushButton:pressed {
    background-color: #1f2335;
}

/* Collapsible Drawer Toggle */
QPushButton#drawerToggle {
    background-color: rgba(36, 40, 59, 0.5);
    border: 1px dashed rgba(122, 162, 247, 0.4);
    border-radius: 8px;
    padding: 6px;
    font-size: 12px;
    color: #7aa2f7;
}

QPushButton#drawerToggle:hover {
    background-color: rgba(122, 162, 247, 0.15);
    border: 1px solid #00f0ff;
    color: #00f0ff;
}

/* Form Controls in Overrides Panel */
QComboBox {
    background-color: #1f2335;
    border: 1px solid #414868;
    border-radius: 6px;
    padding: 5px 10px;
    color: #c0caf5;
}

QComboBox:hover {
    border: 1px solid #7aa2f7;
}

QComboBox::drop-down {
    border: none;
    width: 20px;
}

QLineEdit {
    background-color: #1f2335;
    border: 1px solid #414868;
    border-radius: 6px;
    padding: 6px 10px;
    color: #c0caf5;
}

QLineEdit:focus {
    border: 1px solid #00f0ff;
}

QSlider::groove:horizontal {
    border: none;
    height: 6px;
    background: #1f2335;
    border-radius: 3px;
}

QSlider::sub-page:horizontal {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #7aa2f7, stop:1 #00f0ff);
    border-radius: 3px;
}

QSlider::handle:horizontal {
    background: #00f0ff;
    border: 2px solid #16161e;
    width: 14px;
    margin-top: -4px;
    margin-bottom: -4px;
    border-radius: 7px;
}

QSlider::handle:horizontal:hover {
    background: #ffffff;
}

/* Scroll Area */
QScrollArea {
    border: none;
    background-color: transparent;
}

QScrollBar:vertical {
    border: none;
    background: #16161e;
    width: 6px;
    margin: 0px;
}

QScrollBar::handle:vertical {
    background: #414868;
    min-height: 20px;
    border-radius: 3px;
}

QScrollBar::handle:vertical:hover {
    background: #7aa2f7;
}

QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
    height: 0px;
}
"""
