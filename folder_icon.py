import os
import json
import shutil
from PyQt6.QtWidgets import QWidget, QApplication
from PyQt6.QtCore import Qt, QVariantAnimation, QEasingCurve, QPoint, QPointF, QRect, QRectF, QFileInfo, QPropertyAnimation
from PyQt6.QtGui import QPainter, QColor, QRadialGradient, QAction, QPixmap, QPainterPath

from config import ConfigManager, STORAGE_PATH
from utils import WinAPI, IconExtractor, VectorIcon
from ui_common import AnimatedMenu
from folder_view import FolderView
from app_icon import AppIcon

class FolderIcon(QWidget):
    def __init__(self, data, cfg, dashboard=None):
        super().__init__()
        self.data = data
        self.cfg = cfg
        self.dashboard = dashboard
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.Tool | Qt.WindowType.WindowStaysOnBottomHint)
        self.setFixedSize(300, 300)
        self.move(data['pos'][0], data['pos'][1])
        self.setAcceptDrops(True)
        self.setMouseTracking(True)
        
        self._scale = 1.0
        self.pulse_anim = QVariantAnimation(self)
        self.pulse_anim.setDuration(300)
        self.pulse_anim.setEasingCurve(QEasingCurve.Type.OutBack)
        self.pulse_anim.setStartValue(1.1)
        self.pulse_anim.setEndValue(1.0)
        self.pulse_anim.valueChanged.connect(self._set_scale)
        
        self._hover_progress = 0.0
        self.hover_anim = QVariantAnimation(self)
        self.hover_anim.setDuration(250)
        self.hover_anim.setEasingCurve(QEasingCurve.Type.OutCubic)
        self.hover_anim.setStartValue(0.0)
        self.hover_anim.setEndValue(1.0)
        self.hover_anim.valueChanged.connect(self._set_hover_progress)
        
        self.local_mouse_pos = QPoint(150, 150)
        self.is_dragging = False
        self._suppress_restore = False
        self._desktop_init = False
        
        self.setMouseTracking(True)
        self.setAttribute(Qt.WidgetAttribute.WA_Hover)

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

    def _set_scale(self, v): self._scale = v; self.update()
    def _set_hover_progress(self, v): self._hover_progress = v; self.update()
    def trigger_pulse(self): self.pulse_anim.stop(); self.pulse_anim.start()
    
    def _update_hover_speed(self):
        speed_mode = self.get_setting('hover_speed', 'Fluid')
        self.hover_anim.setDuration({"Snappy": 150, "Fluid": 250, "Relaxed": 400}.get(speed_mode, 250))

    def enterEvent(self, e): 
        if __import__('time').time() < getattr(self, '_hover_lockout_until', 0): return
        self._update_hover_speed()
        self.hover_anim.setDirection(QVariantAnimation.Direction.Forward)
        self.hover_anim.start()
    def leaveEvent(self, e): 
        self._update_hover_speed()
        self.hover_anim.setDirection(QVariantAnimation.Direction.Backward)
        self.hover_anim.start()
        self.local_mouse_pos = QPoint(150, 150)
    def showEvent(self, e): 
        WinAPI.set_modern_visuals(self.winId(), False)
        WinAPI.allow_drag_drop(self.winId())
        # Apply WorkerW trick slightly after show to prevent rendering glitches
        __import__('PyQt6.QtCore').QtCore.QTimer.singleShot(50, lambda: WinAPI.pin_to_workerw(self.winId()))

    def _get_grid_params(self, hp=None):
        if hp is None: hp = self._hover_progress
        cx, cy = self.width() / 2, self.height() / 2
        folder_size = self.get_setting('folder_size', 80)
        mini_icon_size = self.get_setting('mini_icon_size', 16)
        
        isz = mini_icon_size + (11 * hp)
        gap = (folder_size / 20) + ((folder_size / 5) * hp)
        tl = 3 * isz + 2 * gap
        gx, gy = cx - tl / 2, cy - tl / 2
        
        # Edge avoidance
        scr = QApplication.primaryScreen().availableGeometry()
        global_left, global_top = self.x() + gx, self.y() + gy
        global_right, global_bottom = global_left + tl, global_top + tl
        
        if global_left < scr.left() + 5: gx += (scr.left() + 5 - global_left)
        if global_right > scr.right() - 5: gx -= (global_right - (scr.right() - 5))
        if global_top < scr.top() + 5: gy += (scr.top() + 5 - global_top)
        if global_bottom > scr.bottom() - 5: gy -= (global_bottom - (scr.bottom() - 5))
        
        # Clamp to widget bounds
        if gx < 10: gx = 10
        elif gx + tl > 290: gx = 290 - tl
        if gy < 10: gy = 10
        elif gy + tl > 290: gy = 290 - tl
        
        return gx, gy, isz, gap, tl

    def paintEvent(self, e):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
        
        # Clean background fill with CompositionMode_Source to prevent ghosting
        p.setCompositionMode(QPainter.CompositionMode.CompositionMode_Source)
        p.fillRect(self.rect(), Qt.GlobalColor.transparent)
        p.setCompositionMode(QPainter.CompositionMode.CompositionMode_SourceOver)
        
        cx, cy = self.width() / 2, self.height() / 2
        folder_size = self.get_setting('folder_size', 80)
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
            
        if self._hover_progress > 0 or self.is_dragging:
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
        p.drawRoundedRect(QRectF(cx - folder_size / 2, cy - folder_size / 2, folder_size, folder_size).adjusted(0.5, 0.5, -0.5, -0.5), radius, radius)
        
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
            gx, gy, isz, gap, tl = self._get_grid_params()
            apps = self.data.get('apps', [])[:9]
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
            title_color = QColor(self.get_setting('title_color', '#ffffff'))
            title_color.setAlpha(int(title_color.alpha() * (1.0 - self._hover_progress)))
            p.setPen(title_color)
            p.drawText(QRect(0, int(cy + folder_size / 2 + 3), 300, 20), Qt.AlignmentFlag.AlignCenter, self.data['name'])

    def mousePressEvent(self, e):
        if e.button() == Qt.MouseButton.LeftButton: 
            self.dsp = e.globalPosition().toPoint()
            self.wsp = self.pos()

    def mouseReleaseEvent(self, e):
        self.is_dragging = False
        if self.rect().contains(e.pos()):
            self.hover_anim.setDirection(QVariantAnimation.Direction.Forward)
            self.hover_anim.start()

        if e.button() == Qt.MouseButton.LeftButton and hasattr(self, 'dsp') and (e.globalPosition().toPoint() - self.dsp).manhattanLength() < 5: 
            if e.modifiers() & Qt.KeyboardModifier.AltModifier:
                # Alt-click detected. Assume fully fanned out.
                hp = 1.0 if self._hover_progress < 0.5 else self._hover_progress
                
                gx, gy, isz, gap, tl = self._get_grid_params(hp)
                cx, cy = self.width() / 2, self.height() / 2
                
                hover_zoom = 1.0 + (0.15 * hp)
                combined_scale = self._scale * hover_zoom
                
                lp = e.position()

                apps = self.data.get('apps', [])[:9]
                for i, a in enumerate(apps):
                    r, c_idx = i // 3, i % 3
                    
                    logical_x = gx + c_idx * (isz + gap)
                    logical_y = gy + r * (isz + gap)
                    
                    visual_x = cx + (logical_x - cx) * combined_scale
                    visual_y = cy + (logical_y - cy) * combined_scale
                    visual_size = isz * combined_scale
                    
                    # 5px padding on all sides
                    hit_box = QRectF(visual_x - 5, visual_y - 5, visual_size + 10, visual_size + 10)
                    
                    if hit_box.contains(lp):
                        if os.path.exists(a['path']): os.startfile(a['path'])
                        return
            FolderView(self.data, self).show_morph(self.geometry())
        elif e.button() == Qt.MouseButton.LeftButton and hasattr(self, 'dsp'):
            if self.get_setting('grid_snap', False):
                grid_size = self.cfg.get('global_settings', {}).get('grid_size', 110)
                if grid_size > 0:
                    cx = self.x() + 150
                    cy = self.y() + 150
                    
                    def get_snap_pos(x, y):
                        scr_c = QApplication.primaryScreen().availableGeometry().center()
                        nx = scr_c.x() + round((x - scr_c.x()) / grid_size) * grid_size
                        ny = scr_c.y() + round((y - scr_c.y()) / grid_size) * grid_size
                        return nx, ny
                    
                    target_gx, target_gy = get_snap_pos(cx, cy)
                    
                    fs = self.get_setting('folder_size', 80)
                    edge_padding = self.cfg.get('global_settings', {}).get('edge_padding', 15)
                    margin = fs / 2 + edge_padding
                    scr = QApplication.primaryScreen().availableGeometry()
                    safe_rect = scr.adjusted(int(margin), int(margin), -int(margin), -int(margin))
                    
                    def is_valid_and_unoccupied(gx, gy, exclude_id):
                        if not safe_rect.contains(QPoint(int(gx), int(gy))):
                            return False
                        if not self.dashboard: return True
                        for w in self.dashboard.app_instances:
                            if w.data.get('id') == exclude_id: continue
                            # If the widget is animating, check its target
                            if hasattr(w, 'anim_move') and w.anim_move.state() == QPropertyAnimation.State.Running:
                                end_val = w.anim_move.endValue()
                                wgx, wgy = get_snap_pos(end_val.x() + 150, end_val.y() + 150)
                            else:
                                wgx, wgy = get_snap_pos(w.x() + 150, w.y() + 150)
                            if gx == wgx and gy == wgy:
                                return False
                        return True
                        
                    # Spiral search for the nearest valid and empty slot
                    spiral_dx = [0, 1, 0, -1]
                    spiral_dy = [-1, 0, 1, 0]
                    step = 0
                    dir_idx = 0
                    steps_in_dir = 1
                    curr_gx, curr_gy = target_gx, target_gy
                    
                    while not is_valid_and_unoccupied(curr_gx, curr_gy, self.data.get('id')) and step < 200:
                        curr_gx += spiral_dx[dir_idx] * grid_size
                        curr_gy += spiral_dy[dir_idx] * grid_size
                        step += 1
                        if step % steps_in_dir == 0:
                            dir_idx = (dir_idx + 1) % 4
                            if dir_idx % 2 == 0:
                                steps_in_dir += 1
                                
                    nx = curr_gx - 150
                    ny = curr_gy - 150
                    
                    self.anim_move = QPropertyAnimation(self, b"pos")
                    self.anim_move.setDuration(150)
                    self.anim_move.setEasingCurve(QEasingCurve.Type.OutQuad)
                    self.anim_move.setEndValue(QPoint(int(nx), int(ny)))
                    self.anim_move.finished.connect(lambda: (self.data.update({'pos': [self.x(), self.y()]}), ConfigManager.save(self.cfg)))
                    self.anim_move.start()

    def mouseMoveEvent(self, e):
        if e.buttons() & Qt.MouseButton.LeftButton:
            if self.data.get('locked', False): return
            
            # Collapse grid smoothly while dragging
            if not self.is_dragging:
                self.is_dragging = True
                if self._hover_progress > 0:
                    self.hover_anim.setDirection(QVariantAnimation.Direction.Backward)
                    self.hover_anim.start()
                
            if hasattr(self, 'wsp') and hasattr(self, 'dsp'):
                np = self.wsp + e.globalPosition().toPoint() - self.dsp
            else:
                np = self.pos() + e.pos() - QPoint(150, 150)
            scr = QApplication.primaryScreen().availableGeometry()
            fs = self.get_setting('folder_size', 80)
            min_x = scr.left() - 150 + fs / 2
            max_x = scr.right() - 150 - fs / 2
            min_y = scr.top() - 150 + fs / 2
            max_y = scr.bottom() - 150 - fs / 2
            nx, ny = max(min_x, min(np.x(), max_x)), max(min_y, min(np.y(), max_y))
            self.move(int(nx), int(ny))
            self.data['pos'] = [self.x(), self.y()]
            ConfigManager.save(self.cfg)
        elif e.buttons() == Qt.MouseButton.NoButton:
            self.local_mouse_pos = e.position().toPoint()
            if self._hover_progress > 0: self.update()

    def contextMenuEvent(self, e):
        m = AnimatedMenu(self)
        l = QAction("Launch All", self); l.triggered.connect(self.launch_all); m.addAction(l)
        if self.dashboard:
            s = QAction("Settings", self); s.triggered.connect(lambda: self.dashboard.show_folder(self.data['id'])); m.addAction(s)
        d = QAction("Delete", self); d.triggered.connect(self.delete_folder); m.addAction(d)
        m.exec(e.globalPos())

    def launch_all(self):
        for app in self.data.get('apps', []):
            try:
                if os.path.exists(app.get('path', '')): os.startfile(app['path'])
            except: pass

    def delete_folder(self): 
        self._is_deleted = True
        self._suppress_restore = True
        from utils import DesktopMonitor
        DesktopMonitor.unregister(self)
        WinAPI.unregister_appbar(self.winId())
        self.cfg['folders'].remove(self.data)
        ConfigManager.save(self.cfg)
        if self.dashboard:
            self.dashboard.handle_folder_deleted(self)
        self.hide()
        self.deleteLater()
    def dragEnterEvent(self, e): 
        if e.mimeData().hasFormat("application/x-cusfolder-app") or e.mimeData().hasUrls(): e.acceptProposedAction()
    def dragMoveEvent(self, e): e.acceptProposedAction()
    
    def dropEvent(self, e):
        if e.mimeData().hasFormat("application/x-cusfolder-app"):
            sid = e.mimeData().data("application/x-cusfolder-app").data().decode()
            try:
                dropped_apps = json.loads(e.mimeData().text())
                if isinstance(dropped_apps, dict):
                    dropped_apps = [dropped_apps]
            except json.JSONDecodeError:
                dropped_apps = []

            for ad in dropped_apps:
                ad['pinned'] = False
                if isinstance(e.source(), AppIcon): e.source().is_internal = True
                for f in self.cfg['folders']:
                    if f['id'] == sid: f['apps'] = [a for a in f['apps'] if a['path'] != ad['path']]; break
                self.data['apps'].append(ad)
                
            ConfigManager.save(self.cfg)
            if self.data.get('sort_type', 'name') != 'custom':
                self.apply_sort_logic()
            self.update()
            self.trigger_pulse()
            e.acceptProposedAction()
            return
        for u in e.mimeData().urls():
            s = u.toLocalFile()
            d = os.path.join(STORAGE_PATH, os.path.basename(s))
            try: 
                shutil.move(s, d)
                self.data['apps'].append({"name": QFileInfo(d).baseName(), "path": d, "pinned": False})
            except: pass
        ConfigManager.save(self.cfg)
        if self.data.get('sort_type', 'name') != 'custom':
            self.apply_sort_logic()
        self.update()
        self.trigger_pulse()
        e.acceptProposedAction()

    def apply_sort_logic(self):
        rev = self.data.get('sort_order', 'asc') == 'desc'
        st = self.data.get('sort_type', 'name')
        def sk(app):
            p = app.get('path', '')
            info = QFileInfo(p)
            name_key = app.get('name', '').lower()
            if st == 'extension':
                if info.isDir(): return (0, '_folder', name_key)
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
            if st == 'size': return (0, info.size(), name_key)
            if st == 'date': return (0, info.lastModified().toMSecsSinceEpoch(), name_key)
            if st == 'recent':
                bt = info.birthTime().toMSecsSinceEpoch() if info.birthTime().isValid() else info.lastModified().toMSecsSinceEpoch()
                return (0, bt, name_key)
            return (0, name_key, "")

        p = [a for a in self.data.get('apps', []) if a.get('pinned')]
        u = [a for a in self.data.get('apps', []) if not a.get('pinned')]
        self.data['apps'] = sorted(p, key=sk, reverse=rev) + sorted(u, key=sk, reverse=rev)
        ConfigManager.save(self.cfg)
