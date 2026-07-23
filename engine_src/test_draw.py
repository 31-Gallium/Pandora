from PySide6.QtGui import QImage, QPainter, QPixmap
import ctypes
from PySide6.QtWidgets import QApplication

app = QApplication([])

buf_array = (ctypes.c_uint8 * (512 * 512 * 4))()
mem_view = memoryview(buf_array)
qimg = QImage(mem_view, 512, 512, QImage.Format.Format_ARGB32_Premultiplied)
print("isNull:", qimg.isNull())

pix = QPixmap(512, 512)
p = QPainter(pix)
p.drawImage(0, 0, qimg)
p.end()
print("Drawn successfully")
