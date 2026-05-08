import os
import json
import copy
import shutil
from PyQt6.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
                               QFormLayout, QSlider, QPushButton, 
                               QLabel, QFileDialog, QStackedWidget, QLineEdit, 
                               QGridLayout, QScrollArea, QFrame, QSizePolicy, QApplication)
from PyQt6.QtCore import (Qt, QEvent, QPoint, QPointF, QRect, QRectF, QPropertyAnimation, 
                          QEasingCurve, pyqtSignal, QVariantAnimation, QParallelAnimationGroup)
from PyQt6.QtGui import (QColor, QPainter, QFont, QPen, QAction, QPixmap, 
                         QPainterPath, QRadialGradient, QLinearGradient, QRegion)
from config import ConfigManager, STORAGE_PATH
from utils import WinAPI, VectorIcon, IconExtractor
from ui_common import AnimatedMenu
from folder_view import FolderView

# Default settings for reset
DEFAULTS = {
    "size_preset": "Medium",
    "folder_size": 80,
    "mini_icon_size": 27,
    "font_size": 10,
    "expanded_icon_size": 48,
    "glow_intensity": 40,
    "glow_color": "#ffffff",
    "bg_color": "#141414",
    "title_color": "#ffffff",
    "highlight_color": "#50FA7B",
    "opacity": 80,
    "radius": 20,
    "cover_blur": 0,
    "cover_opacity": 255,
    "hover_speed": "Fluid",
    "morph_speed": "Fluid",
    "grid_snap": False,
    "grid_size": 110,
    "edge_padding": 0,
    "show_cover": False,
    "show_title": True
}

SCROLLBAR_CSS = """
QScrollArea, QScrollArea > QWidget > QWidget {
    background: transparent;
    border: none;
}
QScrollBar:vertical {
    width: 8px;
    background: transparent;
}
QScrollBar::handle:vertical {
    background: rgba(255, 255, 255, 50);
    border-radius: 4px;
    min-height: 20px;
}
QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical,
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
    background: none;
    border: none;
}
"""

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

    def hide_morph(self):
        super().hide_morph()

    def refresh(self, new_paths=None):
        super().refresh(new_paths)
        if hasattr(self, 'grid_w') and hasattr(self, 'grid_h'):
            self.setFixedSize(int(self.grid_w + 30), int(self.grid_h + 70))
            self.hw.setFixedSize(int(self.grid_w), 35)

class SandboxFolderIcon(QWidget):
    def __init__(self, cfg):
        super().__init__()
        self.setFixedSize(300, 300)
        self.cfg = cfg
        self.local_settings = copy.deepcopy(cfg.get('global_settings', DEFAULTS))
        
        dummy_apps = []
        for i in range(27):
            dummy_apps.append({
                "name": f"App {i+1}", 
                "path": f"C:\\Windows\\explorer.exe" + " " * i, 
                "pinned": False
            })
            
        self.data = {
            "id": "sandbox_folder",
            "name": "Live Preview",
            "pos": [0, 0],
            "use_custom_settings": True,
            "custom_settings": self.local_settings,
            "apps": dummy_apps
        }
        
        self.setMouseTracking(True)
        self._scale = 1.0
        self._hover_progress = 0.0
        self.hover_anim = QVariantAnimation(self)
        self.hover_anim.setDuration(250)
        self.hover_anim.setEasingCurve(QEasingCurve.Type.OutCubic)
        self.hover_anim.setStartValue(0.0)
        self.hover_anim.setEndValue(1.0)
        self.hover_anim.valueChanged.connect(self._set_hover_progress)
        self.pulse_anim = QVariantAnimation(self)
        self.pulse_anim.setDuration(400); self.pulse_anim.setStartValue(1.0); self.pulse_anim.setEndValue(1.1)
        self.pulse_anim.setEasingCurve(QEasingCurve.Type.OutElastic)
        self.pulse_anim.valueChanged.connect(lambda v: (setattr(self, '_scale', v), self.update()))
        self.local_mouse_pos = QPoint(150, 150)
        self.is_dragging = False

    def trigger_pulse(self): self.pulse_anim.stop(); self.pulse_anim.start()

    def get_setting(self, key, default):
        preset = self.cfg.get('global_settings', {}).get('size_preset', 'Medium')
        use_custom = self.data.get('use_custom_settings', False)
        if use_custom:
            preset = self.data.get('custom_settings', {}).get('size_preset', preset)
            
        SIZE_PRESETS = {
            "Small": {"folder_size": 60, "mini_icon_size": 12, "font_size": 9, "expanded_icon_size": 32},
            "Medium": {"folder_size": 80, "mini_icon_size": 16, "font_size": 10, "expanded_icon_size": 48},
            "Large": {"folder_size": 110, "mini_icon_size": 24, "font_size": 12, "expanded_icon_size": 64}
        }
        
        if preset in SIZE_PRESETS and key in SIZE_PRESETS[preset]:
            return SIZE_PRESETS[preset][key]
            
        if use_custom:
            return self.data.get('custom_settings', {}).get(key, self.cfg.get('global_settings', {}).get(key, default))
        return self.cfg.get('global_settings', {}).get(key, default)

    def _set_hover_progress(self, v): 
        self._hover_progress = v
        self.update()
    
    def update_sandbox_settings(self, new_settings, real_apps=None):
        self.data['custom_settings'].update(new_settings)
        if real_apps is not None:
            self.data['apps'] = copy.deepcopy(real_apps)
        self.update()

    def enterEvent(self, e):
        speed_mode = self.get_setting('hover_speed', 'Fluid')
        self.hover_anim.setDuration({"Snappy": 150, "Fluid": 250, "Relaxed": 400}.get(speed_mode, 250))
        self.hover_anim.setDirection(QVariantAnimation.Direction.Forward)
        self.hover_anim.start()
        
    def leaveEvent(self, e):
        self.hover_anim.setDirection(QVariantAnimation.Direction.Backward)
        self.hover_anim.start()
        self.local_mouse_pos = QPoint(150, 150)

    def mouseMoveEvent(self, e):
        self.local_mouse_pos = e.position().toPoint()
        if self._hover_progress > 0: self.update()

    def paintEvent(self, e):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
        p.fillRect(self.rect(), Qt.GlobalColor.transparent)
        
        cx, cy = self.width() / 2, self.height() / 2
        folder_size = self.get_setting('folder_size', 80)
        mini_icon_size = self.get_setting('mini_icon_size', 16)
        glow_intensity = self.get_setting('glow_intensity', 40)
        glow_color = self.get_setting('glow_color', '#ffffff')
        bg_color = self.get_setting('bg_color', '#141414')
        opacity = self.get_setting('opacity', 80)
        radius = self.get_setting('radius', 20)
        
        if self._hover_progress > 0:
            p.save()
            p.setPen(Qt.PenStyle.NoPen)
            glow_c = QColor(glow_color)
            steps = 6
            max_a = int(glow_intensity * self._hover_progress)
            step_a = max(1, int(max_a / steps)) if steps > 0 else 0
            glow_c.setAlpha(step_a)
            p.setBrush(glow_c)
            for i in range(steps, 0, -1):
                offset = i * 4 * self._hover_progress
                p.drawRoundedRect(QRectF(cx - folder_size / 2 - offset, 
                                         cy - folder_size / 2 - offset, 
                                         folder_size + offset * 2, 
                                         folder_size + offset * 2), 
                                  radius + offset / 2, radius + offset / 2)
            p.restore()
            
        hover_zoom = 1.0 + (0.15 * self._hover_progress)
        combined_scale = self._scale * hover_zoom
        if combined_scale != 1.0: 
            p.translate(cx, cy)
            p.scale(combined_scale, combined_scale)
            p.translate(-cx, -cy)
            
        p.save()
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QColor(0, 0, 0, int(15 * self._hover_progress)))
        for i in range(6, 0, -1):
            offset = i * 2 * self._hover_progress
            p.drawRoundedRect(QRectF(cx - folder_size / 2 - offset, 
                                     cy - folder_size / 2 - offset + 3, 
                                     folder_size + offset * 2, 
                                     folder_size + offset * 2), 
                               radius + offset / 2, radius + offset / 2)
        p.restore()
        
        c = QColor(glow_color)
        c.setAlpha(30)
        bg_c = QColor(bg_color)
        bg_c.setAlpha(opacity)
        p.setBrush(bg_c)
        p.setPen(Qt.PenStyle.NoPen)
        p.drawRoundedRect(QRectF(cx - folder_size / 2, cy - folder_size / 2, folder_size, folder_size), radius, radius)
        
        draw_grid = True
        show_cover = self.get_setting('show_cover', False)
        cover_path = self.data.get('cover_image')
        
        if show_cover:
            pixmap = None
            if cover_path and os.path.exists(cover_path):
                pixmap = QPixmap(cover_path)
            else:
                # Use default thumbnail
                pixmap = VectorIcon.icon("folders", "#ffffff").pixmap(256, 256)
                
            if pixmap and not pixmap.isNull():
                path = QPainterPath()
                path.addRoundedRect(QRectF(cx - folder_size / 2, cy - folder_size / 2, folder_size, folder_size), radius, radius)
                p.setClipPath(path)
                
                blur_amount = self.get_setting('cover_blur', 0)
                if blur_amount > 0:
                    scale_factor = max(4, int(32 - (blur_amount / 100.0) * 28))
                    pixmap = pixmap.scaled(scale_factor, scale_factor, Qt.AspectRatioMode.KeepAspectRatioByExpanding, Qt.TransformationMode.SmoothTransformation)
                    
                cover_opacity = self.get_setting('cover_opacity', 100) / 100.0
                p.setOpacity((1.0 - self._hover_progress) * cover_opacity)
                
                scaled_pixmap = pixmap.scaled(int(folder_size), int(folder_size), Qt.AspectRatioMode.KeepAspectRatioByExpanding, Qt.TransformationMode.SmoothTransformation)
                px, py = cx - folder_size / 2 + (folder_size - scaled_pixmap.width()) / 2.0, cy - folder_size / 2 + (folder_size - scaled_pixmap.height()) / 2.0
                p.drawPixmap(int(px), int(py), scaled_pixmap)
                p.setClipping(False)
                p.setOpacity(1.0)
                if self._hover_progress <= 0: draw_grid = False
                else: p.setOpacity(self._hover_progress)

        if draw_grid:
            apps = self.data.get('apps', [])[:9]
            isz = mini_icon_size + (11 * self._hover_progress)
            gap = (folder_size / 20) + ((folder_size / 5) * self._hover_progress)
            tl = 3 * isz + 2 * gap
            gx, gy = cx - tl / 2, cy - tl / 2
            if gx < 10: gx = 10
            elif gx + tl > 290: gx = 290 - tl
            if gy < 10: gy = 10
            elif gy + tl > 290: gy = 290 - tl
            for i, a in enumerate(apps):
                r, c_idx = i // 3, i % 3
                x, y = gx + c_idx * (isz + gap), gy + r * (isz + gap)
                raw_pix = IconExtractor.get_icon_pixmap(a['path'], int(isz))
                if not raw_pix.isNull():
                    scaled_pix = raw_pix.scaled(int(isz), int(isz), Qt.AspectRatioMode.IgnoreAspectRatio, Qt.TransformationMode.SmoothTransformation)
                    p.drawPixmap(int(x), int(y), int(isz), int(isz), scaled_pix)
            p.setOpacity(1.0)
            
        p.resetTransform()
        if self.get_setting('show_title', True):
            title_color = self.get_setting('title_color', '#ffffff')
            p.setPen(QColor(title_color))
            p.drawText(QRect(0, int(cy + folder_size / 2 + 35), 300, 20), Qt.AlignmentFlag.AlignCenter, self.data['name'])

