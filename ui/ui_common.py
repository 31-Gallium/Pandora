
def fill_themed_path(p, path, width, height):
    from config import ConfigManager
    from PyQt6.QtGui import QColor
    cfg = ConfigManager.load()
    gen_settings = cfg.get('general_settings', {})
    intensity_setting = gen_settings.get('theme_intensity')
    if not intensity_setting:
        old_darkness = gen_settings.get('folder_darkness', 'Dark')
        intensity_setting = 'Subtle' if old_darkness == 'Light' else 'Balanced' if old_darkness == 'Medium' else 'Solid' if old_darkness == 'Pitch Black' else 'Intense'
    
    intensity_map = {'Subtle': 100, 'Balanced': 150, 'Intense': 180, 'Solid': 230}
    darkness = intensity_map.get(intensity_setting, 180)
    
    folder_theme = gen_settings.get('folder_theme', 'Default')
    
    if folder_theme == 'Desktop':
        accents = gen_settings.get('desktop_accents', [])
        if accents and len(accents) >= 2:
            from PyQt6.QtGui import QLinearGradient
            gradient = QLinearGradient(0, 0, width, height)
            c1, c2 = accents[0], accents[1]
            gradient.setColorAt(0, QColor(c1[0], c1[1], c1[2], darkness))
            gradient.setColorAt(1, QColor(c2[0], c2[1], c2[2], darkness))
            p.fillPath(path, gradient)
        elif accents and len(accents) > 0:
            c = accents[0]
            p.fillPath(path, QColor(c[0], c[1], c[2], darkness))
        else:
            p.fillPath(path, QColor(20, 20, 20, darkness))
    elif folder_theme == 'Custom':
        custom_hex = gen_settings.get('folder_custom_color', '#161B22FF')
        try:
            hex_str = custom_hex.lstrip('#')
            if len(hex_str) == 8:
                r = int(hex_str[0:2], 16)
                g = int(hex_str[2:4], 16)
                b = int(hex_str[4:6], 16)
                a = int(hex_str[6:8], 16)
                base_color = QColor(r, g, b, a)
            else:
                base_color = QColor(custom_hex)
                base_color.setAlpha(darkness)
            p.fillPath(path, base_color)
        except Exception:
            p.fillPath(path, QColor(20, 20, 20, darkness))

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

class ToastNotification(QDialog):
    def __init__(self, message, parent=None, duration_ms=2500):
        super().__init__(parent)
        self.setWindowFlags(
            Qt.WindowType.WindowStaysOnTopHint |
            Qt.WindowType.FramelessWindowHint |
            Qt.WindowType.Tool
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating)
        
        layout = QHBoxLayout(self)
        layout.setContentsMargins(20, 10, 20, 10)
        
        self.label = QLabel(message)
        from PyQt6.QtGui import QFont
        font = QFont("Segoe UI", 11)
        font.setWeight(QFont.Weight.DemiBold)
        self.label.setFont(font)
        self.label.setStyleSheet("color: white;")
        layout.addWidget(self.label)
        
        self._enable_windows_blur()
        
        self.setStyleSheet("""
            QDialog {
                background-color: rgba(30, 30, 30, 180);
                border: 1px solid rgba(255, 255, 255, 30);
                border-radius: 18px;
            }
        """)
        
        self.adjustSize()
        
        from PyQt6.QtGui import QGuiApplication
        screen = QGuiApplication.primaryScreen().geometry()
        
        self.final_y = 60
        self.start_y = -self.height() - 20
        self.x_pos = screen.center().x() - self.width() // 2
        
        self.move(self.x_pos, self.start_y)
        
        from PyQt6.QtCore import QEasingCurve
        self.anim = QPropertyAnimation(self, b"pos")
        self.anim.setDuration(600)
        self.anim.setEasingCurve(QEasingCurve.Type.OutBack)
        self.anim.setEndValue(QPoint(self.x_pos, self.final_y))
        
        from PyQt6.QtCore import QTimer
        self.timer = QTimer(self)
        self.timer.setSingleShot(True)
        self.timer.timeout.connect(self._hide_toast)
        self.duration_ms = duration_ms
    def showEvent(self, e):
        super().showEvent(e)
        self.anim.start()
        self.timer.start(self.duration_ms)
        
    def _hide_toast(self):
        from PyQt6.QtCore import QEasingCurve
        self.anim.setEasingCurve(QEasingCurve.Type.InBack)
        self.anim.setDuration(400)
        self.anim.setEndValue(QPoint(self.x_pos, self.start_y))
        self.anim.finished.connect(self.close)
        self.anim.start()
        
    def _enable_windows_blur(self):
        try:
            import ctypes
            from ctypes import c_int, c_uint, Structure, POINTER, pointer
            class ACCENTPOLICY(Structure):
                _fields_ = [
                    ("AccentState", c_uint),
                    ("AccentFlags", c_uint),
                    ("GradientColor", c_uint),
                    ("AnimationId", c_uint)
                ]
            class WINDOWCOMPOSITIONATTRIBDATA(Structure):
                _fields_ = [
                    ("Attribute", c_int),
                    ("Data", POINTER(ACCENTPOLICY)),
                    ("SizeOfData", c_uint)
                ]
            policy = ACCENTPOLICY()
            policy.AccentState = 4 # ACCENT_ENABLE_ACRYLICBLURBEHIND
            policy.AccentFlags = 0x20 | 0x40 | 0x80 | 0x100
            policy.GradientColor = 0x80111111
            
            data = WINDOWCOMPOSITIONATTRIBDATA()
            data.Attribute = 19
            data.Data = pointer(policy)
            data.SizeOfData = ctypes.sizeof(policy)
            
            ctypes.windll.user32.SetWindowCompositionAttribute(int(self.winId()), pointer(data))
        except Exception:
            pass


