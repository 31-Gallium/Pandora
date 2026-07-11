
def get_theme_bg_color():
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
    is_light = False
    bg_c = QColor(20, 20, 20, darkness)
    
    if folder_theme == 'Desktop':
        accents = gen_settings.get('desktop_accents', [])
        from utils import is_desktop_light_vibe
        is_light = is_desktop_light_vibe()
        
        if is_light and accents:
            ar, ag, ab = accents[0]
            bg_c = QColor(min(255, int(ar*0.05 + 240)), min(255, int(ag*0.05 + 240)), min(255, int(ab*0.05 + 245)), darkness)
        elif accents and len(accents) > 1:
            r_avg = int(sum(c[0] for c in accents) / len(accents))
            g_avg = int(sum(c[1] for c in accents) / len(accents))
            b_avg = int(sum(c[2] for c in accents) / len(accents))
            bg_c = QColor(r_avg, g_avg, b_avg, darkness)
        elif accents and len(accents) == 1:
            c = accents[0]
            bg_c = QColor(c[0], c[1], c[2], darkness)
    elif folder_theme == 'Custom':
        custom_hex = gen_settings.get('folder_custom_color', '#161B22FF')
        try:
            hex_str = custom_hex.lstrip('#')
            if len(hex_str) == 8:
                r = int(hex_str[0:2], 16)
                g = int(hex_str[2:4], 16)
                b = int(hex_str[4:6], 16)
                a = int(hex_str[6:8], 16)
                bg_c = QColor(r, g, b, a)
            else:
                bg_c = QColor(custom_hex)
                bg_c.setAlpha(darkness)
        except Exception:
            pass
            
    return bg_c, is_light

def fill_themed_path(p, path, width, height):
    bg_c, _ = get_theme_bg_color()
    p.fillPath(path, bg_c)

from PyQt6.QtWidgets import QMenu, QGraphicsOpacityEffect, QPushButton, QDialog, QVBoxLayout, QLabel, QLineEdit, QHBoxLayout, QLayout, QSizePolicy
from PyQt6.QtCore import Qt, QPropertyAnimation, pyqtSignal, QPoint, QRect, QSize, QObject

