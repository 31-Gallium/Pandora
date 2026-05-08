import os
import json
import shutil
import time
from PyQt6.QtWidgets import QWidget, QHBoxLayout, QLabel, QLineEdit, QPushButton, QApplication
from PyQt6.QtCore import Qt, QEvent, QVariantAnimation, QEasingCurve, QFileInfo, QPoint, QPropertyAnimation, QRectF, QRect
from PyQt6.QtGui import QColor, QPainter, QPen, QAction

from config import ConfigManager, DESKTOP_PATH, STORAGE_PATH
from utils import WinAPI, VectorIcon
from ui_common import AnimatedMenu
from app_icon import AppIcon

class FolderView(QWidget):
    def __init__(self, data, parent_icon, parent=None):
        super().__init__(parent)
        self.folder_data = data
        self.parent_icon = parent_icon
        self.cfg = parent_icon.cfg
        self.is_dragging = False
        self.active_drag_app = None
        self.drag_placeholder_idx = -1
        self.app_widgets = {}
        self.search_query = ""
        self.is_closing = False
        self.anim_progress = 0.0
        self.selected_apps = set()
        self.last_selected_path = None
        self.current_vis_paths = []
        self.current_page = 0
        self._last_scroll_time = 0
        self._last_launch_time = 0
        
        self.is_sandbox = parent is not None
        if not self.is_sandbox:
            self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.Tool | Qt.WindowType.WindowStaysOnTopHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setStyleSheet("FolderView { background: transparent; }")
        self.setAcceptDrops(True)
        
        icon_size = self.get_setting('expanded_icon_size', 48)
        font_size = self.get_setting('font_size', 10)
        self.cell_w = max(icon_size + 40, 100)
        self.cell_h = icon_size + font_size * 2 + 40
        self.grid_w = self.cell_w * 3 + 20
        self.grid_h = self.cell_h * 3
        
        self.hw = QWidget(self)
        self.hw.setFixedSize(self.grid_w, 35)
        self.hw.move(15, 15)
        hl = QHBoxLayout(self.hw)
        hl.setContentsMargins(5, 0, 5, 0)
        
        tc = self.get_setting('title_color', '#ffffff')
        self.title_lbl = QLabel(data['name'])
        self.title_lbl.setStyleSheet(f"color: {tc}; font-weight: bold; font-size: 20px; background: transparent;")
        self.title_lbl.mouseDoubleClickEvent = lambda e: self.start_rename()
        self.title_lbl.setMinimumWidth(0)
        self.title_lbl.setMaximumWidth(self.grid_w - 100)
        self.title_lbl.setToolTip(data['name'])
        
        self.title_edit = QLineEdit(data['name'])
        self.title_edit.setStyleSheet(f"background: rgba(0,0,0,80); color: {tc}; border-radius: 4px; border: 1px solid rgba(255,255,255,30); font-size: 18px; font-weight: bold;")
        self.title_edit.hide()
        self.title_edit.returnPressed.connect(self.save_title)
        self.title_edit.installEventFilter(self)
        
        hl.addWidget(self.title_lbl)
        hl.addWidget(self.title_edit)
        hl.addStretch()
        
        hc = self.get_setting('highlight_color', '#50FA7B')
        self.sb = QLineEdit()
        self.sb.setPlaceholderText("Search...")
        self.sb.setMinimumWidth(0)
        self.sb.setMaximumWidth(0)
        self.sb.setFixedHeight(30)
        self.sb.setStyleSheet(f"background: rgba(0,0,0,140); color: white; border-radius: 15px; padding: 0 12px; border: 1px solid {hc}40;")
        self.sb.textChanged.connect(self.on_search)
        self.sb.returnPressed.connect(self.launch_first)
        hl.addWidget(self.sb)
        
        self.sbtn = QPushButton()
        self.sbtn.setFixedSize(24, 24)
        self.sbtn.setIcon(VectorIcon.icon("search", hc))
        self.sbtn.setStyleSheet("background: rgba(255,255,255,20); border-radius: 12px; border: none;")
        self.sbtn.clicked.connect(self.toggle_search)
        hl.addWidget(self.sbtn)
        
        self.sort_btn = QPushButton()
        self.sort_btn.setFixedSize(24, 24)
        self.sort_btn.setIcon(VectorIcon.icon("sort_asc", hc))
        self.sort_btn.setStyleSheet("background: rgba(255,255,255,20); border-radius: 12px; border: none;")
        self.sort_btn.clicked.connect(self.toggle_sort)
        self.sort_btn.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.sort_btn.customContextMenuRequested.connect(self.show_sort_menu)
        hl.addWidget(self.sort_btn)
        
        self.launch_btn = QPushButton()
        self.launch_btn.setFixedSize(24, 24)
        self.launch_btn.setIcon(VectorIcon.icon("rocket", hc))
        self.launch_btn.setStyleSheet("background: rgba(255,255,255,20); border-radius: 12px; border: none;")
        self.launch_btn.clicked.connect(self.launch_all)
        hl.addWidget(self.launch_btn)
        
        self.cw = QWidget(self)
        self.cw.setFixedSize(self.grid_w, self.grid_h)
        self.cw.move(15, 55)
        
        self.grid_widget = QWidget(self.cw)
        self.grid_widget.move(0, 0)
        
        self.morph = QVariantAnimation(self)
        self.morph.setDuration(250)
        self.morph.valueChanged.connect(self._animate_morph)
        self.morph.finished.connect(self._morph_finished)

    def get_setting(self, key, default):
        preset = self.cfg.get('global_settings', {}).get('size_preset', 'Medium')
        use_custom = self.folder_data.get('use_custom_settings', False)
        if use_custom:
            preset = self.folder_data.get('custom_settings', {}).get('size_preset', preset)
            
        SIZE_PRESETS = {
            "Small": {"folder_size": 60, "mini_icon_size": 12, "font_size": 9, "expanded_icon_size": 32},
            "Medium": {"folder_size": 80, "mini_icon_size": 16, "font_size": 10, "expanded_icon_size": 48},
            "Large": {"folder_size": 110, "mini_icon_size": 24, "font_size": 12, "expanded_icon_size": 64}
        }
        
        if preset in SIZE_PRESETS and key in SIZE_PRESETS[preset]:
            return SIZE_PRESETS[preset][key]
            
        if use_custom:
            return self.folder_data.get('custom_settings', {}).get(key, self.cfg.get('global_settings', {}).get(key, default))
        return self.cfg.get('global_settings', {}).get(key, default)

    def eventFilter(self, obj, event):
        if obj == self.title_edit and event.type() == QEvent.Type.KeyPress:
            if event.key() == Qt.Key.Key_Escape: 
                self.exit_rename()
                return True
        return super().eventFilter(obj, event)

    def start_rename(self): 
        self.title_lbl.hide()
        self.title_edit.setText(self.folder_data['name'])
        self.title_edit.show()
        self.title_edit.setFocus()
        self.title_edit.selectAll()

    def save_title(self):
        n = self.title_edit.text()
        if n: 
            self.folder_data['name'] = n
            self.title_lbl.setText(n)
            self.parent_icon.update()
            ConfigManager.save(self.cfg)
        self.exit_rename()

    def exit_rename(self): 
        self.title_edit.hide()
        self.title_lbl.show()
        self.setFocus()

    def toggle_search(self):
        w = 150 if self.sb.maximumWidth() == 0 else 0
        self.search_anim = QVariantAnimation(self)
        self.search_anim.setDuration(300)
        self.search_anim.setEasingCurve(QEasingCurve.Type.OutCubic)
        self.search_anim.setStartValue(self.sb.maximumWidth())
        self.search_anim.setEndValue(w)
        
        # Animate title width to avoid collision
        start_title_w = self.grid_w - 100 if w > 0 else self.grid_w - 250
        end_title_w = self.grid_w - 250 if w > 0 else self.grid_w - 100
        
        def upd_v(v):
            self.sb.setMinimumWidth(v)
            self.sb.setMaximumWidth(v)
            # Map search width (0-150) to title width
            progress = v / 150.0 if w > 0 else (150.0 - v) / 150.0
            if w == 0: progress = 1.0 - (v / 150.0)
            
            cur_title_w = start_title_w + (end_title_w - start_title_w) * (v / 150.0 if w > 0 else 1.0 - (v / 150.0))
            self.title_lbl.setMaximumWidth(int(cur_title_w))

        self.search_anim.valueChanged.connect(upd_v)
        self.search_anim.start()
        if w > 0: 
            self.sb.setFocus()

    def launch_first(self):
        f = [a for a in self.folder_data.get('apps', []) if self.search_query in a.get('name', '').lower()]
        if f:
            try: 
                os.startfile(f[0]['path'])
                self.hide_morph()
            except: 
                pass

    def launch_all(self):
        if self.is_sandbox: return
        current_time = time.time()
        if current_time - getattr(self, '_last_launch_time', 0) < 2.0: return
        self._last_launch_time = current_time
        
        for app in self.folder_data.get('apps', []):
            try:
                if os.path.exists(app.get('path', '')): 
                    os.startfile(app['path'])
            except: 
                pass
        self.hide_morph()

    def toggle_sort(self):
        if self.folder_data.get('sort_type', 'name') == 'custom':
            self.folder_data['sort_type'] = 'name'
        self.folder_data['sort_order'] = 'desc' if self.folder_data.get('sort_order', 'asc') == 'asc' else 'asc'
        self.sort_btn.setIcon(VectorIcon.icon("sort_asc" if self.folder_data['sort_order'] == 'asc' else "sort_desc"))
        self.apply_sort()

    def show_sort_menu(self, pos):
        m = AnimatedMenu(self)
        ct = self.folder_data.get('sort_type', 'name')
        for l, v in [("Name", "name"), ("Type", "extension"), ("Size", "size"), ("Date", "date"), ("Recently Added", "recent"), ("Custom (Manual)", "custom")]:
            a = QAction(l, self)
            a.triggered.connect(lambda _, s=v: self.set_sort_type(s))
            if ct == v: 
                a.setIcon(VectorIcon.icon("check", "#50FA7B"))
            m.addAction(a)
        m.exec(self.sort_btn.mapToGlobal(pos))

    def set_sort_type(self, st): 
        self.folder_data['sort_type'] = st
        self.apply_sort()

    def apply_sort(self, new_paths=None):
        st = self.folder_data.get('sort_type', 'name')
        if st == 'custom':
            self.refresh(new_paths=new_paths)
            self.parent_icon.update()
            return
            
        rev = self.folder_data.get('sort_order', 'asc') == 'desc'
        def sk(app):
            p = app.get('path', '')
            info = QFileInfo(p)
            name_key = app.get('name', '').lower()
            
            if st == 'extension': 
                if info.isDir():
                    return (0, '_folder', name_key)
                
                ext = info.suffix().lower()
                is_folder_link = False
                
                if ext == 'lnk':
                    try:
                        import win32com.client
                        shell = win32com.client.Dispatch("WScript.Shell")
                        shortcut = shell.CreateShortCut(p)
                        target = shortcut.TargetPath
                        if target: 
                            target_info = QFileInfo(target)
                            is_folder_link = target_info.isDir()
                            ext = '_folder' if is_folder_link else target_info.suffix().lower()
                    except: pass
                elif ext == 'url':
                    try:
                        with open(p, 'r', encoding='utf-8', errors='ignore') as f:
                            for line in f:
                                if line.startswith('URL='):
                                    url_val = line.strip().split('=', 1)[1]
                                    if url_val.startswith('file:///'): url_val = url_val[8:]
                                    elif url_val.startswith('steam://') or url_val.startswith('com.epicgames'): ext = 'game'; break
                                    target_info = QFileInfo(url_val)
                                    is_folder_link = target_info.isDir()
                                    ext = '_folder' if is_folder_link else target_info.suffix().lower()
                                    break
                    except: pass
                
                return (0 if is_folder_link else 1, ext, name_key)
            
            # For other sorts, ensure a uniform tuple to prevent crashes
            if st == 'size': return (0, info.size(), name_key)
            if st == 'date': return (0, info.lastModified().toMSecsSinceEpoch(), name_key)
            if st == 'recent': 
                bt = info.birthTime().toMSecsSinceEpoch() if info.birthTime().isValid() else info.lastModified().toMSecsSinceEpoch()
                return (0, bt, name_key)
                
            return (0, name_key, "")
        
        p = [a for a in self.folder_data['apps'] if a.get('pinned')]
        u = [a for a in self.folder_data['apps'] if not a.get('pinned')]
        self.folder_data['apps'] = sorted(p, key=sk, reverse=rev) + sorted(u, key=sk, reverse=rev)
        ConfigManager.save(self.cfg)
        self.refresh()
        self.parent_icon.update()

    def on_search(self, t): 
        self.search_query = t.lower()
        self.refresh()

    def scroll_to_page(self, page, animate=True):
        self.current_page = page
        target_y = -page * self.grid_h
        
        if not hasattr(self, 'scroll_anim'):
            self.scroll_anim = QPropertyAnimation(self.grid_widget, b"pos")
            self.scroll_anim.setDuration(300)
            self.scroll_anim.setEasingCurve(QEasingCurve.Type.OutCubic)
            
        target_pos = QPoint(0, int(target_y))
        if animate:
            self.scroll_anim.stop()
            self.scroll_anim.setEndValue(target_pos)
            self.scroll_anim.start()
        else:
            self.scroll_anim.stop()
            self.grid_widget.move(target_pos)
        self.update()

    def refresh(self, new_paths=None):
        font_size = self.get_setting('font_size', 10)
        expanded_icon_size = self.get_setting('expanded_icon_size', 48)
        self.cell_w = max(expanded_icon_size + 40, 100)
        self.cell_h = expanded_icon_size + font_size * 2 + 40
        self.grid_w = self.cell_w * 3 + 20
        self.grid_h = 3 * self.cell_h

        f = [a for a in self.folder_data.get('apps', []) if self.search_query in a.get('name', '').lower()]
        vis = [a for a in f if not (self.is_dragging and a['path'] in self.selected_apps)]
        ap = {a['path'] for a in vis}
        self.current_vis_paths = [a['path'] for a in vis]
        
        for p in list(self.app_widgets.keys()):
            if p not in ap: 
                self.app_widgets[p].hide()
                self.app_widgets.pop(p).deleteLater()
                
        for i, app in enumerate(vis):
            v_idx = i + 1 if self.drag_placeholder_idx != -1 and i >= self.drag_placeholder_idx else i
            t = QPoint(int((v_idx % 3) * self.cell_w), int((v_idx // 3) * self.cell_h))
            if app['path'] not in self.app_widgets:
                w = AppIcon(app, self, pop_in=(new_paths and app['path'] in new_paths), font_size=font_size, icon_size=expanded_icon_size)
                w.move(t)
                w.show()
                self.app_widgets[app['path']] = w
            else:
                w = self.app_widgets[app['path']]
                if not hasattr(w, 'pos_anim'): 
                    w.pos_anim = QPropertyAnimation(w, b"pos")
                    w.pos_anim.setDuration(200)
                    w.pos_anim.setEasingCurve(QEasingCurve.Type.OutQuad)
                if w.pos_anim.endValue() != t: 
                    w.pos_anim.stop()
                    w.pos_anim.setEndValue(t)
                    w.pos_anim.start()
                    
        total_items = len(vis) + (1 if self.drag_placeholder_idx != -1 else 0)
        rows = max(3, (total_items + 2) // 3)
        self.grid_h = 3 * self.cell_h
        self.content_h = rows * self.cell_h
        
        self.grid_widget.setFixedSize(self.grid_w, self.content_h)
        self.cw.setFixedSize(self.grid_w, self.grid_h)
        
        max_page = max(0, (rows - 1) // 3)
        if getattr(self, 'current_page', 0) > max_page:
            self.current_page = max_page
            
        self.scroll_to_page(self.current_page, animate=False)

    def showEvent(self, e):
        super().showEvent(e)
        self._apply_mask()

    def resizeEvent(self, e):
        super().resizeEvent(e)
        self._schedule_mask()

    def _schedule_mask(self):
        if not hasattr(self, '_mask_timer'):
            from PyQt6.QtCore import QTimer
            self._mask_timer = QTimer(self)
            self._mask_timer.setSingleShot(True)
            self._mask_timer.timeout.connect(self._apply_mask)
        self._mask_timer.start(50)

    def _apply_mask(self):
        from PyQt6.QtGui import QRegion, QPainterPath
        path = QPainterPath()
        rad = self.get_setting('radius', 20)
        path.addRoundedRect(QRectF(self.rect()), rad, rad)
        self.setMask(QRegion(path.toFillPolygon().toPolygon()))

    def paintEvent(self, e):
        rad = self.get_setting('radius', 20)
        bg_col = QColor(self.get_setting('bg_color', '#141414'))
        bg_col.setAlpha(225) 
        
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)

        # CompositionMode_Source ensures we overwrite any existing junk in the window buffer
        if not getattr(self, 'is_sandbox', False):
            p.setCompositionMode(QPainter.CompositionMode.CompositionMode_Source)
            p.fillRect(self.rect(), Qt.GlobalColor.transparent)
            p.setCompositionMode(QPainter.CompositionMode.CompositionMode_SourceOver)

        p.setBrush(bg_col)
        p.setPen(Qt.PenStyle.NoPen)
        p.drawRoundedRect(QRectF(self.rect()), rad, rad)
        
        # Draw Page Indicators
        if hasattr(self, 'content_h') and self.content_h > self.grid_h:
            num_pages = (self.content_h + self.grid_h - 1) // self.grid_h
            if num_pages > 1:
                dot_size = 6
                gap = 8
                total_w = (num_pages * dot_size) + ((num_pages - 1) * gap)
                sx = (self.width() - total_w) / 2
                sy = self.height() - 15
                
                for i in range(num_pages):
                    p.setPen(Qt.PenStyle.NoPen)
                    alpha = 255 if i == self.current_page else 60
                    dot_color = QColor(self.get_setting('highlight_color', '#50FA7B'))
                    dot_color.setAlpha(alpha)
                    p.setBrush(dot_color)
                    p.drawEllipse(QRectF(sx + i * (dot_size + gap), sy, dot_size, dot_size))

        if self.morph.state() == QVariantAnimation.State.Running or self.anim_progress < 1.0:
            gw = getattr(self, 'grid_w', 300)
            gh = getattr(self, 'grid_h', 345)
            sx = (self.width() - gw) / 2
            sy = (self.height() - (gh + 30)) / 2
            
            opacity = 255 if self.anim_progress < 0.7 else int(max(0, 255 - ((self.anim_progress - 0.7) / 0.3) * 255))
            if opacity > 0:
                p.setBrush(QColor(255, 255, 255, opacity // 10))
                p.setPen(Qt.PenStyle.NoPen)
                p.drawRoundedRect(int(sx + 5), int(sy + 5), 150, 20, 4, 4)
                p.drawRoundedRect(int(sx + gw - 120), int(sy + 3), 120, 24, 12, 12)
                
                num = min(9, len(self.folder_data.get('apps', [])))
                num = 9 if num == 0 else num
                cw = getattr(self, 'cell_w', 100)
                ch = getattr(self, 'cell_h', 115)
                for i in range(num):
                    col, row = i % 3, i // 3
                    x = int(sx + (col * cw) + (cw - 48) / 2)
                    y = int(sy + 40 + (row * ch) + 10)
                    p.drawRoundedRect(x, y, 48, 48, 8, 8)
                    p.drawRoundedRect(x - 10, y + 60, 68, 8, 4, 4)

    def _animate_morph(self, v):
        self.anim_progress = v
        if hasattr(self, 'sr') and hasattr(self, 'tr') and not self.parent():
            w = self.sr.width() + (self.tr.width() - self.sr.width()) * v
            h = self.sr.height() + (self.tr.height() - self.sr.height()) * v
            cx = self.sr.center().x() + (self.tr.center().x() - self.sr.center().x()) * v
            cy = self.sr.center().y() + (self.tr.center().y() - self.sr.center().y()) * v
            self.setGeometry(int(cx - w / 2), int(cy - h / 2), int(w), int(h))
        self.setWindowOpacity(v)
        self.update()

    def _update_morph_speed(self):
        speed_mode = self.get_setting('morph_speed', 'Fluid')
        self.morph.setDuration({"Snappy": 150, "Fluid": 250, "Relaxed": 400}.get(speed_mode, 250))

    def show_morph(self, rect):
        self.parent_icon._suppress_restore = True
        self.parent_icon.hide()
        self._update_morph_speed()
        self.sr = rect
        
        icon_size = self.get_setting('expanded_icon_size', 48)
        font_size = self.get_setting('font_size', 10)
        self.cell_w = max(icon_size + 40, 100)
        self.cell_h = icon_size + font_size * 2 + 40
        self.grid_w = self.cell_w * 3 + 20
        self.grid_h = 3 * self.cell_h
        
        tw = self.grid_w + 30
        th = self.grid_h + 80
        
        if self.is_sandbox:
            # Center within parent widget (PreviewWindow)
            win = self.window()
            # If the window has a target_width (from our expansion animation), use that for centering
            pw = getattr(win, 'target_width', win.width())
            ph = win.height()
            self.tr = QRect(
                int((pw - tw) / 2),
                int((ph - th) / 2),
                int(tw), int(th)
            )
        else:
            scr = QApplication.primaryScreen().availableGeometry()
            self.tr = QRect(
                int(max(scr.left() + 20, min(rect.center().x() - tw / 2, scr.right() - tw - 20))), 
                int(max(scr.top() + 20, min(rect.center().y() - th / 2, scr.bottom() - th - 20))), 
                int(tw), int(th)
            )
        
        self.is_closing = False
        self.anim_progress = 0.0
        self.hw.hide()
        self.cw.hide()
        
        self.hw.setFixedSize(self.grid_w, 35)
        
        self.refresh()
        self.show()
        
        if not self.is_sandbox:
            WinAPI.set_modern_visuals(self.winId(), True)
            WinAPI.allow_drag_drop(self.winId())
        
        self.morph.setStartValue(0.0)
        self.morph.setEndValue(1.0)
        self.morph.start()
        self.activateWindow()
        self.setFocus()

    def hide_morph(self):
        if self.is_closing: return
        self.is_closing = True
        self._update_morph_speed()
        self.hw.hide()
        self.cw.hide()
        self.morph.setStartValue(1.0)
        self.morph.setEndValue(0.0)
        self.morph.start()

    def _morph_finished(self):
        if not self.is_closing: 
            self.hw.show()
            self.cw.show()
            self.anim_progress = 1.0
            self.hw.raise_()
        else: 
            self.hide()
            self.is_closing = False
            self.anim_progress = 0.0
            if self.parent_icon:
                self.parent_icon._suppress_restore = False
                self.parent_icon._desktop_init = False
                self.parent_icon.show()
        self.update()

    def mousePressEvent(self, e):
        if e.button() == Qt.MouseButton.LeftButton:
            if self.selected_apps:
                self.selected_apps.clear()
                for w in self.app_widgets.values():
                    w.update()
        super().mousePressEvent(e)

    def keyPressEvent(self, e):
        if e.key() == Qt.Key.Key_Escape: 
            if not self.is_sandbox:
                self.hide_morph()
        elif e.key() == Qt.Key.Key_F2: 
            self.start_rename()
        elif not self.sb.hasFocus() and not self.title_edit.isVisible() and len(e.text()) > 0 and e.text().isprintable():
            if self.sb.maximumWidth() == 0: 
                self.toggle_search()
            self.sb.setText(self.sb.text() + e.text())
            self.sb.setFocus()

    def wheelEvent(self, e):
        if not hasattr(self, 'content_h'): return
        rows = self.content_h // self.cell_h
        max_page = max(0, (rows - 1) // 3)
        
        if e.angleDelta().y() < 0:
            if self.current_page < max_page:
                self.scroll_to_page(self.current_page + 1)
        elif e.angleDelta().y() > 0:
            if self.current_page > 0:
                self.scroll_to_page(self.current_page - 1)

    def changeEvent(self, e):
        if e.type() == QEvent.Type.ActivationChange and not self.isActiveWindow() and not self.is_dragging and not self.title_edit.isVisible(): 
            self.hide_morph()

    def dragEnterEvent(self, e): 
        if e.mimeData().hasFormat("application/x-pandora-app") or e.mimeData().hasUrls(): 
            e.acceptProposedAction()

    def dragLeaveEvent(self, e): 
        self.drag_placeholder_idx = -1
        self.refresh()

    def dragMoveEvent(self, e):
        if e.mimeData().hasFormat("application/x-pandora-app") or e.mimeData().hasUrls():
            e.acceptProposedAction()
            p = e.position().toPoint() - self.cw.pos()
            
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

            adjusted_y = p.y() - self.grid_widget.y()
            if adjusted_y < 0: adjusted_y = 0
            
            idx = int((adjusted_y // getattr(self, 'cell_h', 115)) * 3 + (p.x() // getattr(self, 'cell_w', 100)))
            
            f = [a for a in self.folder_data.get('apps', []) if self.search_query in a.get('name', '').lower()]
            vis_len = len([a for a in f if not (self.is_dragging and a['path'] in self.selected_apps)])
            
            if idx > vis_len:
                idx = vis_len
                
            if self.drag_placeholder_idx != idx: 
                self.drag_placeholder_idx = idx
                self.refresh()

    def dropEvent(self, e):
        idx = max(0, min(self.drag_placeholder_idx, len(self.folder_data['apps'])))
        self.drag_placeholder_idx = -1
        dropped = []

        initial_pinned = sum(1 for a in self.folder_data['apps'] if a.get('pinned'))
        target_is_pinned = (idx < initial_pinned)

        is_internal_move = False

        if e.mimeData().hasFormat("application/x-pandora-app"):
            sid = e.mimeData().data("application/x-pandora-app").data().decode()
            try:
                dropped_apps = json.loads(e.mimeData().text())
                if isinstance(dropped_apps, dict):
                    dropped_apps = [dropped_apps]
            except json.JSONDecodeError:
                dropped_apps = []

            for ad in dropped_apps:
                if isinstance(e.source(), AppIcon):
                    e.source().is_internal = True
                    is_internal_move = True

                for f in self.cfg['folders']:
                    if f['id'] == sid:
                        f['apps'] = [a for a in f['apps'] if a['path'] != ad['path']]
                        break

                current_pinned = [a for a in self.folder_data['apps'] if a.get('pinned')]
                current_unpinned = [a for a in self.folder_data['apps'] if not a.get('pinned')]

                ad['pinned'] = target_is_pinned

                if ad['pinned']:
                    insert_idx = min(idx, len(current_pinned))
                    current_pinned.insert(insert_idx, ad)
                else:
                    insert_idx = max(0, idx - len(current_pinned))
                    insert_idx = min(insert_idx, len(current_unpinned))
                    current_unpinned.insert(insert_idx, ad)

                self.folder_data['apps'] = current_pinned + current_unpinned
                idx += 1
                dropped.append(ad['path'])

            if is_internal_move:
                self.folder_data['sort_type'] = 'custom'

            # Final deduplication check
            seen = set(); unique = []
            for a in self.folder_data['apps']:
                if a['path'] not in seen:
                    unique.append(a); seen.add(a['path'])
            self.folder_data['apps'] = unique

            ConfigManager.save(self.cfg)
            if self.folder_data.get('sort_type', 'name') != 'custom':
                self.apply_sort(new_paths=dropped)
            else:
                self.refresh(new_paths=dropped)
                self.parent_icon.update()
            self.parent_icon.trigger_pulse()
            e.acceptProposedAction()

        elif e.mimeData().hasUrls():
            for u in e.mimeData().urls():
                s = u.toLocalFile()
                d = os.path.join(STORAGE_PATH, os.path.basename(s))
                try:
                    shutil.move(s, d)
                    ad = {"name": QFileInfo(d).baseName(), "path": d, "pinned": target_is_pinned}

                    current_pinned = [a for a in self.folder_data['apps'] if a.get('pinned')]
                    current_unpinned = [a for a in self.folder_data['apps'] if not a.get('pinned')]

                    if ad['pinned']:
                        insert_idx = min(idx, len(current_pinned))
                        current_pinned.insert(insert_idx, ad)
                    else:
                        insert_idx = max(0, idx - len(current_pinned))
                        insert_idx = min(insert_idx, len(current_unpinned))
                        current_unpinned.insert(insert_idx, ad)

                    self.folder_data['apps'] = current_pinned + current_unpinned
                    idx += 1
                    dropped.append(d)
                except:
                    pass
            
            # Final deduplication check for URLs
            seen = set(); unique = []
            for a in self.folder_data['apps']:
                if a['path'] not in seen:
                    unique.append(a); seen.add(a['path'])
            self.folder_data['apps'] = unique

            ConfigManager.save(self.cfg)
            if self.folder_data.get('sort_type', 'name') != 'custom':
                self.apply_sort(new_paths=dropped)
            else:
                self.refresh(new_paths=dropped)
                self.parent_icon.update()
            self.parent_icon.trigger_pulse()
            e.acceptProposedAction()
    def move_to_desktop(self, ad_or_list):
        if not isinstance(ad_or_list, list):
            ad_or_list = [ad_or_list]
            
        for ad in ad_or_list:
            try:
                dest = os.path.join(DESKTOP_PATH, os.path.basename(ad['path']))
                if os.path.exists(ad['path']):
                    if os.path.exists(dest) and dest != ad['path']:
                        os.remove(ad['path'])
                    else:
                        shutil.move(ad['path'], dest)
            except:
                pass
            self.folder_data['apps'] = [a for a in self.folder_data['apps'] if a['path'] != ad['path']]
            
        self.selected_apps.clear()
        ConfigManager.save(self.cfg)
        if self.folder_data.get('sort_type', 'name') != 'custom':
            self.apply_sort()
        else:
            self.refresh()
            self.parent_icon.update()