class IslandRenameDialog(QDialog):
    def __init__(self, initial_text="", on_save=None, parent=None):
        super().__init__(parent)
        self.setWindowFlags(
            Qt.WindowType.WindowStaysOnTopHint |
            Qt.WindowType.FramelessWindowHint |
            Qt.WindowType.Tool
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        
        layout = QHBoxLayout(self)
        layout.setContentsMargins(20, 10, 20, 10)
        
        from PyQt6.QtWidgets import QLineEdit
        self.input_field = QLineEdit(initial_text)
        from PyQt6.QtGui import QFont
        font = QFont("Segoe UI", 12)
        font.setWeight(QFont.Weight.DemiBold)
        self.input_field.setFont(font)
        
        self.input_field.setStyleSheet("""
            QLineEdit {
                background: transparent;
                border: none;
                color: white;
                selection-background-color: rgba(38, 192, 211, 0.4);
            }
        """)
        self.input_field.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.input_field.setMinimumWidth(250)
        self.input_field.setMaxLength(24)
        
        self.on_save = on_save
        self.input_field.returnPressed.connect(self.save_and_close)
        
        layout.addWidget(self.input_field)
        
        self._enable_windows_blur()
        
        self.setStyleSheet("""
        """)
        
        self.adjustSize()
        
        from PyQt6.QtGui import QGuiApplication
        screen = QGuiApplication.primaryScreen().geometry()
        
        self.final_y = 60
        self.start_y = -self.height() - 20
        self.x_pos = screen.center().x() - self.width() // 2
        
        self.move(self.x_pos, self.start_y)
        
        from PyQt6.QtCore import QEasingCurve, QPropertyAnimation, QPoint
        self.anim = QPropertyAnimation(self, b"pos")
        self.anim.setDuration(600)
        self.anim.setEasingCurve(QEasingCurve.Type.OutBack)
        self.anim.setEndValue(QPoint(self.x_pos, self.final_y))

    def paintEvent(self, e):
        from PyQt6.QtGui import QPainter, QPainterPath, QColor, QPen
        from PyQt6.QtCore import QRectF
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        path = QPainterPath()
        r = 8
        rect = QRectF(1, 1, self.width()-2, self.height()-2)
        path.addRoundedRect(rect, r, r)
        fill_themed_path(p, path, self.width(), self.height())
        p.strokePath(path, QPen(QColor(255, 255, 255, 30), 1))

    def resizeEvent(self, e):
        super().resizeEvent(e)
        from PyQt6.QtGui import QPainterPath, QRegion
        from PyQt6.QtCore import QRectF
        path = QPainterPath()
        path.addRoundedRect(QRectF(0, 0, self.width(), self.height()), 8, 8)
        self.setMask(QRegion(path.toFillPolygon().toPolygon()))

    def showEvent(self, e):
        super().showEvent(e)
        self.anim.start()
        self.activateWindow()
        self.raise_()
        self.input_field.setFocus()
        self.input_field.selectAll()

    def changeEvent(self, e):
        super().changeEvent(e)
        from PyQt6.QtCore import QEvent
        if e.type() == QEvent.Type.ActivationChange:
            if not self.isActiveWindow():
                self.reject()
                
    def save_and_close(self):
        if self.on_save:
            self.on_save(self.input_field.text())
        self._hide_and_close()

    def reject(self):
        self._hide_and_close()

    def _hide_and_close(self):
        if hasattr(self, '_is_closing') and self._is_closing:
            return
        self._is_closing = True
        from PyQt6.QtCore import QEasingCurve, QPropertyAnimation, QPoint
        self.anim.setEasingCurve(QEasingCurve.Type.InBack)
        self.anim.setDuration(400)
        self.anim.setEndValue(QPoint(self.x_pos, self.start_y))
        self.anim.finished.connect(self.close)
        self.anim.start()
        
    def _enable_windows_blur(self):
        try:
            import ctypes
            from ctypes import c_int, c_uint, Structure, POINTER
            class ACCENTPOLICY(Structure):
                _fields_ = [
                    ("AccentState", c_uint),
                    ("AccentFlags", c_uint),
                    ("GradientColor", c_uint),
                    ("AnimationId", c_uint)
                ]
            class WINDOWCOMPOSITIONATTRIBDATA(Structure):
                _fields_ = [
                    ("Attribute", c_int),
                    ("Data", POINTER(ACCENTPOLICY)),
                    ("SizeOfData", c_uint)
                ]
            policy = ACCENTPOLICY()
            policy.AccentState = 4
            policy.GradientColor = 0x01000000
            data = WINDOWCOMPOSITIONATTRIBDATA()
            data.Attribute = 19
            data.SizeOfData = ctypes.sizeof(policy)
            data.Data = ctypes.pointer(policy)
            hwnd = int(self.winId())
            ctypes.windll.user32.SetWindowCompositionAttribute(hwnd, ctypes.pointer(data))
            
            # Tell Windows 11 to round the blur corners to perfectly match the 8px drawn radius
            corner_pref = ctypes.c_int(2) # DWMWCP_ROUND = 2
            ctypes.windll.dwmapi.DwmSetWindowAttribute(hwnd, 33, ctypes.byref(corner_pref), ctypes.sizeof(corner_pref))
        except:
            pass


class IslandConfirmDialog(QDialog):
    def __init__(self, message, options, on_choice=None, parent=None):
        super().__init__(parent)
        self.setWindowFlags(
            Qt.WindowType.WindowStaysOnTopHint |
            Qt.WindowType.FramelessWindowHint |
            Qt.WindowType.Tool
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        
        layout = QHBoxLayout(self)
        layout.setContentsMargins(20, 15, 20, 15)
        layout.setSpacing(15)
        
        from PyQt6.QtWidgets import QLabel, QPushButton
        from PyQt6.QtGui import QFont, QCursor
        
        msg_font = QFont("Segoe UI", 11)
        msg_font.setWeight(QFont.Weight.DemiBold)
        
        msg_label = QLabel(message)
        msg_label.setFont(msg_font)
        msg_label.setStyleSheet("color: white;")
        layout.addWidget(msg_label)
        
        btn_font = QFont("Segoe UI", 10)
        btn_font.setWeight(QFont.Weight.Bold)
        
        self.on_choice = on_choice
        
        for opt, color in options:
            btn = QPushButton(opt)
            btn.setFont(btn_font)
            btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
            btn.setStyleSheet(f"""
                QPushButton {{
                    background: {color};
                    color: white;
                    border: none;
                    border-radius: 8px;
                    padding: 6px 16px;
                }}
                QPushButton:hover {{
                    background: rgba(255, 255, 255, 0.2);
                    border: 1px solid rgba(255, 255, 255, 0.4);
                }}
            """)
            btn.clicked.connect(lambda checked, text=opt: self.make_choice(text))
            layout.addWidget(btn)
        
        self._enable_windows_blur()
        
        self.setStyleSheet("""
        """)
        
        self.adjustSize()
        
        from PyQt6.QtGui import QGuiApplication
        screen = QGuiApplication.primaryScreen().geometry()
        
        self.final_y = 60
        self.start_y = -self.height() - 20
        self.x_pos = screen.center().x() - self.width() // 2
        
        self.move(self.x_pos, self.start_y)
        
        from PyQt6.QtCore import QEasingCurve, QPropertyAnimation, QPoint
        self.anim = QPropertyAnimation(self, b"pos")
        self.anim.setDuration(600)
        self.anim.setEasingCurve(QEasingCurve.Type.OutBack)
        self.anim.setEndValue(QPoint(self.x_pos, self.final_y))
    def paintEvent(self, e):
        from PyQt6.QtGui import QPainter, QPainterPath, QColor, QPen
        from PyQt6.QtCore import QRectF
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        path = QPainterPath()
        r = 8
        rect = QRectF(1, 1, self.width()-2, self.height()-2)
        path.addRoundedRect(rect, r, r)
        fill_themed_path(p, path, self.width(), self.height())
        p.strokePath(path, QPen(QColor(255, 255, 255, 30), 1))

    def resizeEvent(self, e):
        super().resizeEvent(e)
        from PyQt6.QtGui import QPainterPath, QRegion
        from PyQt6.QtCore import QRectF
        path = QPainterPath()
        path.addRoundedRect(QRectF(0, 0, self.width(), self.height()), 8, 8)
        self.setMask(QRegion(path.toFillPolygon().toPolygon()))

    def showEvent(self, e):
        super().showEvent(e)
        self.anim.start()
        self.activateWindow()
        self.raise_()

    def changeEvent(self, e):
        super().changeEvent(e)
        from PyQt6.QtCore import QEvent
        if e.type() == QEvent.Type.ActivationChange:
            if not self.isActiveWindow():
                self.reject()

    def make_choice(self, choice):
        if self.on_choice:
            self.on_choice(choice)
        self._hide_and_close()

    def reject(self):
        self._hide_and_close()

    def _hide_and_close(self):
        if hasattr(self, '_is_closing') and self._is_closing:
            return
        self._is_closing = True
        from PyQt6.QtCore import QEasingCurve, QPropertyAnimation, QPoint
        self.anim.setEasingCurve(QEasingCurve.Type.InBack)
        self.anim.setDuration(400)
        self.anim.setEndValue(QPoint(self.x_pos, self.start_y))
        self.anim.finished.connect(self.close)
        self.anim.start()
        
    def _enable_windows_blur(self):
        try:
            import ctypes
            from ctypes import c_int, c_uint, Structure, POINTER
            class ACCENTPOLICY(Structure):
                _fields_ = [
                    ("AccentState", c_uint),
                    ("AccentFlags", c_uint),
                    ("GradientColor", c_uint),
                    ("AnimationId", c_uint)
                ]
            class WINDOWCOMPOSITIONATTRIBDATA(Structure):
                _fields_ = [
                    ("Attribute", c_int),
                    ("Data", POINTER(ACCENTPOLICY)),
                    ("SizeOfData", c_uint)
                ]
            policy = ACCENTPOLICY()
            policy.AccentState = 4
            policy.GradientColor = 0x01000000
            data = WINDOWCOMPOSITIONATTRIBDATA()
            data.Attribute = 19
            data.SizeOfData = ctypes.sizeof(policy)
            data.Data = ctypes.pointer(policy)
            hwnd = int(self.winId())
            ctypes.windll.user32.SetWindowCompositionAttribute(hwnd, ctypes.pointer(data))
            
            # Tell Windows 11 to round the blur corners to perfectly match the 8px drawn radius
            corner_pref = ctypes.c_int(2) # DWMWCP_ROUND = 2
            ctypes.windll.dwmapi.DwmSetWindowAttribute(hwnd, 33, ctypes.byref(corner_pref), ctypes.sizeof(corner_pref))
        except:
            pass