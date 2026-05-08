from PyQt6.QtWidgets import QMenu, QGraphicsOpacityEffect
from PyQt6.QtCore import Qt, QPropertyAnimation

class AnimatedMenu(QMenu):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowFlags(self.windowFlags() | Qt.WindowType.FramelessWindowHint | Qt.WindowType.NoDropShadowWindowHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setStyleSheet("QMenu { background: rgba(25,25,25,240); color: white; border: 1px solid rgba(255,255,255,30); border-radius: 12px; padding: 4px; } QMenu::item { padding: 8px 24px; border-radius: 6px; margin: 2px; } QMenu::item:selected { background: rgba(255,255,255,20); }")
        self.eff = QGraphicsOpacityEffect(self); self.setGraphicsEffect(self.eff)
        self.anim = QPropertyAnimation(self.eff, b"opacity"); self.anim.setDuration(200)
    def exec(self, pos):
        self.eff.setOpacity(0); self.anim.setStartValue(0); self.anim.setEndValue(1); self.anim.start()
        return super().exec(pos)
