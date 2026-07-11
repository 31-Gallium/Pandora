import os
import ctypes
import math
from PyQt6.QtWidgets import QWidget, QApplication
from PyQt6.QtCore import Qt, QPoint, QRect, QTimer, QVariantAnimation, QEasingCurve
from PyQt6.QtGui import QPainter, QColor, QPen
from utils import WinAPI

class GridOverlay(QWidget):
    def __init__(self, cfg):
        super().__init__()
        self.cfg = cfg
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint | 
            Qt.WindowType.Tool | 
            Qt.WindowType.WindowStaysOnTopHint | 
            Qt.WindowType.WindowTransparentForInput |
            Qt.WindowType.WindowDoesNotAcceptFocus |
            Qt.WindowType.NoDropShadowWindowHint
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setAttribute(Qt.WidgetAttribute.WA_NoSystemBackground, True)
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating, True)
        
        geom = QApplication.primaryScreen().geometry()
        for screen in QApplication.screens():
            geom = geom.united(screen.geometry())
        
        # Offset by 1px to avoid Windows 11 DND detection
        self.setGeometry(geom.x(), geom.y(), geom.width(), geom.height() - 1)
        
        self.manually_visible = False
        self.is_dragging = False
        self.time = 0.0
        self.entrance_progress = 0.0
        self.wave_origin = None
        
        self.anim_timer = QTimer(self)
        self.anim_timer.timeout.connect(self._step_anim)
        self.anim_timer.setInterval(16)
        
        self.entrance_anim = QVariantAnimation(self)
        self.entrance_anim.setDuration(1200)
        self.entrance_anim.setEasingCurve(QEasingCurve.Type.OutCubic)
        self.entrance_anim.valueChanged.connect(self._upd_entrance)
        
    def _step_anim(self):
        self.time += 0.05
        if self.cfg.get('general_settings', {}).get('grid_animated_color', True):
            self.update()
        
    def _upd_entrance(self, v):
        self.entrance_progress = v
        self.update()
        
    def _on_anim_finished(self):
        if self.entrance_anim.direction() == QVariantAnimation.Direction.Backward:
            super().setVisible(False)
            self.anim_timer.stop()
            self.wave_origin = None

    def showEvent(self, e):
        QTimer.singleShot(50, lambda: WinAPI.pin_to_workerw(self.winId()))
        super().showEvent(e)
        
    def setVisible(self, visible, origin=None):
        is_exiting = (self.entrance_anim.state() == QVariantAnimation.State.Running and 
                     self.entrance_anim.direction() == QVariantAnimation.Direction.Backward)
        
        if visible:
            if not self.isVisible() or is_exiting:
                super().setVisible(True)
                self.wave_origin = origin
                self.entrance_anim.stop()
                self.entrance_anim.setEasingCurve(QEasingCurve.Type.OutCubic)
                self.entrance_anim.setDirection(QVariantAnimation.Direction.Forward)
                self.entrance_anim.setStartValue(self.entrance_progress)
                self.entrance_anim.setEndValue(1.0)
                self.entrance_anim.start()
                self.anim_timer.start()
        else:
            if self.isVisible() and not is_exiting:
                self.wave_origin = origin
                self.entrance_anim.stop()
                self.entrance_anim.setEasingCurve(QEasingCurve.Type.InQuart)
                self.entrance_anim.setDirection(QVariantAnimation.Direction.Backward)
                self.entrance_anim.setStartValue(0.0)
                self.entrance_anim.setEndValue(self.entrance_progress)
                try: self.entrance_anim.finished.disconnect()
                except: pass
                self.entrance_anim.finished.connect(self._on_anim_finished)
                self.entrance_anim.start()

    def toggle(self):
        self.manually_visible = not self.manually_visible
        self.setVisible(self.manually_visible or self.is_dragging)
        return self.manually_visible

    def set_drag_state(self, dragging, pos=None):
        self.is_dragging = dragging
        show_on_drag = self.cfg.get('general_settings', {}).get('show_grid_on_drag', True)
        if dragging:
            if show_on_drag: self.setVisible(True, origin=pos)
        else:
            if not self.manually_visible: self.setVisible(False, origin=pos)

    def get_snap_pos(self, global_pos):
        gen = self.cfg.get('general_settings', {})
        grid_size = gen.get('grid_size', 110)
        if grid_size <= 0: return None
        
        pad_t = gen.get('edge_padding_t', gen.get('edge_padding', 0))
        pad_b = gen.get('edge_padding_b', gen.get('edge_padding', 0))
        pad_l = gen.get('edge_padding_l', gen.get('edge_padding', 0))
        pad_r = gen.get('edge_padding_r', gen.get('edge_padding', 0))
        
        m_t = int(40 + pad_t)
        m_b = int(40 + pad_b)
        m_l = int(40 + pad_l)
        m_r = int(40 + pad_r)
        
        screen = QApplication.screenAt(global_pos)
        if not screen: screen = QApplication.primaryScreen()
        
        scr_geom = screen.availableGeometry()
        scr_c = scr_geom.center()
        
        # Symmetrical offset calculation matching paintEvent
        offset_x = scr_c.x() % grid_size
        offset_y = scr_c.y() % grid_size
        
        snapped_x = round((global_pos.x() - offset_x) / grid_size) * grid_size + offset_x
        snapped_y = round((global_pos.y() - offset_y) / grid_size) * grid_size + offset_y
        
        # clamp to screen bounds inside margins
        snapped_x = max(scr_geom.left() + m_l, min(snapped_x, scr_geom.right() - m_r))
        snapped_y = max(scr_geom.top() + m_t, min(snapped_y, scr_geom.bottom() - m_b))
        
        return QPoint(int(snapped_x), int(snapped_y))

    def paintEvent(self, e):
        if not self.isVisible(): return
        
        gen = self.cfg.get('general_settings', {})
        grid_size = gen.get('grid_size', 110)
        if grid_size <= 0: return
        
        user_opacity = gen.get('grid_opacity', 100) / 100.0
        animated_color = gen.get('grid_animated_color', True)
        wave_entrance = gen.get('grid_wave_entrance', True)
        wave_fade = gen.get('grid_wave_fade', True)
        pad_t = gen.get('edge_padding_t', gen.get('edge_padding', 0))
        pad_b = gen.get('edge_padding_b', gen.get('edge_padding', 0))
        pad_l = gen.get('edge_padding_l', gen.get('edge_padding', 0))
        pad_r = gen.get('edge_padding_r', gen.get('edge_padding', 0))
        
        m_t = int(40 + pad_t)
        m_b = int(40 + pad_b)
        m_l = int(40 + pad_l)
        m_r = int(40 + pad_r)
        
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        geom = self.geometry()
        
        is_exiting = self.entrance_anim.direction() == QVariantAnimation.Direction.Backward
        
        for screen in QApplication.screens():
            scr_geom = screen.availableGeometry()
            safe_rect = scr_geom.adjusted(m_l, m_t, -m_r, -m_b)
            local_safe_rect = safe_rect.translated(-geom.x(), -geom.y())
            p.setClipRect(local_safe_rect)
            
            scr_c = scr_geom.center()
            lcx_fixed, lcy_fixed = scr_c.x() - geom.x(), scr_c.y() - geom.y()
            offset_x, offset_y = int(lcx_fixed % grid_size), int(lcy_fixed % grid_size)
            
            if self.wave_origin and scr_geom.contains(self.wave_origin):
                ox, oy = self.wave_origin.x() - geom.x(), self.wave_origin.y() - geom.y()
            else:
                ox, oy = lcx_fixed, lcy_fixed
            
            diag = math.sqrt(scr_geom.width()**2 + scr_geom.height()**2)
            edge_w = 1200 
            wave_radius = self.entrance_progress * (diag + edge_w)
            
            for x_val in range(int(offset_x - grid_size), int(self.width() + grid_size), int(grid_size)):
                for y_val in range(int(offset_y - grid_size), int(self.height() + grid_size), int(grid_size)):
                    x, y = float(x_val), float(y_val)
                    
                    if wave_entrance:
                        dx, dy = x - ox, y - oy
                        dist = math.sqrt(dx*dx + dy*dy)
                        
                        if dist > wave_radius:
                            p_prog = 0.0
                        else:
                            if wave_fade:
                                p_prog = min(1.0, (wave_radius - dist) / edge_w)
                            else:
                                p_prog = 1.0 # Hard cutoff
                        
                        # 3D Depth only applies when Wave Entrance is ON
                        max_scale = 3.0 if is_exiting else 5.0
                        p_scale = 1.0 + (1.0 - p_prog) * max_scale
                        glow_boost = 1.0 + (1.0 - p_prog) * 1.2
                    else:
                        p_prog = self.entrance_progress
                        dist = 0
                        # 3D Depth is DISABLED if Wave Entrance is OFF
                        p_scale = 1.0
                        glow_boost = 1.0
                    
                    if p_prog <= 0: continue
                    
                    alpha_pow = 3.0 if is_exiting else 1.0
                    final_alpha = (p_prog ** alpha_pow) * user_opacity
                    
                    if animated_color:
                        hue = int((self.time * 20 + dist * 0.1) % 360)
                        color = QColor.fromHsv(hue, int(150 / glow_boost), min(255, int(255 * glow_boost)))
                    else:
                        c_val = min(255, int(255 * glow_boost))
                        color = QColor(c_val, c_val, c_val)
                    
                    # Draw "Depth Halo" - only if wave_entrance is enabled
                    if wave_entrance and p_prog < 1.0:
                        p.setPen(Qt.PenStyle.NoPen)
                        halo_alpha = int(25 * (1.0 - p_prog) * final_alpha)
                        if halo_alpha > 0:
                            p.setBrush(QColor(color.red(), color.green(), color.blue(), halo_alpha))
                            hs = 8 * p_scale
                            p.drawEllipse(int(x - hs/2), int(y - hs/2), int(hs), int(hs))
                    
                    # Draw Main Cross
                    p.setPen(QPen(QColor(color.red(), color.green(), color.blue(), int(120 * final_alpha)), max(1, int(p_scale))))
                    cs = 4 * p_scale
                    p.drawLine(int(x - cs), int(y), int(x + cs), int(y))
                    p.drawLine(int(x), int(y - cs), int(x), int(y + cs))
                    
                    # Draw Line Segments
                    line_p = max(0, (p_prog - 0.2) / 0.8)
                    if line_p > 0:
                        l_alpha_pow = 4.0 if is_exiting else 2.0
                        lw = max(1, int(2 * p_scale))
                        p.setPen(QPen(QColor(color.red(), color.green(), color.blue(), int(45 * (line_p ** l_alpha_pow) * user_opacity)), lw))
                        if x + grid_size < self.width() + grid_size:
                            p.drawLine(int(x + 4), int(y), int(x + grid_size - 4), int(y))
                        if y + grid_size < self.height() + grid_size:
                            p.drawLine(int(x), int(y + cs + 2), int(x), int(y + grid_size - cs - 2))
            
            p.setClipping(False)
