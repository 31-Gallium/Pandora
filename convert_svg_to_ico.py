from PyQt6.QtWidgets import QApplication
from PyQt6.QtSvg import QSvgRenderer
from PyQt6.QtGui import QImage, QPainter
from PyQt6.QtCore import Qt, QRectF
import sys

app = QApplication(sys.argv)
renderer = QSvgRenderer("assets/Pandora.svg")

img = QImage(256, 256, QImage.Format.Format_ARGB32)
img.fill(Qt.GlobalColor.transparent)

painter = QPainter(img)
painter.setRenderHint(QPainter.RenderHint.Antialiasing)
renderer.render(painter, QRectF(img.rect()))
painter.end()

img.save("pandora.png")
print("Saved pandora.png")