class PreviewPanel(QWidget):
    def __init__(self, cfg, parent=None):
        super().__init__(parent); self.cfg = cfg; self.setFixedWidth(400)
        self.main_layout = QVBoxLayout(self); self.main_layout.setContentsMargins(20, 20, 20, 20); self.main_layout.setSpacing(15)
        
        header = QLabel("LIVE PREVIEW"); header.setAlignment(Qt.AlignmentFlag.AlignCenter)
        header.setStyleSheet("color: rgba(255, 255, 255, 100); font-weight: bold; font-size: 12px; letter-spacing: 1px;")
        self.main_layout.addWidget(header)

        # Tab Toggle
        self.tab_container = QWidget(); self.tab_container.setFixedHeight(40)
        self.tab_layout = QHBoxLayout(self.tab_container); self.tab_layout.setContentsMargins(0, 5, 0, 5); self.tab_layout.setSpacing(10)
        
        self.btn_collapsed = QPushButton("Collapsed"); self.btn_expanded = QPushButton("Expanded")
        for b in [self.btn_collapsed, self.btn_expanded]:
            b.setCursor(Qt.CursorShape.PointingHandCursor); b.setCheckable(True); b.setFixedHeight(30)
            b.setStyleSheet("QPushButton { background: rgba(255,255,255,10); color: #aaa; border-radius: 15px; border: none; font-weight: bold; } QPushButton:checked { background: #50FA7B; color: #141414; } QPushButton:hover:!checked { background: rgba(255,255,255,20); }")
        self.btn_collapsed.setChecked(True)
        self.btn_collapsed.clicked.connect(lambda: self.content_stack.setCurrentIndex(0))
        self.btn_expanded.clicked.connect(self.show_expanded)
        self.tab_layout.addWidget(self.btn_collapsed); self.tab_layout.addWidget(self.btn_expanded)
        self.main_layout.addWidget(self.tab_container)
        
        self.content_stack = AnimatedStackedWidget(); self.main_layout.addWidget(self.content_stack, 1)
        
        # Collapsed Page
        self.collapsed_page = QWidget(); self.collapsed_layout = QVBoxLayout(self.collapsed_page)
        self.sandbox_icon = SandboxFolderIcon(cfg)
        self.collapsed_layout.addWidget(self.sandbox_icon, 0, Qt.AlignmentFlag.AlignCenter)
        self.content_stack.addWidget(self.collapsed_page)
        
        # Expanded Page
        self.expanded_page = QWidget(); self.expanded_layout = QVBoxLayout(self.expanded_page); self.expanded_layout.setContentsMargins(0, 0, 0, 0)
        self.expanded_layout.addStretch()
        h_lay = QHBoxLayout(); h_lay.addStretch()
        self.sandbox_view = SandboxFolderView(self.sandbox_icon.data, self.sandbox_icon, parent=self.expanded_page)
        h_lay.addWidget(self.sandbox_view); h_lay.addStretch(); self.expanded_layout.addLayout(h_lay); self.expanded_layout.addStretch()
        self.content_stack.addWidget(self.expanded_page)
        
        hint = QLabel("Tabs switch states • Live rendering"); hint.setAlignment(Qt.AlignmentFlag.AlignCenter)
        hint.setStyleSheet("color: rgba(255,255,255,50); font-size: 11px;")
        self.main_layout.addWidget(hint)

    def show_expanded(self):
        self.content_stack.setCurrentIndex(1)
        self.sandbox_view.anim_progress = 1.0; self.sandbox_view.refresh(); self.sandbox_view.show()
        self.sandbox_view.hw.show(); self.sandbox_view.cw.show()

    def update_sandbox_settings(self, settings, real_apps=None):
        self.sandbox_icon.update_sandbox_settings(settings, real_apps)
        if hasattr(self, 'sandbox_view'):
            self.sandbox_view.cfg['global_settings'] = settings
            if real_apps is not None:
                self.sandbox_view.folder_data['apps'] = copy.deepcopy(real_apps)
            self.sandbox_view.refresh(); self.sandbox_view.update()

    def paintEvent(self, e):
        p = QPainter(self); p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.setPen(QPen(QColor(255, 255, 255, 15), 1))
        p.drawLine(0, 40, 0, self.height() - 40)

