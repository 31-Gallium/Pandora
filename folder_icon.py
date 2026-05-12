import os
import json
import shutil
import math
from PyQt6.QtWidgets import QWidget, QApplication
from PyQt6.QtCore import Qt, QVariantAnimation, QEasingCurve, QPoint, QPointF, QRect, QRectF, QFileInfo, QPropertyAnimation
from PyQt6.QtGui import QPainter, QColor, QRadialGradient, QAction, QPixmap, QPainterPath

from config import ConfigManager, STORAGE_PATH
from utils import WinAPI, IconExtractor, VectorIcon
from ui_common import AnimatedMenu
from folder_view import FolderView
from app_icon import AppIcon
from layout_logic import get_engine
from ui_utils import draw_folder_thumbnail
from logic import handle_app_drop
import logging
logger = logging.getLogger("Pandora")

class FolderIcon(QWidget):
    def __init__(self, data, cfg, dashboard=None):
        super().__init__()
        self.data = data
        self.cfg = cfg
        self.dashboard = dashboard
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.Tool | Qt.WindowType.WindowStaysOnBottomHint)
        self.setFixedSize(300, 300)
        self.move(int(data['pos'][0]), int(data['pos'][1]))
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
        self.movie = None
        self.dsp = QPoint(0, 0)
        self.wsp = self.pos()
        self._update_movie()
        
        self.setMouseTracking(True)
        self.setAttribute(Qt.WidgetAttribute.WA_Hover)

        # Paging State
        self._page_idx = 0
        self._next_page_idx = 0
        self._page_direction = 1
        self._page_anim_progress = 1.0
        self.page_anim = QVariantAnimation(self)
        self.page_anim.setDuration(400)
        self.page_anim.setEasingCurve(QEasingCurve.Type.InOutCubic)
        self.page_anim.setStartValue(0.0)
        self.page_anim.setEndValue(1.0)
        self.page_anim.valueChanged.connect(self._set_page_progress)
        self.page_anim.finished.connect(self._on_page_anim_finished)

    def _set_page_progress(self, v): self._page_anim_progress = v; self.update()
    def _on_page_anim_finished(self): self._page_idx = self._next_page_idx; self._page_anim_progress = 1.0; self.update()

    def wheelEvent(self, e):
        if self._hover_progress < 0.5: return
        apps = self.data.get('apps', [])
        page_size = 7 if self.data.get('template_type') == 'flower' else 9
        if len(apps) <= page_size: return
        
        delta = e.angleDelta().y()
        if abs(delta) < 20: return
        
        direction = 1 if delta < 0 else -1
        max_pages = (len(apps) + page_size - 1) // page_size
        new_page = self._page_idx + direction
        
        if 0 <= new_page < max_pages:
            if self.page_anim.state() != QVariantAnimation.State.Running:
                self._page_direction = direction
                self._next_page_idx = new_page
                self.page_anim.start()

    def _update_movie(self):
        cp = self.data.get('cover_image')
        if cp and cp.lower().endswith('.gif') and os.path.exists(cp):
            if not self.movie or self.movie.fileName() != cp:
                from PyQt6.QtGui import QMovie
                self.movie = QMovie(cp)
                self.movie.frameChanged.connect(lambda _: self.update())
                self.movie.start()
        elif self.movie:
            self.movie.stop(); self.movie = None

    def get_setting(self, key, default):
        INSTANCE_KEYS = ('show_title', 'grid_snap', 'show_cover', 'title_color')
        if key in INSTANCE_KEYS and key in self.data:
            return self.data[key]
        t_type = self.data.get('template_type', 'grid')
        t_name = self.data.get('template_name', 'Default')
        t_data = self.cfg.get('templates', {}).get(t_type, {}).get(t_name, {})
        use_custom = self.data.get('use_custom_settings', False)
        if use_custom:
            val = self.data.get('custom_settings', {}).get(key)
            if val is not None: return val
        if key in t_data: return t_data[key]
        preset = t_data.get('size_preset', 'Medium')
        if use_custom:
            preset = self.data.get('custom_settings', {}).get('size_preset', preset)
        SIZE_PRESETS = {
            "Small": {"folder_size": 60, "mini_icon_size": 20, "font_size": 9, "expanded_icon_size": 32},
            "Medium": {"folder_size": 80, "mini_icon_size": 27, "font_size": 10, "expanded_icon_size": 48},
            "Large": {"folder_size": 110, "mini_icon_size": 34, "font_size": 12, "expanded_icon_size": 64}
        }
        if preset in SIZE_PRESETS and key in SIZE_PRESETS[preset]:
            return SIZE_PRESETS[preset][key]
        return self.cfg.get('general_settings', {}).get(key, default)

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
        __import__('PyQt6.QtCore').QtCore.QTimer.singleShot(50, lambda: WinAPI.pin_to_workerw(self.winId()))

    def paintEvent(self, e):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
        p.setCompositionMode(QPainter.CompositionMode.CompositionMode_Source)
        p.fillRect(self.rect(), Qt.GlobalColor.transparent)
        p.setCompositionMode(QPainter.CompositionMode.CompositionMode_SourceOver)
        
        cx, cy = self.width() / 2, self.height() / 2
        
        # Apply Pulse Scale
        if self._scale != 1.0:
            p.translate(cx, cy); p.scale(self._scale, self._scale); p.translate(-cx, -cy)

        # Refresh movie if path changed, then inject GIF frame if active
        self._update_movie()
        if self.movie: self.data['_current_cover_frame'] = self.movie.currentPixmap()
        else: self.data.pop('_current_cover_frame', None)

        draw_folder_thumbnail(p, self.rect(), self.data, self.cfg, 
                              hover_progress=self._hover_progress,
                              paging_params={
                                  'page': self._page_idx, 
                                  'next_page': self._next_page_idx, 
                                  'progress': self._page_anim_progress,
                                  'direction': self._page_direction
                              })
        
        if self.get_setting('show_title', True):
            p.resetTransform() # Reset for text so it doesn't zoom too much
            title_color = QColor(self.get_setting('title_color', '#ffffff'))
            title_color.setAlpha(int(title_color.alpha() * (1.0 - self._hover_progress)))
            p.setPen(title_color)
            folder_size = self.get_setting('folder_size', 80)
            p.drawText(QRect(0, int(cy + folder_size / 2 + 3), 300, 20), Qt.AlignmentFlag.AlignCenter, self.data['name'])

    def get_app_at_pos(self, pos):
        cx, cy = self.width() / 2, self.height() / 2
        folder_size = self.get_setting('folder_size', 80)
        mini_icon_size = self.get_setting('mini_icon_size', 18)
        t_type = self.data.get('template_type', 'grid')
        engine = get_engine(t_type)
        apps = self.data.get('apps', [])
        
        # Account for paging in hit detection
        page_size = 7 if t_type == 'flower' else 9
        start_idx = self._page_idx * page_size
        current_apps = apps[start_idx : start_idx + page_size]

        pos_list = engine.get_collapsed_positions(cx, cy, folder_size, mini_icon_size, len(current_apps), self._hover_progress)
        isz = mini_icon_size * (1.0 + 0.5 * self._hover_progress)
        for i, p_pos in enumerate(pos_list):
            if i >= len(current_apps): break
            r = QRectF(p_pos.x() + (mini_icon_size - isz) / 2, p_pos.y() + (mini_icon_size - isz) / 2, isz, isz)
            if r.contains(QPointF(pos)): return current_apps[i]
        return None

    def mousePressEvent(self, e):
        # We handle the 'press' mainly for drag-start detection.
        # But for Right Click to work as a configurable action, we need to store the start pos.
        if e.button() in (Qt.MouseButton.LeftButton, Qt.MouseButton.MiddleButton, Qt.MouseButton.RightButton): 
            self.dsp = e.globalPosition().toPoint()
            self.wsp = self.pos()

    def mouseReleaseEvent(self, e):
        if self.is_dragging:
            if self.dashboard and hasattr(self.dashboard, 'grid_overlay'):
                self.dashboard.grid_overlay.set_drag_state(False, pos=e.globalPosition().toPoint())
                if self.get_setting('grid_snap', False):
                    snapped = self.dashboard.grid_overlay.get_snap_pos(e.globalPosition().toPoint())
                    if snapped:
                        target_np = QPoint(int(snapped.x() - self.width()/2), int(snapped.y() - self.height()/2))
                        self.snap_anim = QPropertyAnimation(self, b"pos"); self.snap_anim.setDuration(400); self.snap_anim.setEasingCurve(QEasingCurve.Type.OutBack); self.snap_anim.setEndValue(target_np); self.snap_anim.start()
                        self.data['pos'] = [target_np.x(), target_np.y()]
                else: self.data['pos'] = [self.pos().x(), self.pos().y()]
            ConfigManager.save(self.cfg); self.is_dragging = False
        elif hasattr(self, 'dsp') and (e.globalPosition().toPoint() - self.dsp).manhattanLength() < 5:
            gs = self.cfg.get('general_settings', {})
            kb = gs.get('keybinds', {"launch_app": 1, "open_folder": 4, "show_menu": 2})
            btn = e.button().value
            
            # Prioritization logic for collisions: Launch > Open > Menu
            if btn == kb.get('launch_app'):
                app = self.get_app_at_pos(e.pos())
                if app and os.path.exists(app['path']): 
                    os.startfile(app['path'])
                    return
                else:
                    # Fallback to Open Folder if they clicked Launch App but missed
                    if not hasattr(self, 'view') or self.view.isHidden():
                        self.view = FolderView(self.data, self); self.view.show_morph(self.geometry())
                    return

            if btn == kb.get('open_folder'):
                if not hasattr(self, 'view') or self.view.isHidden():
                    self.view = FolderView(self.data, self); self.view.show_morph(self.geometry())
            elif btn == kb.get('show_menu'):
                self.show_context_menu(e.globalPosition().toPoint())
        
        self.local_mouse_pos = QPoint(150, 150); self.update()

    def mouseMoveEvent(self, e):
        if e.buttons() & Qt.MouseButton.LeftButton:
            if not self.is_dragging and (e.globalPosition().toPoint() - self.dsp).manhattanLength() > 10:
                self.is_dragging = True
                if hasattr(self, 'snap_anim'): self.snap_anim.stop()
                if self.dashboard and hasattr(self.dashboard, 'grid_overlay'):
                    self.dashboard.grid_overlay.set_drag_state(True)
            
            if self.is_dragging:
                delta = e.globalPosition().toPoint() - self.dsp
                np = self.wsp + delta
                self.move(np)
        
        self.local_mouse_pos = e.pos()
        self.update()

    def dragEnterEvent(self, e):
        if e.mimeData().hasUrls(): e.acceptProposedAction()
    def dropEvent(self, e):
        if e.mimeData().hasFormat("application/x-pandora-app"):
            success, _ = handle_app_drop(self.cfg, self.data, e.mimeData(), e.source(), False, 0, self.dashboard)
            if success:
                ConfigManager.save(self.cfg)
                if hasattr(self, 'view') and self.view:
                    self.view.refresh()
                self.update()
                self.trigger_pulse()
                e.acceptProposedAction()
            return

        new_apps = []
        target_storage = os.path.join(STORAGE_PATH, self.data['id'])
        if not os.path.exists(target_storage): os.makedirs(target_storage)
        
        for url in e.mimeData().urls():
            s = url.toLocalFile()
            if os.path.exists(s):
                bn = os.path.basename(s)
                d = os.path.join(target_storage, bn)
                
                # Collision handling within THIS folder
                if os.path.exists(d):
                    name_part, ext_part = os.path.splitext(bn)
                    counter = 1
                    while os.path.exists(os.path.join(target_storage, f"{name_part} ({counter}){ext_part}")):
                        counter += 1
                    d = os.path.join(target_storage, f"{name_part} ({counter}){ext_part}")

                try:
                    shutil.move(s, d)
                    fi = QFileInfo(d)
                    name = fi.completeBaseName() if fi.isFile() else os.path.basename(d)
                    if not name: name = os.path.basename(d)
                    new_apps.append({"name": name, "path": d, "pinned": False})
                except Exception as ex:
                    logger.error(f"FolderIcon drop error: {ex}")
        
        if new_apps:
            self.data['apps'].extend(new_apps)
            ConfigManager.save(self.cfg)
            self.trigger_pulse()
            self.update()

    def contextMenuEvent(self, e):
        # We don't trigger here if it's already handled in mouseReleaseEvent.
        # But we keep it for standard context menu triggers.
        gs = self.cfg.get('general_settings', {})
        if gs.get('right_click_action') == 'Show Menu':
            self.show_context_menu(e.globalPos())

    def show_context_menu(self, pos):
        m = AnimatedMenu(self)
        s = QAction("Settings", self); s.triggered.connect(self.open_settings); m.addAction(s)
        t = QAction("Change Template", self); m.addAction(t)
        tm = AnimatedMenu(self); t.setMenu(tm)
        t_type = self.data.get('template_type', 'grid')
        for name in self.cfg.get('templates', {}).get(t_type, {}).keys():
            ta = QAction(name, self); ta.triggered.connect(lambda _, n=name: self.set_template(n))
            if name == self.data.get('template_name', 'Default'): ta.setIcon(VectorIcon.icon("check", "#50FA7B"))
            tm.addAction(ta)
        r = QAction("Remove Folder", self); r.triggered.connect(self.remove_self); m.addAction(r)
        m.exec(pos)

    def open_settings(self):
        if self.dashboard: self.dashboard.show_folder(self.data['id'])
    def set_template(self, name):
        self.data['template_name'] = name; ConfigManager.save(self.cfg); self.update()
    def remove_self(self):
        self.cfg['folders'] = [f for f in self.cfg['folders'] if f['id'] != self.data['id']]
        ConfigManager.save(self.cfg)
        if self.dashboard: self.dashboard.handle_folder_deleted(self)
        self.close()
