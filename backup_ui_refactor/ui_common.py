from PyQt6.QtWidgets import QMenu, QGraphicsOpacityEffect, QPushButton, QDialog, QVBoxLayout, QLabel, QLineEdit, QHBoxLayout, QLayout, QSizePolicy
from PyQt6.QtCore import Qt, QPropertyAnimation, pyqtSignal, QPoint, QRect, QSize

class AnimatedMenu(QMenu):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowFlags(self.windowFlags() | Qt.WindowType.FramelessWindowHint | Qt.WindowType.NoDropShadowWindowHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setStyleSheet("QMenu { background: rgba(25,25,25,240); color: white; border: 1px solid rgba(255,255,255,30); border-radius: 12px; padding: 4px; } QMenu::item { padding: 8px 16px; border-radius: 6px; margin: 2px 4px; } QMenu::item:selected { background: rgba(255,255,255,20); }")

    def exec(self, pos):        # Create effect on the fly to avoid deletion issues
        eff = QGraphicsOpacityEffect(self); self.setGraphicsEffect(eff)
        anim = QPropertyAnimation(eff, b"opacity")
        anim.setDuration(200); anim.setStartValue(0); anim.setEndValue(1)
        eff.setOpacity(0); anim.start()
        # Keep references alive during animation
        self._anim = anim; self._eff = eff
        return super().exec(pos)

class DropdownButton(QPushButton):
    valueChanged = pyqtSignal(str)
    def __init__(self, current_val, items, parent=None):
        super().__init__(parent)
        self.setObjectName("DropdownButton")
        self.is_dict = isinstance(items, dict)
        self.items = items
        self.current_val = current_val

        self.setMinimumHeight(36); self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.menu = AnimatedMenu(self)
        self.menu.aboutToHide.connect(self._mark_menu_closing)
        self.clicked.connect(self.show_menu)
        self._last_close_time = 0
        self._refresh_menu()
        self._update_text()
        
        # Apply theme-aware styling immediately at creation time
        from ui_dashboard_common import get_theme_colors
        colors = get_theme_colors()
        theme = colors['theme']
        bg = colors['button_bg']
        border = colors['button_border']
        text_color = colors['text_primary']
        accent = colors['accent_color']
        self.update_theme_style(theme, bg, border, text_color, accent)

    def update_theme_style(self, theme, bg, border, text_color, accent):
        self.setStyleSheet(f"""
            QPushButton {{
                background: {bg};
                border: {border};
                border-radius: 6px;
                color: {text_color};
                font-size: 13px;
                font-weight: 500;
                padding: 0 30px 0 12px;
                text-align: left;
            }}
            QPushButton:hover {{
                background: {bg};
                border: 1px solid {accent};
                color: {text_color};
            }}
        """)
        if theme == 'Light':
            self.menu.setStyleSheet(f"""
                QMenu {{
                    background: #ffffff;
                    color: #1c1d22;
                    border: 1px solid #c8cbd0;
                    border-radius: 12px;
                    padding: 4px;
                }}
                QMenu::item {{
                    padding: 8px 16px;
                    border-radius: 6px;
                    margin: 2px 4px;
                    background: transparent;
                }}
                QMenu::item:selected {{
                    background: rgba(0, 0, 0, 15);
                    color: #1c1d22;
                }}
            """)
        elif theme == 'Dark':
            self.menu.setStyleSheet(f"""
                QMenu {{
                    background: #181822;
                    color: #ffffff;
                    border: 1px solid #282835;
                    border-radius: 12px;
                    padding: 4px;
                }}
                QMenu::item {{
                    padding: 8px 16px;
                    border-radius: 6px;
                    margin: 2px 4px;
                    background: transparent;
                }}
                QMenu::item:selected {{
                    background: rgba(255, 255, 255, 15);
                    color: #ffffff;
                }}
            """)
        else: # Default Glassmorphism
            self.menu.setStyleSheet(f"""
                QMenu {{
                    background: rgba(25, 25, 25, 240);
                    color: white;
                    border: 1px solid rgba(255, 255, 255, 30);
                    border-radius: 12px;
                    padding: 4px;
                }}
                QMenu::item {{
                    padding: 8px 16px;
                    border-radius: 6px;
                    margin: 2px 4px;
                    background: transparent;
                }}
                QMenu::item:selected {{
                    background: rgba(255, 255, 255, 20);
                }}
            """)


    def _mark_menu_closing(self):
        import time; self._last_close_time = time.time()

    def _update_text(self):
        if self.is_dict:
            self.setText(self.items.get(self.current_val, self.current_val))
        else:
            self.setText(self.current_val)

    def _refresh_menu(self):
        self.menu.clear()
        if self.is_dict:
            for val, label in self.items.items():
                a = self.menu.addAction(label)
                a.triggered.connect(lambda _, v=val: self.setTextValue(v))
        else:
            for i in self.items:
                a = self.menu.addAction(i)
                a.triggered.connect(lambda _, val=i: self.setTextValue(val))

    def setTextValue(self, v):
        self.current_val = v; self._update_text(); self.valueChanged.emit(v)

    def show_menu(self):
        import time
        if time.time() - self._last_close_time < 0.15: return
        self._refresh_menu()
        self.menu.setMinimumWidth(self.width())
        self.menu.exec(self.mapToGlobal(QPoint(0, self.height() + 5)))

    def paintEvent(self, e):
        super().paintEvent(e)
        from PyQt6.QtGui import QPainter, QColor, QFont
        from ui_dashboard_common import get_theme_colors
        colors = get_theme_colors()
        text_sec = QColor(colors.get('text_secondary', '#aaaaaa'))
        
        p = QPainter(self); p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.setPen(text_sec); p.setFont(QFont("Segoe UI", 10))
        p.drawText(self.width() - 24, 0, 20, self.height(), Qt.AlignmentFlag.AlignCenter, "▾")

class AnimatedButton(QPushButton):
    def __init__(self, text, color="#50FA7B", parent=None):
        super().__init__(text, parent)
        self.setFixedHeight(35); self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setStyleSheet(f"QPushButton {{ background: rgba(255,255,255,10); color: {color}; border: 1px solid {color}; border-radius: 8px; font-weight: bold; }} QPushButton:hover {{ background: {color}; color: #141414; }}")

class CustomInputDialog(QDialog):
    def __init__(self, parent=None, title="Input", placeholder="", default_text=""):
        super().__init__(parent)
        self.setWindowTitle(title)
        self.setFixedSize(350, 150)
        
        # Detect theme from parent hierarchy
        theme = "Default"
        accent_hex = "#00f0ff"
        bg_color = "#1a1a24"
        text_color = "white"
        input_bg = "rgba(0,0,0,50)"
        input_border = "rgba(255,255,255,20)"
        btn_bg = "rgba(255,255,255,5)"
        btn_border = "rgba(255,255,255,15)"
        hover_bg = "rgba(0,240,255,20)"
        
        win = parent
        while win:
            if win.__class__.__name__ == "DashboardUI":
                theme = win.cfg.get('general_settings', {}).get('dashboard_theme', 'Default')
                break
            win = win.parent()
            
        if theme == 'Light':
            accent_hex = "#4F46E5"
            bg_color = "#ffffff"
            text_color = "#1c1d22"
            input_bg = "#f3f4f6"
            input_border = "#cccfd6"
            btn_bg = "#f3f4f6"
            btn_border = "#e5e7eb"
            hover_bg = "rgba(79, 70, 229, 0.15)"
        elif theme == 'Dark':
            accent_hex = "#a78bfa"
            bg_color = "#181822"
            text_color = "#ffffff"
            input_bg = "#22222d"
            input_border = "#3c3c4f"
            btn_bg = "#22222d"
            btn_border = "#3c3c4f"
            hover_bg = "rgba(167, 139, 250, 0.15)"
            
        self.setStyleSheet(f"""
            QDialog {{ background: {bg_color}; border: 1px solid {btn_border}; border-radius: 8px; }} 
            QLabel {{ color: {text_color}; font-weight: bold; }} 
            QLineEdit {{ background: {input_bg}; border: 1px solid {input_border}; border-radius: 6px; color: {text_color}; padding: 6px 10px; font-size: 12px; }} 
            QLineEdit:focus {{ border: 1px solid {accent_hex}; }} 
            QPushButton {{ background: {btn_bg}; border: 1px solid {btn_border}; border-radius: 6px; color: {text_color}; padding: 6px 12px; }} 
            QPushButton:hover {{ background: {hover_bg}; border: 1px solid {accent_hex}; color: {accent_hex}; }}
        """)
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(12)
        
        self.lbl = QLabel(title)
        layout.addWidget(self.lbl)
        
        self.input_field = QLineEdit(default_text)
        self.input_field.setPlaceholderText(placeholder)
        layout.addWidget(self.input_field)
        
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        
        self.cancel_btn = QPushButton("Cancel")
        self.cancel_btn.clicked.connect(self.reject)
        
        self.ok_btn = QPushButton("Save")
        self.ok_btn.clicked.connect(self.accept)
        
        btn_layout.addWidget(self.cancel_btn)
        btn_layout.addWidget(self.ok_btn)
        
        layout.addLayout(btn_layout)
        
    def get_text(self):
        return self.input_field.text()


class FlowLayout(QLayout):
    def __init__(self, parent=None, margin=0, hSpacing=12, vSpacing=12):
        super().__init__(parent)
        self.itemList = []
        self.hSpace = hSpacing
        self.vSpace = vSpacing
        self.setContentsMargins(margin, margin, margin, margin)

    def __del__(self):
        while self.itemList:
            self.takeAt(0)

    def addItem(self, item):
        self.itemList.append(item)

    def horizontalSpacing(self):
        return self.hSpace

    def verticalSpacing(self):
        return self.vSpace

    def count(self):
        return len(self.itemList)

    def itemAt(self, index):
        if index >= 0 and index < len(self.itemList):
            try:
                item = self.itemList[index]
                if item is not None:
                    _ = item.widget()
                return item
            except (RuntimeError, AttributeError):
                return None
        return None

    def takeAt(self, index):
        if index >= 0 and index < len(self.itemList):
            item = self.itemList.pop(index)
            try:
                if item is not None:
                    _ = item.widget()
                return item
            except (RuntimeError, AttributeError):
                return None
        return None

    def expandingDirections(self):
        return Qt.Orientation(0)

    def hasHeightForWidth(self):
        return True

    def heightForWidth(self, width):
        return self.doLayout(QRect(0, 0, width, 0), True)

    def setGeometry(self, rect):
        super().setGeometry(rect)
        self.doLayout(rect, False)

    def sizeHint(self):
        return self.minimumSize()

    def minimumSize(self):
        size = QSize()
        for item in self.itemList:
            try:
                size = size.expandedTo(item.minimumSize())
            except (RuntimeError, AttributeError):
                continue
        margins = self.contentsMargins()
        size += QSize(margins.left() + margins.right(), margins.top() + margins.bottom())
        return size

    def doLayout(self, rect, testOnly):
        left, top, right, bottom = self.getContentsMargins()
        effectiveRect = rect.adjusted(+left, +top, -right, -bottom)
        x = effectiveRect.x()
        y = effectiveRect.y()
        lineHeight = 0

        for item in self.itemList:
            try:
                wid = item.widget()
                if wid is None:
                    continue
                _ = wid.width()
            except (RuntimeError, AttributeError):
                continue
            
            try:
                spaceX = self.horizontalSpacing()
                spaceY = self.verticalSpacing()
                sh = item.sizeHint()
                nextX = x + sh.width() + spaceX
                if nextX - spaceX > effectiveRect.right() and lineHeight > 0:
                    x = effectiveRect.x()
                    y = y + lineHeight + spaceY
                    nextX = x + sh.width() + spaceX
                    lineHeight = 0

                if not testOnly:
                    item.setGeometry(QRect(QPoint(x, y), sh))

                x = nextX
                lineHeight = max(lineHeight, sh.height())
            except (RuntimeError, AttributeError):
                continue

        return y + lineHeight - rect.y() + bottom