class AnimatedButton(QPushButton):
    def __init__(self, text, parent=None, color="#50FA7B"):
        super().__init__(text, parent); self.setCursor(Qt.CursorShape.PointingHandCursor)
        self._color = QColor(color); self._alpha = 50
        self.anim = QVariantAnimation(self); self.anim.setDuration(250); self.anim.valueChanged.connect(self._on_anim)
    def _on_anim(self, v): self._alpha = v; self.update()
    def enterEvent(self, e): self.anim.setStartValue(self._alpha); self.anim.setEndValue(120); self.anim.start()
    def leaveEvent(self, e): self.anim.setStartValue(self._alpha); self.anim.setEndValue(50); self.anim.start()
    def paintEvent(self, e):
        p = QPainter(self); p.setRenderHint(QPainter.RenderHint.Antialiasing); bg = QColor(self._color); bg.setAlpha(int(self._alpha))
        p.setBrush(bg); p.setPen(QPen(QColor(255, 255, 255, 40), 1)); p.drawRoundedRect(self.rect().adjusted(1, 1, -1, -1), 10, 10)
        p.setPen(Qt.GlobalColor.white); p.setFont(QFont("Segoe UI", 10, QFont.Weight.Medium)); p.drawText(self.rect(), Qt.AlignmentFlag.AlignCenter, self.text())

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
        if self.is_active: p.fillRect(self.rect(), QColor(80, 250, 123, 20)); p.fillRect(0, 0, 3, self.height(), QColor(80, 250, 123)); p.setPen(QColor(80, 250, 123))
        else: (p.fillRect(self.rect(), QColor(255, 255, 255, 10)) if self.is_hover else None); p.setPen(QColor(170, 170, 170))
        ic = "#50fa7b" if self.is_active else ("#ffffff" if self.is_hover else "#aaaaaa")
        p.drawPixmap(15, 10, VectorIcon.icon(self.icon, ic).pixmap(20, 20))
        if self.width() > 60: p.setFont(QFont("Segoe UI", 10)); p.drawText(QRect(50, 0, self.width()-50, self.height()), Qt.AlignmentFlag.AlignVCenter, self.text)

class Sidebar(QFrame):
    tabChanged = pyqtSignal(int)
    def __init__(self, parent=None):
        super().__init__(parent); self.expanded = False; self.setFixedWidth(50)
        self.setStyleSheet("Sidebar { background-color: transparent; border-right: 1px solid rgba(255,255,255,10); border-bottom-left-radius: 15px; }")
        self.layout = QVBoxLayout(self); self.layout.setContentsMargins(0, 10, 0, 10); self.layout.setSpacing(5); self.layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        self.t_btn = QPushButton("≡"); self.t_btn.setFixedSize(50, 40); self.t_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.t_btn.setStyleSheet("QPushButton { color: white; font-size: 24px; font-weight: bold; background: transparent; border: none; } QPushButton:hover { background: rgba(255,255,255,20); }")
        self.t_btn.clicked.connect(self.toggle_sidebar); self.layout.addWidget(self.t_btn); self.layout.addSpacing(10)
        self.btns, self.current_idx = [], 0
        self.a_min = QPropertyAnimation(self, b"minimumWidth"); self.a_min.setDuration(200); self.a_min.setEasingCurve(QEasingCurve.Type.InOutQuad)
        self.a_max = QPropertyAnimation(self, b"maximumWidth"); self.a_max.setDuration(200); self.a_max.setEasingCurve(QEasingCurve.Type.InOutQuad)
    def toggle_sidebar(self):
        self.expanded = not self.expanded; s, e = (150, 50) if not self.expanded else (50, 150)
        self.a_min.setStartValue(s); self.a_min.setEndValue(e); self.a_min.start()
        self.a_max.setStartValue(s); self.a_max.setEndValue(e); self.a_max.start()
    def addTab(self, i, t):
        idx = len(self.btns); b = SidebarButton(i, t); b.clicked.connect(lambda: self.select_tab(idx))
        self.layout.addWidget(b); self.btns.append(b); self.update_styles()
    def select_tab(self, i): (self.set_idx(i) if self.current_idx != i else None)
    def set_idx(self, i): self.current_idx = i; self.update_styles(); self.tabChanged.emit(i)
    def update_styles(self): 
        for i, b in enumerate(self.btns): b.set_active(i == self.current_idx)

class CustomToggle(QWidget):
    toggled = pyqtSignal(bool)
    def __init__(self, checked=False, parent=None):
        super().__init__(parent); self.setFixedSize(54, 28); self._checked = checked; self._position = 28 if checked else 2
        self.anim = QVariantAnimation(self); self.anim.setDuration(250); self.anim.setEasingCurve(QEasingCurve.Type.InOutQuad)
        self.anim.valueChanged.connect(self._animate); self.setCursor(Qt.CursorShape.PointingHandCursor)
    def _animate(self, v): self._position = v; self.update()
    def isChecked(self): return self._checked
    def setChecked(self, c):
        if self._checked == c: return
        self._checked = c; self.anim.setStartValue(self._position); self.anim.setEndValue(28 if c else 2); self.anim.start(); self.toggled.emit(c)
    def mouseReleaseEvent(self, e): (self.setChecked(not self._checked) if e.button()==Qt.MouseButton.LeftButton else None)
    def paintEvent(self, e):
        p = QPainter(self); p.setRenderHint(QPainter.RenderHint.Antialiasing); bg = QColor("#50FA7B") if self._checked else QColor(255, 255, 255, 40)
        p.setBrush(bg); p.setPen(Qt.PenStyle.NoPen); p.drawRoundedRect(self.rect(), 14, 14); p.setBrush(Qt.GlobalColor.white); p.drawEllipse(int(self._position), 4, 20, 20)

class AnimatedStackedWidget(QStackedWidget):
    def __init__(self, parent=None):
        super().__init__(parent); self._animating = False; self._target_index = 0
    def targetIndex(self):
        return self._target_index if self._animating else self.currentIndex()
    def setCurrentIndexFast(self, index):
        self._target_index = index; self._animating = False; super().setCurrentIndex(index)
        for i in range(self.count()):
            w = self.widget(i)
            if w:
                if i == index: w.move(0, 0); w.show(); w.raise_()
                else: w.hide()
        p = self.parentWidget()
        while p: p.update(); p = p.parentWidget()
    def setCurrentIndex(self, index):
        if index == self.currentIndex() or self._animating: return
        self._target_index = index; old_idx = self.currentIndex(); next_w = self.widget(index); curr_w = self.currentWidget()
        if not curr_w or not next_w: super().setCurrentIndex(index); return
        self._animating = True; width = self.width(); direction = 1 if index > old_idx else -1
        next_w.setGeometry(0, 0, width, self.height()); next_w.move(direction * width, 0); next_w.show(); next_w.raise_()
        self.anim_curr = QPropertyAnimation(curr_w, b"pos"); self.anim_curr.setDuration(350); self.anim_curr.setEasingCurve(QEasingCurve.Type.OutCubic)
        self.anim_curr.setStartValue(QPoint(0, 0)); self.anim_curr.setEndValue(QPoint(-direction * width, 0))
        self.anim_next = QPropertyAnimation(next_w, b"pos"); self.anim_next.setDuration(350); self.anim_next.setEasingCurve(QEasingCurve.Type.OutCubic)
        self.anim_next.setStartValue(QPoint(direction * width, 0)); self.anim_next.setEndValue(QPoint(0, 0))
        self.group = QParallelAnimationGroup(); self.group.addAnimation(self.anim_curr); self.group.addAnimation(self.anim_next)
        self.group.finished.connect(lambda: self._anim_done(index, curr_w)); self.group.start()
    def _anim_done(self, index, old_w):
        old_w.hide(); super().setCurrentIndex(index); old_w.move(0, 0); self._animating = False
        if self.window(): self.window().update()

class DropdownButton(QPushButton):
    valueChanged = pyqtSignal(str)
    def __init__(self, c, o, parent=None):
        super().__init__(c, parent); self.current = c; self.options = o; self.setCursor(Qt.CursorShape.PointingHandCursor); self.setFixedWidth(120)
        self.setStyleSheet("background: rgba(255,255,255,20); color: white; padding: 8px; padding-right: 25px; border-radius: 6px; text-align: left; font-weight: bold;"); self.clicked.connect(self.show_popup)
    def setTextValue(self, t): self.current = t; self.setText(t); self.repaint()
    def show_popup(self):
        m = AnimatedMenu(self)
        for o in self.options:
            a = QAction(o, self); a.triggered.connect(lambda checked, opt=o: self.on_selected(opt)); m.addAction(a)
        m.exec(self.mapToGlobal(QPoint(0, self.height())))
    def on_selected(self, o): 
        self.setTextValue(o); self.valueChanged.emit(o)
        if self.window(): self.window().update()
    def paintEvent(self, e):
        super().paintEvent(e); p = QPainter(self); p.setPen(Qt.GlobalColor.white)
        p.drawText(self.rect().adjusted(0, 0, -10, 0), Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter, "▼")
    def setText(self, t):
        super().setText(t); self.repaint()
        if self.window(): self.window().update()

