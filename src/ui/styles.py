"""
Dark theme styles cho PyQt6
"""

DARK_STYLE = """
QMainWindow, QWidget {
    background-color: #121212;
    color: #e0e0e0;
    font-family: 'Segoe UI', sans-serif;
    font-size: 13px;
}

QGroupBox {
    font-weight: bold;
    border: 1px solid #3d3d3d;
    border-radius: 8px;
    margin-top: 10px;
    padding-top: 15px;
}

QGroupBox::title {
    subcontrol-origin: margin;
    left: 10px;
    padding: 0 5px;
    color: #00d4ff;
}

QLineEdit, QTextEdit, QComboBox, QSpinBox {
    background-color: #1e1e1e;
    border: 1px solid #3d3d3d;
    border-radius: 5px;
    padding: 8px;
    color: #e0e0e0;
}

QLineEdit:focus, QTextEdit:focus, QComboBox:focus {
    border-color: #0d6efd;
}

QPushButton {
    background-color: #0d6efd;
    color: white;
    border: none;
    border-radius: 5px;
    padding: 10px 20px;
    font-weight: bold;
}

QPushButton:hover {
    background-color: #0b5ed7;
}

QPushButton:pressed {
    background-color: #0a58ca;
}

QPushButton:disabled {
    background-color: #555555;
    color: #888888;
}

QProgressBar {
    border: none;
    border-radius: 5px;
    background-color: #2d2d2d;
    height: 10px;
    text-align: center;
}

QProgressBar::chunk {
    background-color: #0d6efd;
    border-radius: 5px;
}

QCheckBox {
    spacing: 8px;
}

QCheckBox::indicator {
    width: 18px;
    height: 18px;
    border-radius: 3px;
    border: 2px solid #3d3d3d;
    background-color: #1e1e1e;
}

QCheckBox::indicator:checked {
    background-color: #0d6efd;
    border-color: #0d6efd;
}

QSlider::groove:horizontal {
    border: none;
    height: 6px;
    background: #2d2d2d;
    border-radius: 3px;
}

QSlider::handle:horizontal {
    background: #0d6efd;
    width: 16px;
    margin: -5px 0;
    border-radius: 8px;
}

QSlider::sub-page:horizontal {
    background: #0d6efd;
    border-radius: 3px;
}

QComboBox::drop-down {
    border: none;
    width: 30px;
}

QComboBox::down-arrow {
    width: 12px;
    height: 12px;
}

QComboBox QAbstractItemView {
    background-color: #1e1e1e;
    border: 1px solid #3d3d3d;
    selection-background-color: #0d6efd;
}

QTabWidget::pane {
    border: 1px solid #3d3d3d;
    border-radius: 5px;
    background-color: #1a1a1a;
}

QTabBar::tab {
    background-color: #2d2d2d;
    color: #888888;
    padding: 10px 20px;
    margin-right: 5px;
    border-top-left-radius: 5px;
    border-top-right-radius: 5px;
}

QTabBar::tab:selected {
    background-color: #0d6efd;
    color: white;
}

QTabBar::tab:hover:!selected {
    background-color: #3d3d3d;
}

QScrollBar:vertical {
    background-color: #1e1e1e;
    width: 12px;
    border-radius: 6px;
}

QScrollBar::handle:vertical {
    background-color: #3d3d3d;
    border-radius: 6px;
    min-height: 30px;
}

QScrollBar::handle:vertical:hover {
    background-color: #4d4d4d;
}

QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
    height: 0px;
}

QMessageBox {
    background-color: #1e1e1e;
}

QMessageBox QLabel {
    color: #e0e0e0;
}

QMessageBox QPushButton {
    min-width: 80px;
}

QToolTip {
    background-color: #2d2d2d;
    color: #e0e0e0;
    border: 1px solid #3d3d3d;
    border-radius: 3px;
    padding: 5px;
}
"""
