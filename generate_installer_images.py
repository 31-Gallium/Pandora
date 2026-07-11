from PyQt6.QtWidgets import QApplication
from PyQt6.QtSvg import QSvgRenderer
from PyQt6.QtGui import QImage, QPainter, QColor
from PyQt6.QtCore import Qt, QRectF
import sys
import os

app = QApplication(sys.argv)
renderer = QSvgRenderer("assets/Pandora.svg")

def create_image(filename, width, height, bg_color, padding=0):
    img = QImage(width, height, QImage.Format.Format_RGB32)
    img.fill(QColor(bg_color))
    
    painter = QPainter(img)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    
    # Calculate rect with padding to keep aspect ratio centered
    # SVGs are square for Pandora.svg
    size = min(width, height) - (padding * 2)
    x = (width - size) / 2
    y = (height - size) / 2
    rect = QRectF(x, y, size, size)
    
    renderer.render(painter, rect)
    painter.end()
    
    img.save(filename, "BMP")
    print(f"Saved {filename}")

# Create Wizard Image (Side banner) - 164x314
create_image("wizard_image.bmp", 164, 314, "#1E1E1E", padding=20)

# Create Wizard Small Image (Top right logo) - 55x55
create_image("wizard_small.bmp", 55, 55, "#1E1E1E", padding=5)
