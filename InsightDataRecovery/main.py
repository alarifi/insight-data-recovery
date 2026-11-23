"""
Insight Data Recovery Studio Pro - Application Entry Point
"""
import os
import sys
import ctypes

# Enable high-DPI scaling
os.environ["QT_AUTO_SCREEN_SCALE_FACTOR"] = "1"

# Ensure root package path is on sys.path
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QIcon

from ui.main_window import MainWindow
from ui.theme import get_asset_path


def main():
    # Set Windows taskbar App ID
    try:
        app_id = "insight.recovery.studio.pro.1.0"
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(app_id)
    except Exception:
        pass

    app = QApplication(sys.argv)
    app.setApplicationName("Insight Data Recovery Studio Pro")
    app.setOrganizationName("Insight Software")

    # Set Application Icon
    icon_path = get_asset_path("app_icon.ico")
    if os.path.exists(icon_path):
        app.setWindowIcon(QIcon(icon_path))

    window = MainWindow()
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()

