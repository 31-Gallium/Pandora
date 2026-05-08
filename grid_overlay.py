from PyQt6.QtWidgets import QWidget, QApplication
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QPainter, QColor
from utils import WinAPI

class GridOverlay(QWidget):
    def __init__(self, cfg):
        super().__init__()
        self.cfg = cfg
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.Tool | Qt.WindowType.WindowTransparentForInput | Qt.WindowType.WindowStaysOnBottomHint)
        
        # Cover all screens
        geom = QApplication.primaryScreen().geometry()
        for screen in QApplication.screens():
            geom = geom.united(screen.geometry())
        self.setGeometry(geom)
        
        self.is_visible = False
        
    def showEvent(self, e):
        # Apply WorkerW trick slightly after show to pin it behind everything
        __import__('PyQt6.QtCore').QtCore.QTimer.singleShot(50, lambda: WinAPI.pin_to_workerw(self.winId()))
        super().showEvent(e)
        
    def toggle(self):
        self.is_visible = not self.is_visible
        if self.is_visible:
            self.show()
        else:
            self.hide()
        self.update()
        return self.is_visible
        
    def paintEvent(self, e):
        if not self.is_visible: return
        grid_size = self.cfg.get('global_settings', {}).get('grid_size', 110)
        if grid_size <= 0: return
        
        folder_size = self.cfg.get('global_settings', {}).get('folder_size', 80)
        edge_padding = self.cfg.get('global_settings', {}).get('edge_padding', 0)
        margin = int(folder_size / 2 + edge_padding)
        
        p = QPainter(self)
        geom = self.geometry()
        
        for screen in QApplication.screens():
            scr_geom = screen.availableGeometry()
            safe_rect = scr_geom.adjusted(margin, margin, -margin, -margin)
            
            # Map safe_rect to GridOverlay's coordinate system
            local_safe_rect = safe_rect.translated(-geom.x(), -geom.y())
            p.setClipRect(local_safe_rect)
            
            scr_c = scr_geom.center()
            local_cx = scr_c.x() - geom.x()
            local_cy = scr_c.y() - geom.y()
            
            offset_x = int(local_cx % grid_size)
            offset_y = int(local_cy % grid_size)
            
            p.setPen(QColor(255, 255, 255, 20)) # Faint white lines
            for x in range(offset_x, self.width(), grid_size):
                p.drawLine(x, 0, x, self.height())
            for y in range(offset_y, self.height(), grid_size):
                p.drawLine(0, y, self.width(), y)
                
            p.setPen(QColor(255, 255, 255, 60))
            cross_size = 4
            for x in range(offset_x, self.width(), grid_size):
                for y in range(offset_y, self.height(), grid_size):
                    p.drawLine(x - cross_size, y, x + cross_size, y)
                    p.drawLine(x, y - cross_size, x, y + cross_size)
            
            p.setClipping(False)

