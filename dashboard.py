import os
import json
import copy
import shutil
import math
from PyQt6.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
                               QFormLayout, QSlider, QPushButton, 
                               QLabel, QFileDialog, QStackedWidget, QLineEdit, 
                               QGridLayout, QScrollArea, QFrame, QSizePolicy, QApplication, QButtonGroup,
                               QListWidget, QListWidgetItem, QAbstractItemView, QGraphicsOpacityEffect)
from PyQt6.QtCore import (Qt, QEvent, QPoint, QPointF, QRect, QRectF, QPropertyAnimation, 
                          QEasingCurve, pyqtSignal, QVariantAnimation, QParallelAnimationGroup, QSize, QTimer, QAbstractNativeEventFilter)
import ctypes
from ctypes import wintypes
from PyQt6.QtGui import (QColor, QPainter, QFont, QPen, QAction, QPixmap, 
                         QPainterPath, QRadialGradient, QLinearGradient, QRegion, QIcon, QCursor)
from config import ConfigManager, STORAGE_PATH
from utils import WinAPI, VectorIcon, IconExtractor
from ui_common import AnimatedMenu, DropdownButton, AnimatedButton
from folder_view import FolderView
from ui_utils import draw_folder_thumbnail

# Default settings for reset
DEFAULTS = {
    "general_settings": {
        "sync_grid_size": True,
        "grid_size": 110,
        "edge_padding": 0,
        "show_grid_on_drag": True,
        "grid_animated_color": True,
        "grid_wave_entrance": True,
        "grid_wave_fade": True,
        "keybinds": {
            "launch_app": 1,
            "open_folder": 4,
            "show_menu": 2
        }
    },
    "radial_menu": {
        "enabled": True,
        "activation_key": 0xC0,
        "hold_mode": "Hold",
        "theme": "Dark",
        "radius": 160,
        "opacity": 185,
        "deadzone": 30,
        "tools": [
            {"id": "browser", "icon": "browser", "label": "Browser"},
            {"id": "explorer", "icon": "file explorer", "label": "Files"},
            {"id": "grid", "icon": "toggle grid", "label": "Toggle Grid"},
            {"id": "screenshot", "icon": "screenshot", "label": "Snip"},
            {"id": "night", "icon": "night light", "label": "Night Light"},
            {"id": "mute", "icon": "mute", "label": "Mute"},
            {"id": "trash", "icon": "empty recycle bin", "label": "Empty Trash"},
            {"id": "settings", "icon": "Pandora", "label": "Pandora"},
            {"id": "search", "icon": "search", "label": "Search"},
            {"id": "taskmgr", "icon": "task manager", "label": "Tasks"},
            {"id": "notes", "icon": "sticky notes", "label": "Sticky Notes"},
            {"id": "power", "icon": "power", "label": "Power"},
            {"id": "calc", "icon": "calculator", "label": "Calculator"},
            {"id": "cmd", "icon": "terminal", "label": "Terminal"},
            {"id": "notepad", "icon": "notepad", "label": "Notepad"},
            {"id": "prev", "icon": "prev", "label": "Prev Media"},
            {"id": "next", "icon": "next", "label": "Next Media"}
        ],
        "gap_size": 75
    },
    "grid": {
        "size_preset": "Medium", "folder_size": 80, "mini_icon_size": 18, "font_size": 10, "expanded_icon_size": 48,
        "glow_intensity": 20, "glow_color": "#ffffff", "bg_color": "#141414", "title_color": "#ffffff", "highlight_color": "#ffffff",
        "opacity": 80, "radius": 20, "cover_blur": 0, "cover_opacity": 255, "hover_speed": "Fluid", "morph_speed": "Fluid",
        "grid_snap": False, "show_cover": False, "show_title": True, "mini_highlight_shape": "Circle"
    },
    "flower": {
        "size_preset": "Medium", "folder_size": 80, "mini_icon_size": 18, "font_size": 10, "expanded_icon_size": 48,
        "glow_intensity": 20, "glow_color": "#ffffff", "bg_color": "#141414", "title_color": "#ffffff", "highlight_color": "#ffffff",
        "opacity": 80, "radius": 10, "cover_blur": 0, "cover_opacity": 255, "hover_speed": "Fluid", "morph_speed": "Fluid",
        "grid_snap": False, "show_cover": False, "show_title": True, "mini_highlight_shape": "Circle"
    },
    "display_effects": {
        "warmth_intensity": 50,
        "active_preset": "Sunset"
    }
}

SCROLLBAR_CSS = """
QScrollArea, QScrollArea > QWidget > QWidget, QListWidget, QListView, QTextEdit, QPlainTextEdit {
    background: transparent;
    border: none;
}
QScrollBar:vertical {
    width: 6px;
    background: transparent;
    margin: 0px;
}
QScrollBar::handle:vertical {
    background: rgba(255, 255, 255, 40);
    border-radius: 3px;
    min-height: 20px;
}
QScrollBar::handle:vertical:hover {
    background: rgba(255, 255, 255, 80);
}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical,
QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {
    background: none;
    border: none;
    height: 0px;
    width: 0px;
}

QScrollBar:horizontal {
    height: 6px;
    background: transparent;
    margin: 0px;
}
QScrollBar::handle:horizontal {
    background: rgba(255, 255, 255, 40);
    border-radius: 3px;
    min-width: 20px;
}
QScrollBar::handle:horizontal:hover {
    background: rgba(255, 255, 255, 80);
}
QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal,
QScrollBar::add-page:horizontal, QScrollBar::sub-page:horizontal {
    background: none;
    border: none;
    height: 0px;
    width: 0px;
}
"""

class InfoPill(QFrame):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("InfoPill")
        self.setFixedSize(360, 40)
        self.setStyleSheet("""
            QFrame#InfoPill {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 rgba(20, 25, 35, 240), stop:1 rgba(10, 15, 20, 250));
                border: 1px solid rgba(0, 240, 255, 45);
                border-radius: 20px;
            }
        """)
        
        main_l = QHBoxLayout(self); main_l.setContentsMargins(18, 0, 18, 0); main_l.setSpacing(12)
        
        self.icon_cnt = QWidget(); self.icon_cnt.setFixedSize(20, 20)
        self.icon = QLabel(self.icon_cnt); self.icon.setPixmap(VectorIcon.icon("assets/info.svg", "#00f0ff").pixmap(18, 18))
        main_l.addWidget(self.icon_cnt)
        
        # Marquee Container
        self.scroll_area = QWidget(); self.scroll_area.setFixedHeight(24)
        self.label = QLabel("", self.scroll_area); self.label.setStyleSheet("color: #ffffff; font-family: 'Segoe UI Variable Display'; font-size: 12px; font-weight: 700; letter-spacing: 0.5px;")
        self.label.setWordWrap(False)
        main_l.addWidget(self.scroll_area, 1)
        
        self.eff = QGraphicsOpacityEffect(self); self.setGraphicsEffect(self.eff)
        self.anim = QPropertyAnimation(self.eff, b"opacity")
        self.anim.setDuration(300); self.anim.setEasingCurve(QEasingCurve.Type.OutQuart)
        self.eff.setOpacity(0)
        
        self.marquee_anim = QPropertyAnimation(self.label, b"pos")
        self.marquee_anim.setDuration(4000); self.marquee_anim.setEasingCurve(QEasingCurve.Type.InOutSine)
        self.marquee_anim.setLoopCount(-1) # Infinite
        
    def set_text(self, text):
        self.marquee_anim.stop()
        self.label.move(0, self.label.y())
        
        if not text:
            self.anim.stop(); self.anim.setEndValue(0.0); self.anim.start()
        else:
            clean_text = text.replace("\n", "  •  ").upper()
            self.label.setText(clean_text)
            self.label.adjustSize()
            
            self.anim.stop(); self.anim.setEndValue(1.0); self.anim.start()
            
            # Start marquee if text is too wide
            QTimer.singleShot(100, self.check_marquee)

    def check_marquee(self):
        available = self.scroll_area.width()
        text_w = self.label.width()
        if text_w > available:
            diff = text_w - available + 30
            self.marquee_anim.setStartValue(QPoint(0, 3))
            self.marquee_anim.setEndValue(QPoint(-diff, 3))
            self.marquee_anim.start()
        else:
            self.label.move(0, 3)


PANEL_STYLE = """
QWidget#SettingPanel {
    background-color: transparent;
    border-radius: 15px;
}
"""

