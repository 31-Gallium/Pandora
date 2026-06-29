import math
import os
from PyQt6.QtWidgets import QWidget, QApplication
from PyQt6.QtCore import Qt, QPoint, QRectF, QPropertyAnimation, QEasingCurve, pyqtSignal, QPointF, QTimer
from PyQt6.QtGui import QColor, QPainter, QPainterPath, QFont, QPen, QBrush, QLinearGradient
from utils import VectorIcon

class Halo(QWidget):
    command_triggered = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnTopHint | Qt.WindowType.Tool)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setMouseTracking(True)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        
        self.outer_radius = 290
        self.inner_radius = 150
        self.hub_radius = 60 
        self.setGeometry(QApplication.primaryScreen().geometry())
        
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
        
        self.layer_anim_progress = 0.0
        self.layer_anim_dir = 1
        self._override_tools = None
        self._prev_tools = []

        # Performance: Pre-calculate paths and pool resources
        self.bg_path = None
        self.inner_hud_path = None
        self._setup_resources()
        
        # Connect Media Manager
        from utils import MediaSessionManager
        self.media_mgr = MediaSessionManager.instance()
        self.media_mgr.media_changed.connect(self._on_media_update)
        
        from hub import HubManager
        self.hub_manager = HubManager(self)

    def _on_media_update(self, track_info):
        self.update()

    def _setup_resources(self):
        # Fonts
        self.font_main = QFont("Segoe UI Variable Display", 18, QFont.Weight.Bold)
        self.font_sub = QFont("Segoe UI Variable Display", 9)
        self.font_mini = QFont("Segoe UI Variable Display", 10, QFont.Weight.Bold)
        
        # Pens & Brushes
        self.pen_white_low = QPen(QColor(255,255,255,12), 1)
        self.pen_cyan_glow = QPen(QColor(0, 240, 255, 100), 4)
        self.brush_cursor = QBrush(QColor(255, 255, 255, 200))
        self.brush_hud_bg = QBrush(QColor(255,255,255,5))
        
    def _refresh_geometry(self):
        cx, cy = self.center_pt.x(), self.center_pt.y()
        # Pre-calculate background donut
        self.bg_path = QPainterPath()
        self.bg_path.addEllipse(QPointF(self.center_pt), self.outer_radius, self.outer_radius)
        hole = QPainterPath()
        hole.addEllipse(QPointF(self.center_pt), self.inner_radius, self.inner_radius)
        self.bg_path = self.bg_path.subtracted(hole)
        
        # Pre-calculate center HUD ring
        self.inner_hud_path = QPainterPath()
        self.inner_hud_path.addEllipse(QPointF(self.center_pt), self.inner_radius - 12, self.inner_radius - 12)
        
    def _hide_vol_hud(self):
        self.vol_target_opacity = 0.0
        

    @property
    def current_tools(self):
        return getattr(self, '_override_tools', None) or self.tools

    def set_override_tools(self, tools):
        self._prev_tools = self.current_tools.copy()
        self._override_tools = tools
        self.slice_progress = {}
        self.active_index = -1
        self.layer_anim_progress = 1.0
        self.layer_anim_dir = 1
        self.update()

    def clear_override_tools(self):
        self._prev_tools = self.current_tools.copy()
        self._override_tools = None
        self.slice_progress = {}
        self.active_index = -1
        self.layer_anim_progress = 1.0
        self.layer_anim_dir = -1
        self.update()

    def reload_tools(self, cfg):
        rad_cfg = cfg.get('halo', {})
        gen_cfg = cfg.get('general_settings', {})
        self.layer_anim_style = gen_cfg.get('layer_anim_style', 'Z-Depth + Spring')
        
        self.menus = rad_cfg.get('menus', [])
        if not hasattr(self, 'layer_index'): self.layer_index = 0
        if self.layer_index >= len(self.menus): self.layer_index = max(0, len(self.menus) - 1)
        if self.menus:
            self.tools = self.menus[self.layer_index].get('tools', [])
        else:
            self.tools = []
            
        if len(self.current_tools) == 0:
            self.tools = [{"id": "settings", "icon": "settings", "label": "Pandora"}]
            
        self.opacity = rad_cfg.get('opacity', 185)
        self.theme = rad_cfg.get('theme', 'Dark')
        
        # ── RATIO-BASED SIZING ENGINE ─────────────────────
        # 1. Total Menu Bound (Total Radius)
        self.max_bound = rad_cfg.get('max_bound', 300)
        
        # 2. Hub Ratio (Percentage of total radius)
        # Default to 20% if not set
        self.hub_ratio = rad_cfg.get('hub_ratio', 50)
        
        self.inner_radius = int(self.max_bound * (self.hub_ratio / 100.0))
        self.outer_radius = self.max_bound
        self.hub_radius = self.inner_radius
        
        self.scroll_sens = rad_cfg.get('scroll_sens', 50)
        self.mouse_sens = rad_cfg.get('mouse_sens', 100)
        self.gap_size = rad_cfg.get('gap_size', 75)
        
        self.setGeometry(QApplication.primaryScreen().geometry())
        self.center_pt = QPoint(self.width() // 2, self.height() // 2)
        
        if hasattr(self, 'hub_manager'):
            self.hub_manager.reload_config(cfg)
            
        self._refresh_geometry()
            
        self.update()
        
    def wheelEvent(self, e):
        self.handle_wheel(e.angleDelta().y())

    def handle_wheel(self, delta_y):
        hub_holding = False
        if hasattr(self, 'hub_manager'):
            mod = self.hub_manager.get_active_module()
            hub_holding = getattr(mod, '_holding', False)

        # 0. Hub Routing
        if hasattr(self, 'current_mouse_pos'):
            dx = self.current_mouse_pos.x() - self.center_pt.x()
            dy = self.current_mouse_pos.y() - self.center_pt.y()
            if math.hypot(dx, dy) < self.inner_radius or hub_holding:
                if hasattr(self, 'hub_manager'):
                    if self.hub_manager.handle_scroll(self.current_mouse_pos, delta_y):
                        return # Handled by Hub

        # 1. Volume override if hovering mute
        if self.active_index != -1 and self.active_index < len(self.current_tools):
            tool = self.current_tools[self.active_index]
            if tool['id'] == "mute":
                from utils import change_system_volume, get_system_volume_level
                delta = 0.02 if delta_y > 0 else -0.02
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
                delta = 0.05 if delta_y > 0 else -0.05
                
                # Only turn on if scrolling UP while off
                if not engine._is_enabled:
                    if delta > 0:
                        engine.set_enabled(True, instant=True)
                        engine.set_intensity(0.0)
                    else:
                        return # Ignore scroll down if already off
                
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
        delta = delta_y
        
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
            
        if steps != 0:
            self._cycle_layer(steps)

    def _cycle_layer(self, steps):
        if not hasattr(self, 'menus'): return

        valid_indices = [i for i, m in enumerate(self.menus) if m.get('tools')]
        if len(valid_indices) <= 1: return

        # Find current valid index
        curr_valid_idx = valid_indices.index(self.layer_index) if self.layer_index in valid_indices else 0

        self.layer_anim_dir = 1 if steps > 0 else -1
        self.layer_anim_progress = 1.0
        
        self._prev_layer_index = getattr(self, 'layer_index', 0)

        next_valid_idx = (curr_valid_idx + steps) % len(valid_indices)
        self.layer_index = valid_indices[next_valid_idx]

        self.tools = self.menus[self.layer_index].get('tools', [])

        self.slice_progress = {} # reset anims
        self.active_index = -1
        
        # Clear any holding state in modules when cycling
        if hasattr(self, 'hub_manager'):
            for mod in self.hub_manager.modules.values():
                if hasattr(mod, '_holding'):
                    mod._holding = False
            self.clear_override_tools()
            
        self.update()
    def mousePressEvent(self, e):
        e.accept() # Capture the press to prevent it from reaching the background
        
        hub_holding = False
        if hasattr(self, 'hub_manager'):
            mod = self.hub_manager.get_active_module()
            hub_holding = getattr(mod, '_holding', False)
        
        # Route to Hub if mouse is inside inner radius or hub is holding
        if hasattr(self, 'current_mouse_pos'):
            dx = self.current_mouse_pos.x() - self.center_pt.x()
            dy = self.current_mouse_pos.y() - self.center_pt.y()
            if math.hypot(dx, dy) < self.inner_radius or hub_holding:
                if hasattr(self, 'hub_manager'):
                    self.hub_manager.handle_press(self.current_mouse_pos, e.button())
                    return
        
        if math.hypot(dx, dy) > self.outer_radius + 20:
            self.execute_current()
            return
        if e.button() == Qt.MouseButton.XButton1:
            self._cycle_layer(-1)
        elif e.button() == Qt.MouseButton.XButton2:
            self._cycle_layer(1)

    def mouseReleaseEvent(self, e):
        e.accept() # Capture the release to ensure no 'leakage' to background apps
        
        hub_holding = False
        if hasattr(self, 'hub_manager'):
            mod = self.hub_manager.get_active_module()
            hub_holding = getattr(mod, '_holding', False)

        # Route to Hub if mouse is inside inner radius OR if hub is currently holding
        if hasattr(self, 'current_mouse_pos'):
            dx = self.current_mouse_pos.x() - self.center_pt.x()
            dy = self.current_mouse_pos.y() - self.center_pt.y()
            if math.hypot(dx, dy) < self.inner_radius or hub_holding:
                if hasattr(self, 'hub_manager'):
                    self.hub_manager.handle_release(self.current_mouse_pos, e.button())
                    if hub_holding:
                        return
                    return
                    
        if e.button() == Qt.MouseButton.LeftButton:
            # Only trigger if the release happens within the menu boundaries
            self.execute_current()
        elif e.button() == Qt.MouseButton.RightButton:
            self.active_index = -1 # Safe Abort
            self.execute_current()
        
    def _anim_loop(self):
        changed = False
        
        layer_anim = getattr(self, "layer_anim_progress", 0.0)
        if getattr(self, "closing", False):
            self.fade_progress = max(0.0, getattr(self, "fade_progress", 1.0) - 0.15)
            if self.fade_progress <= 0.01:
                self.hide()
                self.closing = False
                return
            changed = True
        else:
            if getattr(self, "fade_progress", 0.0) < 1.0:
                self.fade_progress = min(1.0, getattr(self, "fade_progress", 0.0) + 0.15)
                changed = True
        if layer_anim > 0.01:
            self.layer_anim_progress = layer_anim * 0.8
            changed = True
        elif layer_anim > 0:
            self.layer_anim_progress = 0.0
            changed = True
            
        num_tools = len(self.current_tools)
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

        if changed or self.isVisible():
            self.update()
    def show_center(self):
        from PyQt6.QtGui import QCursor, QGuiApplication
        screen = QGuiApplication.primaryScreen().geometry()
        pos = screen.center()
        self.original_cursor_pos = QCursor.pos()
        self.setGeometry(screen)
        
        QCursor.setPos(pos.x(), pos.y())
        self.anim_timer.start(16) # ~60 FPS
        self.current_mouse_pos = self.center_pt
        self.slice_progress = {}
        self.clear_override_tools()
        
        QApplication.setOverrideCursor(Qt.CursorShape.BlankCursor)
        self.setCursor(Qt.CursorShape.BlankCursor)
        
        from utils import get_system_volume_level, get_battery_info
        self.vol_level = get_system_volume_level()
        self.batt_level, self.batt_plugged = get_battery_info()
        self.vol_opacity = 0.0
        self.vol_target_opacity = 0.0

        if hasattr(QApplication.instance(), 'global_hook'):
            QApplication.instance().global_hook.set_constraint(pos, self.outer_radius - 2)

        self.active_index = -1
        self.closing = False
        self.fade_progress = 0.0
        self.show()
        
    def update_mouse(self, global_pos):
        local_pos = self.mapFromGlobal(global_pos)
        dx = local_pos.x() - self.center_pt.x()
        dy = local_pos.y() - self.center_pt.y()
        sens = getattr(self, 'mouse_sens', 100) / 100.0
        self.current_mouse_pos = QPointF(self.center_pt.x() + dx * sens, self.center_pt.y() + dy * sens)
        dist = math.hypot(dx * sens, dy * sens)
        
        num_tools = len(self.current_tools)

        if dist < self.inner_radius:
            new_idx = -1
            if hasattr(self, 'hub_manager'):
                self.hub_manager.handle_mouse_move(self.current_mouse_pos)
        else:
            if hasattr(self, 'hub_manager'):
                self.hub_manager.handle_mouse_leave()
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
            active_tool = self.current_tools[self.active_index]
            if active_tool['id'] == getattr(self, 'last_adjusted_id', None):
                self.closing = True
                self.anim_timer.start(16)
                return
            
        hub_holding = False
        if hasattr(self, 'hub_manager'):
            mod = self.hub_manager.get_active_module()
            if getattr(mod, '_holding', False):
                hub_holding = True
                mod._holding = False
                self.clear_override_tools()
                
        if not hub_holding:
            if self.active_index != -1 and len(self.current_tools) > 0 and self.active_index < len(self.current_tools):
                cmd = self.current_tools[self.active_index]['id']
                self.command_triggered.emit(cmd)
            
        if self.original_cursor_pos:
            QCursor.setPos(self.original_cursor_pos)
        self.closing = True
        self.anim_timer.start(16)

    def paintEvent(self, e):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.setRenderHint(QPainter.RenderHint.TextAntialiasing)
        p.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
        
        cx, cy = self.center_pt.x(), self.center_pt.y()
        
        # 0. Translucent full-screen background
        fade = getattr(self, "fade_progress", 0.0)
        if fade > 0.01:
            p.fillRect(self.rect(), QColor(0, 0, 0, int(180 * fade)))
        # Invisible shield for center
        p.setBrush(QColor(0, 0, 0, 1))
        p.setPen(Qt.PenStyle.NoPen)
        p.drawEllipse(self.center_pt, self.outer_radius, self.outer_radius)
        
        # Animation transforms for layer switching
        layer_anim = getattr(self, "layer_anim_progress", 0.0)
        if getattr(self, "closing", False):
            self.fade_progress = max(0.0, getattr(self, "fade_progress", 1.0) - 0.15)
            if self.fade_progress <= 0.01:
                self.hide()
                self.closing = False
                return
            changed = True
        else:
            if getattr(self, "fade_progress", 0.0) < 1.0:
                self.fade_progress = min(1.0, getattr(self, "fade_progress", 0.0) + 0.15)
                changed = True
        layer_dir = getattr(self, 'layer_anim_dir', 1)
        
        # Calculate eased progress (0.0 to 1.0)
        progress_t = 1.0 - layer_anim
        # Fast deceleration easing (Cubic Out)
        eased_t = 1.0 - (1.0 - progress_t) ** 3
        
        p.save()
        if layer_anim > 0.01:
            p.translate(cx, cy)
            # Spin 180 degrees with easing
            p.rotate((1.0 - eased_t) * layer_dir * -180)
            
            p.translate(-cx, -cy)
            
        # 1. Background Ring (Pre-calculated Donut)
        if not self.bg_path: self._refresh_geometry()
        
        opacity = getattr(self, 'opacity', 185)
        theme = getattr(self, 'theme', 'Dark')
        bg_r, bg_g, bg_b = (10, 10, 14) if theme == 'Dark' else (240, 240, 245)
        
        p.setBrush(QColor(bg_r, bg_g, bg_b, opacity))
        p.setPen(self.pen_white_low)
        p.drawPath(self.bg_path)

        num_tools = len(self.current_tools)
        angle_step = 360.0 / num_tools

        # 2. Draw Active Highlight smoothly (Disable during transitions for cleaner look)
        if getattr(self, 'layer_anim_progress', 0.0) < 0.01:
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
            
        # 3. Draw Icons smoothly (With smooth joint rotation)
        def draw_toolset(tools, offset_angle, opacity, is_outgoing=False):
            if not tools: return
            num = len(tools)
            if num == 0: return
            step = 360.0 / num
            for i in range(num):
                prog = getattr(self, 'slice_progress', {}).get(i, 0.0) if opacity > 0.8 else 0.0
                
                angle_deg = i * step + offset_angle
                angle_rad = math.radians(angle_deg)
                
                dist_ic = (self.inner_radius + self.outer_radius) / 2

                # If animating, give icons a little trailing rotation
                if layer_anim > 0.01:
                    # Incoming tools start further back, outgoing tools push forward
                    trail_offset = (1.0 - eased_t) * layer_dir * (-45 if is_outgoing else 45)
                    angle_rad += math.radians(trail_offset)

                tx = cx + math.sin(angle_rad) * dist_ic
                ty = cy - math.cos(angle_rad) * dist_ic
                
                tool = tools[i]
                ic_col = "#ffffff" if prog > 0.5 else "#666666"
                pix_size = int(26 + 6 * prog)
                if pix_size > 0:
                    if tool['id'].startswith('stopwatch_lap_'):
                        p.save()
                        p.setOpacity(opacity)
                        parts = tool['id'].split('_')
                        lap_num = int(parts[2])
                        lap_time_val = float(parts[3])
                        
                        lm, ls = divmod(int(lap_time_val), 60)
                        lms = int((lap_time_val - int(lap_time_val)) * 100)
                        time_str = f"{lm:02}:{ls:02}.{lms:02}"
                        
                        theme = getattr(self, 'theme', 'Dark')
                        is_dark = (theme == 'Dark')
                        
                        if prog > 0.5:
                            # Sleek, highly visible dark charcoal text on bright hover gradient
                            text_color = QColor(15, 15, 22)
                            idx_color = QColor(15, 15, 22)
                        else:
                            if is_dark:
                                text_color = QColor(0, 240, 255, 180)
                                idx_color = QColor(255, 255, 255, 120)
                            else:
                                text_color = QColor(0, 180, 200, 180)
                                idx_color = QColor(20, 20, 25, 120)
                        
                        p.setPen(idx_color)
                        p.setFont(QFont("Segoe UI Variable Display", 8, QFont.Weight.Bold))
                        p.drawText(QRectF(tx - 40, ty - 14, 80, 14), Qt.AlignmentFlag.AlignCenter, f"LAP {lap_num}")
                        
                        p.setPen(text_color)
                        p.setFont(QFont("Segoe UI Variable Display", 9, QFont.Weight.DemiBold))
                        p.drawText(QRectF(tx - 40, ty, 80, 14), Qt.AlignmentFlag.AlignCenter, time_str)
                        p.restore()
                    elif tool['id'].startswith('stopwatch_empty'):
                        p.save()
                        p.setOpacity(opacity)
                        theme = getattr(self, 'theme', 'Dark')
                        is_dark = (theme == 'Dark')
                        if prog > 0.5:
                            empty_col = QColor(15, 15, 22, 100) # Subtle dark charcoal on bright background
                        else:
                            empty_col = QColor(255, 255, 255, 40) if is_dark else QColor(20, 20, 25, 40)
                        p.setPen(empty_col)
                        p.setFont(QFont("Segoe UI Variable Display", 8, QFont.Weight.Bold))
                        p.drawText(QRectF(tx - 40, ty - 14, 80, 14), Qt.AlignmentFlag.AlignCenter, "--")
                        p.setFont(QFont("Segoe UI Variable Display", 9, QFont.Weight.DemiBold))
                        p.drawText(QRectF(tx - 40, ty, 80, 14), Qt.AlignmentFlag.AlignCenter, "--:--.--")
                        p.restore()
                    elif tool['id'].startswith('timer_preset_'):
                        p.save()
                        p.setOpacity(opacity)
                        parts = tool['id'].split('_')
                        seconds = int(parts[2])
                        minutes = seconds // 60
                        
                        theme = getattr(self, 'theme', 'Dark')
                        is_dark = (theme == 'Dark')
                        
                        if prog > 0.5:
                            text_color = QColor(15, 15, 22)
                            idx_color = QColor(15, 15, 22)
                        else:
                            if is_dark:
                                text_color = QColor(0, 240, 255, 180)
                                idx_color = QColor(255, 255, 255, 120)
                            else:
                                text_color = QColor(0, 180, 200, 180)
                                idx_color = QColor(20, 20, 25, 120)
                        
                        p.setPen(idx_color)
                        p.setFont(QFont("Segoe UI Variable Display", 8, QFont.Weight.Bold))
                        p.drawText(QRectF(tx - 40, ty - 14, 80, 14), Qt.AlignmentFlag.AlignCenter, "PRESET")
                        
                        p.setPen(text_color)
                        p.setFont(QFont("Segoe UI Variable Display", 11, QFont.Weight.Bold))
                        p.drawText(QRectF(tx - 40, ty, 80, 14), Qt.AlignmentFlag.AlignCenter, f"{minutes} MIN")
                        p.restore()
                    elif tool['id'].startswith('world_tz_') and tool['id'] != "world_tz_none":
                        p.save()
                        p.setOpacity(opacity)
                        
                        tz = tool.get('tz', '')
                        label = tool.get('label', '')
                        
                        from zoneinfo import ZoneInfo
                        from datetime import datetime
                        try:
                            now_tz = datetime.now(ZoneInfo(tz))
                        except Exception:
                            # Robust fallback for Windows without IANA tz database
                            from datetime import timezone, timedelta
                            offsets = {
                                "Africa/Cairo": 2.0, "Africa/Johannesburg": 2.0, "Africa/Lagos": 1.0, "Africa/Nairobi": 3.0,
                                "America/Anchorage": -9.0, "America/Argentina/Buenos_Aires": -3.0, "America/Bogota": -5.0,
                                "America/Caracas": -4.0, "America/Chicago": -6.0, "America/Denver": -7.0, "America/Halifax": -4.0,
                                "America/Los_Angeles": -8.0, "America/Mexico_City": -6.0, "America/New_York": -5.0,
                                "America/Phoenix": -7.0, "America/Santiago": -4.0, "America/Sao_Paulo": -3.0, "America/St_Johns": -3.5,
                                "Asia/Almaty": 6.0, "Asia/Baghdad": 3.0, "Asia/Bangkok": 7.0, "Asia/Colombo": 5.5,
                                "Asia/Dhaka": 6.0, "Asia/Dubai": 4.0, "Asia/Hong_Kong": 8.0, "Asia/Jakarta": 7.0,
                                "Asia/Jerusalem": 2.0, "Asia/Kabul": 4.5, "Asia/Karachi": 5.0, "Asia/Kathmandu": 5.75,
                                "Asia/Kolkata": 5.5, "Asia/Kuala_Lumpur": 8.0, "Asia/Manila": 8.0, "Asia/Riyadh": 3.0,
                                "Asia/Seoul": 9.0, "Asia/Shanghai": 8.0, "Asia/Singapore": 8.0, "Asia/Taipei": 8.0,
                                "Asia/Tashkent": 5.0, "Asia/Tbilisi": 4.0, "Asia/Tehran": 3.5, "Asia/Tokyo": 9.0,
                                "Atlantic/Azores": -1.0, "Atlantic/Cape_Verde": -1.0, "Australia/Adelaide": 9.5,
                                "Australia/Brisbane": 10.0, "Australia/Darwin": 9.5, "Australia/Hobart": 10.0,
                                "Australia/Melbourne": 10.0, "Australia/Perth": 8.0, "Australia/Sydney": 10.0,
                                "Europe/Amsterdam": 1.0, "Europe/Athens": 2.0, "Europe/Berlin": 1.0, "Europe/Brussels": 1.0,
                                "Europe/Budapest": 1.0, "Europe/Copenhagen": 1.0, "Europe/Dublin": 0.0, "Europe/Helsinki": 2.0,
                                "Europe/Istanbul": 3.0, "Europe/Lisbon": 0.0, "Europe/London": 0.0, "Europe/Madrid": 1.0,
                                "Europe/Moscow": 3.0, "Europe/Paris": 1.0, "Europe/Prague": 1.0, "Europe/Rome": 1.0,
                                "Europe/Stockholm": 1.0, "Europe/Vienna": 1.0, "Europe/Warsaw": 1.0, "Europe/Zurich": 1.0,
                                "Pacific/Auckland": 12.0, "Pacific/Chatham": 12.75, "Pacific/Fiji": 12.0, "Pacific/Guadalcanal": 11.0,
                                "Pacific/Honolulu": -10.0, "Pacific/Kiritimati": 14.0, "Pacific/Noumea": 11.0, "Pacific/Pago_Pago": -11.0
                            }
                            offset = offsets.get(tz, 0.0)
                            now_tz = datetime.now(timezone.utc) + timedelta(hours=offset)
                            
                        # Use elegant 12-hour format for maximum readability
                        time_str = now_tz.strftime("%I:%M %p")
                        
                        theme = getattr(self, 'theme', 'Dark')
                        is_dark = (theme == 'Dark')
                        
                        if prog > 0.5:
                            text_color = QColor(15, 15, 22)
                            idx_color = QColor(15, 15, 22)
                        else:
                            if is_dark:
                                text_color = QColor(0, 240, 255, 180)
                                idx_color = QColor(255, 255, 255, 120)
                            else:
                                text_color = QColor(0, 180, 200, 180)
                                idx_color = QColor(20, 20, 25, 120)
                        
                        p.setPen(idx_color)
                        p.setFont(QFont("Segoe UI Variable Display", 8, QFont.Weight.Bold))
                        p.drawText(QRectF(tx - 40, ty - 14, 80, 14), Qt.AlignmentFlag.AlignCenter, label.upper())
                        
                        p.setPen(text_color)
                        p.setFont(QFont("Segoe UI Variable Display", 10, QFont.Weight.Bold))
                        p.drawText(QRectF(tx - 40, ty, 80, 14), Qt.AlignmentFlag.AlignCenter, time_str)
                        p.restore()
                    else:
                        ic_col_final = "#0f0f16" if prog > 0.5 else ("#d0d0d0" if getattr(self, 'theme', 'Dark') == 'Dark' else "#333333")
                        pix = VectorIcon.pixmap(tool['icon'], ic_col_final, pix_size)
                        
                        p.setOpacity(opacity)
                        if prog < 0.5:
                            # Subtle dark circle behind icon for contrast against album art
                            p.setBrush(QColor(0, 0, 0, 100))
                            p.setPen(Qt.PenStyle.NoPen)
                            p.drawEllipse(int(tx - pix_size//2 - 4), int(ty - pix_size//2 - 4), pix_size + 8, pix_size + 8)
                        
                        p.drawPixmap(int(tx - pix_size//2), int(ty - pix_size//2), pix)

        p.save()
        if layer_anim > 0.01:
            # Crossfade during spin
            draw_toolset(self._prev_tools, 0, layer_anim, is_outgoing=True)
            draw_toolset(self.current_tools, 0, progress_t, is_outgoing=False)
        else:
            draw_toolset(self.current_tools, 0, 1.0, False)
        p.setOpacity(1.0)
        p.restore()
        
        # Restore the main painter context to stop the rotation from affecting UI overlays
        p.restore()

        # 4. Center HUD (with premium, solid high-visibility background matching active theme)
        hud_bg_opacity = 255
        p.setBrush(QColor(bg_r, bg_g, bg_b, hud_bg_opacity))
        p.setPen(QPen(QColor(255, 255, 255, 15) if theme == 'Dark' else QColor(0, 0, 0, 15), 1))
        p.drawPath(self.inner_hud_path)
        
        # Check if Hub is in a 'Holding' state (Control Mode)
        hub_holding = False
        if hasattr(self, 'hub_manager'):
            mod = self.hub_manager.get_active_module()
            hub_holding = getattr(mod, '_holding', False)

        if self.active_index != -1 and self.active_index < num_tools and not hub_holding:
            from utils import get_system_mute
            tool = self.current_tools[self.active_index]
            label = tool['label']
            if tool['id'] == "mute":
                label = "UNMUTE" if get_system_mute() else "MUTE"
            
            p.setPen(QColor(255,255,255))
            p.setFont(self.font_main)
            p.drawText(QRectF(cx-100, cy-30, 200, 40), Qt.AlignmentFlag.AlignCenter, label.upper())
            p.setPen(QColor(255,255,255,100))
            p.setFont(self.font_sub)
            sub_label = "SCROLL TO ADJUST" if tool['id'] in ['volume', 'timeline'] else "RELEASE TO EXECUTE"
            p.drawText(QRectF(cx-100, cy+10, 200, 20), Qt.AlignmentFlag.AlignCenter, sub_label)
        else:
            if hasattr(self, 'hub_manager'):
                self.hub_manager.draw_active(p, cx, cy, self.inner_radius)
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
        menus = getattr(self, 'menus', [])
        valid_indices = [i for i, m in enumerate(menus) if m.get('tools')]
        num_layers = len(valid_indices)
        
        if num_layers > 1:
            ind_radius = self.inner_radius - 18
            ind_rect = QRectF(cx - ind_radius, cy - ind_radius, ind_radius*2, ind_radius*2)
            ind_angle_step = 360.0 / num_layers
            for display_idx, actual_idx in enumerate(valid_indices):
                start_a = 90 - (display_idx * ind_angle_step) + (ind_angle_step / 2)
                span_a = -ind_angle_step + min(8, 360 / num_layers * 0.2) # gap
                if actual_idx == getattr(self, 'layer_index', 0):
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
            
            p.setFont(self.font_mini)
            tw = p.fontMetrics().horizontalAdvance(val_text)
            
            # Position at bottom
            tx, ty = cx, cy + self.outer_radius + 12
            
            pix = VectorIcon.pixmap(ic_name, hud_col.name(), 18)
            p.drawPixmap(int(tx - tw/2 - 22), int(ty - 9), pix)
            p.setPen(hud_col)
            p.drawText(QRectF(tx - tw/2 + 2, ty - 10, tw + 10, 20), Qt.AlignmentFlag.AlignVCenter, val_text)
            p.setOpacity(1.0)
                
        # 5. Draw Custom Cursor Dot
        if hasattr(self, 'current_mouse_pos'):
            p.setBrush(self.brush_cursor)
            p.setPen(self.pen_cyan_glow)
            p.drawEllipse(self.current_mouse_pos, 5, 5)

    def keyPressEvent(self, event):
        if hasattr(self, 'hub_manager'):
            if self.hub_manager.handle_key_press(event):
                return
        super().keyPressEvent(event)

    def keyReleaseEvent(self, event):
        if hasattr(self, 'hub_manager'):
            if self.hub_manager.handle_key_release(event):
                return
        super().keyReleaseEvent(event)

    def hideEvent(self, event):
        self.anim_timer.stop()
        if hasattr(QApplication.instance(), 'global_hook'):
            QApplication.instance().global_hook.set_constraint(None, None)
        while QApplication.overrideCursor():
            QApplication.restoreOverrideCursor()
        self.setCursor(Qt.CursorShape.ArrowCursor)

        if hasattr(self, 'hub_manager'):
            for mod in [self.hub_manager.media_hub, self.hub_manager.time_hub]:
                if hasattr(mod, 'cleanup'):
                    mod.cleanup()
        super().hideEvent(event)

