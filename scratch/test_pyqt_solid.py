import sys
from PyQt6.QtWidgets import QApplication, QWidget
from PyQt6.QtCore import Qt

app = QApplication(sys.argv)
w = QWidget()
w.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.Tool | Qt.WindowType.WindowStaysOnTopHint)
# w.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground) # Removed!
w.setStyleSheet("background-color: rgb(0, 255, 0);")
w.setGeometry(985, 315, 412, 520)
w.show()

import threading
def save_ss():
    import time
    time.sleep(1)
    from PIL import ImageGrab
    ImageGrab.grab().save('test_ss_solid.png')
    app.quit()
    
threading.Thread(target=save_ss).start()
sys.exit(app.exec())