class SandboxFolderView(FolderView):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.is_sandbox = True
        self.anim_progress = 1.0 # Always expanded
    def refresh(self, new_paths=None):
        super().refresh(new_paths)
        if hasattr(self, 'grid_w') and hasattr(self, 'grid_h'):
            # Size to fit content but constrained
            self.setFixedSize(int(self.grid_w + 30), int(self.grid_h + 80))
            self.hw.setFixedSize(int(self.grid_w), 35)
            self.hw.show()
            self.cw.show()
    def dragEnterEvent(self, e):
        if e.mimeData().hasFormat("application/x-pandora-app"):
            e.acceptProposedAction()
    def dragMoveEvent(self, e):
        if e.mimeData().hasFormat("application/x-pandora-app"):
            import time
            p = e.position().toPoint() - self.cw.pos()
            
            # Auto-scroll paging logic
            current_time = time.time()
            if current_time - getattr(self, '_last_scroll_time', 0) > 0.5:
                if p.y() < 30 and self.current_page > 0:
                    self.scroll_to_page(self.current_page - 1)
                    self._last_scroll_time = current_time
                elif p.y() > self.grid_h - 30:
                    max_page = max(0, (getattr(self, 'content_h', self.grid_h) // getattr(self, 'cell_h', 115) - 1) // 3)
                    if self.current_page < max_page:
                        self.scroll_to_page(self.current_page + 1)
                        self._last_scroll_time = current_time

            # Improved Math: Detect closest insertion point with higher threshold
            cw = getattr(self, 'cell_w', 100)
            ch = getattr(self, 'cell_h', 115)
            col = int(p.x() // cw)
            row = int(max(0, adjusted_y) // ch)
            col = max(0, min(col, 2))
            
            idx = row * 3 + col
            if (p.x() % cw) > (cw * 0.85): 
                idx += 1

            if self.drag_placeholder_idx != idx:
                self.drag_placeholder_idx = idx
                self.refresh()
            e.acceptProposedAction()
    def dropEvent(self, e):
        # Override to handle sandbox drops purely in memory
        if e.mimeData().hasFormat("application/x-pandora-app"):
            import json
            dropped_apps = json.loads(e.mimeData().text())
            idx = max(0, min(self.drag_placeholder_idx, len(self.folder_data['apps'])))
            
            # For sandbox, we just reorder locally
            for ad in dropped_apps:
                # Remove first
                self.folder_data['apps'] = [a for a in self.folder_data['apps'] if a['path'] != ad['path']]
                # Insert at target index
                self.folder_data['apps'].insert(idx, ad)
                idx += 1
                
            self.is_dragging = False
            self.active_drag_app = None
            self.drag_placeholder_idx = -1
            self.refresh()
            e.acceptProposedAction()
        else:
            self.is_dragging = False; self.active_drag_app = None; self.drag_placeholder_idx = -1
            e.ignore()
    def paintEvent(self, e):
        # Draw a nice frame in sandbox mode
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        rad = self.get_setting('radius', 20)
        bg_col = QColor(self.get_setting('bg_color', '#141414'))
        bg_col.setAlpha(int(self.get_setting('opacity', 200)))
        p.setBrush(bg_col)
        p.setPen(QPen(QColor(255,255,255,20), 1))
        p.drawRoundedRect(QRectF(self.rect()).adjusted(1, 1, -1, -1), rad, rad)

class KeyRecordButton(QPushButton):
    key_recorded = pyqtSignal(int)
    def __init__(self, current_val):
        super().__init__()
        self.val = current_val; self.is_rec = False; self.update_text(); self.setFixedSize(120, 32); self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setStyleSheet("QPushButton { background: rgba(255,255,255,10); border: 1px solid rgba(255,255,255,20); border-radius: 6px; color: white; } QPushButton:hover { background: rgba(255,255,255,20); }")
        self.clicked.connect(self.start_rec)
    def start_rec(self): self.is_rec = True; self.setText("Click Any..."); self.grabMouse()
    def mousePressEvent(self, e):
        if self.is_rec:
            self.val = e.button().value; self.is_rec = False; self.releaseMouse(); self.update_text(); self.key_recorded.emit(self.val)
        else: super().mousePressEvent(e)
    def update_text(self):
        names = {1: "Left Click", 2: "Right Click", 4: "Middle Click", 8: "Side Button 1", 16: "Side Button 2"}
        self.setText(names.get(self.val, f"Button {self.val}"))
    def set_error(self, err):
        if err: self.setStyleSheet("QPushButton { background: rgba(255,85,85,40); border: 1px solid #FF5555; border-radius: 6px; color: #FF5555; }")
        else: self.setStyleSheet("QPushButton { background: rgba(255,255,255,10); border: 1px solid rgba(255,255,255,20); border-radius: 6px; color: white; }")

class KeyboardRecordButton(QPushButton):
    key_recorded = pyqtSignal(object)
    def __init__(self, current_val):
        super().__init__()
        self.val = str(current_val) if isinstance(current_val, str) else hex(current_val)
        self.is_rec = False; self.setFixedHeight(34); self.setMinimumWidth(140); self.setCursor(Qt.CursorShape.PointingHandCursor)
        self._update_style(False)
        self.update_text()
        self.clicked.connect(self.start_rec)
    def _update_style(self, recording):
        if recording:
            self.setStyleSheet("""QPushButton { background: rgba(0,240,255,12); border: 1px solid rgba(0,240,255,60); 
                border-radius: 6px; color: #00f0ff; font-size: 12px; font-weight: 600; padding: 0 12px; }""")
        else:
            self.setStyleSheet("""QPushButton { background: rgba(255,255,255,8); border: 1px solid rgba(255,255,255,15); 
                border-radius: 6px; color: #e0e0e0; font-size: 12px; font-weight: 600; padding: 0 12px; }
                QPushButton:hover { background: rgba(255,255,255,14); border: 1px solid rgba(0,240,255,40); color: white; }""")
    def start_rec(self): self.is_rec = True; self.setText("⌨  Press Key..."); self._update_style(True); self.setFocus()
    def keyPressEvent(self, e):
        if self.is_rec:
            mods = []
            if e.modifiers() & Qt.KeyboardModifier.ControlModifier: mods.append("Ctrl")
            if e.modifiers() & Qt.KeyboardModifier.AltModifier: mods.append("Alt")
            if e.modifiers() & Qt.KeyboardModifier.ShiftModifier: mods.append("Shift")
            
            vk = e.nativeVirtualKey()
            if vk in (0x10, 0x11, 0x12, 0xA0, 0xA1, 0xA2, 0xA3, 0xA4, 0xA5): 
                return
            
            self.val = "+".join(mods + [hex(vk)])
            self.is_rec = False; self.clearFocus(); self.update_text(); self._update_style(False); self.key_recorded.emit(self.val)
        else: super().keyPressEvent(e)
    def update_text(self):
        parts = str(self.val).split("+")
        vk_hex = parts[-1]
        try:
            vk = int(vk_hex, 16) if vk_hex.startswith("0x") else int(vk_hex)
            if vk == 0xC0: key_name = "Tilde (~)"
            elif 0x41 <= vk <= 0x5A or 0x30 <= vk <= 0x39: key_name = chr(vk).upper()
            else: key_name = hex(vk)
        except:
            key_name = vk_hex
        parts[-1] = key_name
        self.setText("⌨  " + " + ".join(parts))

class SandboxFolderIcon(QWidget):
    def __init__(self, cfg):
        super().__init__()
        self.setFixedSize(300, 250)
        self.cfg = cfg
        self.local_settings = copy.deepcopy(DEFAULTS['grid'])
        colors = ["#FF5555", "#50FA7B", "#F1FA8C", "#BD93F9", "#FF79C6", "#8BE9FD"]
        self.dummy_apps = [{"name": f"App {i+1}", "path": f"dummy_{i}", "pinned": False, "is_placeholder": True, "color": colors[i%len(colors)]} for i in range(12)]
        self.data = {
            "name": "Template Preview",
            "apps": self.dummy_apps,
            "template_type": "grid",
            "template_name": "Default",
            "show_title": True,
            "grid_snap": False,
            "show_cover": False,
            "left_click_action": "Launch App (if fanned)",
            "middle_click_action": "Open Folder"
        }
        self._hover_progress = 0.0
        self.hover_anim = QVariantAnimation(self); self.hover_anim.setDuration(250); self.hover_anim.setStartValue(0.0); self.hover_anim.setEndValue(1.0)
        self.hover_anim.valueChanged.connect(self._set_hp)
    def _set_hp(self, v): self._hover_progress = v; self.update()
    def trigger_pulse(self): pass # Dummy for sandbox
    def get_setting(self, key, default):
        # Sandbox uses local_settings which is already merged/resolved
        val = self.local_settings.get(key)
        if val is not None: return val
        # Fallback to general settings in cfg if not in template
        return self.cfg.get('general_settings', {}).get(key, default)
    def enterEvent(self, e): self.hover_anim.setDirection(QVariantAnimation.Direction.Forward); self.hover_anim.start()
    def leaveEvent(self, e): self.hover_anim.setDirection(QVariantAnimation.Direction.Backward); self.hover_anim.start()
    def paintEvent(self, e):
        p = QPainter(self)
        draw_folder_thumbnail(p, self.rect(), self.data, self.cfg, self.local_settings, self._hover_progress)
        if self.data.get('show_title', True):
            tc = QColor(self.local_settings.get('title_color', '#ffffff'))
            tc.setAlpha(int(tc.alpha() * (1.0 - self._hover_progress)))
            p.setPen(tc)
            fs = self.local_settings.get('folder_size', 80)
            p.drawText(QRect(0, int(self.height()/2 + fs/2 + 5), self.width(), 20), Qt.AlignmentFlag.AlignCenter, self.data['name'])

class FolderThumbnail(QWidget):
    """Small thumbnail used in individual folder settings."""
    def __init__(self, data, cfg):
        super().__init__(); self.setFixedSize(60, 60); self.data = data; self.cfg = cfg
    def update_data(self, data): self.data = data; self.update()
    def paintEvent(self, e):
        p = QPainter(self); draw_folder_thumbnail(p, self.rect(), self.data, self.cfg, local_settings={"folder_size": 48, "mini_icon_size": 16})

class PreviewPanel(QFrame):
    def __init__(self, cfg):
        super().__init__()
        self.setFixedWidth(400); self.setStyleSheet("PreviewPanel { background-color: transparent; border: none; }")
        l = QVBoxLayout(self); l.setContentsMargins(10, 20, 10, 20); l.setSpacing(15)
        t_cont = QWidget(); tl = QHBoxLayout(t_cont); tl.setContentsMargins(10, 0, 10, 0); tl.setSpacing(10)
        self.btn_collapsed = QPushButton("Collapsed"); self.btn_expanded = QPushButton("Expanded")
        for b in [self.btn_collapsed, self.btn_expanded]:
            b.setCheckable(True); b.setFixedHeight(32); b.setCursor(Qt.CursorShape.PointingHandCursor)
            b.setStyleSheet("QPushButton { color: #aaaaaa; background: transparent; border: 1px solid rgba(255,255,255,20); border-radius: 16px; } QPushButton:checked { color: #8BE9FD; background: rgba(139,233,253,20); border: 1px solid #8BE9FD; }")
        self.group = QButtonGroup(self); self.group.addButton(self.btn_collapsed); self.group.addButton(self.btn_expanded)
        self.btn_collapsed.setChecked(True); tl.addWidget(self.btn_collapsed); tl.addWidget(self.btn_expanded); l.addWidget(t_cont)
        self.stack = QStackedWidget(); l.addWidget(self.stack)
        self.collapsed_w = QWidget(); cl = QVBoxLayout(self.collapsed_w); cl.setContentsMargins(0,0,0,0)
        self.sandbox_icon = SandboxFolderIcon(cfg); cl.addWidget(self.sandbox_icon, 0, Qt.AlignmentFlag.AlignCenter)
        self.stack.addWidget(self.collapsed_w)
        self.expanded_w = QWidget(); el = QVBoxLayout(self.expanded_w); el.setContentsMargins(0,0,0,0)
        self.sandbox_view = SandboxFolderView(self.sandbox_icon.data, self.sandbox_icon, parent=self.expanded_w)
        self.sandbox_view.anim_progress = 1.0
        el.addWidget(self.sandbox_view, 1, Qt.AlignmentFlag.AlignCenter)
        self.stack.addWidget(self.expanded_w)
        self.btn_collapsed.clicked.connect(lambda: self.stack.setCurrentIndex(0))
        self.btn_expanded.clicked.connect(self.on_expanded_clicked)
    def on_expanded_clicked(self):
        self.sandbox_view.folder_data = self.sandbox_icon.data
        self.sandbox_view.refresh()
        self.stack.setCurrentIndex(1)

class SidebarButton(QWidget):
    clicked = pyqtSignal()
    def __init__(self, icon, text, parent=None):
        super().__init__(parent); self.icon = icon; self.text = text; self.setFixedHeight(40); self.setCursor(Qt.CursorShape.PointingHandCursor); self.is_active = False; self.is_hover = False
    def enterEvent(self, e): self.is_hover = True; self.update()
    def leaveEvent(self, e): self.is_hover = False; self.update()
    def mouseReleaseEvent(self, e): (self.clicked.emit() if e.button()==Qt.MouseButton.LeftButton else None)
    def set_active(self, a): self.is_active = a; self.update()
    def paintEvent(self, e):
        p = QPainter(self); p.setRenderHint(QPainter.RenderHint.Antialiasing)
        if self.is_active: p.fillRect(self.rect(), QColor(139, 233, 253, 20)); p.fillRect(0, 0, 3, self.height(), QColor(139, 233, 253)); p.setPen(QColor(139, 233, 253))
        else: (p.fillRect(self.rect(), QColor(255, 255, 255, 10)) if self.is_hover else None); p.setPen(QColor(170, 170, 170))
        ic = "#8be9fd" if self.is_active else ("#ffffff" if self.is_hover else "#aaaaaa")
        p.drawPixmap(15, 10, VectorIcon.icon(self.icon, ic).pixmap(20, 20))
        if self.width() > 60:
            alpha = int(max(0, min(255, (self.width() - 60) * 4)))
            p.setOpacity(alpha / 255.0)
            p.setFont(QFont("Segoe UI", 10)); p.drawText(QRect(55, 0, self.width()-55, self.height()), Qt.AlignmentFlag.AlignVCenter, self.text)

class SidebarToggle(QWidget):
    clicked = pyqtSignal()
    def __init__(self, icon_path):
        super().__init__(); self.icon_path = icon_path; self.setCursor(Qt.CursorShape.PointingHandCursor); self.setFixedHeight(40)
    def mouseReleaseEvent(self, e): (self.clicked.emit() if e.button()==Qt.MouseButton.LeftButton else None)
    def paintEvent(self, e):
        p = QPainter(self); p.setRenderHint(QPainter.RenderHint.Antialiasing)
        pix = QPixmap(self.icon_path).scaled(24, 24, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
        p.drawPixmap(13, 8, pix)
        if self.width() > 60:
            alpha = int(max(0, min(255, (self.width() - 60) * 4)))
            p.setOpacity(alpha / 255.0); p.setPen(Qt.GlobalColor.white); p.setFont(QFont("Segoe UI", 12, QFont.Weight.Bold))
            p.drawText(QRect(55, 0, self.width()-55, self.height()), Qt.AlignmentFlag.AlignVCenter, "Pandora")

class Sidebar(QFrame):
    tabChanged = pyqtSignal(int)
    def __init__(self, parent=None):
        super().__init__(parent); self.expanded = False; self.setFixedWidth(50)
        self.setStyleSheet("Sidebar { background-color: transparent; border: none; }")
        self.main_layout = QVBoxLayout(self); self.main_layout.setContentsMargins(0, 10, 0, 10); self.main_layout.setSpacing(5); self.main_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        
        self.t_btn = SidebarToggle("assets/Pandora.svg")
        self.t_btn.clicked.connect(self.toggle_sidebar); self.main_layout.addWidget(self.t_btn)
        
        self.main_layout.addSpacing(10)
        self.btns, self.current_idx = [], 0
        
        self.anim = QParallelAnimationGroup(self)
        self.w_anim = QPropertyAnimation(self, b"minimumWidth"); self.w_anim.setDuration(300); self.w_anim.setEasingCurve(QEasingCurve.Type.InOutQuart)
        self.m_anim = QPropertyAnimation(self, b"maximumWidth"); self.m_anim.setDuration(300); self.m_anim.setEasingCurve(QEasingCurve.Type.InOutQuart)
        self.anim.addAnimation(self.w_anim); self.anim.addAnimation(self.m_anim)

    def toggle_sidebar(self):
        self.expanded = not self.expanded; target = 180 if self.expanded else 50
        self.w_anim.setEndValue(target); self.m_anim.setEndValue(target)
        self.anim.start()
    def addTab(self, i, t):
        idx = len(self.btns); b = SidebarButton(i, t); b.clicked.connect(lambda: self.select_tab(idx))
        self.main_layout.addWidget(b); self.btns.append(b); self.update_styles()
    def select_tab(self, i): self.current_idx = i; self.update_styles(); self.tabChanged.emit(i)
    def update_styles(self): 
        for i, b in enumerate(self.btns): b.set_active(i == self.current_idx)

class CustomToggle(QWidget):
    toggled = pyqtSignal(bool)
    def __init__(self, checked=False, parent=None):
        super().__init__(parent); self.setFixedSize(54, 28); self._checked = checked; self._position = 28 if checked else 2
    def isChecked(self): return self._checked
    def setChecked(self, c): 
        if self._checked == c: return
        self._checked = c; self._position = 28 if c else 2; self.update(); self.toggled.emit(c)
    def mouseReleaseEvent(self, e): (self.setChecked(not self._checked) if e.button()==Qt.MouseButton.LeftButton else None)
    def paintEvent(self, e):
        p = QPainter(self); p.setRenderHint(QPainter.RenderHint.Antialiasing); bg = QColor("#8BE9FD") if self._checked else QColor(255, 255, 255, 40)
        p.setBrush(bg); p.setPen(Qt.PenStyle.NoPen); p.drawRoundedRect(self.rect(), 14, 14); p.setBrush(Qt.GlobalColor.white); p.drawEllipse(int(self._position), 4, 20, 20)

class SegmentedToggle(QWidget):
    valueChanged = pyqtSignal(str)
    
    def __init__(self, current_val, options, use_icons=False, tooltips=None, parent=None):
        super().__init__(parent)
        self.options, self.use_icons, self.current_val = options, use_icons, current_val
        self.setFixedHeight(30)
        layout = QHBoxLayout(self); layout.setContentsMargins(2, 2, 2, 2); layout.setSpacing(2)
        
        self.setStyleSheet("SegmentedToggle { background: rgba(255,255,255,10); border-radius: 8px; border: 1px solid rgba(255,255,255,20); }")
        self.buttons = {}
        for val, lbl_ic in options.items():
            btn = QPushButton()
            btn.setFixedSize(32, 24); btn.setCursor(Qt.CursorShape.PointingHandCursor)
            if not use_icons:
                btn.setText(lbl_ic); btn.setFont(QFont("Segoe UI Variable Display", 11, QFont.Weight.Bold))
            if tooltips and val in tooltips:
                btn.setToolTip(tooltips[val])
            btn.clicked.connect(lambda checked, v=val: self.set_value(v))
            layout.addWidget(btn); self.buttons[val] = btn
        layout.addStretch(); self.update_styles()
        
    def setTextValue(self, val):
        self.set_value(val)
        
    def set_value(self, val):
        if self.current_val != val:
            self.current_val = val
            self.update_styles()
            self.valueChanged.emit(val)
            
    def update_styles(self):
        for val, btn in self.buttons.items():
            is_active = (val == self.current_val)
            if self.use_icons:
                ic_col = "#00f0ff" if is_active else "#888888"
                btn.setIcon(VectorIcon.icon(self.options[val], ic_col))
                btn.setIconSize(QSize(18, 18))
            
            if is_active:
                btn.setStyleSheet("""
                    QPushButton {
                        background: rgba(0, 240, 255, 30);
                        color: #00f0ff;
                        border-radius: 6px;
                        border: 1px solid rgba(0, 240, 255, 60);
                    }
                """)
            else:
                btn.setStyleSheet("""
                    QPushButton {
                        background: transparent;
                        color: #888888;
                        border: none;
                    }
                    QPushButton:hover {
                        background: rgba(255, 255, 255, 10);
                        color: white;
                        border-radius: 6px;
                    }
                """)

class AnimatedStackedWidget(QStackedWidget):
    def __init__(self, parent=None): super().__init__(parent)
    def setCurrentIndex(self, i): super().setCurrentIndex(i)

class SmoothScrollArea(QScrollArea):
    def __init__(self, parent=None): super().__init__(parent); self.setFrameShape(QFrame.Shape.NoFrame)
    def wheelEvent(self, e):
        # Forward wheel events to any child QStackedWidget for pagination
        for child in self.widget().findChildren(QStackedWidget) if self.widget() else []:
            if child.objectName() == 'BankStack' and child.underMouse():
                delta = e.angleDelta().y()
                if delta > 0 and child.currentIndex() > 0:
                    child.setCurrentIndex(child.currentIndex() - 1)
                elif delta < 0 and child.currentIndex() < child.count() - 1:
                    child.setCurrentIndex(child.currentIndex() + 1)
                e.accept(); return
        super().wheelEvent(e)

class FolderTile(QFrame):
    clicked = pyqtSignal(str)
    def __init__(self, data, cfg):
        super().__init__(); self.data = data; self.cfg = cfg; self.setFixedSize(160, 180); self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setStyleSheet("FolderTile { background: rgba(255,255,255,4); border: 1px solid rgba(255,255,255,8); border-radius: 10px; } FolderTile:hover { background: rgba(255,255,255,8); border: 1px solid rgba(0,240,255,30); }")
        l = QVBoxLayout(self); l.setAlignment(Qt.AlignmentFlag.AlignCenter); l.setContentsMargins(10,12,10,10); l.setSpacing(8)
        self.icon_lbl = QWidget(); self.icon_lbl.setFixedSize(100, 100); l.addWidget(self.icon_lbl, 0, Qt.AlignmentFlag.AlignCenter)
        self.name_lbl = QLabel(data['name']); self.name_lbl.setStyleSheet("color: #e0e0e0; font-weight: 600; font-size: 12px;"); self.name_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter); l.addWidget(self.name_lbl)
    def mouseReleaseEvent(self, e): self.clicked.emit(self.data['id'])
    def paintEvent(self, e):
        super().paintEvent(e)
        p = QPainter(self); p.translate(self.icon_lbl.pos())
        draw_folder_thumbnail(p, QRect(0, 0, 100, 100), self.data, self.cfg)

class TemplateTile(QFrame):
    clicked = pyqtSignal(str, str)
    action = pyqtSignal(str, str, str) # action_type, t_type, name
    def __init__(self, t_type, name, is_default=False, is_flagged=False):
        super().__init__(); self.t_type = t_type; self.name = name; self.is_default = is_default
        self.setFixedSize(180, 120); self.setCursor(Qt.CursorShape.PointingHandCursor)
        border_style = "2px solid #50FA7B" if is_flagged else "1px solid rgba(255,255,255,5)"
        hover_border = "#50FA7B" if is_flagged else "#8BE9FD"
        self.setStyleSheet(f"TemplateTile {{ background: rgba(255,255,255,10); border-radius: 15px; border: {border_style}; }} TemplateTile:hover {{ background: rgba(255,255,255,15); border: 2px solid {hover_border}; }}")
        l = QVBoxLayout(self); l.setContentsMargins(15, 15, 15, 15); l.setSpacing(10)
        
        self.title = QLabel(name); self.title.setStyleSheet("color: white; font-weight: bold; font-size: 14px;"); l.addWidget(self.title)
        
        type_lbl = QLabel(t_type.title()); type_lbl.setStyleSheet("color: #aaaaaa; font-size: 11px;"); l.addWidget(type_lbl); l.addStretch()
        al = QHBoxLayout(); al.setSpacing(8); l.addLayout(al)
        def create_btn(path, tip, act, color="#aaaaaa"):
            b = QPushButton(); b.setFixedSize(28, 28); b.setCursor(Qt.CursorShape.PointingHandCursor); b.setToolTip(tip)
            b.setIcon(VectorIcon.icon(path, color)); b.setStyleSheet("QPushButton { background: rgba(255,255,255,10); border: none; border-radius: 6px; } QPushButton:hover { background: rgba(255,255,255,20); }")
            b.clicked.connect(lambda: self.action.emit(act, self.t_type, self.name)); return b
        
        if not is_default:
            al.addWidget(create_btn("assets/flag.svg", "Set as Preferred", "flag", "#50FA7B" if is_flagged else "#aaaaaa"))
        al.addWidget(create_btn("assets/duplicate.svg", "Duplicate", "duplicate"))
        if not is_default:
            al.addWidget(create_btn("assets/rename.svg", "Rename", "rename"))
            al.addWidget(create_btn("assets/delete.svg", "Delete", "delete"))
    def mouseReleaseEvent(self, e): 
        if e.button() == Qt.MouseButton.LeftButton:
            if self.childAt(e.position().toPoint()) is None or isinstance(self.childAt(e.position().toPoint()), (QLabel, QFrame)):
                self.clicked.emit(self.t_type, self.name)

class NativeWheelFilter(QAbstractNativeEventFilter):
    def __init__(self, dashboard):
        super().__init__()
        self.dashboard = dashboard
    def nativeEventFilter(self, eventType, message):
        if eventType == b"windows_generic_MSG":
            msg = wintypes.MSG.from_address(int(message))
            if msg.message == 0x020A: # WM_MOUSEWHEEL
                # Extract delta from wParam (high word)
                delta = ctypes.c_short(msg.wParam >> 16).value
                # Forward to any active FolderView that is dragging
                for icon in getattr(self.dashboard, 'app_instances', []):
                    if hasattr(icon, 'view') and icon.view and icon.view.isVisible() and getattr(icon.view, 'is_dragging', False):
                        if delta > 0: icon.view.scroll_to_page(icon.view.current_page - 1)
                        else: icon.view.scroll_to_page(icon.view.current_page + 1)
                        return True, 0
        return False, 0

class ToolGridButton(QPushButton):
    def __init__(self, tool, is_active, order_idx):
        super().__init__()
        self.tool = tool
        self.is_active = is_active
        self.order_idx = order_idx
        self.setFixedSize(100, 100) # Slightly larger
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setToolTip(tool['label'])

    def paintEvent(self, e):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)

        # Tactical Theme Colors (Valorant/Raycast)
        ACCENT = QColor(0, 240, 255) # Electric Cyan
        BG_ACTIVE = QColor(0, 240, 255, 30)
        BG_INACTIVE = QColor(255, 255, 255, 5)
        
        # Background
        if self.is_active:
            grad = QLinearGradient(0, 0, 0, self.height())
            grad.setColorAt(0, BG_ACTIVE); grad.setColorAt(1, QColor(157, 0, 255, 10))
            p.setBrush(grad)
        else:
            p.setBrush(BG_INACTIVE if not self.underMouse() else QColor(255,255,255,10))
            
        # Sharp border
        pen = QPen(ACCENT if self.is_active else QColor(255, 255, 255, 15))
        pen.setWidth(2 if self.is_active else 1)
        p.setPen(pen)
        p.drawRoundedRect(self.rect().adjusted(1,1,-1,-1), 4, 4) # Sharper corners

        # Icon
        ic_col = "#00f0ff" if self.is_active else "#666666"
        pix = VectorIcon.icon(self.tool['icon'], ic_col).pixmap(36, 36)
        p.drawPixmap(int((self.width()-36)/2), 22, pix)
        
        # Label
        p.setPen(QColor(255,255,255) if self.is_active else QColor(140,140,140))
        p.setFont(QFont("Segoe UI Variable Display", 8, QFont.Weight.Bold))
        label = self.tool['label']
        if self.tool['id'] == "mute":
            from utils import get_system_mute
            label = "UNMUTE" if get_system_mute() else "MUTE"
        p.drawText(QRectF(0, 68, self.width(), 20), Qt.AlignmentFlag.AlignCenter, label.upper())

        # Glowing Badge
        if self.is_active:
            # Outer glow
            glow = QRadialGradient(82, 18, 12)
            glow.setColorAt(0, QColor(0, 240, 255, 150)); glow.setColorAt(1, Qt.GlobalColor.transparent)
            p.setBrush(glow); p.setPen(Qt.PenStyle.NoPen); p.drawEllipse(70, 6, 24, 24)
            
            # Badge circle
            p.setBrush(ACCENT)
            p.drawEllipse(74, 10, 16, 16)
            p.setPen(QColor(0,0,0))
            p.setFont(QFont("Segoe UI Variable Display", 8, QFont.Weight.Black))
            p.drawText(QRectF(74, 10, 16, 16), Qt.AlignmentFlag.AlignCenter, str(self.order_idx))

class SandboxRadialMenu(QWidget):
    def __init__(self, dashboard):
        super().__init__()
        self.dashboard = dashboard
        self.setFixedSize(400, 400)
        self.setMouseTracking(True)
        self.active_index = -1
        self.drag_start_index = -1
        self.drag_current_pos = None
        self.center_pt = QPoint(200, 200)
        self.outer_radius = 160
        self.inner_radius = 80
        self.deadzone = 30
        self.opacity = 185
        self.tools = []

    def update_settings(self, cfg):
        rad_cfg = cfg.get('radial_menu', {})
        # Scale down for preview if radius is very large
        full_radius = rad_cfg.get('radius', 160)
        self.outer_radius = min(180, full_radius) # Cap at 180 for 400x400 widget
        self.inner_radius = self.outer_radius // 2
        self.deadzone = rad_cfg.get('deadzone', 30)
        self.opacity = rad_cfg.get('opacity', 185)
        self.update()

    def update_tools(self, tools):
        self.tools = tools
        self.update()

    def mouseMoveEvent(self, e):
        self.drag_current_pos = e.pos()
        self._handle_mouse(e.pos())
        
    def dragMoveEvent(self, e):
        self._handle_mouse(e.position().toPoint())
        e.acceptProposedAction()
        
    def _handle_mouse(self, pos):
        dx = pos.x() - self.center_pt.x()
        dy = pos.y() - self.center_pt.y()
        dist = math.sqrt(dx*dx + dy*dy)
        num_tools = len(self.tools)
        if num_tools == 0: return
        if dist < self.deadzone:
            new_idx = -1
        else:
            angle = math.degrees(math.atan2(dx, -dy))
            if angle < 0: angle += 360
            angle_step = 360.0 / num_tools
            new_idx = int((angle + angle_step/2) % 360 // angle_step)
        if self.active_index != new_idx:
            self.active_index = new_idx
            self.update()
        elif self.drag_start_index != -1:
            self.update()

    def leaveEvent(self, e):
        self.active_index = -1
        self.drag_current_pos = None
        self.update()

    def mousePressEvent(self, e):
        if self.active_index != -1 and self.active_index < len(self.tools):
            if e.button() == Qt.MouseButton.RightButton:
                t = self.tools[self.active_index]
                self.dashboard.remove_radial_tool_by_id(t['id'])
                self.active_index = -1
                self.drag_start_index = -1
                self.update()
            elif e.button() == Qt.MouseButton.LeftButton:
                self.drag_start_index = self.active_index
                self.drag_current_pos = e.pos()
                self.update()

    def mouseReleaseEvent(self, e):
        if hasattr(self, 'drag_start_index') and self.drag_start_index != -1:
            if self.active_index != -1 and self.active_index != self.drag_start_index:
                # Swap tools instead of pushing/rearranging
                self.tools[self.drag_start_index], self.tools[self.active_index] = \
                    self.tools[self.active_index], self.tools[self.drag_start_index]
                self.dashboard.save_radial_order_from_sandbox(self.tools)
            self.drag_start_index = -1
            self.drag_current_pos = None
            self.update()

    def paintEvent(self, e):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.setRenderHint(QPainter.RenderHint.TextAntialiasing)
        p.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
        
        cx, cy = self.center_pt.x(), self.center_pt.y()
        
        # 1. Radar background pattern
        p.setOpacity(0.08)
        p.setPen(QPen(QColor(0, 240, 255), 1))
        for r in [60, 100, 140, 180]:
            p.drawEllipse(self.center_pt, r, r)
        p.drawLine(cx-200, cy, cx+200, cy)
        p.drawLine(cx, cy-200, cx, cy+200)
        # Diagonal crosshairs
        p.setOpacity(0.04)
        p.drawLine(cx-140, cy-140, cx+140, cy+140)
        p.drawLine(cx-140, cy+140, cx+140, cy-140)
        p.setOpacity(1.0)

        # 2. Background Ring
        bg_path = QPainterPath()
        bg_path.addEllipse(QPointF(self.center_pt), self.outer_radius, self.outer_radius)
        hole = QPainterPath()
        hole.addEllipse(QPointF(self.center_pt), self.inner_radius, self.inner_radius)
        p.setBrush(QColor(15, 23, 34, self.opacity))
        p.setPen(QPen(QColor(0, 240, 255, 30), 1))
        p.drawPath(bg_path.subtracted(hole))

        # 3. Empty slot dashed circles — aligned to actual tool positions
        dist_ic = (self.inner_radius + self.outer_radius) / 2
        num_slots = max(len(self.tools), 8)  # Show at least 8 slot positions
        slot_step = 360.0 / num_slots
        p.setPen(QPen(QColor(255,255,255,15), 1, Qt.PenStyle.DashLine))
        for i in range(num_slots):
            angle_rad = math.radians(i * slot_step)
            tx = cx + math.sin(angle_rad) * dist_ic
            ty = cy - math.cos(angle_rad) * dist_ic
            p.drawEllipse(QPointF(tx, ty), 14, 14)

        num_tools = len(self.tools)
        if num_tools == 0:
            p.setPen(QColor(0, 240, 255, 80))
            p.setFont(QFont("Segoe UI Variable Display", 9, QFont.Weight.Bold))
            p.drawText(self.rect(), Qt.AlignmentFlag.AlignCenter, "NO TOOLS ASSIGNED")
            return
            
        angle_step = 360.0 / num_tools
        is_dragging = self.drag_start_index != -1

        # 4. Active sector highlight
        if self.active_index != -1 and self.active_index < num_tools:
            i = self.active_index
            path = QPainterPath()
            start_angle = 90 - (i * angle_step) + (angle_step / 2)
            span_angle = -angle_step
            r_outer = self.outer_radius + 4
            r_inner = self.inner_radius - 2
            path.arcMoveTo(QRectF(cx - r_outer, cy - r_outer, r_outer*2, r_outer*2), start_angle)
            path.arcTo(QRectF(cx - r_outer, cy - r_outer, r_outer*2, r_outer*2), start_angle, span_angle)
            path.arcTo(QRectF(cx - r_inner, cy - r_inner, r_inner*2, r_inner*2), start_angle + span_angle, -span_angle)
            path.closeSubpath()
            
            grad = QLinearGradient(cx, cy - r_outer, cx, cy + r_outer)
            if is_dragging and self.active_index != self.drag_start_index:
                grad.setColorAt(0, QColor(0, 255, 150, 200)); grad.setColorAt(1, QColor(0, 180, 80, 200))
            else:
                grad.setColorAt(0, QColor(0, 240, 255, 200)); grad.setColorAt(1, QColor(157, 0, 255, 200))
            p.setBrush(grad); p.setPen(QPen(QColor(255,255,255,80), 1)); p.drawPath(path)
            
        # 5. Tool icons
        for i in range(num_tools):
            if is_dragging and i == self.drag_start_index: continue
            is_active = (i == self.active_index)
            angle_rad = math.radians(i * angle_step)
            tx = cx + math.sin(angle_rad) * dist_ic
            ty = cy - math.cos(angle_rad) * dist_ic
            tool = self.tools[i]
            ic_col = "#00f0ff" if is_active else "#ffffff"
            pix_size = 28 if is_active else 22
            pix = VectorIcon.icon(tool['icon'], ic_col).pixmap(pix_size, pix_size)
            p.drawPixmap(int(tx - pix_size//2), int(ty - pix_size//2), pix)

        # 6. Center HUD
        p.setBrush(QColor(8, 12, 18, 180))
        p.setPen(QPen(QColor(0, 240, 255, 60), 1))
        p.drawEllipse(self.center_pt, self.inner_radius - 12, self.inner_radius - 12)
        
        if self.active_index != -1 and self.active_index < num_tools:
            if is_dragging and self.active_index != self.drag_start_index:
                p.setPen(QColor(0, 255, 150))
                p.setFont(QFont("Segoe UI Variable Display", 10, QFont.Weight.Bold))
                p.drawText(QRectF(cx-100, cy-12, 200, 24), Qt.AlignmentFlag.AlignCenter, "MOVE HERE")
            else:
                tool = self.tools[self.active_index]
                p.setPen(QColor(255,255,255))
                p.setFont(QFont("Segoe UI Variable Display", 11, QFont.Weight.Bold))
                p.drawText(QRectF(cx-100, cy-14, 200, 24), Qt.AlignmentFlag.AlignCenter, tool['label'].upper())
                p.setPen(QColor(0, 240, 255, 120))
                p.setFont(QFont("Segoe UI Variable Display", 7, QFont.Weight.Black))
                p.drawText(QRectF(cx-100, cy+10, 200, 16), Qt.AlignmentFlag.AlignCenter, "RADIAL CALIBRATION" if not is_dragging else "DRAGGING...")
        else:
            p.setPen(QColor(255,255,255,120))
            p.setFont(QFont("Segoe UI Variable Display", 10, QFont.Weight.Bold))
            p.drawText(QRectF(cx-100, cy-14, 200, 24), Qt.AlignmentFlag.AlignCenter, "PREVIEW MODE")
            p.setPen(QColor(0, 240, 255, 70))
            p.setFont(QFont("Segoe UI Variable Display", 7, QFont.Weight.Black))
            p.drawText(QRectF(cx-100, cy+10, 200, 16), Qt.AlignmentFlag.AlignCenter, "RADIAL OS HUD")

        # 7. Drag ghost
        if is_dragging and self.drag_current_pos:
            tool = self.tools[self.drag_start_index]
            pix = VectorIcon.icon(tool['icon'], "#ffffff").pixmap(28, 28)
            p.setOpacity(0.7)
            p.drawPixmap(self.drag_current_pos.x() - 14, self.drag_current_pos.y() - 14, pix)
            p.setOpacity(1.0)



class DashboardUI(QMainWindow):
    def __init__(self, cfg, app_instances):
        super().__init__(); self.cfg, self.app_instances = cfg, app_instances; self.current_fid = None
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.Window); self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground); self.setFixedSize(1200, 700)
        self.setWindowIcon(QIcon("assets/Pandora.svg"))
        self.setStyleSheet(SCROLLBAR_CSS)
        self.cw = QWidget(); self.setCentralWidget(self.cw); self.main_layout = QHBoxLayout(self.cw); self.main_layout.setContentsMargins(0,0,0,0); self.main_layout.setSpacing(0)
        self.sidebar = Sidebar()
        self.sidebar.addTab("assets/general.svg", "General"); self.sidebar.addTab("assets/template.svg", "Templates"); self.sidebar.addTab("assets/folders.svg", "Folders"); self.sidebar.addTab("assets/reset.svg", "Menu")
        self.main_layout.addWidget(self.sidebar)
        
        right_area = QVBoxLayout(); right_area.setContentsMargins(0,0,0,0); right_area.setSpacing(0)
        self.main_layout.addLayout(right_area, 1)
        
        self.top_bar = QHBoxLayout(); self.top_bar.setContentsMargins(0, 10, 20, 0)
        self.top_bar.addStretch()
        self.close_btn = QPushButton("✕"); self.close_btn.setFixedSize(32, 32); self.close_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.close_btn.setStyleSheet("QPushButton { background-color: rgba(255,255,255,15); color: #ffffff; border: none; font-weight: bold; font-size: 14px; border-radius: 16px;} QPushButton:hover { background-color: #ff4c4c; }")
        self.close_btn.clicked.connect(self.close); self.top_bar.addWidget(self.close_btn)
        right_area.addLayout(self.top_bar)
        
        content_area = QHBoxLayout(); content_area.setSpacing(0)
        right_area.addLayout(content_area, 1)
        self.stack = AnimatedStackedWidget(); content_area.addWidget(self.stack, 1); self.stack.currentChanged.connect(self.update_preview_visibility)
        self.preview_panel = PreviewPanel(cfg); content_area.addWidget(self.preview_panel)
        
        self.setup_general_tab(); self.setup_templates_tab(); self.setup_individual_tab(); self.setup_radial_tab()
        self.sidebar.tabChanged.connect(self.on_tab_changed); self.refresh_grid()
        # Setup Info Pill HUD
        self.info_pill = InfoPill(self)
        self.info_pill.move(self.width() - 380, self.height() - 60)
        QApplication.instance().installEventFilter(self)
        
        # Setup Low-Level Hook for Drag-Wheel support
        self._hook = None
        self._hook_proc = None

    def _setup_drag_hook(self):
        """Install a low-level mouse hook to catch wheel events during Windows DoDragDrop loop."""
        if self._hook: return
        
        CMPFUNC = ctypes.WINFUNCTYPE(ctypes.c_int, ctypes.c_int, ctypes.c_int, ctypes.POINTER(ctypes.c_void_p))
        
        def hook_callback(nCode, wParam, lParam):
            if nCode >= 0 and wParam == 0x020A: # WM_MOUSEWHEEL
                # lParam is a pointer to MSLLHOOKSTRUCT
                # Offset 8 in MSLLHOOKSTRUCT is mouseData (high word is delta)
                data = ctypes.cast(lParam, ctypes.POINTER(ctypes.c_uint32))
                mouseData = data[2] # 3rd uint32 is mouseData
                delta = ctypes.c_short(mouseData >> 16).value
                
                # Signal the dashboard to scroll
                if delta != 0:
                    for icon in getattr(self, 'app_instances', []):
                        if hasattr(icon, 'view') and icon.view and icon.view.isVisible() and getattr(icon.view, 'is_dragging', False):
                            if delta > 0: icon.view.scroll_to_page(icon.view.current_page - 1)
                            else: icon.view.scroll_to_page(icon.view.current_page + 1)
                            # We don't return True here to allow other apps to see the wheel too
            return ctypes.windll.user32.CallNextHookEx(self._hook, nCode, wParam, lParam)

        self._hook_proc = CMPFUNC(hook_callback)
        self._hook = ctypes.windll.user32.SetWindowsHookExW(14, self._hook_proc, None, 0) # WH_MOUSE_LL = 14

    def _remove_drag_hook(self):
        if self._hook:
            ctypes.windll.user32.UnhookWindowsHookEx(self._hook)
            self._hook = None
            self._hook_proc = None

    def eventFilter(self, obj, e):
        if e.type() == QEvent.Type.ToolTip:
            if hasattr(obj, 'toolTip') and obj.toolTip():
                self.info_pill.set_text(obj.toolTip())
                return True
        elif e.type() in [QEvent.Type.Leave, QEvent.Type.MouseButtonPress]:
            self.info_pill.set_text(None)
        elif e.type() == QEvent.Type.Wheel:
            # Standard Qt path (works when NOT in modal drag loop)
            for icon in getattr(self, 'app_instances', []):
                if hasattr(icon, 'view') and icon.view and icon.view.isVisible() and getattr(icon.view, 'is_dragging', False):
                    icon.view.wheelEvent(e)
                    return True
        return super().eventFilter(obj, e)
    def prewarm(self):
        self.setWindowOpacity(0.0); self.show()
        for i in range(len(self.sidebar.btns)): self.sidebar.select_tab(i); QApplication.processEvents()
        self.hide(); self.setWindowOpacity(1.0); self.sidebar.select_tab(0)
    def setup_general_tab(self):
        GLASS_CARD = "QFrame#GlassCard { background: rgba(255,255,255,3); border: 1px solid rgba(255,255,255,8); border-radius: 8px; }"
        SECTION_LBL = "color: #00f0ff; font-size: 11px; font-weight: 700; letter-spacing: 2px; font-family: 'Segoe UI Variable Display';"
        
        main_page = QWidget(); main_page.setObjectName("SettingPanel"); main_page.setStyleSheet(PANEL_STYLE)
        main_l = QVBoxLayout(main_page); main_l.setContentsMargins(0, 0, 0, 0); main_l.setSpacing(0)
        
        header_cnt = QWidget(); hl = QVBoxLayout(header_cnt); hl.setContentsMargins(40, 30, 40, 10)
        hl.addWidget(self.create_header("GENERAL SETTINGS")); main_l.addWidget(header_cnt)
        
        scroll = SmoothScrollArea(); scroll.setWidgetResizable(True); scroll.setStyleSheet("QScrollArea { background: transparent; border: none; }")
        inner = QWidget(); inner.setStyleSheet("background: transparent;")
        l = QVBoxLayout(inner); l.setContentsMargins(40, 0, 40, 30); l.setSpacing(24)
        
        c1 = QFrame(); c1.setObjectName("GlassCard"); c1.setStyleSheet(GLASS_CARD)
        c1l = QVBoxLayout(c1); c1l.setContentsMargins(20,16,20,16); c1l.setSpacing(14)
        c1l.addWidget(QLabel("◆  APPEARANCE", styleSheet=SECTION_LBL))
        f = QFormLayout(); f.setSpacing(14); c1l.addLayout(f)
        self.add_slider(f, "Grid Size", 40, 200, self.cfg.get('general_settings', {}).get('grid_size', 110), lambda v: self.upd_gen('grid_size', v))
        self.add_slider(f, "Edge Padding", 0, 100, self.cfg.get('general_settings', {}).get('edge_padding', 0), lambda v: self.upd_gen('edge_padding', v))
        self.add_toggle(f, "Show Grid on Drag", self.cfg.get('general_settings', {}).get('show_grid_on_drag', True), lambda v: self.upd_gen('show_grid_on_drag', v))
        self.add_toggle(f, "Animated Grid Color", self.cfg.get('general_settings', {}).get('grid_animated_color', True), lambda v: self.upd_gen('grid_animated_color', v))
        self.add_toggle(f, "Wave Entrance", self.cfg.get('general_settings', {}).get('grid_wave_entrance', True), lambda v: self.upd_gen('grid_wave_entrance', v))
        self.add_toggle(f, "Wave Color Fade", self.cfg.get('general_settings', {}).get('grid_wave_fade', True), lambda v: self.upd_gen('grid_wave_fade', v))
        self.add_slider(f, "Grid Visibility", 10, 100, self.cfg.get('general_settings', {}).get('grid_opacity', 100), lambda v: self.upd_gen('grid_opacity', v))
        l.addWidget(c1)
        
        c2 = QFrame(); c2.setObjectName("GlassCard"); c2.setStyleSheet(GLASS_CARD)
        c2l = QVBoxLayout(c2); c2l.setContentsMargins(20,16,20,16); c2l.setSpacing(14)
        c2l.addWidget(QLabel("◆  INTERACTION", styleSheet=SECTION_LBL))
        if_lay1 = QFormLayout(); if_lay1.setSpacing(14); c2l.addLayout(if_lay1)
        l.addWidget(c2)
        
        c3 = QFrame(); c3.setObjectName("GlassCard"); c3.setStyleSheet(GLASS_CARD)
        c3l = QVBoxLayout(c3); c3l.setContentsMargins(20,16,20,16); c3l.setSpacing(14)
        c3l.addWidget(QLabel("◆  BINDINGS", styleSheet=SECTION_LBL))
        if_lay = QFormLayout(); if_lay.setSpacing(14); c3l.addLayout(if_lay)
        l.addWidget(c3)
        
        kb = self.cfg.get('general_settings', {}).get('keybinds', {"launch_app": 1, "open_folder": 4, "show_menu": 2})
        self.recorders = {}
        for k, label in [("launch_app", "Launch App"), ("open_folder", "Open Folder"), ("show_menu", "Show Menu")]:
            rec = KeyRecordButton(kb.get(k, 1))
            rec.key_recorded.connect(lambda v, key=k: self.upd_kb(key, v))
            self.recorders[k] = rec
            if_lay.addRow(self.create_label(label), rec)
        self.check_kb_collisions()
        
        c4 = QFrame(); c4.setObjectName("GlassCard"); c4.setStyleSheet(GLASS_CARD)
        c4l = QVBoxLayout(c4); c4l.setContentsMargins(20,16,20,16); c4l.setSpacing(14)
        c4l.addWidget(QLabel("◆  RADIAL MENU ACTIVATION", styleSheet=SECTION_LBL))
        f4 = QFormLayout(); f4.setSpacing(14); c4l.addLayout(f4)
        self.kb_btn = KeyboardRecordButton(self.cfg.get('radial_menu', {}).get('activation_key', 0xC0))
        self.kb_btn.key_recorded.connect(lambda v: self.upd_radial('activation_key', v))
        f4.addRow(self.create_label("Activation Key"), self.kb_btn)
        self.rad_mode = SegmentedToggle(self.cfg.get('radial_menu', {}).get('hold_mode', 'Hold'), 
                                       {"Hold": "assets/hold.svg", "Toggle": "assets/tap.svg"}, use_icons=True,
                                       tooltips={"Hold": "HOLD: Menu stays open only while the key is held.", "Toggle": "TOGGLE: Tap once to open, tap again to close."})
        self.rad_mode.valueChanged.connect(lambda v: self.upd_radial('hold_mode', v))
        f4.addRow(self.create_label("Activation Mode"), self.rad_mode)
        l.addWidget(c4)

        c5 = QFrame(); c5.setObjectName("GlassCard"); c5.setStyleSheet(GLASS_CARD)
        c5l = QVBoxLayout(c5); c5l.setContentsMargins(20,16,20,16); c5l.setSpacing(14)
        c5l.addWidget(QLabel("◆  RADIAL MENU APPEARANCE", styleSheet=SECTION_LBL))
        f5 = QFormLayout(); f5.setSpacing(14); c5l.addLayout(f5)
        self.rad_theme = DropdownButton(self.cfg.get('radial_menu', {}).get('theme', 'Dark'), ["Dark", "Light", "Glass"])
        self.rad_theme.valueChanged.connect(lambda v: self.upd_radial('theme', v))
        f5.addRow(self.create_label("Visual Theme"), self.rad_theme)
        
        # 7-way gap toggle
        self.rad_gap = SegmentedToggle(str(self.cfg.get('radial_menu', {}).get('gap_size', 75)), 
                                       {"0": "0", "15": "15", "30": "30", "45": "45", "60": "60", "75": "75", "90": "90"}, 
                                       use_icons=False,
                                       tooltips={k: f"Arc Gap: {k}px spacing" for k in ["0","15","30","45","60","75","90"]})
        self.rad_gap.valueChanged.connect(lambda v: self.upd_radial('gap_size', int(v)))
        f5.addRow(self.create_label("HUD Arc Gap"), self.rad_gap)
        def create_slider(key, label, min_val, max_val, default):
            def reset():
                self.upd_radial(key, default)
                slider.setValue(default)
            slider = self.add_slider(f5, label, min_val, max_val, self.cfg.get('radial_menu', {}).get(key, default), lambda v: self.upd_radial(key, v), reset)
            return slider
            
        self.rad_radius_s = create_slider('radius', "Menu Radius", 100, 300, 160)
        self.rad_opacity_s = create_slider('opacity', "BG Opacity", 50, 255, 185)
        self.rad_deadzone_s = create_slider('deadzone', "Center Deadzone", 10, 100, 30)
        self.rad_scroll_sens_s = create_slider('scroll_sens', "Scroll Sensitivity", 1, 100, 50)
        self.rad_mouse_sens_s = create_slider('mouse_sens', "Mouse Sensitivity", 10, 200, 100)
        l.addWidget(c5)
        
        # DISPLAY EFFECTS ENGINE
        c6 = QFrame(); c6.setObjectName("GlassCard"); c6.setStyleSheet(GLASS_CARD)
        c6l = QVBoxLayout(c6); c6l.setContentsMargins(20,16,20,16); c6l.setSpacing(14)
        c6l.addWidget(QLabel("◆  DISPLAY EFFECTS (WARM FILTER)", styleSheet=SECTION_LBL))
        f6 = QFormLayout(); f6.setSpacing(14); c6l.addLayout(f6)
        
        from utils import DisplayEffectsEngine
        engine = DisplayEffectsEngine.instance()
        
        self.disp_preset = SegmentedToggle(self.cfg.get('display_effects', {}).get('active_preset', 'Sunset'), 
                                           {"Reading": "R", "Sunset": "S", "Movie": "M", "Eye Saver": "E"}, use_icons=False,
                                           tooltips={"Reading": "READING: Deep warmth, zero blue light.", 
                                                     "Sunset": "SUNSET: Natural evening tones.", 
                                                     "Movie": "MOVIE: Cinematic color preservation.", 
                                                     "Eye Saver": "EYE SAVER: Maximum comfort for long sessions."})
        self.disp_preset.valueChanged.connect(lambda v: self.upd_display_effect('active_preset', v))
        f6.addRow(self.create_label("Filter Preset"), self.disp_preset)
        
        self.add_slider(f6, "Warmth Intensity", 0, 100, self.cfg.get('display_effects', {}).get('warmth_intensity', 50), 
                        lambda v: self.upd_display_effect('warmth_intensity', v), 
                        lambda: self.upd_display_effect('warmth_intensity', 50))
        l.addWidget(c6)
        
        l.addStretch(); scroll.setWidget(inner); main_l.addWidget(scroll); self.stack.addWidget(main_page)
    def upd_display_effect(self, k, v):
        if 'display_effects' not in self.cfg: self.cfg['display_effects'] = {}
        self.cfg['display_effects'][k] = v; ConfigManager.save(self.cfg)
        from utils import DisplayEffectsEngine
        engine = DisplayEffectsEngine.instance()
        if k == 'active_preset': engine.set_preset(v)
        elif k == 'warmth_intensity': engine.set_intensity(v / 100.0)
    def upd_kb(self, k, v):
        if 'keybinds' not in self.cfg['general_settings']: self.cfg['general_settings']['keybinds'] = {}
        self.cfg['general_settings']['keybinds'][k] = v; ConfigManager.save(self.cfg); self.check_kb_collisions(); self.update_instances()
    def check_kb_collisions(self):
        kb = self.cfg.get('general_settings', {}).get('keybinds', {})
        vals = list(kb.values())
        for k, rec in self.recorders.items():
            val = kb.get(k)
            rec.set_error(vals.count(val) > 1)
    def upd_gen(self, k, v):
        self.cfg['general_settings'][k] = v; ConfigManager.save(self.cfg); self.update_instances()
        if hasattr(self, 'grid_overlay'): self.grid_overlay.update()
    def setup_templates_tab(self):
        self.templates_tab = QWidget(); self.templates_tab.setObjectName("SettingPanel"); self.templates_tab.setStyleSheet(PANEL_STYLE)
        self.temp_main_l = QVBoxLayout(self.templates_tab); self.stack.addWidget(self.templates_tab)
        
        self.temp_stack = QStackedWidget(); self.temp_main_l.addWidget(self.temp_stack); self.temp_stack.currentChanged.connect(self.update_preview_visibility)
        
        # PAGE 1: Template List
        self.temp_list_page = QWidget(); tlp_l = QVBoxLayout(self.temp_list_page); tlp_l.setContentsMargins(40, 40, 40, 40); tlp_l.setSpacing(20)
        tlp_header = QHBoxLayout(); tlp_header.addWidget(self.create_header("TEMPLATE MANAGEMENT")); tlp_header.addStretch()
        add_btn = QPushButton("+ Create New Template"); add_btn.setFixedHeight(35); add_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        add_btn.setStyleSheet("QPushButton { color: #8BE9FD; border: 1px dashed #8BE9FD; border-radius: 8px; padding: 0 15px; } QPushButton:hover { background: rgba(139,233,253,20); }")
        add_btn.clicked.connect(self.prompt_new_template); tlp_header.addWidget(add_btn); tlp_l.addLayout(tlp_header)
        
        self.temp_scroll = SmoothScrollArea(); self.temp_scroll.setWidgetResizable(True); self.temp_scroll.setStyleSheet(SCROLLBAR_CSS)
        self.temp_list_cnt = QWidget(); self.temp_list_l = QVBoxLayout(self.temp_list_cnt); self.temp_list_l.setAlignment(Qt.AlignmentFlag.AlignTop); self.temp_list_l.setSpacing(30)
        self.temp_scroll.setWidget(self.temp_list_cnt); tlp_l.addWidget(self.temp_scroll)
        self.temp_stack.addWidget(self.temp_list_page)
        
        # PAGE 2: Template Editor
        self.temp_editor_page = QWidget(); tep_l = QVBoxLayout(self.temp_editor_page); tep_l.setContentsMargins(0, 0, 0, 0)
        tep_header = QHBoxLayout(); tep_header.setContentsMargins(40, 20, 40, 0)
        back_btn = QPushButton(); back_btn.setFixedSize(30, 30); back_btn.setIcon(VectorIcon.icon("assets/back.svg", "#aaaaaa")); back_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        back_btn.setStyleSheet("background: transparent; border: none;"); back_btn.clicked.connect(self.back_to_template_list)
        self.editor_title = QLabel("Template Name"); self.editor_title.setStyleSheet("color: #8BE9FD; font-weight: bold; font-size: 16px; margin-left: 10px;")
        tep_header.addWidget(back_btn); tep_header.addWidget(self.editor_title); tep_header.addStretch(); tep_l.addLayout(tep_header)
        
        self.t_scroll = SmoothScrollArea(); self.t_scroll.setWidgetResizable(True); self.t_scroll.setStyleSheet(SCROLLBAR_CSS)
        self.t_form_cnt = QWidget(); self.t_form = QVBoxLayout(self.t_form_cnt); self.t_form.setContentsMargins(40, 20, 50, 40); self.t_form.setSpacing(20); self.t_scroll.setWidget(self.t_form_cnt)
        tep_l.addWidget(self.t_scroll); self.temp_stack.addWidget(self.temp_editor_page)
        
        self.current_temp_type = "grid"; self.current_temp_name = "Default"; self.refresh_template_list()

    def back_to_template_list(self):
        self.temp_stack.setCurrentIndex(0); self.preview_panel.hide(); self.refresh_template_list()
    
    def refresh_template_list(self):
        while self.temp_list_l.count():
            item = self.temp_list_l.takeAt(0)
            if item.widget(): item.widget().deleteLater()
        
        for t_type in ["grid", "flower"]:
            group_w = QWidget(); gl = QVBoxLayout(group_w); gl.setContentsMargins(0,0,0,0); gl.setSpacing(10)
            header = QLabel(t_type.upper()); header.setStyleSheet("color: #aaaaaa; font-size: 12px; font-weight: bold; letter-spacing: 1px;")
            gl.addWidget(header)
            
            grid_w = QWidget(); grid = QGridLayout(grid_w); grid.setContentsMargins(0,0,0,0); grid.setSpacing(15); grid.setAlignment(Qt.AlignmentFlag.AlignLeft)
            templates = self.cfg.get('templates', {}).get(t_type, {})
            row, col = 0, 0
            pref = self.cfg.get('general_settings', {}).get('preferred_template')
            for name in templates.keys():
                is_flagged = (pref and pref['type'] == t_type and pref['name'] == name)
                tile = TemplateTile(t_type, name, is_default=(name=="Default"), is_flagged=is_flagged)
                tile.clicked.connect(self.open_template_editor)
                tile.action.connect(self.handle_template_action)
                grid.addWidget(tile, row, col)
                col += 1
                if col > 2: col = 0; row += 1
            gl.addWidget(grid_w); self.temp_list_l.addWidget(group_w)
    
    def handle_template_action(self, act, t_type, name):
        if act == "flag":
            pref = self.cfg['general_settings'].get('preferred_template')
            if pref and pref['type'] == t_type and pref['name'] == name:
                self.cfg['general_settings']['preferred_template'] = None # Unflag
            else:
                self.cfg['general_settings']['preferred_template'] = {"type": t_type, "name": name}
            ConfigManager.save(self.cfg); self.refresh_template_list()
        elif act == "duplicate":
            new_name = f"{name} Copy"; i = 1
            while new_name in self.cfg['templates'][t_type]: new_name = f"{name} Copy {i}"; i += 1
            self.cfg['templates'][t_type][new_name] = copy.deepcopy(self.cfg['templates'][t_type][name])
            ConfigManager.save(self.cfg); self.refresh_template_list()
        elif act == "delete":
            if name == "Default": return
            del self.cfg['templates'][t_type][name]
            # Update folders using this template
            for f in self.cfg['folders']:
                if f.get('template_type') == t_type and f.get('template_name') == name:
                    f['template_name'] = "Default"
            ConfigManager.save(self.cfg); self.refresh_template_list()
        elif act == "rename":
            if name == "Default": return
            from PyQt6.QtWidgets import QInputDialog
            new_name, ok = QInputDialog.getText(self, "Rename Template", "Enter new name:", QLineEdit.EchoMode.Normal, name)
            if ok and new_name and new_name != "Default" and new_name not in self.cfg['templates'][t_type]:
                data = self.cfg['templates'][t_type].pop(name)
                self.cfg['templates'][t_type][new_name] = data
                for f in self.cfg['folders']:
                    if f.get('template_type') == t_type and f.get('template_name') == name:
                        f['template_name'] = new_name
                ConfigManager.save(self.cfg); self.refresh_template_list()

    def prompt_new_template(self):
        from PyQt6.QtWidgets import QMenu
        m = QMenu(self); m.setStyleSheet("QMenu { background: #282a36; color: white; border: 1px solid #44475a; } QMenu::item:selected { background: #44475a; }")
        m.addAction("Grid Template", lambda: self.create_new_template("grid"))
        m.addAction("Flower Template", lambda: self.create_new_template("flower"))
        m.exec(self.cursor().pos())

    def create_new_template(self, t_type):
        name = f"New {t_type.title()} Template"; i = 1
        while name in self.cfg['templates'][t_type]: name = f"New {t_type.title()} Template {i}"; i += 1
        self.cfg['templates'][t_type][name] = copy.deepcopy(DEFAULTS[t_type])
        ConfigManager.save(self.cfg); self.refresh_template_list()

    def open_template_editor(self, t_type, name):
        self.current_temp_type = t_type; self.current_temp_name = name
        self.editor_title.setText(f"{t_type.title()} : {name}")
        self.build_template_editor()
        self.temp_stack.setCurrentIndex(1)
        # Update preview - clear previous instance overrides
        si = self.preview_panel.sandbox_icon
        for k in ['show_title', 'show_cover', 'grid_snap', 'cover_image']:
            if k in si.data: del si.data[k]
        si.data['template_type'] = t_type; si.data['template_name'] = name
        si.local_settings = copy.deepcopy(self.cfg['templates'][t_type][name]); si.update()
    def build_template_editor(self):
        GLASS_CARD = "QFrame#GlassCard { background: rgba(255,255,255,3); border: 1px solid rgba(255,255,255,8); border-radius: 8px; }"
        SECTION_LBL = "color: #00f0ff; font-size: 11px; font-weight: 700; letter-spacing: 2px; font-family: 'Segoe UI Variable Display';"
        
        while self.t_form.count():
            item = self.t_form.takeAt(0)
            if item.widget(): item.widget().deleteLater()
        t_type = self.current_temp_type; t_data = self.cfg['templates'][t_type][self.current_temp_name]
        
        rs_btn = QPushButton("Reset Template to Defaults"); rs_btn.setFixedHeight(30); rs_btn.setIcon(VectorIcon.icon("assets/reset.svg", "#aaaaaa"))
        rs_btn.setStyleSheet("QPushButton { color: #aaaaaa; background: rgba(255,255,255,10); border-radius: 6px; font-size: 12px; padding: 0 10px; } QPushButton:hover { background: rgba(255,255,255,20); color: white; }")
        rs_btn.clicked.connect(self.reset_template_defaults); self.t_form.addWidget(rs_btn)
        
        c1 = QFrame(); c1.setObjectName("GlassCard"); c1.setStyleSheet(GLASS_CARD)
        c1l = QVBoxLayout(c1); c1l.setContentsMargins(20,16,20,16); c1l.setSpacing(14)
        c1l.addWidget(QLabel("◆  BEHAVIOR", styleSheet=SECTION_LBL))
        f1 = QFormLayout(); f1.setSpacing(14); c1l.addLayout(f1)
        
        self.add_toggle(f1, "Show Folder Name", t_data.get('show_title', True), lambda v: self.upd_temp('show_title', v))
        self.add_toggle(f1, "Snap to Grid", t_data.get('grid_snap', False), lambda v: self.upd_temp('grid_snap', v))
        row = QWidget(); rl = QHBoxLayout(row); rl.setContentsMargins(0,0,0,0); rl.setSpacing(10)
        tg = CustomToggle(t_data.get('show_cover', False)); tg.toggled.connect(lambda v: self.upd_temp('show_cover', v))
        up = QPushButton(); up.setFixedSize(30, 30); up.setIcon(VectorIcon.icon("assets/upload.svg", "#50FA7B")); up.setCursor(Qt.CursorShape.PointingHandCursor); up.setStyleSheet("background: rgba(255,255,255,10); border: none; border-radius: 6px;"); up.clicked.connect(self.pick_t_cover)
        rl.addWidget(tg); rl.addWidget(up); rl.addStretch()
        f1.addRow(self.create_label("Show Cover"), row)
        self.t_shape = SegmentedToggle(t_data.get('mini_highlight_shape', 'Rounded Square'), 
                                      {"Circle": "assets/circle.svg", "Square": "assets/square.svg", "Rounded Square": "assets/rounded square.svg"}, 
                                      use_icons=True,
                                      tooltips={"Circle": "Circle: Sharp circular highlight.", "Square": "Square: Classic square highlight.", "Rounded Square": "Rounded: Smooth organic highlight."})
        self.t_shape.valueChanged.connect(lambda v: self.upd_temp('mini_highlight_shape', v))
        f1.addRow(self.create_label("Highlight Shape"), self.t_shape)
        self.t_form.addWidget(c1)
        
        c2 = QFrame(); c2.setObjectName("GlassCard"); c2.setStyleSheet(GLASS_CARD)
        c2l = QVBoxLayout(c2); c2l.setContentsMargins(20,16,20,16); c2l.setSpacing(14)
        c2l.addWidget(QLabel("◆  STYLING & SIZING", styleSheet=SECTION_LBL))
        f2 = QFormLayout(); f2.setSpacing(14); c2l.addLayout(f2)
        
        self.t_preset = SegmentedToggle(t_data.get('size_preset', 'Medium'), 
                                       {"Small": "S", "Medium": "M", "Large": "L", "Custom": "C"}, 
                                       use_icons=False,
                                       tooltips={"Small": "Small: 60px footprint.", "Medium": "Medium: 80px footprint.", "Large": "Large: 110px footprint.", "Custom": "Custom: Unlock manual sliders."})
        self.t_preset.valueChanged.connect(lambda v: self.upd_temp('size_preset', v))
        f2.addRow(self.create_label("Size Preset"), self.t_preset)
        self.t_custom_w = QWidget(); self.t_custom_l = QFormLayout(self.t_custom_w); self.t_custom_l.setContentsMargins(0,0,0,0); self.t_custom_l.setSpacing(15); f2.addRow(self.t_custom_w)
        for k, lbl, mn, mx in [('folder_size', "Size", 40, 200), ('mini_icon_size', "Mini Icon", 10, 60), ('font_size', "Font Size", 6, 24), ('expanded_icon_size', "App Icon", 16, 128)]:
            def reset_t_val(checked=False, key=k): self.upd_temp(key, DEFAULTS[t_type][key]); self.build_template_editor()
            self.add_slider(self.t_custom_l, lbl, mn, mx, t_data.get(k, DEFAULTS[t_type][k]), lambda v, key=k: self.upd_temp(key, v), reset_t_val)
        self.t_custom_w.setVisible(t_data.get('size_preset') == "Custom")
        
        for k, lbl, mn, mx in [('glow_intensity', "Glow", 0, 100), ('opacity', "Opacity", 0, 255), ('radius', "Radius", 0, 50), ('cover_blur', "Blur", 0, 100), ('cover_opacity', "Cover Opacity", 0, 100)]:
            def reset_val(checked=False, key=k): self.upd_temp(key, DEFAULTS[t_type][key]); self.build_template_editor()
            self.add_slider(f2, lbl, mn, mx, t_data.get(k, DEFAULTS[t_type][k]), lambda v, key=k: self.upd_temp(key, v), reset_val)
            
        for k, lbl in [('glow_color', "Glow Color"), ('bg_color', "BG Color"), ('title_color', "Text Color"), ('highlight_color', "Highlight")]:
            btn = QPushButton(); btn.setFixedSize(65, 26); btn.setCursor(Qt.CursorShape.PointingHandCursor); btn.setStyleSheet(f"background: {t_data.get(k, DEFAULTS[t_type][k])}; border-radius: 6px; border: 2px solid rgba(255,255,255,30);")
            btn.clicked.connect(lambda _, key=k, b=btn: self.pick_temp_color(key, b)); f2.addRow(self.create_label(lbl), btn)
        self.t_form.addWidget(c2); self.t_form.addStretch()
    def pick_t_cover(self):
        path, _ = QFileDialog.getOpenFileName(self, "Select Cover Image", "", "Images (*.png *.jpg *.jpeg *.svg)")
        if path: self.upd_temp('cover_image', path)
    def reset_template_defaults(self):
        t_type = self.current_temp_type; self.cfg['templates'][t_type][self.current_temp_name] = copy.deepcopy(DEFAULTS[t_type])
        ConfigManager.save(self.cfg); self.build_template_editor(); self.update_instances(); self._update_preview()
    def upd_temp(self, k, v):
        t_type = self.current_temp_type; t_data = self.cfg['templates'][t_type][self.current_temp_name]; t_data[k] = v
        if k == 'size_preset' and v != "Custom":
            presets = {"Small": {"folder_size": 60, "mini_icon_size": 14, "font_size": 9, "expanded_icon_size": 32}, "Medium": {"folder_size": 80, "mini_icon_size": 18, "font_size": 10, "expanded_icon_size": 48}, "Large": {"folder_size": 110, "mini_icon_size": 26, "font_size": 12, "expanded_icon_size": 64}}
            if v in presets: t_data.update(presets[v])
            self.build_template_editor()
        elif k == 'size_preset': self.t_custom_w.setVisible(True)
        ConfigManager.save(self.cfg); self.update_instances(); self._update_preview()
    def _update_preview(self):
        t_type = self.current_temp_type; t_data = self.cfg['templates'][t_type][self.current_temp_name]
        si = self.preview_panel.sandbox_icon
        si.data['template_type'] = t_type; si.data['template_name'] = self.current_temp_name
        si.data['show_cover'] = t_data.get('show_cover', False)
        si.data['show_title'] = t_data.get('show_title', True)
        si.local_settings = copy.deepcopy(t_data); si.update()
        if self.preview_panel.stack.currentIndex() == 1:
            self.preview_panel.sandbox_view.refresh()
    def pick_temp_color(self, k, btn):
        t_type = self.current_temp_type; curr = QColor(self.cfg['templates'][t_type][self.current_temp_name].get(k, DEFAULTS[t_type][k]))
        from PyQt6.QtWidgets import QColorDialog
        c = QColorDialog.getColor(curr, self, f"Pick {k.replace('_',' ').title()}")
        if c.isValid(): hex_c = c.name(); btn.setStyleSheet(f"background: {hex_c}; border-radius: 6px; border: 2px solid rgba(255,255,255,30);"); self.upd_temp(k, hex_c)
    def setup_individual_tab(self):
        self.ind_tab = QWidget(); self.ind_tab.setObjectName("SettingPanel"); self.ind_tab.setStyleSheet(PANEL_STYLE)
        l = QVBoxLayout(self.ind_tab); l.setContentsMargins(0,0,0,0); self.ind_stack = QStackedWidget(); l.addWidget(self.ind_stack); self.ind_stack.currentChanged.connect(self.update_preview_visibility)
        
        # PAGE 1: Folder Grid Browser
        grid_w = QWidget(); gl = QVBoxLayout(grid_w); gl.setContentsMargins(32, 20, 32, 20); gl.setSpacing(16)
        # Header
        hdr = QHBoxLayout()
        hdr_title = QLabel("FOLDER LIBRARY"); hdr_title.setStyleSheet("color: #8BE9FD; font-size: 14px; font-weight: 700; letter-spacing: 2px;")
        hdr.addWidget(hdr_title); hdr.addStretch()
        gl.addLayout(hdr)
        # Search Bar
        search_row = QHBoxLayout(); search_row.setSpacing(12)
        self.f_search = QLineEdit(); self.f_search.setPlaceholderText("Search Folders...")
        self.f_search.setStyleSheet("""QLineEdit { background: rgba(255,255,255,5); border: 1px solid rgba(255,255,255,10); 
            border-radius: 8px; color: #e0e0e0; padding: 8px 14px; font-size: 13px; }
            QLineEdit:focus { border: 1px solid rgba(0,240,255,40); background: rgba(255,255,255,8); }""")
        self.f_search.textChanged.connect(self.refresh_grid)
        self.f_sort = QPushButton("Sort: A-Z"); self.f_sort.setFixedHeight(36)
        self.f_sort.setStyleSheet("""QPushButton { background: rgba(255,255,255,5); border: 1px solid rgba(255,255,255,12); 
            border-radius: 8px; color: #aaaaaa; font-size: 12px; font-weight: 600; padding: 0 16px; }
            QPushButton:hover { background: rgba(255,255,255,10); color: white; border: 1px solid rgba(0,240,255,30); }""")
        self.f_sort.clicked.connect(lambda: (self.f_sort.setText("Sort: Z-A" if self.f_sort.text()=="Sort: A-Z" else "Sort: A-Z"), self.refresh_grid()))
        search_row.addWidget(self.f_search); search_row.addWidget(self.f_sort); gl.addLayout(search_row)
        # Scroll area for grid
        s = SmoothScrollArea(); s.setWidgetResizable(True); s.setStyleSheet(SCROLLBAR_CSS); gl.addWidget(s)
        cnt = QWidget(); self.grid_layout = QGridLayout(cnt); self.grid_layout.setContentsMargins(4, 8, 4, 20); self.grid_layout.setSpacing(14); self.grid_layout.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft); s.setWidget(cnt); self.ind_stack.addWidget(grid_w)
        
        # PAGE 2: Individual Folder Settings
        set_w = QWidget(); sl = QVBoxLayout(set_w); sl.setContentsMargins(0,0,0,0)
        stk = QWidget(); stk.setFixedHeight(76)
        stk.setStyleSheet("background: rgba(255,255,255,3); border-bottom: 1px solid rgba(255,255,255,8);")
        hl = QHBoxLayout(stk); hl.setContentsMargins(24, 8, 24, 8); hl.setSpacing(14)
        bk = QPushButton(); bk.setIcon(VectorIcon.icon("back", "#8BE9FD")); bk.setFixedSize(32, 32); bk.setStyleSheet("background: transparent; border: none;"); bk.setCursor(Qt.CursorShape.PointingHandCursor); bk.clicked.connect(lambda: self.ind_stack.setCurrentIndex(0))
        self.f_thumb = FolderThumbnail({}, self.cfg)
        self.ind_header = QLabel("Folder Name"); self.ind_header.setStyleSheet("color: white; font-weight: bold; font-size: 16px;")
        rs = QPushButton(); rs.setFixedSize(30, 30); rs.setIcon(VectorIcon.icon("assets/reset.svg", "#aaaaaa")); rs.setStyleSheet("background: transparent; border: none;"); rs.setCursor(Qt.CursorShape.PointingHandCursor); rs.clicked.connect(self.reset_ind_all)
        hl.addWidget(bk); hl.addWidget(self.f_thumb); hl.addWidget(self.ind_header); hl.addStretch(); hl.addWidget(rs); sl.addWidget(stk)
        s = SmoothScrollArea(); s.setWidgetResizable(True); s.setStyleSheet(SCROLLBAR_CSS); sl.addWidget(s)
        cnt = QWidget(); self.is_form = QVBoxLayout(cnt); self.is_form.setContentsMargins(32, 20, 40, 30); self.is_form.setSpacing(20); s.setWidget(cnt); self.setup_individual_fields(); self.ind_stack.addWidget(set_w); self.stack.addWidget(self.ind_tab)
    def setup_individual_fields(self):
        GLASS_CARD = "QFrame#GlassCard { background: rgba(255,255,255,3); border: 1px solid rgba(255,255,255,8); border-radius: 8px; }"
        SECTION_LBL = "color: #00f0ff; font-size: 11px; font-weight: 700; letter-spacing: 2px; font-family: 'Segoe UI Variable Display';"
        
        c1 = QFrame(); c1.setObjectName("GlassCard"); c1.setStyleSheet(GLASS_CARD)
        c1l = QVBoxLayout(c1); c1l.setContentsMargins(20,16,20,16); c1l.setSpacing(14)
        c1l.addWidget(QLabel("◆  GENERAL", styleSheet=SECTION_LBL))
        f1 = QFormLayout(); f1.setSpacing(14); c1l.addLayout(f1)
        
        self.i_show_title = CustomToggle(True); self.i_show_title.toggled.connect(lambda v: self.upd_f_root('show_title', v)); f1.addRow(self.create_label("Show Folder Name"), self.i_show_title)
        self.i_grid_snap = CustomToggle(False); self.i_grid_snap.toggled.connect(lambda v: self.upd_f_root('grid_snap', v)); f1.addRow(self.create_label("Snap to Grid"), self.i_grid_snap)
        row = QWidget(); rl = QHBoxLayout(row); rl.setContentsMargins(0,0,0,0); rl.setSpacing(10)
        self.i_show_cover = CustomToggle(False); self.i_show_cover.toggled.connect(lambda v: self.upd_f_root('show_cover', v))
        self.i_up_btn = QPushButton(); self.i_up_btn.setFixedSize(30, 30); self.i_up_btn.setIcon(VectorIcon.icon("assets/upload.svg", "#8BE9FD")); self.i_up_btn.setCursor(Qt.CursorShape.PointingHandCursor); self.i_up_btn.setStyleSheet("background: rgba(255,255,255,10); border: none; border-radius: 6px;"); self.i_up_btn.clicked.connect(self.pick_f_cover)
        rl.addWidget(self.i_show_cover); rl.addWidget(self.i_up_btn); rl.addStretch()
        f1.addRow(self.create_label("Show Cover"), row)
        self.is_form.addWidget(c1)
        
        c2 = QFrame(); c2.setObjectName("GlassCard"); c2.setStyleSheet(GLASS_CARD)
        c2l = QVBoxLayout(c2); c2l.setContentsMargins(20,16,20,16); c2l.setSpacing(14)
        c2l.addWidget(QLabel("◆  STYLING", styleSheet=SECTION_LBL))
        f2 = QFormLayout(); f2.setSpacing(14); c2l.addLayout(f2)
        
        self.i_temp_sel = DropdownButton("Default", ["Default"]); self.i_temp_sel.valueChanged.connect(self.on_i_template_changed); f2.addRow(self.create_label("Base Template"), self.i_temp_sel)
        self.ind_toggle = CustomToggle(False); self.ind_toggle.toggled.connect(self.on_ind_toggle_changed); f2.addRow(self.create_label("Use Custom Styling"), self.ind_toggle)
        self.i_custom_cnt = QWidget(); self.i_custom_lay = QFormLayout(self.i_custom_cnt); self.i_custom_lay.setContentsMargins(0,0,0,0); self.i_custom_lay.setSpacing(20); f2.addRow(self.i_custom_cnt)
        self.is_form.addWidget(c2); self.is_form.addStretch()
    def setup_radial_tab(self):
        GLASS_CARD = "QFrame#GlassCard { background: rgba(255,255,255,3); border: 1px solid rgba(255,255,255,8); border-radius: 8px; }"
        SECTION_LBL = "color: #00f0ff; font-size: 11px; font-weight: 700; letter-spacing: 2px; font-family: 'Segoe UI Variable Display';"
        SUB_LBL = "color: #556677; font-size: 10px; font-weight: 600; letter-spacing: 1.5px; font-family: 'Segoe UI Variable Display';"

        main_page = QWidget(); main_page.setStyleSheet("background: rgba(255,255,255,2); border-radius: 12px;")
        main_l = QVBoxLayout(main_page); main_l.setContentsMargins(0, 0, 0, 0); main_l.setSpacing(0)
        
        # ── HEADER ──────────────────────────────────────────
        header_cnt = QWidget(); header_row = QHBoxLayout(header_cnt); header_row.setContentsMargins(32, 24, 32, 16); header_row.setSpacing(12)
        h1 = QLabel("RADIAL MENU CONFIGURATION"); h1.setStyleSheet("color: #e5e2e3; font-size: 16px; font-weight: 700; letter-spacing: 2px; font-family: 'Segoe UI Variable Display';")
        header_row.addWidget(h1); header_row.addStretch()
        
        status_lbl = QLabel("RADIAL_HUD STATUS:"); status_lbl.setStyleSheet("color: #556677; font-size: 10px; font-weight: 600; letter-spacing: 1px;")
        header_row.addWidget(status_lbl)
        self.rad_enabled_toggle = CustomToggle(self.cfg.get('radial_menu', {}).get('enabled', True))
        self.rad_enabled_toggle.toggled.connect(lambda v: self.upd_radial('enabled', v))
        header_row.addWidget(self.rad_enabled_toggle)
        
        reset_btn = QPushButton("RESET TO DEFAULTS")
        reset_btn.setStyleSheet("QPushButton { background: rgba(255,255,255,4); border: 1px solid rgba(255,255,255,12); border-radius: 4px; padding: 6px 14px; font-size: 10px; font-weight: 700; color: #849495; letter-spacing: 0.5px; } QPushButton:hover { background: rgba(0,240,255,8); border: 1px solid rgba(0,240,255,60); color: #00f0ff; }")
        reset_btn.clicked.connect(self.reset_radial_defaults)
        header_row.addWidget(reset_btn); main_l.addWidget(header_cnt)

        # Scrollable wrapper
        scroll = SmoothScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("QScrollArea { background: transparent; border: none; }")
        main_l.addWidget(scroll)
        
        container = QWidget(); container.setStyleSheet("background: transparent;")
        l = QVBoxLayout(container); l.setContentsMargins(32, 0, 32, 24); l.setSpacing(16)
        
        # ── TOP ROW: Layer Navigation Bar ──────────────────
        nav_card = QFrame(); nav_card.setObjectName("GlassCard"); nav_card.setStyleSheet(GLASS_CARD)
        nav_l = QHBoxLayout(nav_card); nav_l.setContentsMargins(16, 12, 16, 12); nav_l.setSpacing(12)
        
        self.layer_list = QListWidget()
        self.layer_list.setFlow(QListWidget.Flow.LeftToRight)
        self.layer_list.setFixedHeight(80)
        self.layer_list.setSpacing(10)
        self.layer_list.setStyleSheet("QListWidget { background: transparent; border: none; outline: none; } QListWidget::item { background: rgba(255,255,255,10); border-radius: 6px; width: 60px; height: 60px; } QListWidget::item:selected { border: 2px solid #00f0ff; background: rgba(0,240,255,20); }")
        self.layer_list.setDragDropMode(QAbstractItemView.DragDropMode.InternalMove)
        self.layer_list.setMovement(QListWidget.Movement.Snap)
        self.layer_list.currentRowChanged.connect(self.on_layer_selected)
        self.layer_list.model().rowsMoved.connect(self.on_layer_reordered)
        
        nav_l.addWidget(self.layer_list, 1)
        
        btn_col = QVBoxLayout(); btn_col.setSpacing(8)
        self.add_layer_btn = QPushButton("+"); self.add_layer_btn.setFixedSize(30, 30)
        self.add_layer_btn.setStyleSheet("QPushButton { background: rgba(255,255,255,10); border-radius: 6px; color: #8BE9FD; font-size: 16px; font-weight: bold; } QPushButton:hover { background: rgba(139,233,253,30); }")
        self.add_layer_btn.clicked.connect(self.add_layer)
        
        self.del_layer_btn = QPushButton("-"); self.del_layer_btn.setFixedSize(30, 30)
        self.del_layer_btn.setStyleSheet("QPushButton { background: rgba(255,255,255,10); border-radius: 6px; color: #FF5555; font-size: 16px; font-weight: bold; } QPushButton:hover { background: rgba(255,85,85,30); }")
        self.del_layer_btn.clicked.connect(self.del_layer)
        
        btn_col.addWidget(self.add_layer_btn); btn_col.addWidget(self.del_layer_btn); btn_col.addStretch()
        nav_l.addLayout(btn_col)
        
        l.addWidget(nav_card)
        
        # ── BOTTOM: Tools Manager ──────────────────────────
        manager_layout = QHBoxLayout(); manager_layout.setSpacing(16); l.addLayout(manager_layout, 1)

        # Left Side: Command Bank (Paginated)
        left_card = QFrame(); left_card.setObjectName("GlassCard"); left_card.setStyleSheet(GLASS_CARD)
        left_l = QVBoxLayout(left_card); left_l.setContentsMargins(16,16,16,16); left_l.setSpacing(12)
        
        bank_header = QHBoxLayout()
        bank_lbl = QLabel("◆  COMMAND BANK"); bank_lbl.setStyleSheet(SECTION_LBL)
        bank_header.addWidget(bank_lbl); bank_header.addStretch()
        # Page indicators go in the header row
        self.bank_indicator = QWidget(); self.bank_indicator.setFixedHeight(16)
        self.ind_lay = QHBoxLayout(self.bank_indicator); self.ind_lay.setContentsMargins(0,0,0,0); self.ind_lay.setAlignment(Qt.AlignmentFlag.AlignCenter); self.ind_lay.setSpacing(6)
        bank_header.addWidget(self.bank_indicator)
        left_l.addLayout(bank_header)
        
        self.bank_stack = QStackedWidget()
        self.bank_stack.setObjectName('BankStack')
        self.bank_stack.setMinimumHeight(360)
        self.bank_stack.setStyleSheet("QStackedWidget { background: transparent; border: none; }")
        left_l.addWidget(self.bank_stack)
        
        manager_layout.addWidget(left_card, 1)

        # Right Side: Configuration Stage
        right_card = QFrame(); right_card.setObjectName("GlassCard"); right_card.setStyleSheet(GLASS_CARD)
        right_l = QVBoxLayout(right_card); right_l.setContentsMargins(16,16,16,16); right_l.setSpacing(12)
        stage_lbl = QLabel("◆  CONFIGURATION STAGE"); stage_lbl.setStyleSheet(SECTION_LBL)
        right_l.addWidget(stage_lbl)
        
        self.sandbox_radial = SandboxRadialMenu(self)
        right_l.addWidget(self.sandbox_radial, alignment=Qt.AlignmentFlag.AlignCenter)
        right_l.addStretch()
        
        manager_layout.addWidget(right_card, 1)

        self.bank_stack.currentChanged.connect(self.on_bank_page_changed)
        self.sandbox_radial.update_settings(self.cfg)
        self.populate_layer_list()
        
        scroll.setWidget(container)
        self.stack.addWidget(main_page)


    def upd_radial(self, k, v):
        if 'radial_menu' not in self.cfg: self.cfg['radial_menu'] = {}
        self.cfg['radial_menu'][k] = v; ConfigManager.save(self.cfg)
        # Update running instances
        if hasattr(QApplication.instance(), 'radial_menu'):
            QApplication.instance().radial_menu.reload_tools(self.cfg)
        if hasattr(QApplication.instance(), 'global_hook'):
            QApplication.instance().global_hook.reload_config(self.cfg)
        self.sandbox_radial.update_settings(self.cfg)
        self.update_radial_instance()

    def populate_layer_list(self):
        self.layer_list.clear()
        menus = self.cfg.get('radial_menu', {}).get('menus', [])
        for i, menu in enumerate(menus):
            item = QListWidgetItem(f"L{i+1}")
            item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            item.setFont(QFont("Segoe UI Variable Display", 14, QFont.Weight.Bold))
            item.setData(Qt.ItemDataRole.UserRole, i)
            self.layer_list.addItem(item)
        if menus:
            self.layer_list.setCurrentRow(0)
            
    def on_layer_selected(self, row):
        if row < 0: return
        self.refresh_radial_lists()
        
    def on_layer_reordered(self):
        menus = self.cfg.get('radial_menu', {}).get('menus', [])
        new_menus = []
        for i in range(self.layer_list.count()):
            old_idx = self.layer_list.item(i).data(Qt.ItemDataRole.UserRole)
            if old_idx < len(menus):
                new_menus.append(menus[old_idx])
        if 'radial_menu' not in self.cfg: self.cfg['radial_menu'] = {}
        self.cfg['radial_menu']['menus'] = new_menus
        ConfigManager.save(self.cfg)
        self.populate_layer_list() # Re-bind UserRoles to new indices
        self.update_radial_instance()
        
    def add_layer(self):
        menus = self.cfg.setdefault('radial_menu', {}).setdefault('menus', [])
        menus.append({"name": f"Layer {len(menus)+1}", "tools": []})
        ConfigManager.save(self.cfg)
        self.populate_layer_list()
        self.layer_list.setCurrentRow(len(menus)-1)
        self.update_radial_instance()
        
    def del_layer(self):
        menus = self.cfg.get('radial_menu', {}).get('menus', [])
        if len(menus) <= 1: return # Prevent deleting last layer
        row = self.layer_list.currentRow()
        if row >= 0 and row < len(menus):
            menus.pop(row)
            ConfigManager.save(self.cfg)
            self.populate_layer_list()
            self.update_radial_instance()

    def toggle_radial_tool(self, tool, is_active):
        if 'radial_menu' not in self.cfg: self.cfg['radial_menu'] = {}
        menus = self.cfg['radial_menu'].setdefault('menus', [])
        row = self.layer_list.currentRow()
        if row < 0 or row >= len(menus): return
        
        tools = menus[row].get('tools', [])
        if is_active:
            tools = [x for x in tools if x['id'] != tool['id']]
        else:
            if len(tools) >= 12: return
            tools.append(tool)
        menus[row]['tools'] = tools
        ConfigManager.save(self.cfg)
        self.refresh_radial_lists()
        self.update_radial_instance()
        
    def save_radial_order_from_sandbox(self, tools):
        if 'radial_menu' not in self.cfg: self.cfg['radial_menu'] = {}
        menus = self.cfg['radial_menu'].setdefault('menus', [])
        row = self.layer_list.currentRow()
        if row < 0 or row >= len(menus): return
        
        menus[row]['tools'] = tools
        ConfigManager.save(self.cfg)
        self.refresh_radial_lists()
        self.update_radial_instance()

    def on_bank_page_changed(self, idx):
        for i in range(self.ind_lay.count()):
            w = self.ind_lay.itemAt(i).widget()
            if w: w.setStyleSheet(f"background: {'#00f0ff' if i == idx else 'rgba(255,255,255,30)'}; border-radius: 4px; border: none;")

    def refresh_radial_lists(self):
        # Clear existing pages
        while self.bank_stack.count():
            w = self.bank_stack.widget(0)
            self.bank_stack.removeWidget(w)
            if w: w.deleteLater()
        while self.ind_lay.count():
            item = self.ind_lay.takeAt(0)
            if item.widget(): item.widget().deleteLater()
            
        row = self.layer_list.currentRow()
        menus = self.cfg.get('radial_menu', {}).get('menus', [])
        active = menus[row].get('tools', []) if (0 <= row < len(menus)) else []
        active_ids = [t['id'] for t in active]
        self.sandbox_radial.update_tools(active)
        self.sandbox_radial.update()

        ALL_TOOLS = [
            {"id": "browser", "icon": "browser", "label": "Browser"},
            {"id": "explorer", "icon": "file explorer", "label": "Files"},
            {"id": "grid", "icon": "toggle grid", "label": "Toggle Grid"},
            {"id": "screenshot", "icon": "screenshot", "label": "Snip"},
            {"id": "night", "icon": "night light", "label": "Night Light"},
            {"id": "mute", "icon": "mute", "label": "Mute"},
            {"id": "trash", "icon": "empty recycle bin", "label": "Empty Trash"},
            {"id": "settings", "icon": "Pandora", "label": "Pandora"},
            {"id": "search", "icon": "search", "label": "Search"},
            {"id": "taskmgr", "icon": "task manager", "label": "Tasks"},
            {"id": "notes", "icon": "sticky notes", "label": "Sticky Notes"},
            {"id": "power", "icon": "power", "label": "Power"},
            {"id": "calc", "icon": "calculator", "label": "Calculator"},
            {"id": "cmd", "icon": "terminal", "label": "Terminal"},
            {"id": "notepad", "icon": "notepad", "label": "Notepad"},
            {"id": "prev", "icon": "prev", "label": "Prev Media"},
            {"id": "next", "icon": "next", "label": "Next Media"}
        ]

        # 3x3 Pagination (9 items per page)
        per_page = 9
        for p_idx in range(0, len(ALL_TOOLS), per_page):
            page_w = QWidget()
            gl = QGridLayout(page_w); gl.setContentsMargins(8,8,8,8); gl.setSpacing(10)
            chunk = ALL_TOOLS[p_idx:p_idx+per_page]
            for i, t in enumerate(chunk):
                is_active = t['id'] in active_ids
                order_idx = active_ids.index(t['id']) + 1 if is_active else 0
                btn = ToolGridButton(t, is_active, order_idx)
                btn.clicked.connect(lambda checked, tool=t, act=is_active: self.toggle_radial_tool(tool, act))
                gl.addWidget(btn, i // 3, i % 3)
            self.bank_stack.addWidget(page_w)
            
            # Dot indicator
            dot = QPushButton()
            dot.setFixedSize(8, 8); dot.setCursor(Qt.CursorShape.PointingHandCursor)
            is_curr = (self.bank_stack.count() - 1 == self.bank_stack.currentIndex())
            dot_col = "#00f0ff" if is_curr else "rgba(255,255,255,30)"
            dot.setStyleSheet(f"background: {dot_col}; border-radius: 4px; border: none;")
            dot.clicked.connect(lambda _, idx=self.bank_stack.count()-1: self.bank_stack.setCurrentIndex(idx))
            self.ind_lay.addWidget(dot)

        # Sync dots with current page
        self.on_bank_page_changed(self.bank_stack.currentIndex())

    def remove_radial_tool_by_id(self, tool_id):
        if 'radial_menu' not in self.cfg: self.cfg['radial_menu'] = {}
        tools = self.cfg['radial_menu'].get('tools', [])
        if len(tools) <= 1: return
        self.cfg['radial_menu']['tools'] = [x for x in tools if x['id'] != tool_id]
        ConfigManager.save(self.cfg); self.refresh_radial_lists()
        self.update_radial_instance()
        
    def update_radial_instance(self):
        for w in QApplication.topLevelWidgets():
            if w.__class__.__name__ == "RadialMenu":
                w.reload_tools(self.cfg)
                break

    def pick_f_cover(self):
        path, _ = QFileDialog.getOpenFileName(self, "Select Cover Image", "", "Images (*.png *.jpg *.jpeg *.svg *.gif)")
        if path: self.upd_f_root('cover_image', path)
    def open_f_settings(self, fid):
        self.current_fid = fid; f_data = next((f for f in self.cfg['folders'] if f['id'] == fid), None)
        if not f_data: return
        self.ind_header.setText(f_data['name']); self.f_thumb.update_data(f_data); self.i_show_title.setChecked(f_data.get('show_title', True)); self.i_grid_snap.setChecked(f_data.get('grid_snap', False))
        t_type = f_data.get('template_type', 'grid')
        self.i_show_cover.setChecked(f_data.get('show_cover', False))
        templates = list(self.cfg.get('templates', {}).get(t_type, {}).keys())
        self.i_temp_sel.items = templates; self.i_temp_sel._refresh_menu(); self.i_temp_sel.setTextValue(f_data.get('template_name', 'Default'))
        
        use_custom = f_data.get('use_custom_settings', False)
        self.ind_toggle.setChecked(use_custom)
        self.refresh_ind_custom_fields()
        self.on_ind_toggle_changed(use_custom)
        self.ind_stack.setCurrentIndex(1)
    def refresh_ind_custom_fields(self):
        while self.i_custom_lay.count():
            item = self.i_custom_lay.takeAt(0)
            if item.widget(): item.widget().deleteLater()
        f_data = next((f for f in self.cfg['folders'] if f['id'] == self.current_fid), None)
        if not f_data: return
        c_data = f_data.get('custom_settings', {}); t_type = f_data.get('template_type', 'grid')
        self.i_pst = SegmentedToggle(c_data.get('size_preset', 'Medium'), 
                                    {"Small": "S", "Medium": "M", "Large": "L", "Custom": "C"}, 
                                    use_icons=False,
                                    tooltips={"Small": "Small: 60px footprint.", "Medium": "Medium: 80px footprint.", "Large": "Large: 110px footprint.", "Custom": "Custom: Unlock manual sliders."})
        self.i_pst.valueChanged.connect(lambda v: self.upd_f_custom('size_preset', v))
        self.i_custom_lay.addRow(self.create_label("Size Preset"), self.i_pst)
        
        self.i_h_shape = SegmentedToggle(c_data.get('mini_highlight_shape', DEFAULTS[t_type].get('mini_highlight_shape', 'Rounded Square')), 
                                        {"Circle": "assets/circle.svg", "Square": "assets/square.svg", "Rounded Square": "assets/rounded square.svg"}, 
                                        use_icons=True,
                                        tooltips={"Circle": "Circle: Sharp circular highlight.", "Square": "Square: Classic square highlight.", "Rounded Square": "Rounded: Smooth organic highlight."})
        self.i_h_shape.valueChanged.connect(lambda v: self.upd_f_custom('mini_highlight_shape', v))
        self.i_custom_lay.addRow(self.create_label("Highlight Shape"), self.i_h_shape)
        self.i_cust_box = QWidget(); self.i_cust_l = QFormLayout(self.i_cust_box); self.i_cust_l.setContentsMargins(0,0,0,0); self.i_cust_l.setSpacing(15); self.i_custom_lay.addRow(self.i_cust_box)
        for k, lbl, mn, mx in [('folder_size', "Size", 40, 200), ('mini_icon_size', "Mini Icon", 10, 60), ('font_size', "Font Size", 6, 24), ('expanded_icon_size', "App Icon", 16, 128)]:
            def reset_i_val(checked=False, key=k):
                t_data = self.cfg['templates'][t_type].get(f_data.get('template_name', 'Default'), DEFAULTS[t_type])
                self.upd_f_custom(key, t_data.get(key, DEFAULTS[t_type][key])); self.refresh_ind_custom_fields()
            self.add_slider(self.i_cust_l, lbl, mn, mx, c_data.get(k, DEFAULTS[t_type][k]), lambda v, key=k: self.upd_f_custom(key, v), reset_i_val)
        self.i_cust_box.setVisible(c_data.get('size_preset') == "Custom"); self.i_custom_lay.addRow(self.create_sep())
        for k, lbl, mn, mx in [('glow_intensity', "Glow", 0, 100), ('opacity', "Opacity", 0, 255), ('radius', "Radius", 0, 50), ('cover_blur', "Blur", 0, 100), ('cover_opacity', "Cover Opacity", 0, 100)]:
            def reset_i_val(checked=False, key=k):
                t_data = self.cfg['templates'][t_type].get(f_data.get('template_name', 'Default'), DEFAULTS[t_type])
                self.upd_f_custom(key, t_data.get(key, DEFAULTS[t_type][key])); self.refresh_ind_custom_fields()
            self.add_slider(self.i_custom_lay, lbl, mn, mx, c_data.get(k, DEFAULTS[t_type][k]), lambda v, key=k: self.upd_f_custom(key, v), reset_i_val)
        self.i_custom_lay.addRow(self.create_sep())
        for k, lbl in [('glow_color', "Glow Color"), ('bg_color', "BG Color"), ('title_color', "Text Color"), ('highlight_color', "Highlight")]:
            btn = QPushButton(); btn.setFixedSize(65, 26); btn.setCursor(Qt.CursorShape.PointingHandCursor); btn.setStyleSheet(f"background: {c_data.get(k, DEFAULTS[t_type][k])}; border-radius: 6px; border: 2px solid rgba(255,255,255,30);")
            btn.clicked.connect(lambda _, key=k, b=btn: self.pick_ind_color(key, b)); self.i_custom_lay.addRow(self.create_label(lbl), btn)
    def upd_f_custom(self, k, v):
        f_data = next((f for f in self.cfg['folders'] if f['id'] == self.current_fid), None)
        if not f_data: return
        if 'custom_settings' not in f_data: f_data['custom_settings'] = {}
        f_data['custom_settings'][k] = v
        if k == 'size_preset' and v != "Custom":
            presets = {"Small": {"folder_size": 60, "mini_icon_size": 14, "font_size": 9, "expanded_icon_size": 32}, "Medium": {"folder_size": 80, "mini_icon_size": 18, "font_size": 10, "expanded_icon_size": 48}, "Large": {"folder_size": 110, "mini_icon_size": 26, "font_size": 12, "expanded_icon_size": 64}}
            if v in presets: f_data['custom_settings'].update(presets[v])
            self.refresh_ind_custom_fields()
        elif k == 'size_preset': self.i_cust_box.setVisible(True)
        ConfigManager.save(self.cfg); self.upd_inst(self.current_fid); self.f_thumb.update(); self._update_ind_preview()
    def upd_f_root(self, k, v):
        if not self.current_fid: return
        f = next((f for f in self.cfg['folders'] if f['id'] == self.current_fid), None)
        if f: f[k] = v; ConfigManager.save(self.cfg); self.upd_inst(self.current_fid); self.f_thumb.update(); self._update_ind_preview()
    def on_i_template_changed(self, v):
        if not self.current_fid: return
        f = next((f for f in self.cfg['folders'] if f['id'] == self.current_fid), None)
        if f: f['template_name'] = v; ConfigManager.save(self.cfg); self.upd_inst(self.current_fid); self.f_thumb.update(); self._update_ind_preview()
    def on_ind_toggle_changed(self, v):
        if self.current_fid:
            f = next((f for f in self.cfg['folders'] if f['id'] == self.current_fid), None)
            if f: f['use_custom_settings'] = v; ConfigManager.save(self.cfg); self.upd_inst(self.current_fid)
            self.i_custom_cnt.setEnabled(v)
            effect = QGraphicsOpacityEffect()
            effect.setOpacity(1.0 if v else 0.4)
            self.i_custom_cnt.setGraphicsEffect(effect)
            self.f_thumb.update(); self._update_ind_preview()
    def _update_ind_preview(self):
        if not self.current_fid: return
        f = next((f for f in self.cfg['folders'] if f['id'] == self.current_fid), None)
        if not f: return
        t_type = f.get('template_type', 'grid'); t_name = f.get('template_name', 'Default'); t_data = self.cfg.get('templates', {}).get(t_type, {}).get(t_name, {})
        merged = copy.deepcopy(t_data); (merged.update(f.get('custom_settings', {})) if f.get('use_custom_settings') else None)
        si = self.preview_panel.sandbox_icon
        si.data['template_type'] = t_type; si.data['template_name'] = t_name
        si.data['show_title'] = f.get('show_title', True); si.data['show_cover'] = f.get('show_cover', False)
        si.local_settings = merged; si.update()
        if self.preview_panel.stack.currentIndex() == 1:
            self.preview_panel.sandbox_view.refresh()
    def refresh_grid(self):
        while self.grid_layout.count(): item = self.grid_layout.takeAt(0); w = item.widget(); (w.deleteLater() if w else None)
        q = self.f_search.text().lower(); folders = [f for f in self.cfg['folders'] if q in f['name'].lower()]
        for i, f in enumerate(folders): t = FolderTile(f, self.cfg); t.clicked.connect(self.open_f_settings); self.grid_layout.addWidget(t, i // 4, i % 4)
    def reset_ind_all(self):
        if not self.current_fid: return
        f = next((f for f in self.cfg['folders'] if f['id'] == self.current_fid), None)
        if f:
            f['custom_settings'] = {}; f['use_custom_settings'] = False; f['template_name'] = 'Default'; f['show_title'] = True; f['show_cover'] = False
            ConfigManager.save(self.cfg); self.open_f_settings(self.current_fid); self.upd_inst(self.current_fid); self.f_thumb.update(); self._update_ind_preview()
    def pick_ind_color(self, k, btn):
        if self.current_fid:
            f = next((f for f in self.cfg['folders'] if f['id'] == self.current_fid), None)
            if not f: return
            t_type = f.get('template_type', 'grid'); t_defaults = self.cfg['templates'][t_type].get(f.get('template_name', 'Default'), DEFAULTS[t_type])
            curr = QColor(f.get('custom_settings', {}).get(k, t_defaults.get(k, '#ffffff')))
            from PyQt6.QtWidgets import QColorDialog
            c = QColorDialog.getColor(curr, self, f"Pick {k.replace('_',' ').title()} color")
            if c.isValid(): btn.setStyleSheet(f"background: {c.name()}; border-radius: 6px; border: 2px solid rgba(255,255,255,30);"); self.upd_f_custom(k, c.name())
    def update_instances(self):
        for w in self.app_instances: (w.update() if hasattr(w, 'update') else None)
    def upd_inst(self, fid): (next((w for w in self.app_instances if hasattr(w, 'data') and w.data.get('id') == fid), None).update() if any(hasattr(w, 'data') and w.data.get('id') == fid for w in self.app_instances) else None)
    def handle_folder_deleted(self, folder_widget):
        fid = folder_widget.data.get('id') if hasattr(folder_widget, 'data') else None; self.app_instances = [w for w in self.app_instances if w is not folder_widget]
        if fid and self.current_fid == fid: self.current_fid = None; self.ind_stack.setCurrentIndex(0)
        self.refresh_grid()
    def show_folder(self, fid): self.sidebar.select_tab(2); self.open_f_settings(fid); self.show(); self.raise_()
    def on_tab_changed(self, idx): 
        # Reset sub-stacks first to ensure visibility logic is triggered for all layers
        if idx != 1: self.temp_stack.setCurrentIndex(0)
        if idx != 2: self.ind_stack.setCurrentIndex(0)
        
        self.stack.setCurrentIndex(idx)
        
        if idx == 1: self.refresh_template_list()
        elif idx == 2: self.refresh_grid()
        elif idx == 3: self.refresh_radial_lists()
        self.update_preview_visibility()
    def update_preview_visibility(self):
        idx = self.stack.currentIndex()
        is_temp_settings = (idx == 1 and self.temp_stack.currentIndex() == 1)
        is_ind_settings = (idx == 2 and self.ind_stack.currentIndex() == 1)
        # Only show for Template or Individual folder settings where folder preview is relevant
        self.preview_panel.setVisible(is_temp_settings or is_ind_settings)
    def create_header(self, t): l = QLabel(t); l.setStyleSheet("color: #8BE9FD; font-weight: bold; font-size: 14px; letter-spacing: 1px; margin-bottom: 5px;"); return l
    def create_label(self, t): l = QLabel(t); l.setStyleSheet("color: #e0e0e0; font-size: 14px; font-weight: 500;"); l.setFixedWidth(140); return l
    def create_sep(self): f = QFrame(); f.setFrameShape(QFrame.Shape.HLine); f.setStyleSheet("background: rgba(255,255,255,20); margin: 10px 0;"); return f
    def add_combo(self, layout, label_text, items, current_v, callback):
        row_w = QWidget(); rl = QHBoxLayout(row_w); rl.setContentsMargins(0,0,0,0)
        lbl = self.create_label(label_text); rl.addWidget(lbl); rl.addStretch()
        
        btn = DropdownButton(current_v, items)
        btn.valueChanged.connect(callback)
        rl.addWidget(btn); layout.addRow(row_w)
    def add_slider(self, lay, label, min_v, max_v, cur_v, callback, reset_cb=None):
        row_w = QWidget(); rl = QHBoxLayout(row_w); rl.setContentsMargins(0,0,0,0); rl.setSpacing(10)
        val_lbl = QLabel(str(int(cur_v))); val_lbl.setFixedWidth(35); val_lbl.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        val_lbl.setStyleSheet("color: #00f0ff; font-weight: 700; font-size: 12px; font-family: 'Segoe UI Variable Display';")
        s = QSlider(Qt.Orientation.Horizontal)
        s.setRange(min_v, max_v); s.setValue(int(cur_v))
        s.setStyleSheet("""
            QSlider::groove:horizontal { background: rgba(255,255,255,10); height: 6px; border-radius: 3px; }
            QSlider::sub-page:horizontal { background: qlineargradient(x1:0,y1:0,x2:1,y2:0, stop:0 #00f0ff, stop:1 #9d00ff); border-radius: 3px; }
            QSlider::add-page:horizontal { background: rgba(255,255,255,8); border-radius: 3px; }
            QSlider::handle:horizontal { background: #00f0ff; width: 14px; height: 14px; margin: -4px 0; border-radius: 7px; border: 2px solid #0a1520; }
            QSlider::handle:horizontal:hover { background: #66f7ff; border: 2px solid #00f0ff; }
        """)
        s.valueChanged.connect(lambda v: (val_lbl.setText(str(v)), callback(v)))
        rl.addWidget(s, 1); rl.addWidget(val_lbl)
        if reset_cb:
            rb = QPushButton(); rb.setFixedSize(20, 20); rb.setIcon(VectorIcon.icon("assets/reset.svg", "#666666")); rb.setCursor(Qt.CursorShape.PointingHandCursor)
            rb.setStyleSheet("QPushButton { background: transparent; border: none; } QPushButton:hover { background: rgba(255,255,255,10); border-radius: 4px; }"); rb.clicked.connect(reset_cb); rl.addWidget(rb)
        lay.addRow(self.create_label(label), row_w)
        return s

    def reset_radial_defaults(self):
        self.cfg['radial_menu'] = copy.deepcopy(DEFAULTS['radial_menu'])
        ConfigManager.save(self.cfg)
        rm = self.cfg['radial_menu']
        
        # Update Widgets
        self.rad_enabled_toggle.setChecked(rm.get('enabled', True))
        self.kb_btn.key_code = rm['activation_key']; self.kb_btn.update()
        self.rad_mode.setTextValue(rm.get('hold_mode', 'Hold'))
        self.rad_theme.setTextValue(rm.get('theme', 'Dark'))
        self.rad_radius_s.setValue(rm.get('radius', 160))
        self.rad_opacity_s.setValue(rm.get('opacity', 185))
        self.rad_deadzone_s.setValue(rm.get('deadzone', 30))
        self.rad_scroll_sens_s.setValue(rm.get('scroll_sens', 50))
        self.rad_mouse_sens_s.setValue(rm.get('mouse_sens', 100))
        
        self.refresh_radial_lists()
        self.sandbox_radial.update_settings(self.cfg)
        self.update_radial_instance()
    def add_toggle(self, layout, label_text, checked, callback):
        t = CustomToggle(checked); t.toggled.connect(callback); layout.addRow(self.create_label(label_text), t); return t
    def paintEvent(self, e):
        p = QPainter(self); p.setRenderHint(QPainter.RenderHint.Antialiasing); p.setBrush(QColor(20, 20, 25, 235)); p.setPen(Qt.PenStyle.NoPen); p.drawRoundedRect(self.rect(), 15, 15)
        grad = QLinearGradient(0, 0, 0, 100); grad.setColorAt(0, QColor(255, 255, 255, 15)); grad.setColorAt(1, Qt.GlobalColor.transparent); p.setBrush(grad); p.drawRoundedRect(self.rect(), 15, 15)

    def mousePressEvent(self, event): 
        if event.button() == Qt.MouseButton.LeftButton and event.position().y() < 60:
            self._start_pos = event.globalPosition().toPoint()
    def mouseMoveEvent(self, event):
        if hasattr(self, '_start_pos') and self._start_pos: 
            curr_pos = event.globalPosition().toPoint(); delta = curr_pos - self._start_pos
            self.move(self.pos() + delta); self._start_pos = curr_pos
    def mouseReleaseEvent(self, event): self._start_pos = None

