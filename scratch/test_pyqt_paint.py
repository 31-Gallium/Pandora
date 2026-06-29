import sys
from PyQt6.QtWidgets import QApplication, QWidget
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QPainter, QColor

class TestWin(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.Tool | Qt.WindowType.WindowStaysOnTopHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setGeometry(985, 315, 412, 520)
        
    def paintEvent(self, event):
        painter = QPainter(self)
        painter.fillRect(self.rect(), QColor(255, 0, 0, 128))

app = QApplication(sys.argv)
w = TestWin()
w.show()

import threading
def save_ss():
    import time
    time.sleep(1)
    from PIL import ImageGrab
    ImageGrab.grab().save('test_ss_paint.png')
    app.quit()
    
threading.Thread(target=save_ss).start()
sys.exit(app.exec())
