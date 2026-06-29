import sys
from PyQt6.QtWidgets import QApplication, QWidget
from PyQt6.QtGui import QWindow
from PyQt6.QtCore import Qt
import ctypes

app = QApplication(sys.argv)
win = QWidget()
win.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.Tool)
win.resize(200, 200)
win.setStyleSheet("background: red;")
win.show() # Must show before getting windowHandle()

# Try setting transient parent
electron_hwnd = ctypes.windll.user32.FindWindowW(None, "Pandora Dashboard \u2014 UI Prototype")
if electron_hwnd:
    print(f"Found Electron window: {electron_hwnd}")
    foreign_win = QWindow.fromWinId(electron_hwnd)
    win.windowHandle().setTransientParent(foreign_win)
    print("Transient parent set successfully!")
else:
    print("Electron window not found.")

sys.exit(app.exec())