class CollapsibleContainer(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent); self.layout = QVBoxLayout(self); self.layout.setContentsMargins(0,0,0,0); self.layout.setSpacing(10); self.setMaximumHeight(0)
        self.anim = QPropertyAnimation(self, b"maximumHeight"); self.anim.setDuration(300); self.anim.setEasingCurve(QEasingCurve.Type.InOutQuad)
        self.anim.valueChanged.connect(lambda: self.updateGeometry())
    def addLayout(self, l): self.layout.addLayout(l)
    def setExpanded(self, e):
        t = 500 if e else 0
        if self.maximumHeight() == t: return
        self.anim.setStartValue(self.height()); self.anim.setEndValue(t); self.anim.start()

class ColorPicker(QWidget):
    colorSelected = pyqtSignal(str)
    def __init__(self, initial, parent=None):
        super().__init__(parent); self.setWindowFlags(Qt.WindowType.Popup | Qt.WindowType.FramelessWindowHint); self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setFixedSize(260, 220); self.c = QWidget(self); self.c.setGeometry(0, 0, 260, 220); self.c.setStyleSheet("background: rgba(30, 30, 30, 245); border: 1px solid rgba(255,255,255,40); border-radius: 15px;")
        l = QVBoxLayout(self.c); l.setContentsMargins(18, 18, 18, 18); self.hex = QLineEdit(initial); self.hex.setStyleSheet("background: rgba(0,0,0,140); color: white; border: 1px solid #666; padding: 10px; border-radius: 8px;")
        l.addWidget(self.hex); self.hex.textChanged.connect(lambda t: (self.colorSelected.emit(t) if len(t)==7 else None)); g = QGridLayout(); g.setSpacing(10); colors = ["#ff5555", "#ffb86c", "#f1fa8c", "#50fa7b", "#8be9fd", "#bd93f9", "#ff79c6", "#ffffff", "#aaaaaa", "#6272a4", "#44475a", "#282a36"]
        for i, c in enumerate(colors):
            b = QPushButton(); b.setFixedSize(34, 34); b.setCursor(Qt.CursorShape.PointingHandCursor); b.setStyleSheet(f"background: {c}; border-radius: 17px; border: 2px solid rgba(255,255,255,20);")
            b.clicked.connect(lambda _, col=c: (self.colorSelected.emit(col), self.close())); g.addWidget(b, i // 4, i % 4)
        l.addLayout(g)

class FolderTile(QWidget):
    clicked = pyqtSignal(str)
    def __init__(self, data, parent=None):
        super().__init__(parent); self.data = data; self.setFixedSize(140, 180); self.setCursor(Qt.CursorShape.PointingHandCursor); self._hover_val = 0.0
        self.anim = QVariantAnimation(self); self.anim.setDuration(200); self.anim.valueChanged.connect(self._on_anim)
        self._preview_pixmap = None
    def _animate(self, e): self.anim.stop(); self.anim.setStartValue(self._hover_val); self.anim.setEndValue(e); self.anim.start()
    def _on_anim(self, v): self._hover_val = v; self.update()
    def enterEvent(self, e): self._animate(1.0)
    def leaveEvent(self, e): self._animate(0.0)
    def mouseReleaseEvent(self, e): (self.clicked.emit(self.data['id']) if e.button()==Qt.MouseButton.LeftButton else None)
    
    def _generate_preview(self):
        isz, pad = 28, 5; tl = 3*isz+2*pad
        self._preview_pixmap = QPixmap(int(tl), int(tl)); self._preview_pixmap.fill(Qt.GlobalColor.transparent)
        pp = QPainter(self._preview_pixmap); pp.setRenderHint(QPainter.RenderHint.Antialiasing); pp.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
        apps = self.data.get('apps', [])[:9]
        for i, a in enumerate(apps):
            r, c = i//3, i%3; x, y = c*(isz+pad), r*(isz+pad)
            px = IconExtractor.get_icon_pixmap(a['path'], int(isz))
            if not px.isNull(): pp.drawPixmap(int(x), int(y), int(isz), int(isz), px.scaled(isz, isz, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation))
        pp.end()

    def paintEvent(self, e):
        p = QPainter(self); p.setRenderHint(QPainter.RenderHint.Antialiasing); p.save()
        sc = 1.0 + (0.08 * self._hover_val); p.translate(70, 75); p.scale(sc, sc); p.translate(-70, -75)
        if self._hover_val > 0: p.setBrush(QColor(80, 250, 123, int(60 * self._hover_val))); p.setPen(QPen(QColor(80, 250, 123, int(200 * self._hover_val)), 2))
        else: p.setBrush(QColor(255, 255, 255, 15)); p.setPen(QPen(QColor(255, 255, 255, 30), 1))
        p.drawRoundedRect(15, 15, 110, 110, 18, 18)
        if self._preview_pixmap is None: self._generate_preview()
        if self._preview_pixmap:
            tl = self._preview_pixmap.width(); sx, sy = 15+(110-tl)/2, 15+(110-tl)/2
            p.drawPixmap(QPointF(sx, sy), self._preview_pixmap)
        p.restore(); p.setPen(Qt.GlobalColor.white); p.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold if self._hover_val > 0.5 else QFont.Weight.Normal))
        p.drawText(QRectF(0, 140, 140, 30), Qt.AlignmentFlag.AlignCenter, self.data.get('name', 'Folder'))

