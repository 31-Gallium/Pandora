import os
from PyQt6.QtCore import QRectF, Qt
from PyQt6.QtGui import QFont, QColor
from .base import BaseHubModule

class DefaultLogoHub(BaseHubModule):
    """Displays the Pandora logo in the dead zone center."""
    def __init__(self, manager):
        super().__init__(manager)
        self.logo_renderer = None
        logo_path = os.path.join(os.getcwd(), "assets", "Pandora.svg")
        if os.path.exists(logo_path):
            from PyQt6.QtSvg import QSvgRenderer
            self.logo_renderer = QSvgRenderer(logo_path)

    def draw(self, p, cx, cy, inner_radius):
        logo_size = 55
        logo_rect = QRectF(cx - logo_size/2, cy - logo_size/2, logo_size, logo_size)
        if self.logo_renderer:
            self.logo_renderer.render(p, logo_rect)
        else:
            p.setPen(QColor(255, 255, 255, 80))
            p.setFont(QFont("Segoe UI Variable Display", 12, QFont.Weight.Bold))
            p.drawText(QRectF(cx-100, cy-15, 200, 30), Qt.AlignmentFlag.AlignCenter, "PANDORA")
