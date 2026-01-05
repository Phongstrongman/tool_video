"""
DouyinVoice Pro - Video Voice Changer Tool v3.0
Main entry point
"""
import sys
import io
from pathlib import Path

# Fix Windows Unicode output FIRST (before any prints)
if sys.platform == 'win32':
    try:
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
        sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')
    except:
        pass  # Ignore if already wrapped

# Add src to path
src_path = Path(__file__).parent / "src"
sys.path.insert(0, str(src_path))

from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import Qt


def main():
    # Enable High DPI
    QApplication.setHighDpiScaleFactorRoundingPolicy(
        Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
    )

    app = QApplication(sys.argv)
    app.setApplicationName("DouyinVoice Pro")
    app.setApplicationVersion("3.0")

    # Import main window
    from src.ui.main_window import MainWindow

    # Show main window directly (no license check)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
