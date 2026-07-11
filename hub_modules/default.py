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
        is_light = getattr(self.manager.halo, 'is_light', False)
        
        if self.logo_renderer:
            if is_light:
                from PyQt6.QtGui import QPixmap, QPainter, QColor
                from PyQt6.QtCore import Qt
                pm = QPixmap(int(logo_size * 2)) # Double resolution for sharpness
                pm.fill(Qt.GlobalColor.transparent)
                
                tmp_p = QPainter(pm)
                tmp_p.setRenderHint(QPainter.RenderHint.Antialiasing)
                self.logo_renderer.render(tmp_p, QRectF(0, 0, pm.width(), pm.height()))
                tmp_p.setCompositionMode(QPainter.CompositionMode.CompositionMode_SourceIn)
                tmp_p.fillRect(pm.rect(), QColor(36, 41, 47, 180))
                tmp_p.end()
                
                pm.setDevicePixelRatio(2.0)
                p.drawPixmap(int(cx - logo_size/2), int(cy - logo_size/2), pm)
            else:
                self.logo_renderer.render(p, logo_rect)
        else:
            p.setPen(QColor(36, 41, 47, 140) if is_light else QColor(255, 255, 255, 80))
            p.setFont(QFont("Segoe UI Variable Display", 12, QFont.Weight.Bold))
            p.drawText(QRectF(cx-100, cy-15, 200, 30), Qt.AlignmentFlag.AlignCenter, "PANDORA")
