import sys
import time
from PyQt6.QtWidgets import QApplication, QWidget
from PyQt6.QtGui import QPainter, QColor
from PyQt6.QtCore import Qt, QTimer

from BlurWindow.blurWindow import GlobalBlur

class BlurTest(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.Tool)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setGeometry(100, 100, 800, 600)
        GlobalBlur(int(self.winId()), Acrylic=True, hexColor='#00000000', Dark=True)
        
        self.fade = 0.0
        self.timer = QTimer()
        self.timer.timeout.connect(self.animate)
        self.timer.start(16)
        
    def animate(self):
        self.fade += 0.02
        if self.fade > 1.0:
            self.fade = 1.0
            self.timer.stop()
        self.update()
        
    def paintEvent(self, e):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        # This enables the blur by drawing something with alpha > 0
        p.fillRect(self.rect(), QColor(0, 0, 0, int(1 + 100 * self.fade)))
        
        p.setOpacity(self.fade)
        p.setBrush(QColor(255, 0, 0))
        p.drawRect(300, 200, 200, 200)

app = QApplication(sys.argv)
w = BlurTest()
w.show()
# close after 2 seconds
QTimer.singleShot(2000, app.quit)
app.exec()