class AnimatedMenu(QDialog):
    aboutToHide = pyqtSignal()
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowFlags(
            Qt.WindowType.Popup | 
            Qt.WindowType.FramelessWindowHint | 
            Qt.WindowType.NoDropShadowWindowHint
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(4, 4, 4, 4)
        self.main_layout.setSpacing(2)
        
        bg_c, is_light = get_theme_bg_color()
        bg_css = f"rgba({bg_c.red()}, {bg_c.green()}, {bg_c.blue()}, {bg_c.alpha()})"
        self.text_c = "black" if is_light else "white"
        self.item_sel = "rgba(0,0,0,15)" if is_light else "rgba(255,255,255,20)"
        border = "rgba(0,0,0,30)" if is_light else "rgba(255,255,255,30)"
        
        self.setStyleSheet(f"QDialog {{ background: {bg_css}; border: 1px solid {border}; border-radius: 12px; }}")
        
        self._actions = []

    def clear(self):
        while self.main_layout.count():
            item = self.main_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        self._actions.clear()

    def addAction(self, action_or_text):
        if isinstance(action_or_text, str):
            from PyQt6.QtGui import QAction
            action = QAction(action_or_text, self)
        else:
            action = action_or_text
            
        btn = QPushButton(action.text())
        btn.setCursor(Qt.CursorShape.PointingHandCursor)
        btn.setStyleSheet(f"""
            QPushButton {{
                color: {self.text_c};
                background: transparent;
                border: none;
                padding: 8px 16px;
                border-radius: 6px;
                text-align: left;
                font-family: "Segoe UI";
                font-size: 13px;
            }}
            QPushButton:hover {{
                background: {self.item_sel};
            }}
        """)
        # When button is clicked, trigger action and close menu
        btn.clicked.connect(lambda _, a=action: self._handle_action(a))
        self.main_layout.addWidget(btn)
        self._actions.append(action)
        return action
        
    def _handle_action(self, action):
        self.close()
        action.trigger()

    def addSeparator(self):
        from PyQt6.QtWidgets import QFrame
        line = QFrame()
        line.setFrameShape(QFrame.Shape.HLine)
        line.setStyleSheet("background-color: rgba(128,128,128,50); border: none; min-height: 1px; max-height: 1px;")
        self.main_layout.addWidget(line)

    def changeEvent(self, e):
        super().changeEvent(e)
        from PyQt6.QtCore import QEvent, QTimer
        if e.type() == QEvent.Type.ActivationChange:
            QTimer.singleShot(50, self._check_focus)
            
    def _check_focus(self):
        if not self.isActiveWindow() and self.isVisible():
            self.close()

    def closeEvent(self, event):
        self.aboutToHide.emit()
        super().closeEvent(event)

    def exec(self, pos):
        self.adjustSize()
        
        from PyQt6.QtGui import QGuiApplication
        screen = QGuiApplication.screenAt(pos)
        if not screen:
            screen = QGuiApplication.primaryScreen()
            
        if screen:
            scr_geom = screen.availableGeometry()
            x = pos.x()
            y = pos.y()
            
            if x + self.width() > scr_geom.right():
                x = scr_geom.right() - self.width()
            if x < scr_geom.left():
                x = scr_geom.left()
                
            if y + self.height() > scr_geom.bottom():
                y = scr_geom.bottom() - self.height()
            if y < scr_geom.top():
                y = scr_geom.top()
                
            self.move(x, y)
        else:
            self.move(pos)
            
        # Ensure it gains focus so it can detect clicking outside
        self.activateWindow()
        self.raise_()
        return super().exec()

    def showEvent(self, event):
        super().showEvent(event)
        def _apply_blur():
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
                policy.AccentState = 4 # ACCENT_ENABLE_ACRYLICBLURBEHIND
                policy.GradientColor = 0x01000000 
                data = WINDOWCOMPOSITIONATTRIBDATA()
                data.Attribute = 19
                data.SizeOfData = ctypes.sizeof(policy)
                data.Data = ctypes.pointer(policy)
                hwnd = int(self.winId())
                ctypes.windll.user32.SetWindowCompositionAttribute(hwnd, ctypes.pointer(data))
                
                corner_pref = ctypes.c_int(2) # DWMWCP_ROUND = 2
                ctypes.windll.dwmapi.DwmSetWindowAttribute(hwnd, 33, ctypes.byref(corner_pref), ctypes.sizeof(corner_pref))
                
                # Draw the window immediately with blur enabled
                self.update()
            except Exception:
                pass
        from PyQt6.QtCore import QTimer
        QTimer.singleShot(0, _apply_blur)

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
        
        bg_c, is_light = get_theme_bg_color()
        if is_light:
            theme = 'light'
            bg = 'rgba(0, 0, 0, 0.05)'
            border = '1px solid rgba(0, 0, 0, 0.1)'
            text_color = '#111827'
            accent = '#2563eb'
        else:
            theme = 'dark'
            bg = '#1a1b26'
            border = '1px solid rgba(255,255,255,0.05)'
            text_color = '#e2e8f0'
            accent = '#26c0d3'
            
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
                QDialog {{
                    background: #ffffff;
                    border: 1px solid #c8cbd0;
                    border-radius: 12px;
                }}
                QPushButton {{
                    color: #1c1d22;
                    background: transparent;
                    border: none;
                    padding: 8px 16px;
                    border-radius: 6px;
                    text-align: left;
                    font-family: "Segoe UI";
                    font-size: 13px;
                }}
                QPushButton:hover {{
                    background: rgba(0, 0, 0, 15);
                }}
            """)
        elif theme == 'Dark':
            self.menu.setStyleSheet(f"""
                QDialog {{
                    background: #181822;
                    border: 1px solid #282835;
                    border-radius: 12px;
                }}
                QPushButton {{
                    color: #ffffff;
                    background: transparent;
                    border: none;
                    padding: 8px 16px;
                    border-radius: 6px;
                    text-align: left;
                    font-family: "Segoe UI";
                    font-size: 13px;
                }}
                QPushButton:hover {{
                    background: rgba(255, 255, 255, 15);
                }}
            """)
        else: # Default Glassmorphism
            self.menu.setStyleSheet(f"""
                QDialog {{
                    background: rgba(25, 25, 25, 240);
                    border: 1px solid rgba(255, 255, 255, 30);
                    border-radius: 12px;
                }}
                QPushButton {{
                    color: white;
                    background: transparent;
                    border: none;
                    padding: 8px 16px;
                    border-radius: 6px;
                    text-align: left;
                    font-family: "Segoe UI";
                    font-size: 13px;
                }}
                QPushButton:hover {{
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
        bg_c, is_light = get_theme_bg_color()
        if is_light:
            text_sec = QColor(100, 100, 100)
        else:
            text_sec = QColor(170, 170, 170)
        
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
        GlobalHoverManager.instance().set_blocked(True)
        self.anim.start()
        self.activateWindow()
        self.raise_()
        self.input_field.setFocus()
        self.input_field.selectAll()

    def changeEvent(self, e):
        super().changeEvent(e)
        from PyQt6.QtCore import QEvent, QTimer
        if e.type() == QEvent.Type.ActivationChange:
            QTimer.singleShot(100, self._check_focus)
            
    def _check_focus(self):
        if not self.isActiveWindow() and self.isVisible():
            self.reject()
    def closeEvent(self, e):
        super().closeEvent(e)
        GlobalHoverManager.instance().set_blocked(False)

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
        GlobalHoverManager.instance().set_blocked(False)
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
        GlobalHoverManager.instance().set_blocked(True)
        self.anim.start()
        self.activateWindow()
        self.raise_()

    def changeEvent(self, e):
        super().changeEvent(e)
        from PyQt6.QtCore import QEvent
        if e.type() == QEvent.Type.ActivationChange:
            if not self.isActiveWindow():
                self.reject()

    def closeEvent(self, e):
        super().closeEvent(e)
        GlobalHoverManager.instance().set_blocked(False)

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
        GlobalHoverManager.instance().set_blocked(False)
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
class GlobalHoverManager(QObject):
    _instance = None
    
    @classmethod
    def instance(cls):
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance
        
    def __init__(self):
        super().__init__()
        self.pill = None
        self.is_blocked = False
        
    def set_blocked(self, blocked):
        self.is_blocked = blocked
        if blocked and self.pill:
            self.pill.force_hide()
            
    def show_text(self, text, icon_path=''):
        if self.is_blocked: return
        if not self.pill:
            self.pill = HoverPillDialog()
        self.pill.show_text(text, icon_path)
        
    def request_hide(self, text=None):
        if self.pill:
            self.pill.request_hide(text)

class HoverPillDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowFlags(
            Qt.WindowType.WindowStaysOnTopHint |
            Qt.WindowType.FramelessWindowHint |
            Qt.WindowType.Tool
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating)
        
        self.layout = QHBoxLayout(self)
        self.layout.setContentsMargins(20, 10, 20, 10)
        self.layout.setSpacing(8)
        
        self.icon_label = QLabel()
        self.icon_label.hide()
        self.layout.addWidget(self.icon_label)
        
        self.label = QLabel()
        from PyQt6.QtGui import QFont
        font = QFont("Segoe UI", 11)
        font.setWeight(QFont.Weight.DemiBold)
        self.label.setFont(font)
        self.label.setStyleSheet("color: white;")
        self.layout.addWidget(self.label)
        
        self._enable_windows_blur()
        
        self.current_text = ""
        self.is_showing = False
        
        from PyQt6.QtGui import QGuiApplication
        screen = QGuiApplication.primaryScreen().geometry()
        self.final_y = 60
        self.start_y = -100
        
        from PyQt6.QtCore import QEasingCurve, QPropertyAnimation, QTimer
        self.anim = QPropertyAnimation(self, b"pos")
        self.anim.setEasingCurve(QEasingCurve.Type.OutBack)
        
        self.hide_timer = QTimer(self)
        self.hide_timer.setSingleShot(True)
        self.hide_timer.timeout.connect(self.force_hide)

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
            
            corner_pref = ctypes.c_int(2)
            ctypes.windll.dwmapi.DwmSetWindowAttribute(hwnd, 33, ctypes.byref(corner_pref), ctypes.sizeof(corner_pref))
        except:
            pass

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

    def show_text(self, text, icon_path=''):
        self.hide_timer.stop()
        if self.current_text == text and self.is_showing: return
        
        self.current_text = text
        self.label.setText(text)
        
        if icon_path:
            from PyQt6.QtGui import QPixmap
            pix = QPixmap(icon_path).scaled(16, 16, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
            self.icon_label.setPixmap(pix)
            self.icon_label.show()
        else:
            self.icon_label.hide()
            
        self.adjustSize()
        from PyQt6.QtGui import QGuiApplication
        screen = QGuiApplication.primaryScreen().geometry()
        x_pos = screen.center().x() - self.width() // 2
        
        if not self.is_showing:
            self.is_showing = True
            self.move(x_pos, self.start_y)
            self.show()
            self.anim.stop()
            self.anim.setDuration(400)
            from PyQt6.QtCore import QEasingCurve, QPoint
            self.anim.setEasingCurve(QEasingCurve.Type.OutBack)
            self.anim.setEndValue(QPoint(x_pos, self.final_y))
            self.anim.start()
        else:
            # Smooth resize/move without dropping again
            from PyQt6.QtCore import QPropertyAnimation, QPoint, QEasingCurve
            self.anim.stop()
            self.anim.setDuration(200)
            self.anim.setEasingCurve(QEasingCurve.Type.OutQuad)
            self.anim.setEndValue(QPoint(x_pos, self.final_y))
            self.anim.start()

    def request_hide(self, text=None):
        if text is not None and self.current_text != text:
            return
        # Add slight delay so moving mouse between folders doesn't drop it out immediately
        self.hide_timer.start(100)
        
    def force_hide(self):
        self.hide_timer.stop()
        if not self.is_showing: return
        self.is_showing = False
        self.anim.stop()
        self.anim.setDuration(300)
        from PyQt6.QtCore import QEasingCurve, QPoint
        self.anim.setEasingCurve(QEasingCurve.Type.InBack)
        self.anim.setEndValue(QPoint(self.pos().x(), self.start_y))
        
        try:
            self.anim.finished.disconnect()
        except TypeError:
            pass
        self.anim.finished.connect(self._on_hide_anim_finished)
        self.anim.start()
        
    def _on_hide_anim_finished(self):
        if not self.is_showing:
            self.hide()
