from PyQt6.QtWidgets import QMenu, QGraphicsOpacityEffect, QPushButton
from PyQt6.QtCore import Qt, QPropertyAnimation, pyqtSignal, QPoint

class AnimatedMenu(QMenu):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowFlags(self.windowFlags() | Qt.WindowType.FramelessWindowHint | Qt.WindowType.NoDropShadowWindowHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setStyleSheet("QMenu { background: rgba(25,25,25,240); color: white; border: 1px solid rgba(255,255,255,30); border-radius: 12px; padding: 4px; } QMenu::item { padding: 8px 24px; border-radius: 6px; margin: 2px; } QMenu::item:selected { background: rgba(255,255,255,20); }")
        
    def exec(self, pos):
        # Create effect on the fly to avoid deletion issues
        eff = QGraphicsOpacityEffect(self); self.setGraphicsEffect(eff)
        anim = QPropertyAnimation(eff, b"opacity")
        anim.setDuration(200); anim.setStartValue(0); anim.setEndValue(1)
        eff.setOpacity(0); anim.start()
        # Keep references alive during animation
        self._anim = anim; self._eff = eff
        return super().exec(pos)

class DropdownButton(QPushButton):
    valueChanged = pyqtSignal(str)
    def __init__(self, current_text, items, parent=None):
        super().__init__(current_text, parent)
        self.current_text = current_text; self.items = items
        self.setMinimumHeight(32); self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setStyleSheet("""QPushButton { 
            background: rgba(255,255,255,8); border: 1px solid rgba(255,255,255,15); border-radius: 6px; 
            color: #e0e0e0; font-size: 12px; font-weight: 500; padding: 0 30px 0 12px; text-align: left; 
        } QPushButton:hover { background: rgba(255,255,255,14); border: 1px solid rgba(0,240,255,40); color: white; }""")
        self.menu = AnimatedMenu(self)
        self.menu.aboutToHide.connect(self._mark_menu_closing)
        self.clicked.connect(self.show_menu)
        self._last_close_time = 0
        self._refresh_menu()

    def _mark_menu_closing(self):
        import time; self._last_close_time = time.time()

    def _refresh_menu(self):
        self.menu.clear()
        for i in self.items:
            a = self.menu.addAction(i)
            a.triggered.connect(lambda _, val=i: self.setTextValue(val))

    def setTextValue(self, v):
        self.current_text = v; self.setText(v); self.valueChanged.emit(v)

    def show_menu(self):
        import time
        if time.time() - self._last_close_time < 0.15: return
        self._refresh_menu()
        self.menu.exec(self.mapToGlobal(QPoint(0, self.height() + 5)))

    def paintEvent(self, e):
        super().paintEvent(e)
        from PyQt6.QtGui import QPainter, QColor, QFont
        p = QPainter(self); p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.setPen(QColor(130, 140, 150)); p.setFont(QFont("Segoe UI", 9))
        p.drawText(self.width() - 24, 0, 20, self.height(), Qt.AlignmentFlag.AlignCenter, "▾")


class AnimatedButton(QPushButton):
    def __init__(self, text, color="#50FA7B", parent=None):
        super().__init__(text, parent)
        self.setFixedHeight(35); self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setStyleSheet(f"QPushButton {{ background: rgba(255,255,255,10); color: {color}; border: 1px solid {color}; border-radius: 8px; font-weight: bold; }} QPushButton:hover {{ background: {color}; color: #141414; }}")