class DashboardUI(QMainWindow):
    def __init__(self, cfg, app_instances):
        super().__init__(); self.cfg, self.app_instances = cfg, app_instances; self.current_fid = None
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.Window)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground); self.setFixedSize(1200, 700)
        self.setStyleSheet("QMainWindow { background: transparent; }")
        
        self.cw = QWidget(); self.cw.setStyleSheet("background: transparent;"); self.setCentralWidget(self.cw)
        self.main_layout = QVBoxLayout(self.cw); self.main_layout.setContentsMargins(0, 0, 0, 0); self.main_layout.setSpacing(0)
        
        self.title_bar = TitleBar(self); self.main_layout.addWidget(self.title_bar)
        
        content_area = QHBoxLayout(); content_area.setContentsMargins(0, 0, 0, 0); content_area.setSpacing(0)
        self.main_layout.addLayout(content_area)
        
        self.sidebar = Sidebar(); self.sidebar.addTab("settings", "Global"); self.sidebar.addTab("folders", "Individual"); content_area.addWidget(self.sidebar)
        
        self.stack = AnimatedStackedWidget(); content_area.addWidget(self.stack, 1)
        
        self.preview_panel = PreviewPanel(cfg); content_area.addWidget(self.preview_panel)
        
        self.setup_global_tab(); self.setup_individual_tab()
        self.sidebar.tabChanged.connect(self.on_tab_changed); self.refresh_grid()

    def prewarm(self):
        self.setWindowOpacity(0.0); self.show(); QApplication.processEvents()
        self.preview_panel.sandbox_icon.hover_anim.start(); self.preview_panel.sandbox_icon.hover_anim.stop()
        self.hide(); self.setWindowOpacity(1.0)

    def showEvent(self, e):
        super().showEvent(e); self._apply_mask()
        __import__('PyQt6.QtCore').QtCore.QTimer.singleShot(100, lambda: WinAPI.set_modern_visuals(self.winId(), True))

    def _apply_mask(self):
        path = QPainterPath(); path.addRoundedRect(QRectF(self.rect()), 15, 15)
        self.setMask(QRegion(path.toFillPolygon().toPolygon()))

    def setup_global_tab(self):
        self.global_tab = QWidget(); self.global_tab.setObjectName("SettingPanel"); self.global_tab.setStyleSheet(PANEL_STYLE)
        l = QVBoxLayout(self.global_tab); scr = QScrollArea(); scr.setWidgetResizable(True); scr.setStyleSheet(SCROLLBAR_CSS); cnt = QWidget(); scr.setWidget(cnt); l.addWidget(scr); self.stack.addWidget(self.global_tab)
        self.g_layout = QFormLayout(cnt); self.g_layout.setContentsMargins(40, 30, 40, 30); self.g_layout.setSpacing(20)
        self.g_sliders, self.g_slider_labels, self.g_color_btns = {}, {}, {}
        gs = self.cfg.get('global_settings', {})
        self.g_preset = DropdownButton(gs.get('size_preset', 'Medium'), ["Small", "Medium", "Large", "Custom"]); self.g_preset.valueChanged.connect(self.on_g_preset_changed); self.g_layout.addRow(self.create_label("Size Preset"), self.g_preset)
        self.g_size_container = CollapsibleContainer(); sf = QFormLayout(); self.g_size_container.addLayout(sf); self.g_layout.addRow(self.g_size_container)
        for k, lbl, mn, mx in [('folder_size', "Folder Size", 60, 200), ('mini_icon_size', "Mini Icon", 12, 64), ('font_size', "Font Size", 8, 16), ('expanded_icon_size', "App Icon", 24, 96)]:
            c, s, lv = self.create_static_slider(gs.get(k, DEFAULTS[k]), mn, mx, DEFAULTS[k], lambda v, key=k: self.upd_g(key, v))
            self.g_sliders[k] = s; self.g_slider_labels[k] = lv; sf.addRow(self.create_label(lbl), c)
        self.g_size_container.setExpanded(gs.get('size_preset') == "Custom"); self.g_layout.addRow(self.create_sep())
        
        self.g_show_title = CustomToggle(gs.get('show_title', True)); self.g_show_title.toggled.connect(lambda v: self.upd_g('show_title', v)); self.g_layout.addRow(self.create_label("Show Folder Name"), self.g_show_title)
        self.g_show_cover = CustomToggle(gs.get('show_cover', False)); self.g_show_cover.toggled.connect(self.on_g_show_cover_changed); self.g_layout.addRow(self.create_label("Show Cover"), self.g_show_cover)
        
        self.g_cover_container = CollapsibleContainer(); cf = QFormLayout(); self.g_cover_container.addLayout(cf); self.g_layout.addRow(self.g_cover_container)
        for k, lbl, mn, mx in [('cover_blur', "Cover Blur", 0, 50), ('cover_opacity', "Cover Opacity", 0, 255)]:
            c, s, lv = self.create_static_slider(gs.get(k, DEFAULTS[k]), mn, mx, DEFAULTS[k], lambda v, key=k: self.upd_g(key, v))
            self.g_sliders[k] = s; self.g_slider_labels[k] = lv; cf.addRow(self.create_label(lbl), c)
        self.g_cover_container.setExpanded(gs.get('show_cover', False))
        
        self.g_layout.addRow(self.create_sep())
        for k, lbl, mn, mx in [('glow_intensity', "Glow Alpha", 0, 255), ('radius', "Radius", 0, 50), ('opacity', "Opacity", 0, 255)]:
            c, s, lv = self.create_static_slider(gs.get(k, DEFAULTS[k]), mn, mx, DEFAULTS[k], lambda v, key=k: self.upd_g(key, v))
            self.g_sliders[k] = s; self.g_slider_labels[k] = lv; self.g_layout.addRow(self.create_label(lbl), c)
        self.g_grid_snap = CustomToggle(gs.get('grid_snap', False)); self.g_grid_snap.toggled.connect(lambda v: self.upd_g('grid_snap', v)); self.g_layout.addRow(self.create_label("Snap to Grid"), self.g_grid_snap)
        c, s, lv = self.create_static_slider(gs.get('grid_size', DEFAULTS['grid_size']), 10, 200, DEFAULTS['grid_size'], lambda v: self.upd_g('grid_size', v))
        self.g_sliders['grid_size'] = s; self.g_slider_labels['grid_size'] = lv; self.g_layout.addRow(self.create_label("Grid Size"), c)
        c, s, lv = self.create_static_slider(gs.get('edge_padding', DEFAULTS['edge_padding']), 0, 100, DEFAULTS['edge_padding'], lambda v: self.upd_g('edge_padding', v))
        self.g_sliders['edge_padding'] = s; self.g_slider_labels['edge_padding'] = lv; self.g_layout.addRow(self.create_label("Edge Padding"), c)
        self.g_h_speed = DropdownButton(gs.get('hover_speed', 'Fluid'), ["Snappy", "Fluid", "Relaxed"]); self.g_h_speed.valueChanged.connect(lambda v: self.upd_g('hover_speed', v)); self.g_layout.addRow(self.create_label("Hover Speed"), self.g_h_speed)
        self.g_m_speed = DropdownButton(gs.get('morph_speed', 'Fluid'), ["Snappy", "Fluid", "Relaxed"]); self.g_m_speed.valueChanged.connect(lambda v: self.upd_g('morph_speed', v)); self.g_layout.addRow(self.create_label("Morph Speed"), self.g_m_speed)
        self.g_layout.addRow(self.create_sep())
        for k, lbl in [('glow_color', "Glow Color"), ('bg_color', "BG Color"), ('title_color', "Text Color"), ('highlight_color', "Highlight")]:
            btn = QPushButton(); btn.setFixedSize(65, 26); btn.setCursor(Qt.CursorShape.PointingHandCursor); btn.setStyleSheet(f"background: {gs.get(k, DEFAULTS[k])}; border-radius: 6px; border: 2px solid rgba(255,255,255,30);")
            btn.clicked.connect(lambda _, key=k, b=btn: self.pick_global_color(key, b)); self.g_color_btns[k] = btn; self.g_layout.addRow(self.create_label(lbl), btn)
        rst = AnimatedButton("Reset All to Default", color="#ff5555"); rst.clicked.connect(self.reset_global_all); self.g_layout.addRow(rst)

    def setup_individual_tab(self):
        self.ind_tab = QWidget(); self.ind_tab.setObjectName("SettingPanel"); self.ind_tab.setStyleSheet(PANEL_STYLE)
        l = QVBoxLayout(self.ind_tab); self.ind_stack = AnimatedStackedWidget(); l.addWidget(self.ind_stack)
        grid_w = QWidget(); gl = QVBoxLayout(grid_w); sc = QWidget(); sc.setFixedHeight(60); sl = QHBoxLayout(sc); sl.setContentsMargins(30, 15, 30, 0)
        self.f_search = QLineEdit(); self.f_search.setPlaceholderText("Search folders..."); self.f_search.textChanged.connect(lambda: self.refresh_grid()); self.f_search.setStyleSheet("background: rgba(0,0,0,100); color: white; border: 1px solid rgba(255,255,255,30); padding: 8px; border-radius: 6px;")
        self.f_sort = QPushButton("Sort: A-Z"); self.f_sort.setCursor(Qt.CursorShape.PointingHandCursor); self.f_sort.setStyleSheet("background: rgba(255,255,255,20); color: white; padding: 8px; border-radius: 6px;")
        self.f_sort_dir = True; self.f_sort.clicked.connect(lambda: (setattr(self, 'f_sort_dir', not self.f_sort_dir), self.f_sort.setText("Sort: A-Z" if self.f_sort_dir else "Sort: Z-A"), self.refresh_grid()))
        sl.addWidget(self.f_search); sl.addWidget(self.f_sort); gl.addWidget(sc); s = QScrollArea(); s.setWidgetResizable(True); s.setStyleSheet(SCROLLBAR_CSS); gl.addWidget(s); cnt = QWidget(); self.grid_layout = QGridLayout(cnt); self.grid_layout.setContentsMargins(30, 20, 30, 20); self.grid_layout.setSpacing(15); self.grid_layout.setAlignment(Qt.AlignmentFlag.AlignTop); s.setWidget(cnt); self.ind_stack.addWidget(grid_w)
        set_w = QWidget(); sl = QVBoxLayout(set_w); stk = QWidget(); stk.setFixedHeight(60); hl = QHBoxLayout(stk); hl.setContentsMargins(20, 0, 20, 0)
        bk = QPushButton(); bk.setIcon(VectorIcon.icon("back", "#8BE9FD")); bk.setFixedSize(32, 32); bk.setStyleSheet("background: transparent; border: none;"); bk.setCursor(Qt.CursorShape.PointingHandCursor); bk.clicked.connect(lambda: self.ind_stack.setCurrentIndex(0))
        self.ind_header = QLabel("Settings for Folder"); self.ind_header.setStyleSheet("color: white; font-weight: bold; font-size: 16px;"); rs = AnimatedButton("Reset All", color="#ff5555"); rs.setFixedSize(100, 30); rs.clicked.connect(self.reset_ind_all)
        hl.addWidget(bk); hl.addWidget(self.ind_header); hl.addStretch(); hl.addWidget(rs); sl.addWidget(stk); s = QScrollArea(); s.setWidgetResizable(True); s.setStyleSheet(SCROLLBAR_CSS); sl.addWidget(s); cnt = QWidget(); self.is_form = QFormLayout(cnt); self.is_form.setContentsMargins(40, 20, 40, 30); self.is_form.setSpacing(20); s.setWidget(cnt); self.setup_individual_fields(); self.ind_stack.addWidget(set_w); self.stack.addWidget(self.ind_tab)

    def setup_individual_fields(self):
        self.ind_toggle = CustomToggle(False); self.ind_toggle.toggled.connect(self.on_ind_toggle_changed); self.is_form.addRow(self.create_label("Use Custom Settings"), self.ind_toggle); self.is_form.addRow(self.create_sep())
        self.i_cnt = QWidget(); self.i_lay = QFormLayout(self.i_cnt); self.i_lay.setContentsMargins(0,0,0,0); self.i_lay.setSpacing(20)
        self.i_pst = DropdownButton("Medium", ["Small", "Medium", "Large", "Custom"]); self.i_pst.valueChanged.connect(self.on_i_preset_changed); self.i_lay.addRow(self.create_label("Size Preset"), self.i_pst)
        self.i_sz_cnt = CollapsibleContainer(); ifm = QFormLayout(); self.i_sz_cnt.addLayout(ifm); self.i_lay.addRow(self.i_sz_cnt)
        self.ind_sliders, self.ind_slider_labels = {}, {}
        for k, lbl, mn, mx in [('folder_size', "Size", 60, 200), ('mini_icon_size', "Mini Icon", 12, 64), ('font_size', "Font Size", 8, 16), ('expanded_icon_size', "App Icon", 24, 96)]:
            c, s, l = self.create_ind_slider(k, lbl, mn, mx); ifm.addRow(self.create_label(lbl), c)
        
        self.i_show_title = CustomToggle(True); self.i_show_title.toggled.connect(lambda v: self.upd_f(self.current_fid, 'show_title', v)); self.i_lay.addRow(self.create_label("Show Folder Name"), self.i_show_title)
        self.i_show_cover = CustomToggle(False); self.i_show_cover.toggled.connect(self.on_i_show_cover_changed); self.i_lay.addRow(self.create_label("Show Cover"), self.i_show_cover)
        
        self.i_cover_container = CollapsibleContainer(); icf = QFormLayout(); self.i_cover_container.addLayout(icf); self.i_lay.addRow(self.i_cover_container)
        for k, lbl, mn, mx in [('cover_blur', "Cover Blur", 0, 50), ('cover_opacity', "Cover Opacity", 0, 255)]:
            c, s, l = self.create_ind_slider(k, lbl, mn, mx); icf.addRow(self.create_label(lbl), c)
        
        cbt = AnimatedButton("Set Cover Image", color="#BD93F9"); cbt.clicked.connect(self.choose_cover); icf.addRow(self.create_label("Hero Cover"), cbt)
        clb = AnimatedButton("Clear Cover", color="#FF5555"); clb.clicked.connect(self.clear_cover); icf.addRow(None, clb)
        
        for k, lbl, mn, mx in [('glow_intensity', "Glow", 0, 255), ('radius', "Radius", 0, 50), ('opacity', "Opacity", 0, 255)]:
            c, s, l = self.create_ind_slider(k, lbl, mn, mx); self.i_lay.addRow(self.create_label(lbl), c)
        self.i_grid_snap = CustomToggle(False); self.i_grid_snap.toggled.connect(lambda v: self.upd_f(self.current_fid, 'grid_snap', v)); self.i_lay.addRow(self.create_label("Snap to Grid"), self.i_grid_snap)
        self.i_hs = DropdownButton("Fluid", ["Snappy", "Fluid", "Relaxed"]); self.i_hs.valueChanged.connect(lambda v: self.upd_f(self.current_fid, 'hover_speed', v)); self.i_lay.addRow(self.create_label("Hover Speed"), self.i_hs)
        self.i_ms = DropdownButton("Fluid", ["Snappy", "Fluid", "Relaxed"]); self.i_ms.valueChanged.connect(lambda v: self.upd_f(self.current_fid, 'morph_speed', v)); self.i_lay.addRow(self.create_label("Morph Speed"), self.i_ms)
        self.ind_color_btns = {}
        for k, lbl in [('glow_color', "Glow Color"), ('bg_color', "BG Color"), ('title_color', "Text Color"), ('highlight_color', "Highlight")]:
            btn = QPushButton(); btn.setFixedSize(65, 26); btn.setCursor(Qt.CursorShape.PointingHandCursor); btn.clicked.connect(lambda _, key=k, b=btn: self.pick_ind_color(key, b)); self.ind_color_btns[k] = btn; self.i_lay.addRow(self.create_label(lbl), btn)
        self.is_form.addRow(self.i_cnt)

    def on_g_show_cover_changed(self, v):
        self.upd_g('show_cover', v)
        self.g_cover_container.setExpanded(v)

    def on_i_show_cover_changed(self, v):
        if self.current_fid:
            self.upd_f(self.current_fid, 'show_cover', v)
            self.i_cover_container.setExpanded(v)

    def create_ind_slider(self, k, lbl, mn, mx):
        c = QWidget(); l = QHBoxLayout(c); s = QSlider(Qt.Orientation.Horizontal); s.setRange(mn, mx)
        s.setStyleSheet("QSlider::groove:horizontal { height: 6px; background: rgba(255,255,255,20); border-radius: 3px; } QSlider::handle:horizontal { background: #50FA7B; width: 16px; height: 16px; margin: -5px 0; border-radius: 8px; border: 2px solid white; }")
        lv = QLabel("0"); lv.setFixedWidth(35); lv.setStyleSheet("color: #50FA7B; font-weight: bold; font-family: 'Consolas', monospace; font-size: 13px;"); r = QPushButton(); r.setFixedSize(20, 20); r.setIcon(VectorIcon.icon("reset", "#aaaaaa")); r.setStyleSheet("background: transparent; border: none;"); r.setCursor(Qt.CursorShape.PointingHandCursor)
        s.valueChanged.connect(lambda v, key=k, ll=lv, slider=s: (ll.setText(str(v)), self.update(), slider.repaint(), self.upd_f(self.current_fid, key, v) if self.current_fid else None))
        r.clicked.connect(lambda: s.setValue(int(self.cfg['global_settings'].get(k, DEFAULTS[k])))); l.addWidget(s); l.addWidget(lv); l.addWidget(r); self.ind_sliders[k] = s; self.ind_slider_labels[k] = lv; return c, s, lv

    def on_g_preset_changed(self, p):
        self.cfg.setdefault('global_settings', {})['size_preset'] = p; self.g_size_container.setExpanded(p == "Custom")
        if p != "Custom":
            pv = {"Small": {"folder_size": 60, "mini_icon_size": 20, "font_size": 9, "expanded_icon_size": 32}, "Medium": {"folder_size": 80, "mini_icon_size": 27, "font_size": 10, "expanded_icon_size": 48}, "Large": {"folder_size": 110, "mini_icon_size": 34, "font_size": 12, "expanded_icon_size": 64}}[p]
            for k, v in pv.items():
                self.cfg['global_settings'][k] = v
                if k in self.g_sliders: self.g_sliders[k].blockSignals(True); self.g_sliders[k].setValue(v); self.g_slider_labels[k].setText(str(v)); self.g_sliders[k].blockSignals(False)
        self.preview_panel.update_sandbox_settings(self.cfg['global_settings']); ConfigManager.save(self.cfg); self.update_instances()

    def on_i_preset_changed(self, p):
        if not self.current_fid: return
        self.i_sz_cnt.setExpanded(p == "Custom"); f = next((f for f in self.cfg['folders'] if f['id'] == self.current_fid), None)
        if f:
            cs = f.setdefault('custom_settings', {}); cs['size_preset'] = p
            if p != "Custom":
                pv = {"Small": {"folder_size": 60, "mini_icon_size": 20, "font_size": 9, "expanded_icon_size": 32}, "Medium": {"folder_size": 80, "mini_icon_size": 27, "font_size": 10, "expanded_icon_size": 48}, "Large": {"folder_size": 110, "mini_icon_size": 34, "font_size": 12, "expanded_icon_size": 64}}[p]
                for k, v in pv.items():
                    cs[k] = v
                    if k in self.ind_sliders: self.ind_sliders[k].blockSignals(True); self.ind_sliders[k].setValue(v); self.ind_slider_labels[k].setText(str(v)); self.ind_sliders[k].blockSignals(False)
            merged = self.cfg['global_settings'].copy(); merged.update(cs); self.preview_panel.update_sandbox_settings(merged); ConfigManager.save(self.cfg); self.upd_inst(self.current_fid)

    def reset_global_all(self):
        self.cfg['global_settings'].update(DEFAULTS); self.preview_panel.update_sandbox_settings(self.cfg['global_settings']); ConfigManager.save(self.cfg)
        self.g_preset.setTextValue(DEFAULTS['size_preset']); self.g_size_container.setExpanded(DEFAULTS['size_preset'] == "Custom")
        for k, s in self.g_sliders.items(): (s.blockSignals(True), s.setValue(int(DEFAULTS[k])), self.g_slider_labels[k].setText(str(int(DEFAULTS[k]))), s.blockSignals(False))
        for k, b in self.g_color_btns.items(): b.setStyleSheet(f"background: {DEFAULTS[k]}; border-radius: 6px; border: 2px solid rgba(255,255,255,30);")
        self.g_h_speed.setTextValue(DEFAULTS['hover_speed']); self.g_m_speed.setTextValue(DEFAULTS['morph_speed'])
        self.g_grid_snap.blockSignals(True); self.g_grid_snap.setChecked(DEFAULTS['grid_snap']); self.g_grid_snap.blockSignals(False)
        self.g_show_title.blockSignals(True); self.g_show_title.setChecked(DEFAULTS['show_title']); self.g_show_title.blockSignals(False)
        self.g_show_cover.blockSignals(True); self.g_show_cover.setChecked(DEFAULTS['show_cover']); self.g_show_cover.blockSignals(False)
        self.g_cover_container.setExpanded(DEFAULTS['show_cover'])
        self.update_instances()

    def reset_ind_all(self):
        if not self.current_fid: return
        f = next((f for f in self.cfg['folders'] if f['id'] == self.current_fid), None)
        if f:
            f['custom_settings'], f['use_custom_settings'] = {}, False; ConfigManager.save(self.cfg); self.ind_toggle.setChecked(False); self.preview_panel.update_sandbox_settings(self.cfg['global_settings'])
            gs = self.cfg['global_settings']; self.i_pst.setTextValue(gs.get('size_preset', DEFAULTS['size_preset'])); self.i_sz_cnt.setExpanded(gs.get('size_preset') == "Custom")
            for k, s in self.ind_sliders.items(): (s.blockSignals(True), s.setValue(int(gs.get(k, DEFAULTS[k]))), self.ind_slider_labels[k].setText(str(int(gs.get(k, DEFAULTS[k])))), s.blockSignals(False))
            for k, b in self.ind_color_btns.items(): b.setStyleSheet(f"background: {gs.get(k, DEFAULTS[k])}; border-radius: 6px; border: 2px solid rgba(255,255,255,30);")
            self.i_hs.setTextValue(gs.get('hover_speed', 'Fluid')); self.i_ms.setTextValue(gs.get('morph_speed', 'Fluid'))
            self.i_grid_snap.blockSignals(True); self.i_grid_snap.setChecked(gs.get('grid_snap', False)); self.i_grid_snap.blockSignals(False)
            self.i_show_title.blockSignals(True); self.i_show_title.setChecked(gs.get('show_title', True)); self.i_show_title.blockSignals(False)
            self.i_show_cover.blockSignals(True); self.i_show_cover.setChecked(gs.get('show_cover', False)); self.i_show_cover.blockSignals(False)
            self.i_cover_container.setExpanded(gs.get('show_cover', False))
            self.upd_inst(self.current_fid)

    def refresh_grid(self):
        while self.grid_layout.count(): item = self.grid_layout.takeAt(0); w = item.widget(); (w.deleteLater() if w else None)
        q = self.f_search.text().lower(); folders = [f for f in self.cfg['folders'] if q in f['name'].lower()]
        if self.f_sort.text() == "Sort: A-Z": folders.sort(key=lambda x: x['name'].lower())
        elif self.f_sort.text() == "Sort: Z-A": folders.sort(key=lambda x: x['name'].lower(), reverse=True)
        for i, f in enumerate(folders): t = FolderTile(f); t.clicked.connect(self.open_f_settings); self.grid_layout.addWidget(t, i // 4, i % 4)

    def open_f_settings(self, fid):
        self.current_fid = fid; self.ind_stack.setCurrentIndex(1)
        f = next((f for f in self.cfg['folders'] if f['id'] == fid), None)
        if not f: return
        self.ind_header.setText(f"Settings for: {f['name']}"); cs, gs, uc = f.get('custom_settings', {}), self.cfg['global_settings'], f.get('use_custom_settings', False)
        merged = gs.copy(); (merged.update(cs) if uc else None); self.preview_panel.update_sandbox_settings(merged, real_apps=f.get('apps', [])); self.ind_toggle.blockSignals(True); self.ind_toggle.setChecked(uc); self.ind_toggle.blockSignals(False); self.i_cnt.setEnabled(uc)
        p = cs.get('size_preset', gs.get('size_preset', 'Medium')); self.i_pst.setTextValue(p); is_c = p == "Custom"
        self.i_sz_cnt.setExpanded(is_c); self.i_sz_cnt.setMaximumHeight(500 if is_c else 0)
        for k, s in self.ind_sliders.items(): v = cs.get(k, gs.get(k, DEFAULTS[k])); s.blockSignals(True); s.setValue(int(v)); self.ind_slider_labels[k].setText(str(int(v))); s.blockSignals(False)
        for k, b in self.ind_color_btns.items(): col = cs.get(k, gs.get(k, DEFAULTS[k])); b.setStyleSheet(f"background: {col}; border-radius: 6px; border: 2px solid rgba(255,255,255,30);")
        self.i_hs.setTextValue(cs.get('hover_speed', gs.get('hover_speed', 'Fluid'))); self.i_ms.setTextValue(cs.get('morph_speed', gs.get('morph_speed', 'Fluid')))
        
        self.i_show_title.blockSignals(True); self.i_show_title.setChecked(cs.get('show_title', gs.get('show_title', True))); self.i_show_title.blockSignals(False)
        self.i_show_cover.blockSignals(True); self.i_show_cover.setChecked(cs.get('show_cover', gs.get('show_cover', False))); self.i_show_cover.blockSignals(False)
        self.i_cover_container.setExpanded(cs.get('show_cover', gs.get('show_cover', False)))


    def on_ind_toggle_changed(self, c):
        if self.current_fid: 
            f = next((f for f in self.cfg['folders'] if f['id'] == self.current_fid), None)
            if f:
                f['use_custom_settings'] = c; merged = self.cfg['global_settings'].copy(); (merged.update(f.get('custom_settings', {})) if c else None); self.preview_panel.update_sandbox_settings(merged)
            ConfigManager.save(self.cfg); self.i_cnt.setEnabled(c); self.upd_inst(self.current_fid)

    def pick_ind_color(self, k, b):
        f = next(f for f in self.cfg['folders'] if f['id'] == self.current_fid); curr = f.get('custom_settings', {}).get(k, self.cfg['global_settings'].get(k, DEFAULTS[k]))
        self.pick_color_popup(b, curr, lambda c: (b.setStyleSheet(f"background: {c}; border-radius: 6px; border: 2px solid white;"), self.upd_f(self.current_fid, k, c)))
    def pick_global_color(self, k, b): self.pick_color_popup(b, self.cfg['global_settings'].get(k, DEFAULTS[k]), lambda c: (b.setStyleSheet(f"background: {c}; border-radius: 6px; border: 2px solid white;"), self.upd_g(k, c)))
    def _queue_save(self):
        if not hasattr(self, '_save_timer'):
            self._save_timer = __import__('PyQt6.QtCore').QtCore.QTimer()
            self._save_timer.setSingleShot(True)
            self._save_timer.timeout.connect(lambda: ConfigManager.save(self.cfg))
        self._save_timer.start(500)

    def upd_g(self, k, v): self.cfg.setdefault('global_settings', {})[k] = v; self.preview_panel.update_sandbox_settings(self.cfg['global_settings']); self._queue_save(); self.update_instances(); (self.grid_overlay.update() if hasattr(self, 'grid_overlay') else None)
    def upd_f(self, fid, k, v): 
        f = next((f for f in self.cfg['folders'] if f['id'] == fid), None)
        if f:
            f.setdefault('custom_settings', {})[k] = v; merged = self.cfg['global_settings'].copy(); merged.update(f['custom_settings']); self.preview_panel.update_sandbox_settings(merged)
        self._queue_save(); self.upd_inst(fid)
    def choose_cover(self):
        p, _ = QFileDialog.getOpenFileName(self, "Image", "", "Images (*.png *.jpg *.jpeg *.webp)"); 
        if p and self.current_fid: f = next(f for f in self.cfg['folders'] if f['id'] == self.current_fid); f['cover_image'] = p; ConfigManager.save(self.cfg); self.upd_inst(self.current_fid); self.open_f_settings(self.current_fid)
    def clear_cover(self):
        if self.current_fid:
            f = next((f for f in self.cfg['folders'] if f['id'] == self.current_fid), None)
            if f: f['cover_image'] = None; ConfigManager.save(self.cfg); self.upd_inst(self.current_fid); self.open_f_settings(self.current_fid)
    def upd_inst(self, fid): (next((w for w in self.app_instances if hasattr(w, 'data') and w.data.get('id') == fid), None).update() if any(hasattr(w, 'data') and w.data.get('id') == fid for w in self.app_instances) else None)
    def update_instances(self):
        for w in self.app_instances: (w.update() if hasattr(w, 'update') else None)
    def handle_folder_deleted(self, folder_widget):
        fid = folder_widget.data.get('id') if hasattr(folder_widget, 'data') else None
        self.app_instances = [w for w in self.app_instances if w is not folder_widget]
        if fid and self.current_fid == fid: self.current_fid = None; self.ind_stack.setCurrentIndex(0)
        self.refresh_grid()
    def show_folder(self, fid): self.sidebar.select_tab(1); self.open_f_settings(fid); self.show(); self.raise_()
    def on_tab_changed(self, idx): 
        self.stack.setCurrentIndex(idx)
        if idx == 1: 
            self.ind_stack.setCurrentIndex(0); self.refresh_grid()
        else:
            dummy = [{'name': f'App {i+1}', 'path': f'C:\\Windows\\explorer.exe' + ' ' * i, 'pinned': False} for i in range(27)]
            self.preview_panel.update_sandbox_settings(self.cfg['global_settings'], real_apps=dummy)
        self.update()

    def paintEvent(self, e):
        p = QPainter(self); p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.setCompositionMode(QPainter.CompositionMode.CompositionMode_Source)
        p.fillRect(self.rect(), Qt.GlobalColor.transparent)
        p.setCompositionMode(QPainter.CompositionMode.CompositionMode_SourceOver)
        r = QRectF(self.rect())
        p.setBrush(QColor(18, 18, 22, 160)); p.setPen(Qt.PenStyle.NoPen); p.drawRoundedRect(r, 15, 15)
        inner = r.adjusted(6, 6, -6, -6); p.setBrush(QColor(18, 18, 22, 245)); p.drawRoundedRect(inner, 11, 11)
        gloss = QLinearGradient(0, 0, 0, 60); gloss.setColorAt(0, QColor(255, 255, 255, 18)); gloss.setColorAt(1, QColor(255, 255, 255, 0))
        p.setBrush(gloss); p.drawRoundedRect(r, 15, 15)
        p.setBrush(Qt.BrushStyle.NoBrush); p.setPen(QPen(QColor(255, 255, 255, 28), 1)); p.drawRoundedRect(r.adjusted(0.5, 0.5, -0.5, -0.5), 15, 15)

    def create_label(self, t): l = QLabel(t); l.setStyleSheet("color: #e0e0e0; font-size: 14px; font-weight: 500;"); return l
    def create_sep(self): f = QFrame(); f.setFrameShape(QFrame.Shape.HLine); f.setStyleSheet("background: rgba(255,255,255,20); margin: 10px 0;"); return f
    def pick_color_popup(self, b, curr, cb): p = ColorPicker(curr, self); p.colorSelected.connect(cb); p.move(b.mapToGlobal(QPoint(0, 30))); p.show()
    def create_static_slider(self, val, mn, mx, default_val, callback):
        c = QWidget(); l = QHBoxLayout(c); l.setContentsMargins(0, 0, 0, 0); l.setSpacing(10); s = QSlider(Qt.Orientation.Horizontal); s.setRange(mn, mx); s.setValue(int(val))
        s.setStyleSheet("QSlider::groove:horizontal { height: 6px; background: rgba(255,255,255,20); border-radius: 3px; } QSlider::handle:horizontal { background: #50FA7B; width: 16px; height: 16px; margin: -5px 0; border-radius: 8px; border: 2px solid white; }")
        lv = QLabel(str(int(val))); lv.setFixedWidth(35); lv.setStyleSheet("color: #50FA7B; font-weight: bold; font-family: 'Consolas', monospace; font-size: 13px;"); r = QPushButton(); r.setFixedSize(20, 20); r.setIcon(VectorIcon.icon("reset", "#aaaaaa")); r.setStyleSheet("background: transparent; border: none;"); r.setCursor(Qt.CursorShape.PointingHandCursor)
        r.clicked.connect(lambda: s.setValue(int(default_val))); s.valueChanged.connect(lambda v, slider=s: (lv.setText(str(v)), self.update(), slider.repaint(), callback(v))); l.addWidget(s); l.addWidget(lv); l.addWidget(r); return c, s, lv

class TitleBar(QWidget):
    def __init__(self, parent):
        super().__init__(parent); self.parent = parent; self.setFixedHeight(60); self.layout = QHBoxLayout(self); self.layout.setContentsMargins(25, 0, 20, 0)
        self.title_label = QLabel("CusFolder Dashboard"); self.title_label.setStyleSheet("color: #ffffff; font-weight: bold; font-size: 18px; background: transparent;"); self.layout.addWidget(self.title_label); self.layout.addStretch()
        self.close_btn = QPushButton("✕"); self.close_btn.setFixedSize(32, 32); self.close_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.close_btn.setStyleSheet("QPushButton { background-color: rgba(255,255,255,15); color: #ffffff; border: none; font-weight: bold; font-size: 14px; border-radius: 16px;} QPushButton:hover { background-color: #ff4c4c; }")
        self.close_btn.clicked.connect(self.parent.close); self.layout.addWidget(self.close_btn); self._start_pos = None
    def mousePressEvent(self, event): (setattr(self, '_start_pos', event.globalPosition().toPoint()) if event.button() == Qt.MouseButton.LeftButton else None)
    def mouseMoveEvent(self, event):
        if hasattr(self, '_start_pos') and self._start_pos:
            curr_pos = event.globalPosition().toPoint()
            delta = curr_pos - self._start_pos
            self.parent.move(self.parent.pos() + delta)
            self._start_pos = curr_pos
    def mouseReleaseEvent(self, event): self._start_pos = None
