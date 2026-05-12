import math
import os
from PyQt6.QtWidgets import QWidget, QApplication
from PyQt6.QtCore import Qt, QPoint, QRectF, QPropertyAnimation, QEasingCurve, pyqtSignal, QPointF, QTimer
from PyQt6.QtGui import QColor, QPainter, QPainterPath, QFont, QPen, QBrush, QLinearGradient
from utils import VectorIcon

class RadialMenu(QWidget):
    command_triggered = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnTopHint | Qt.WindowType.Tool)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setMouseTracking(True)
        
        self.outer_radius = 290
        self.inner_radius = 150
        self.deadzone = 60 
        self.setFixedSize(self.outer_radius * 2 + 100, self.outer_radius * 2 + 100)
        
        self.tools = [
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
            {"id": "power", "icon": "power", "label": "Power"}
        ]
        
        self.active_index = -1
        self.center_pt = QPoint(self.width() // 2, self.height() // 2)
        self.original_cursor_pos = None
        self.current_mouse_pos = self.center_pt
        self.slice_progress = {}
        
        self.logo_renderer = None
        logo_path = os.path.join(os.getcwd(), "assets", "Pandora.svg")
        if os.path.exists(logo_path):
            from PyQt6.QtSvg import QSvgRenderer
            self.logo_renderer = QSvgRenderer(logo_path)
            
        # Aggressive cursor suppression and animation timer
        self.anim_timer = QTimer(self)
        self.anim_timer.timeout.connect(self._anim_loop)

        # Volume HUD state
        self.vol_opacity = 0.0
        self.vol_level = 0.0
        self.vol_target_opacity = 0.0
        self.vol_fade_timer = QTimer(self)
        self.vol_fade_timer.setSingleShot(True)
        self.vol_fade_timer.timeout.connect(self._hide_vol_hud)
        
    def _hide_vol_hud(self):
        self.vol_target_opacity = 0.0
        
    def reload_tools(self, cfg):
        rad_cfg = cfg.get('radial_menu', {})
        self.menus = rad_cfg.get('menus', [])
        if not hasattr(self, 'layer_index'): self.layer_index = 0
        if self.layer_index >= len(self.menus): self.layer_index = max(0, len(self.menus) - 1)
        if self.menus:
            self.tools = self.menus[self.layer_index].get('tools', [])
        else:
            self.tools = []
            
        if len(self.tools) == 0:
            self.tools = [{"id": "settings", "icon": "settings", "label": "Pandora"}]
            
        self.opacity = rad_cfg.get('opacity', 185)
        self.theme = rad_cfg.get('theme', 'Dark')
        self.deadzone = rad_cfg.get('deadzone', 30)
        self.scroll_sens = rad_cfg.get('scroll_sens', 50)
        self.mouse_sens = rad_cfg.get('mouse_sens', 100)
        self.outer_radius = rad_cfg.get('radius', 160)
        self.gap_size = rad_cfg.get('gap_size', 75)
        self.inner_radius = self.outer_radius // 2
        self.setFixedSize(self.outer_radius * 2 + 100, self.outer_radius * 2 + 100)
        self.center_pt = QPoint(self.width() // 2, self.height() // 2)
        self.update()
        
    def wheelEvent(self, e):
        # 1. Volume override if hovering mute
        if self.active_index != -1 and self.active_index < len(self.tools):
            tool = self.tools[self.active_index]
            if tool['id'] == "mute":
                from utils import change_system_volume, get_system_volume_level
                delta = 0.02 if e.angleDelta().y() > 0 else -0.02
                change_system_volume(delta)
                self.vol_level = get_system_volume_level()
                self.vol_target_opacity = 1.0; self.vol_opacity = 1.0
                self.vol_hud_val = int(self.vol_level * 100)
                self.vol_hud_dir = "up" if delta > 0 else "down"
                self.last_adjusted_id = "mute"
                self.vol_fade_timer.start(1500)
                self.update(); return
            elif tool['id'] == "night":
                from utils import DisplayEffectsEngine
                engine = DisplayEffectsEngine.instance()
                delta = 0.05 if e.angleDelta().y() > 0 else -0.05
                
                # Only turn on if scrolling UP while off
                if not engine._is_enabled:
                    if delta > 0:
                        engine.set_enabled(True, instant=True)
                        engine.set_intensity(0.0)
                    else:
                        e.accept(); return # Ignore scroll down if already off
                
                new_val = max(0.0, min(1.0, engine._target_intensity + delta))
                
                if new_val <= 0.001 and delta < 0:
                    engine.set_enabled(False)
                    self.vol_target_opacity = 0.0
                else:
                    engine.set_intensity(new_val)
                    self.vol_target_opacity = 1.0; self.vol_opacity = 1.0
                    self.vol_hud_val = int(new_val * 100)
                    self.vol_hud_dir = "night_up" if delta > 0 else "night_down"
                    self.last_adjusted_id = "night"
                    self.vol_fade_timer.start(1500)
                
                self.update(); return

        if not hasattr(self, 'menus') or len(self.menus) <= 1: return
        delta = e.angleDelta().y()
        
        sens = getattr(self, 'scroll_sens', 50) / 50.0
        if not hasattr(self, 'scroll_acc'): self.scroll_acc = 0.0
        self.scroll_acc += delta * sens
        
        steps = 0
        while self.scroll_acc >= 120:
            steps -= 1
            self.scroll_acc -= 120
        while self.scroll_acc <= -120:
            steps += 1
            self.scroll_acc += 120
            
        if steps == 0: return
        
        self.layer_anim_dir = 1 if steps > 0 else -1
        self.layer_anim_progress = 1.0
        
        self.layer_index = (self.layer_index + steps) % len(self.menus)
            
        self.tools = self.menus[self.layer_index].get('tools', [])
        if len(self.tools) == 0:
            self.tools = [{"id": "settings", "icon": "settings", "label": "Pandora"}]
            
        self.slice_progress = {} # reset anims
        self.active_index = -1
        self.update()
        
    def _anim_loop(self):
        if self.isVisible():
            QApplication.setOverrideCursor(Qt.CursorShape.BlankCursor)
            self.setCursor(Qt.CursorShape.BlankCursor)
            
        changed = False
        
        layer_anim = getattr(self, 'layer_anim_progress', 0.0)
        if layer_anim > 0.01:
            self.layer_anim_progress = layer_anim * 0.7
            changed = True
        elif layer_anim > 0:
            self.layer_anim_progress = 0.0
            changed = True
            
        num_tools = len(self.tools)
        for i in range(num_tools):
            target = 1.0 if i == self.active_index else 0.0
            current = self.slice_progress.get(i, 0.0)
            if abs(current - target) > 0.01:
                self.slice_progress[i] = current + (target - current) * 0.3
                changed = True
            else:
                self.slice_progress[i] = target
                
        # Volume HUD animation
        if abs(self.vol_opacity - self.vol_target_opacity) > 0.01:
            self.vol_opacity += (self.vol_target_opacity - self.vol_opacity) * 0.15
            changed = True
            
        if changed:
            self.update()

    def show_center(self):
        from PyQt6.QtGui import QCursor, QGuiApplication
        screen = QGuiApplication.primaryScreen().geometry()
        pos = screen.center()
        self.original_cursor_pos = QCursor.pos()
        self.move(pos.x() - self.width() // 2, pos.y() - self.height() // 2)
        
        QCursor.setPos(pos.x(), pos.y())
        self.anim_timer.start(16) # ~60 FPS
        self.current_mouse_pos = self.center_pt
        self.slice_progress = {}
        
        from utils import get_system_volume_level, get_battery_info
        self.vol_level = get_system_volume_level()
        self.batt_level, self.batt_plugged = get_battery_info()
        self.vol_opacity = 0.0
        self.vol_target_opacity = 0.0

        if hasattr(QApplication.instance(), 'global_hook'):
            QApplication.instance().global_hook.set_constraint(pos, self.outer_radius - 2)

        self.active_index = -1
        self.show()
        
    def update_mouse(self, global_pos):
        local_pos = self.mapFromGlobal(global_pos)
        dx = local_pos.x() - self.center_pt.x()
        dy = local_pos.y() - self.center_pt.y()
        sens = getattr(self, 'mouse_sens', 100) / 100.0
        self.current_mouse_pos = QPointF(self.center_pt.x() + dx * sens, self.center_pt.y() + dy * sens)
        dist = math.hypot(dx * sens, dy * sens)
        
        num_tools = len(self.tools)

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
            
    def execute_current(self):
        from PyQt6.QtGui import QCursor
        self.anim_timer.stop()
        if hasattr(QApplication.instance(), 'global_hook'):
            QApplication.instance().global_hook.set_constraint(None, None)
        
        while QApplication.overrideCursor():
            QApplication.restoreOverrideCursor()
        self.setCursor(Qt.CursorShape.ArrowCursor)
        
        # Interaction Shield: Block execution ONLY for the tool being adjusted
        if self.vol_opacity > 0.1 and self.active_index != -1:
            active_tool = self.tools[self.active_index]
            if active_tool['id'] == getattr(self, 'last_adjusted_id', None):
                self.hide()
                return
            
        if self.active_index != -1 and len(self.tools) > 0 and self.active_index < len(self.tools):
            cmd = self.tools[self.active_index]['id']
            self.command_triggered.emit(cmd)
            
        if self.original_cursor_pos:
            QCursor.setPos(self.original_cursor_pos)
        self.hide()

    def paintEvent(self, e):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.setRenderHint(QPainter.RenderHint.TextAntialiasing)
        p.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
        
        cx, cy = self.center_pt.x(), self.center_pt.y()
        
        # 0. Invisible shield to prevent Windows click-through on alpha=0 pixels
        p.setBrush(QColor(0, 0, 0, 1))
        p.setPen(Qt.PenStyle.NoPen)
        p.drawEllipse(self.center_pt, self.outer_radius, self.outer_radius)
        
        # Animation transforms for layer switching
        layer_anim = getattr(self, 'layer_anim_progress', 0.0)
        layer_dir = getattr(self, 'layer_anim_dir', 1)
        
        p.save()
        if layer_anim > 0.01:
            p.translate(cx, cy)
            p.rotate(layer_anim * layer_dir * -60)
            scale = 1.0 - (layer_anim * 0.15)
            p.scale(scale, scale)
            p.translate(-cx, -cy)
            p.setOpacity(max(0.0, 1.0 - (layer_anim * 1.5)))
            
        # 1. Background Ring (Large Hole Donut)
        bg_path = QPainterPath()
        bg_path.addEllipse(QPointF(self.center_pt), self.outer_radius, self.outer_radius)
        hole = QPainterPath()
        hole.addEllipse(QPointF(self.center_pt), self.inner_radius, self.inner_radius)
        
        opacity = getattr(self, 'opacity', 185)
        theme = getattr(self, 'theme', 'Dark')
        bg_r, bg_g, bg_b = (10, 10, 14) if theme == 'Dark' else (240, 240, 245)
        
        p.setBrush(QColor(bg_r, bg_g, bg_b, opacity))
        p.setPen(QPen(QColor(255,255,255,12), 1))
        p.drawPath(bg_path.subtracted(hole))

        num_tools = len(self.tools)
        angle_step = 360.0 / num_tools

        # 2. Draw Active Highlight smoothly
        for i in range(num_tools):
            prog = getattr(self, 'slice_progress', {}).get(i, 0.0)
            if prog > 0.01:
                path = QPainterPath()
                start_angle = 90 - (i * angle_step) + (angle_step / 2)
                span_angle = -angle_step
                r_outer = self.outer_radius + 4 * prog
                r_inner = self.inner_radius - 2 * prog
                path.arcMoveTo(QRectF(cx - r_outer, cy - r_outer, r_outer*2, r_outer*2), start_angle)
                path.arcTo(QRectF(cx - r_outer, cy - r_outer, r_outer*2, r_outer*2), start_angle, span_angle)
                path.arcTo(QRectF(cx - r_inner, cy - r_inner, r_inner*2, r_inner*2), start_angle + span_angle, -span_angle)
                path.closeSubpath()
                
                grad = QLinearGradient(cx, cy - r_outer, cx, cy + r_outer)
                grad.setColorAt(0, QColor(0, 240, 255, int(230 * prog)))
                grad.setColorAt(1, QColor(157, 0, 255, int(230 * prog)))
                p.setBrush(grad)
                p.setPen(QPen(QColor(255,255,255,int(100 * prog)), 1))
                p.drawPath(path)
                p.setPen(QPen(QColor(0, 240, 255, int(40 * prog)), 12))
                p.drawPath(path)
            
        # 3. Draw Icons smoothly
        for i in range(num_tools):
            prog = getattr(self, 'slice_progress', {}).get(i, 0.0)
            angle_rad = math.radians(i * angle_step)
            dist_ic = (self.inner_radius + self.outer_radius) / 2
            tx = cx + math.sin(angle_rad) * dist_ic
            ty = cy - math.cos(angle_rad) * dist_ic
            tool = self.tools[i]
            ic_col = "#ffffff" if prog > 0.5 else "#666666"
            pix_size = int(26 + 6 * prog)
            pix = VectorIcon.icon(tool['icon'], ic_col).pixmap(pix_size, pix_size)
            p.drawPixmap(int(tx - pix_size//2), int(ty - pix_size//2), pix)

        p.restore()
        
        # 4. Center HUD
        p.setBrush(QColor(255,255,255,5))
        p.setPen(QPen(QColor(255,255,255,10), 1))
        p.drawEllipse(self.center_pt, self.inner_radius - 12, self.inner_radius - 12)
        
        if self.active_index != -1 and self.active_index < num_tools:
            from utils import get_system_mute
            tool = self.tools[self.active_index]
            label = tool['label']
            if tool['id'] == "mute":
                label = "UNMUTE" if get_system_mute() else "MUTE"
            
            p.setPen(QColor(255,255,255))
            p.setFont(QFont("Segoe UI Variable Display", 18, QFont.Weight.Bold))
            p.drawText(QRectF(cx-100, cy-30, 200, 40), Qt.AlignmentFlag.AlignCenter, label.upper())
            p.setPen(QColor(255,255,255,100))
            p.setFont(QFont("Segoe UI Variable Display", 9))
            p.drawText(QRectF(cx-100, cy+10, 200, 20), Qt.AlignmentFlag.AlignCenter, "RELEASE TO EXECUTE")
        else:
            if hasattr(self, 'logo_renderer') and self.logo_renderer:
                logo_size = 55 # 50% of previous 110
                logo_rect = QRectF(cx - logo_size/2, cy - logo_size/2, logo_size, logo_size)
                self.logo_renderer.render(p, logo_rect)
            else:
                p.setPen(QColor(255,255,255,80))
                p.setFont(QFont("Segoe UI Variable Display", 12, QFont.Weight.Bold))
                p.drawText(QRectF(cx-100, cy-15, 200, 30), Qt.AlignmentFlag.AlignCenter, "PANDORA")
                
        # 4.5 Draw Layer Indicator Arc
        num_layers = len(getattr(self, 'menus', []))
        if num_layers > 1:
            ind_radius = self.inner_radius - 18
            ind_rect = QRectF(cx - ind_radius, cy - ind_radius, ind_radius*2, ind_radius*2)
            ind_angle_step = 360.0 / num_layers
            for i in range(num_layers):
                start_a = 90 - (i * ind_angle_step) + (ind_angle_step / 2)
                span_a = -ind_angle_step + min(8, 360 / num_layers * 0.2) # gap
                if i == getattr(self, 'layer_index', 0):
                    p.setPen(QPen(QColor(0, 240, 255, 255), 4, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
                else:
                    p.setPen(QPen(QColor(255, 255, 255, 40), 2, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
                p.drawArc(ind_rect, int(start_a * 16), int(span_a * 16))
                
        # 4.6 Draw Volume Ring
        if self.vol_opacity > 0.01:
            p.setOpacity(self.vol_opacity)
            v_radius = self.outer_radius + 12
            v_rect = QRectF(cx - v_radius, cy - v_radius, v_radius*2, v_radius*2)
            
            # Dynamic gap centered at 270
            start_v = 270 - (getattr(self, 'gap_size', 75) / 2.0)
            span_v = -(360 - getattr(self, 'gap_size', 75))
            
            # Draw track
            p.setPen(QPen(QColor(255, 255, 255, 20), 4, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
            p.drawArc(v_rect, int(start_v * 16), int(span_v * 16))
            
            # Active Arc
            from utils import DisplayEffectsEngine
            engine = DisplayEffectsEngine.instance()
            is_night_active = self.vol_opacity > 0.5 and "night" in getattr(self, 'vol_hud_dir', "")
            
            if is_night_active:
                vol_color = QColor(255, 150, 50, 200) # Warm Orange
                level = engine._current_intensity
            else:
                vol_color = QColor(0, 240, 255, 200) # System Cyan
                level = self.vol_level
            
            p.setPen(QPen(vol_color, 4, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
            p.drawArc(v_rect, int(start_v * 16), int(span_v * level * 16))
            p.setOpacity(1.0)
            
        # 4.7 Draw Battery Ring (when volume is not fully visible)
        if self.vol_opacity < 0.99:
            p.setOpacity(1.0 - self.vol_opacity)
            v_radius = self.outer_radius + 12
            v_rect = QRectF(cx - v_radius, cy - v_radius, v_radius*2, v_radius*2)
            
            # Same dynamic gap
            start_v = 270 - (getattr(self, 'gap_size', 75) / 2.0)
            span_v = -(360 - getattr(self, 'gap_size', 75))
            
            # Draw track (subtle)
            p.setPen(QPen(QColor(255, 255, 255, 10), 2, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
            p.drawArc(v_rect, int(start_v * 16), int(span_v * 16))
            
            # Draw level
            if self.batt_plugged:
                batt_color = QColor(0, 255, 150, 180) # Charging Cyan-Green
            else:
                if self.batt_level > 50:
                    batt_color = QColor(0, 255, 120, 150) # Healthy Green
                elif self.batt_level > 20:
                    batt_color = QColor(255, 200, 0, 150) # Warning Yellow
                else:
                    batt_color = QColor(255, 50, 50, 180) # Critical Red
                    
            p.setPen(QPen(batt_color, 3, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
            p.drawArc(v_rect, int(start_v * 16), int(span_v * (self.batt_level / 100.0) * 16))
            p.setOpacity(1.0)
            
        # 4.8 Draw HUD Icon & Text in the Gap
        hud_opacity = max(self.vol_opacity, 1.0 - self.vol_opacity)
        if hud_opacity > 0.01 and getattr(self, 'gap_size', 75) > 0:
            p.setOpacity(hud_opacity)
            is_vol = self.vol_opacity > 0.5
            is_night = is_vol and "night" in getattr(self, 'vol_hud_dir', "")
            
            if is_night:
                val_text = f"{int(self.vol_hud_val)}%"
                ic_name = "night"
                hud_col = QColor(255, 150, 50)
            elif is_vol:
                val_text = f"{int(self.vol_level * 100)}%"
                ic_name = "volume up" if getattr(self, 'vol_hud_dir', "up") == "up" else "volume down"
                hud_col = QColor(0, 240, 255)
            else:
                ic_name = "charging" if self.batt_plugged else "battery"
                hud_col = batt_color if not self.batt_plugged else QColor(0, 255, 150)
                val_text = f"{int(self.batt_level)}%"
            
            p.setFont(QFont("Segoe UI Variable Display", 10, QFont.Weight.Bold))
            tw = p.fontMetrics().horizontalAdvance(val_text)
            
            # Position at bottom
            tx, ty = cx, cy + self.outer_radius + 12
            
            pix = VectorIcon.icon(ic_name, hud_col.name()).pixmap(18, 18)
            p.drawPixmap(int(tx - tw/2 - 22), int(ty - 9), pix)
            p.setPen(hud_col)
            p.drawText(QRectF(tx - tw/2 + 2, ty - 10, tw + 10, 20), Qt.AlignmentFlag.AlignVCenter, val_text)
            p.setOpacity(1.0)
                
        # 5. Draw Custom Cursor Dot
        if hasattr(self, 'current_mouse_pos'):
            p.setBrush(QColor(255, 255, 255, 200))
            p.setPen(QPen(QColor(0, 240, 255, 100), 4))
            p.drawEllipse(self.current_mouse_pos, 5, 5)
