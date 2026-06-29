import sys
import ctypes
from PyQt6.QtWidgets import QApplication, QWidget, QVBoxLayout, QPushButton, QLabel
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor, QPainter, QFont

class MARGINS(ctypes.Structure):
    _fields_ = [
        ("cxLeftWidth", ctypes.c_int),
        ("cxRightWidth", ctypes.c_int),
        ("cyTopHeight", ctypes.c_int),
        ("cyBottomHeight", ctypes.c_int)
    ]

class ACCENTPOLICY(ctypes.Structure):
    _fields_ = [
        ("AccentState", ctypes.c_uint),
        ("AccentFlags", ctypes.c_uint),
        ("GradientColor", ctypes.c_uint),
        ("AnimationId", ctypes.c_uint)
    ]

class WINDOWCOMPOSITIONATTRIBDATA(ctypes.Structure):
    _fields_ = [
        ("Attribute", ctypes.c_int),
        ("Data", ctypes.POINTER(ACCENTPOLICY)),
        ("SizeOfData", ctypes.c_uint)
    ]

class FlagTestWindow(QWidget):
    def __init__(self, title, x, y, flags, color):
        super().__init__()
        self.setWindowTitle(title)
        self.setGeometry(x, y, 400, 300)
        
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.Tool | Qt.WindowType.WindowStaysOnTopHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        
        self.flags = flags
        self.color = color
        
        layout = QVBoxLayout()
        label = QLabel(
            f"<h3 style='color: white; font-family: sans-serif; text-align: center;'>"
            f"{title}<br><br>"
            f"<span style='font-size: 11px; font-weight: normal; color: #00f0ff;'>"
            f"Flags: {hex(flags)}<br>Color: {hex(color)}</span></h3>"
        )
        label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(label)
        self.setLayout(layout)
        
        self.old_pos = None

    def paintEvent(self, event):
        p = QPainter(self)
        p.fillRect(self.rect(), QColor(0, 0, 0, 0))

    def mousePressEvent(self, event):
        self.old_pos = event.globalPosition().toPoint()

    def mouseMoveEvent(self, event):
        if self.old_pos:
            delta = event.globalPosition().toPoint() - self.old_pos
            self.move(self.x() + delta.x(), self.y() + delta.y())
            self.old_pos = event.globalPosition().toPoint()

    def mouseReleaseEvent(self, event):
        self.old_pos = None

    def showEvent(self, event):
        super().showEvent(event)
        self.apply_blur_effect()

    def apply_blur_effect(self):
        hwnd = int(self.winId())
        dwmapi = ctypes.windll.dwmapi
        user32 = ctypes.windll.user32
        
        # 1. Extend the frame into the client area
        margins = MARGINS(-1, -1, -1, -1)
        dwmapi.DwmExtendFrameIntoClientArea(hwnd, ctypes.byref(margins))
        
        # 2. Call SWCA Acrylic (State 4) with test flags
        policy = ACCENTPOLICY()
        policy.AccentState = 4 # Acrylic
        policy.AccentFlags = self.flags
        policy.GradientColor = self.color
        policy.AnimationId = 0
        
        data = WINDOWCOMPOSITIONATTRIBDATA()
        data.Attribute = 19
        data.Data = ctypes.pointer(policy)
        data.SizeOfData = ctypes.sizeof(policy)
        user32.SetWindowCompositionAttribute(hwnd, ctypes.pointer(data))

def main():
    app = QApplication(sys.argv)
    
    # We will test a very transparent color (alpha = 1, i.e., 0x01000000)
    # and a semi-transparent color (alpha = 0x30, i.e., 0x30FFFFFF)
    transparent_color = 0x01000000
    tinted_color = 0x30555555
    
    # 4 windows to test different flags
    w1 = FlagTestWindow("1. AccentFlags = 2\n(ACCENT_ENABLE_TRANSPARENTGRADIENT)", 100, 100, 2, transparent_color)
    w1.show()
    
    w2 = FlagTestWindow("2. AccentFlags = 0x1E0\n(qframelesswindow flags)", 550, 100, 0x1E0, transparent_color)
    w2.show()
    
    w3 = FlagTestWindow("3. AccentFlags = 0x1E0\n(With Tinted Color)", 100, 450, 0x1E0, tinted_color)
    w3.show()
    
    w4 = FlagTestWindow("4. AccentFlags = 0\n(No Flags)", 550, 450, 0, transparent_color)
    w4.show()

    # Controls window
    cw = QWidget()
    cw.setWindowFlags(Qt.WindowType.WindowStaysOnTopHint)
    cw.setWindowTitle("Controls")
    cw.setGeometry(500, 800, 250, 80)
    cl = QVBoxLayout()
    btn = QPushButton("Close All Flag Windows")
    btn.clicked.connect(app.quit)
    cl.addWidget(btn)
    cw.setLayout(cl)
    cw.show()

    sys.exit(app.exec())

if __name__ == "__main__":
    main()
