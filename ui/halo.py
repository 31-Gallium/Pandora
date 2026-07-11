import math
import os
import time
from PyQt6.QtWidgets import QWidget, QApplication
from PyQt6.QtCore import Qt, QPoint, QRectF, QPropertyAnimation, QEasingCurve, pyqtSignal, QPointF, QTimer
from PyQt6.QtGui import QColor, QPainter, QPainterPath, QFont, QPen, QBrush, QLinearGradient, QConicalGradient, QPixmap, QImage
from utils import VectorIcon, IconExtractor

def elide_text_to_lines(font_metrics, text, max_width, max_lines=2):
    if font_metrics.horizontalAdvance(text) <= max_width:
        return text

    words = text.split(' ')
    lines = []
    current_line = ""
    
    for i, word in enumerate(words):
        test_line = (current_line + " " + word).strip()
        if font_metrics.horizontalAdvance(test_line) <= max_width:
            current_line = test_line
        else:
            if current_line:
                lines.append(current_line)
            current_line = word
            
            if len(lines) == max_lines - 1:
                remaining_text = " ".join(words[i:]).strip()
                elided = font_metrics.elidedText(remaining_text, Qt.TextElideMode.ElideRight, max_width)
                lines.append(elided)
                current_line = ""
                break
                
    if current_line:
        lines.append(current_line)
        
    return "\n".join(lines[:max_lines])

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
        self.setGeometry(QApplication.primaryScreen().availableGeometry())
        self.setWindowOpacity(0.0)
        
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
        self.last_global_mouse_pos = None
        
        self.batt_level = 100
        self.batt_plugged = True
        self.vol_level = 0.5
        
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

        # Blurred background capture
        self._bg_blur_pixmap = None

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
        
        # Force square corners on Windows 11 to stop the desktop from peeking through
        try:
            import ctypes
            dwmapi = ctypes.windll.dwmapi
            corner_pref = ctypes.c_int(1) # DWMWCP_DONOTROUND
            dwmapi.DwmSetWindowAttribute(int(self.winId()), 33, ctypes.byref(corner_pref), 4)
        except: pass
        
        self._enable_windows_blur()

    def _enable_windows_blur(self):
        try:
            import ctypes
            from ctypes import c_int, c_uint, Structure, POINTER, pointer, sizeof

            # 1. Extend the frame into the client area for frameless window support
            class MARGINS(Structure):
                _fields_ = [
                    ("cxLeftWidth", c_int),
                    ("cxRightWidth", c_int),
                    ("cyTopHeight", c_int),
                    ("cyBottomHeight", c_int)
                ]
            margins = MARGINS(-1, -1, -1, -1)
            ctypes.windll.dwmapi.DwmExtendFrameIntoClientArea(int(self.winId()), pointer(margins))

            # 2. Call SetWindowCompositionAttribute based on blur level setting
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

            blur_level = getattr(self, 'blur_level', 'High')

            policy = ACCENTPOLICY()
            policy.AccentState = 4  # ACCENT_ENABLE_ACRYLICBLURBEHIND (modern Windows 11 Acrylic)
            
            if blur_level == 'Low':
                # Window 3: tinted gray, AccentFlags = 0x1E0, GradientColor = 0x30555555
                policy.AccentFlags = 0x1E0
                policy.GradientColor = 0x30555555
            elif blur_level == 'Medium':
                # Window 2: very transparent, AccentFlags = 0x1E0, GradientColor = 0x01000000
                policy.AccentFlags = 0x1E0
                policy.GradientColor = 0x01000000
            else:  # High
                # Window 4: maximum transparency, AccentFlags = 0, GradientColor = 0x01000000
                policy.AccentFlags = 0
                policy.GradientColor = 0x01000000
                
            policy.AnimationId = 0

            data = WINDOWCOMPOSITIONATTRIBDATA()
            data.Attribute = 19  # WCA_ACCENT_POLICY
            data.Data = pointer(policy)
            data.SizeOfData = sizeof(policy)

            ctypes.windll.user32.SetWindowCompositionAttribute(int(self.winId()), pointer(data))
        except Exception as e:
            from config import logger
            logger.error(f"Failed to enable Windows blur: {e}")
        self._bg_blur_pixmap = None

    def _on_media_update(self, track_info):
        self.update()

    def _setup_resources(self):
        # Fonts
        self.font_main = QFont("Segoe UI Variable Display", 18, QFont.Weight.Bold)
        self.font_sub = QFont("Segoe UI Variable Display", 9)
        self.font_mini = QFont("Segoe UI Variable Display", 10, QFont.Weight.Bold)
        
        # Prewarm fonts
        try:
            from PyQt6.QtGui import QPixmap, QPainter
            dummy_pix = QPixmap(10, 10)
            dp = QPainter(dummy_pix)
            dp.setFont(self.font_main)
            dp.drawText(0, 0, "PREWARM")
            dp.setFont(self.font_sub)
            dp.drawText(0, 0, "PREWARM")
            dp.setFont(self.font_mini)
            dp.drawText(0, 0, "PREWARM")
            dp.setFont(QFont("Segoe UI Variable Display", 12, QFont.Weight.Bold))
            dp.drawText(0, 0, "PREWARM")
            dp.setFont(QFont("Segoe UI Variable Display", 8, QFont.Weight.Bold))
            dp.drawText(0, 0, "PREWARM")
            dp.setFont(QFont("Segoe UI Variable Display", 11, QFont.Weight.Bold))
            dp.drawText(0, 0, "PREWARM")
            dp.end()
        except: pass
        
        # Pens & Brushes
        self.pen_white_low = QPen(QColor(255,255,255,12), 1)
        self.pen_cyan_glow = QPen(QColor(0, 240, 255, 100), 4)
        self.brush_cursor = QBrush(QColor(255, 255, 255, 200))
        self.brush_hud_bg = QBrush(QColor(255,255,255,5))

    def _create_custom_cursor(self):
        from PyQt6.QtGui import QPixmap, QCursor
        pixmap = QPixmap(16, 16)
        pixmap.fill(Qt.GlobalColor.transparent)
        p = QPainter(pixmap)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.setPen(QPen(QColor(0, 240, 255, 100), 4))
        p.setBrush(QColor(255, 255, 255, 200))
        p.drawEllipse(QPointF(8.0, 8.0), 4.5, 4.5)
        p.end()
        return QCursor(pixmap, 8, 8)
        
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
        from utils import VectorIcon
        for t in tools:
            VectorIcon.pixmap(t.get('icon', ''), "#ffffff", 32)
            
        self._prev_tools = self.current_tools.copy()
        self._override_tools = tools
        self.slice_progress = {}
        self.active_index = -1
        self.layer_anim_progress = 1.0
        self.layer_anim_dir = 1
        self.update()

    def clear_override_tools(self, instant=False):
        if getattr(self, '_override_tools', None) is None: return
        self._prev_tools = self.current_tools.copy()
        self._override_tools = None
        self.slice_progress = {}
        self.active_index = -1
        if hasattr(self, 'vol_target_opacity') and self.vol_target_opacity > 0.0:
            self._hide_vol_hud()
        if instant:
            self.layer_anim_progress = 0.0
            self._prev_tools = self.tools.copy()
        else:
            self.layer_anim_progress = 1.0
            self.layer_anim_dir = -1
        self.update()

    def reload_tools(self, cfg):
        rad_cfg = cfg.get('halo', {})
        gen_cfg = cfg.get('general_settings', {})
        self.layer_anim_style = gen_cfg.get('layer_anim_style', 'Z-Depth + Spring')
        
        self.menus = rad_cfg.get('menus', [])
        self.show_arc_hud = rad_cfg.get('show_arc_hud', True)
        self.blend_app_icons = rad_cfg.get('blend_app_icons', False)
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
        self.blur_level = rad_cfg.get('blur_level', 'High')
        self.brightness = rad_cfg.get('brightness', 50)
        self._enable_windows_blur()
        
        for menu in self.menus:
            for t in menu.get('tools', []):
                tid = t.get('id', '')
                is_path = tid and (('/' in tid) or ('\\' in tid) or (':' in tid))
                if is_path:
                    IconExtractor.get_icon_pixmap(tid, 32)
                else:
                    VectorIcon.pixmap(t.get('icon', ''), "#ffffff", 32)
        
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
        
        self.setGeometry(QApplication.primaryScreen().availableGeometry())
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
            tid = tool.get('id', '').strip().lower()
            if tid == 'mute':
                from utils import change_system_volume, get_system_volume_level
                delta = 0.02 if delta_y > 0 else -0.02
                change_system_volume(delta)
                self.vol_level = get_system_volume_level()
                self.vol_target_opacity = 1.0; self.vol_opacity = 1.0
                self.vol_hud_val = int(self.vol_level * 100)
                self.vol_hud_dir = 'up' if delta > 0 else 'down'
                self.last_adjusted_id = tool['id']
                self.has_scrolled = True
                self.vol_fade_timer.stop() # Keep visible while hovering
                self.update(); return
            elif tid in ['night', 'night light']:
                try:
                    from utils import DisplayEffectsEngine
                    engine = DisplayEffectsEngine.instance()
                    delta = 0.05 if delta_y > 0 else -0.05
                    
                    if not engine._is_enabled:
                        if delta > 0:
                            engine.set_enabled(True, instant=True)
                            engine.set_intensity(0.0)
                        else:
                            return
                    
                    new_val = max(0.0, min(1.0, engine._target_intensity + delta))
                    
                    if new_val <= 0.001 and delta < 0:
                        engine.set_enabled(False)
                        self.vol_level = 0.0
                        self.vol_hud_val = 0
                        self.vol_hud_dir = 'night_down'
                        self.vol_target_opacity = 1.0; self.vol_opacity = 1.0
                        self.last_adjusted_id = tool['id']
                        self.has_scrolled = True
                        self.vol_fade_timer.stop()
                    else:
                        engine.set_intensity(new_val)
                        self.vol_level = new_val
                        self.vol_target_opacity = 1.0; self.vol_opacity = 1.0
                        self.vol_hud_val = int(new_val * 100)
                        self.vol_hud_dir = 'night_up' if delta > 0 else 'night_down'
                        self.last_adjusted_id = tool['id']
                        self.has_scrolled = True
                        self.vol_fade_timer.stop() # Keep visible while hovering
                    
                    self.update(); return
                except Exception as e:
                    import traceback
                    with open('scroll_debug.txt', 'a') as df:
                        df.write('Error in night light: ' + str(e) + '\n')
                    return
            elif tid == 'brightness':
                from utils import change_system_brightness
                delta = 0.05 if delta_y > 0 else -0.05
                new_val = change_system_brightness(delta)
                if new_val is not False:
                    self.vol_level = new_val
                    self.vol_target_opacity = 1.0; self.vol_opacity = 1.0
                    self.vol_hud_val = int(new_val * 100)
                    self.vol_hud_dir = 'brightness_up' if delta > 0 else 'brightness_down'
                    self.last_adjusted_id = tool['id']
                    self.has_scrolled = True
                    self.vol_fade_timer.stop()
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

        valid_indices = [i for i, m in enumerate(self.menus) if any(t.get('id') for t in m.get('tools', []))]
        if len(valid_indices) <= 1: return

        # Find current valid index
        curr_valid_idx = valid_indices.index(self.layer_index) if self.layer_index in valid_indices else 0

        self.layer_anim_dir = 1 if steps > 0 else -1
        self.layer_anim_progress = 1.0
        
        self._prev_layer_index = getattr(self, 'layer_index', 0)
        self._prev_tools = getattr(self, 'current_tools', []).copy()

        next_valid_idx = (curr_valid_idx + steps) % len(valid_indices)
        self.layer_index = valid_indices[next_valid_idx]

        self.tools = self.menus[self.layer_index].get('tools', [])

        self.slice_progress = {} # reset anims
        self.active_index = -1
        
        # Clear any holding state in modules when cycling
        if hasattr(self, 'hub_manager'):
            for mod in [getattr(self.hub_manager, 'media_hub', None), getattr(self.hub_manager, 'time_hub', None), getattr(self.hub_manager, 'default_hub', None)]:
                if mod and hasattr(mod, '_holding'):
                    mod._holding = False
            self.clear_override_tools(instant=True)
            
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
            self.execute_current(close_halo=False)
        elif e.button() == Qt.MouseButton.RightButton:
            self.active_index = -1 # Safe Abort
            self.execute_current(close_halo=True)
        
    def _anim_loop(self):
        # Process queued mouse movement once per frame to decouple Win32 hook from Qt rendering
        if getattr(self, 'last_global_mouse_pos', None) is not None:
            self._process_mouse_pos(self.last_global_mouse_pos)
        elif hasattr(self, '_nav_keys') and self._nav_keys:
            from PyQt6.QtGui import QCursor
            self._process_mouse_pos(QCursor.pos())

        changed = False
        
        layer_anim = getattr(self, "layer_anim_progress", 0.0)
        
        current_time = time.perf_counter()
        elapsed = current_time - getattr(self, 'anim_start_time', current_time)
        duration = getattr(self, 'anim_duration', 0.5)
        
        if getattr(self, "closing", False):
            self.fade_t = max(0.0, 1.0 - (elapsed / duration))
            self.fade_progress = self.fade_t ** 2 # Ease out
            self.setWindowOpacity(self.fade_progress)
            changed = True
            
            if self.fade_t <= 0.0:
                self.hide()
                self.closing = False
                self.anim_timer.stop()
                
                # Execute command after fade out completes
                if self.active_index != -1 and len(self.current_tools) > 0 and self.active_index < len(self.current_tools):
                    cmd = self.current_tools[self.active_index]['id']
                    self.command_triggered.emit(cmd)
                    
                if getattr(self, 'original_cursor_pos', None):
                    from PyQt6.QtGui import QCursor
                    QCursor.setPos(self.original_cursor_pos)
                return
        else:
            if getattr(self, "fade_t", 0.0) < 1.0:
                self.fade_t = min(1.0, elapsed / duration)
                # Premium Cubic Out easing for deceleration on entry
                self.fade_progress = 1.0 - (1.0 - self.fade_t) ** 3
                self.setWindowOpacity(self.fade_progress)
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
            diff = abs(current - target)
            if diff > 0.02:
                # Faster lerp for deactivation (snapping away) vs activation (easing in)
                speed = 0.45 if target == 0.0 else 0.25
                self.slice_progress[i] = current + (target - current) * speed
                changed = True
            elif diff > 0:
                self.slice_progress[i] = target
                changed = True
                
        # Volume HUD animation
        if abs(self.vol_opacity - self.vol_target_opacity) > 0.01:
            self.vol_opacity += (self.vol_target_opacity - self.vol_opacity) * 0.15
            changed = True
            
        # Unified HUD Level Animation
        is_vol_or_night = self.vol_target_opacity > 0.5
        is_night = is_vol_or_night and "night" in getattr(self, 'vol_hud_dir', "")
        
        target_hud_level = 0.0
        if is_night:
            from utils import DisplayEffectsEngine
            engine = DisplayEffectsEngine.instance()
            target_hud_level = engine._target_intensity if engine._is_enabled else 0.0
        elif is_vol_or_night:
            target_hud_level = self.vol_level
        else:
            target_hud_level = self.batt_level / 100.0
            
        if not hasattr(self, 'anim_hud_level'):
            self.anim_hud_level = target_hud_level
            
        if abs(self.anim_hud_level - target_hud_level) > 0.001:
            self.anim_hud_level += (target_hud_level - self.anim_hud_level) * 0.25
            changed = True
        else:
            if self.anim_hud_level != target_hud_level:
                self.anim_hud_level = target_hud_level
                changed = True
            
        # Keep UI awake for Audio Visualizers to allow smooth decay
        if hasattr(self, 'hub_manager') and not changed:
            mod = self.hub_manager.get_active_module()
            if getattr(mod, '__class__', None).__name__ == 'MediaHub':
                if mod.settings.get('visualizer', 'None') != 'None':
                    track = mod.media_mgr.current_track
                    if track.get('status') == 'Playing' or getattr(mod, '_smoothed_peak', 0.0) > 0.01:
                        changed = True

        if changed:
            self.update()
    def show_center(self):
        from PyQt6.QtGui import QCursor, QGuiApplication
        screen = QGuiApplication.primaryScreen().availableGeometry()
        pos = screen.center()
        self.original_cursor_pos = QCursor.pos()
        self.setGeometry(screen)
        
        # Ensure visual center is aligned with the screen center used for mouse constraints
        self.center_pt = QPoint(self.width() // 2, self.height() // 2)
        self._refresh_geometry()
        
        QCursor.setPos(pos.x(), pos.y())
        self.anim_timer.start(16) # ~60 FPS
        self.current_mouse_pos = self.center_pt
        self.last_global_mouse_pos = pos
        self.slice_progress = {}
        self.clear_override_tools()
        
        if not hasattr(self, '_custom_cursor'):
            self._custom_cursor = self._create_custom_cursor()
        QApplication.setOverrideCursor(self._custom_cursor)
        self.setCursor(self._custom_cursor)
        
        from utils import get_system_volume_level, get_battery_info
        self.vol_level = get_system_volume_level()
        self.batt_level, self.batt_plugged = get_battery_info()
        self.vol_opacity = 0.0
        self.vol_target_opacity = 0.0

        if hasattr(QApplication.instance(), 'global_hook'):
            QApplication.instance().global_hook.set_constraint(pos, self.outer_radius - 2)

        self.active_index = -1
        self._nav_keys = set()
        self.closing = False
        self.fade_progress = 0.0
        self.fade_t = 0.0
        

        
        # Start animation clock AFTER capture so the capture time doesn't eat into the animation
        self.anim_start_time = time.perf_counter()
        self.anim_duration = 0.35
        
        self.show()
        self.activateWindow()
        self.raise_()
        self.setFocus()
        
        self._refresh_geometry()
        


    def update_mouse(self, global_pos):
        self.last_global_mouse_pos = global_pos

    def _process_mouse_pos(self, global_pos):
        if getattr(self, 'closing', False): return
        local_pos = self.mapFromGlobal(global_pos)
        dx = local_pos.x() - self.center_pt.x()
        dy = local_pos.y() - self.center_pt.y()
        
        if hasattr(self, '_nav_keys') and self._nav_keys:
            kx = 0.0
            ky = 0.0
            if 'W' in self._nav_keys: ky -= 1.0
            if 'S' in self._nav_keys: ky += 1.0
            if 'A' in self._nav_keys: kx -= 1.0
            if 'D' in self._nav_keys: kx += 1.0
            if kx != 0.0 or ky != 0.0:
                dx = kx * 300
                dy = ky * 300
        sens = getattr(self, 'mouse_sens', 100) / 100.0
        self.current_mouse_pos = QPointF(self.center_pt.x() + dx * sens, self.center_pt.y() + dy * sens)
        
        if not hasattr(self, 'mouse_trail'):
            self.mouse_trail = []
        self.mouse_trail.insert(0, self.current_mouse_pos)
        if len(self.mouse_trail) > 15:
            self.mouse_trail.pop()
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
            
            # --- Hover Transform Logic ---
            if new_idx != -1 and new_idx < len(self.current_tools):
                tool = self.current_tools[new_idx]
                tid = tool.get('id', '').strip().lower()
                if tid == 'mute':
                    from utils import get_system_volume_level
                    if getattr(self, 'last_adjusted_id', None) != tool['id']:
                        self.last_adjusted_id = tool['id']
                    self.vol_level = get_system_volume_level()
                    self.vol_hud_val = int(self.vol_level * 100)
                    self.vol_hud_dir = 'up'
                    self.vol_target_opacity = 1.0
                    self.last_adjusted_id = tool['id']
                    self.has_scrolled = False
                    self.vol_fade_timer.stop() # Keep visible while hovering
                elif tid in ['night', 'night light']:
                    from utils import DisplayEffectsEngine
                    engine = DisplayEffectsEngine.instance()
                    if getattr(self, 'last_adjusted_id', None) != tool['id']:
                        self.last_adjusted_id = tool['id']
                    val = engine._target_intensity if engine._is_enabled else 0.0
                    self.vol_level = val
                    self.vol_hud_val = int(val * 100)
                    self.vol_hud_dir = 'night_up'
                    self.vol_target_opacity = 1.0
                    self.last_adjusted_id = tool['id']
                    self.has_scrolled = False
                    self.vol_fade_timer.stop() # Keep visible while hovering
                elif tid == 'brightness':
                    from utils import get_system_brightness
                    if getattr(self, 'last_adjusted_id', None) != tool['id']:
                        self.last_adjusted_id = tool['id']
                    val = get_system_brightness()
                    self.vol_level = val
                    self.vol_hud_val = int(val * 100)
                    self.vol_hud_dir = 'brightness_up'
                    self.vol_target_opacity = 1.0
                    self.last_adjusted_id = tool['id']
                    self.has_scrolled = False
                    self.vol_fade_timer.stop()
                elif tid == 'volume':
                    vol = 0.5
                    if hasattr(self, 'media_mgr'):
                        vol = self.media_mgr.current_track.get('app_volume', 0.5)
                    if getattr(self, 'last_adjusted_id', None) != tool['id']:
                        self.last_adjusted_id = tool['id']
                    self.vol_level = vol
                    self.vol_hud_val = int(vol * 100)
                    self.vol_hud_dir = 'up'
                    self.vol_target_opacity = 1.0
                    self.last_adjusted_id = tool['id']
                    self.has_scrolled = False
                    self.vol_fade_timer.stop() # Keep visible while hovering
                else:
                    if self.vol_target_opacity > 0.0:
                        self._hide_vol_hud()
            else:
                if self.vol_target_opacity > 0.0:
                    self._hide_vol_hud()
            
    def execute_current(self, close_halo=True):
        import time
        from PyQt6.QtGui import QCursor
        
        if not close_halo:
            # Execute immediately on click without closing the overlay
            if self.active_index != -1 and len(self.current_tools) > 0 and self.active_index < len(self.current_tools):
                # Interaction Shield: Block execution ONLY for the tool being adjusted
                if self.vol_opacity > 0.1:
                    active_tool = self.current_tools[self.active_index]
                    if active_tool['id'] == getattr(self, 'last_adjusted_id', None) and getattr(self, 'has_scrolled', False):
                        return
                
                cmd = self.current_tools[self.active_index]['id']
                self.command_triggered.emit(cmd)
            return

        self.anim_timer.stop()
        if hasattr(QApplication.instance(), 'global_hook'):
            QApplication.instance().global_hook.set_constraint(None, None)
        
        while QApplication.overrideCursor():
            QApplication.restoreOverrideCursor()
        self.setCursor(Qt.CursorShape.ArrowCursor)
        
        # Interaction Shield: Block execution ONLY for the tool being adjusted
        if self.vol_opacity > 0.1 and self.active_index != -1 and self.active_index < len(self.current_tools):
            active_tool = self.current_tools[self.active_index]
            if active_tool['id'] == getattr(self, 'last_adjusted_id', None) and getattr(self, 'has_scrolled', False):
                self.closing = True
                self.anim_start_time = time.perf_counter()
                self.anim_duration = 0.2
                self.anim_timer.start(16)
                self.active_index = -1  # Prevent execution on fade out
                return
            
        hub_holding = False
        if hasattr(self, 'hub_manager'):
            mod = self.hub_manager.get_active_module()
            if getattr(mod, '_holding', False):
                hub_holding = True
                mod._holding = False
                self.clear_override_tools()
                
        # Start fade-out animation instead of hiding instantly
        if not getattr(self, "closing", False):
            self.closing = True
            self.anim_start_time = time.perf_counter()
            self.anim_duration = 0.2  # Quick 200ms fade out
            self.anim_timer.start(16)

    def paintEvent(self, e):
        p = QPainter(self)
        try:
            self._do_paint(p)
        except Exception as ex:
            import traceback
            with open("traceback_dump.txt", "a") as f:
                traceback.print_exc(file=f)
        finally:
            if p.isActive():
                p.end()

    def _do_paint(self, p):
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.setRenderHint(QPainter.RenderHint.TextAntialiasing)
        p.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
        
        cx, cy = self.center_pt.x(), self.center_pt.y()
        fade = getattr(self, "fade_progress", 0.0)
        theme = getattr(self, 'theme', 'Dark')
        
        # 1. Full-screen background (Blurred Wallpaper)
        if self._bg_blur_pixmap and not self._bg_blur_pixmap.isNull():
            p.save()
            # Reduce opacity to 85% so background apps bleed through
            p.setOpacity(fade * 0.90)
            
            # 1:1 perfectly aligned hardware blit
            p.drawPixmap(0, 0, self._bg_blur_pixmap)
            p.restore()
        else:
            # Drop the heavy black tint (from 110 down to 15) so the pure Windows 
            # hardware blur shines through without looking like a dark container.
            bg_alpha = max(1, int(15 * fade))
            p.fillRect(self.rect(), QColor(0, 0, 0, bg_alpha))
            
        # Draw black/white screen overlay (available across all themes)
        brightness = getattr(self, 'brightness', 50)
        if brightness < 50:
            # 0 - 49: black screen. 0 is full opacity (255), 49 is almost 0 opacity.
            alpha = int(255 * ((49 - brightness) / 49.0) * fade)
            if alpha > 0:
                p.fillRect(self.rect(), QColor(0, 0, 0, alpha))
        elif brightness > 50:
            # 51 - 100: white screen. 51 is 0 opacity, 100 is full opacity (255).
            alpha = int(255 * ((brightness - 51) / 49.0) * fade)
            if alpha > 0:
                p.fillRect(self.rect(), QColor(255, 255, 255, alpha))
        
        # Soft localized ambient shadow for depth over the native blur
        from PyQt6.QtGui import QRadialGradient
        shadow_grad = QRadialGradient(QPointF(cx, cy), self.outer_radius + 40)
        # Heavily reduced ambient shadow so it doesn't look like a dark container
        shadow_grad.setColorAt(0.0, QColor(0, 0, 0, int(20 * fade)))
        shadow_grad.setColorAt(0.7, QColor(0, 0, 0, int(10 * fade)))
        shadow_grad.setColorAt(1.0, Qt.GlobalColor.transparent)
        p.setBrush(shadow_grad)
        p.setPen(Qt.PenStyle.NoPen)
        p.drawEllipse(QPointF(cx, cy), self.outer_radius + 40, self.outer_radius + 40)
        
        # Apply opacity for the Halo menu elements
        p.setOpacity(fade)
        
        # Invisible shield for center (mouse capture area)
        p.setBrush(QColor(0, 0, 0, 1))
        p.setPen(Qt.PenStyle.NoPen)
        p.drawEllipse(self.center_pt, self.outer_radius, self.outer_radius)
        
        # Animation transforms for layer switching
        layer_anim = getattr(self, "layer_anim_progress", 0.0)
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
        self._accent_color = None
        self._accent_colors = None
        self.is_light = False
        if theme == 'Desktop':
            from utils import get_desktop_accent_colors, is_desktop_light_vibe, order_accents_by_vibe
            accents = get_desktop_accent_colors()
            self.is_light = is_desktop_light_vibe()
            self._accent_colors = [QColor(r, g, b) for r, g, b in order_accents_by_vibe(accents, self.is_light)]
            self._accent_color = self._accent_colors[0]
            ar, ag, ab = accents[0] # Original primary for tint
            if self.is_light:
                bg_r, bg_g, bg_b = min(255, int(ar*0.05 + 240)), min(255, int(ag*0.05 + 240)), min(255, int(ab*0.05 + 245))
            else:
                bg_r, bg_g, bg_b = int(ar * 0.15), int(ag * 0.15), int(ab * 0.15)
        elif theme == 'Gray':
            self._accent_colors = [QColor(220, 220, 220), QColor(160, 160, 160), QColor(100, 100, 100), QColor(60, 60, 60)]
            self._accent_color = self._accent_colors[0]
            bg_r, bg_g, bg_b = (40, 40, 40)
        else:
            bg_r, bg_g, bg_b = (10, 10, 14)
        
        p.setBrush(QColor(bg_r, bg_g, bg_b, opacity))
        if getattr(self, 'is_light', False):
            p.setPen(QPen(QColor(0,0,0,12), 1))
        else:
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
                    # Use exact inner and outer radius so it sits flush inside the ring (more premium look)
                    r_outer = self.outer_radius
                    r_inner = self.inner_radius
                    path.arcMoveTo(QRectF(cx - r_outer, cy - r_outer, r_outer*2, r_outer*2), start_angle)
                    path.arcTo(QRectF(cx - r_outer, cy - r_outer, r_outer*2, r_outer*2), start_angle, span_angle)
                    path.arcTo(QRectF(cx - r_inner, cy - r_inner, r_inner*2, r_inner*2), start_angle + span_angle, -span_angle)
                    path.closeSubpath()
                    
                    # 1. Draw organic "water/gas" luminous highlight FIRST (Behind the slice)
                    p.setCompositionMode(QPainter.CompositionMode.CompositionMode_Plus)
                    
                    trail = getattr(self, 'mouse_trail', [getattr(self, 'current_mouse_pos', QPointF(cx, cy))])
                    
                    for t_idx, m_pos in enumerate(trail):
                        trail_factor = 1.0 - (t_idx / len(trail))
                        
                        alpha_core = max(0, min(255, int(80 * prog * trail_factor)))
                        alpha_mid  = max(0, min(255, int(40 * prog * trail_factor)))
                        alpha_edge = max(0, min(255, int(10 * prog * trail_factor)))
                        
                        if alpha_core <= 0:
                            continue
                            
                        # Set flashlight radius to 21 per user request
                        glow_radius = 21.0 * (0.4 + 0.6 * trail_factor)
                        glow_grad = QRadialGradient(m_pos, glow_radius)
                        
                        glow_grad.setColorAt(0.0, QColor(255, 255, 255, alpha_core))
                        glow_grad.setColorAt(0.2, QColor(255, 255, 255, alpha_mid))
                        glow_grad.setColorAt(0.6, QColor(255, 255, 255, alpha_edge))
                        glow_grad.setColorAt(1.0, QColor(255, 255, 255, 0))
                        
                        p.setBrush(glow_grad)
                        p.setPen(Qt.PenStyle.NoPen)
                        p.drawPath(path)
                    
                    # Restore default composition mode
                    p.setCompositionMode(QPainter.CompositionMode.CompositionMode_SourceOver)

                    # 2. Draw the colored slice ON TOP with lower opacity so light bleeds through
                    slice_alpha = max(0, min(255, int(180 * prog)))
                    if getattr(self, '_accent_colors', None) and len(self._accent_colors) > 0:
                        c = self._accent_colors[0]
                        grad = QRadialGradient(cx, cy, r_outer)
                        grad.setColorAt(0.0, QColor(min(255, c.red()+40), min(255, c.green()+40), min(255, c.blue()+40), slice_alpha))
                        grad.setColorAt(1.0, QColor(c.red(), c.green(), c.blue(), int(slice_alpha * 0.7)))
                    else:
                        grad = QRadialGradient(cx, cy, r_outer)
                        grad.setColorAt(0.0, QColor(0, 160, 255, slice_alpha))
                        grad.setColorAt(1.0, QColor(0, 120, 255, int(slice_alpha * 0.7)))
                    
                    p.setBrush(grad)
                    p.setPen(Qt.PenStyle.NoPen)
                    p.drawPath(path)
                    
                    # 3. Premium outer edge indicator
                    # Thicker (6.0) and exactly 1/3 of the slice width, perfectly centered
                    if theme == 'Desktop' and getattr(self, '_accent_color', None):
                        ac = self._accent_color
                        ind_color = QColor(ac.red(), ac.green(), ac.blue(), int(255 * prog))
                    else:
                        ind_color = QColor(255, 255, 255, int(255 * prog))
                        
                    p.setPen(QPen(ind_color, 6.0, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
                    p.setBrush(Qt.BrushStyle.NoBrush)
                    
                    reduced_span = span_angle / 3.0
                    center_offset = (span_angle - reduced_span) / 2.0
                    
                    p.drawArc(QRectF(cx - r_outer, cy - r_outer, r_outer*2, r_outer*2), 
                              int((start_angle + center_offset) * 16), int(reduced_span * 16))
            
        # 3. Draw Icons smoothly (With smooth joint rotation)
        def draw_toolset(tools, offset_angle, opacity, is_outgoing=False):
            if not tools: return
            num = len(tools)
            if num == 0: return
            # Multiply with global fade progress to inherit entry/exit opacity
            opacity = opacity * fade
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
                            text_color = QColor(255, 255, 255)
                            idx_color = QColor(255, 255, 255, 200)
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
                            text_color = QColor(255, 255, 255)
                            idx_color = QColor(255, 255, 255, 200)
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
                            text_color = QColor(255, 255, 255)
                            idx_color = QColor(255, 255, 255, 200)
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
                        is_light = getattr(self, 'is_light', False)
                        ic_col_final = "#ffffff" if prog > 0.5 else ("#333333" if is_light else "#d0d0d0")
                        
                        tid = tool.get('id', '')
                        
                        # Dynamic Icon Swaps for Hardware Toggles
                        render_icon = tool['icon']
                        if tid in ["wifi", "wi-fi"]:
                            from utils import get_wifi_state
                            render_icon = "assets/wifi on.svg" if get_wifi_state() else "assets/wifi off.svg"
                        elif tid == "bluetooth":
                            from utils import get_bluetooth_state
                            render_icon = "assets/bluetooth on.svg" if get_bluetooth_state() else "assets/bluetooth off.svg"
                        elif tid in ["mic", "microphone"]:
                            from utils import get_mic_mute
                            render_icon = "assets/mic off.svg" if get_mic_mute() else "assets/mic on.svg"
                        elif tid in ["play/pause", "play"]:
                            from utils import MediaSessionManager
                            status = MediaSessionManager.instance().current_track.get('status', 'Stopped')
                            render_icon = "assets/play.svg" if status == "Playing" else "assets/pause.svg"
                            
                        is_path = tid and (('/' in tid) or ('\\' in tid) or (':' in tid)) and tid not in ["play/pause"]
                        if is_path:
                            pix = IconExtractor.get_icon_pixmap(tid, 32)
                            if getattr(self, 'blend_app_icons', False):
                                original_pix = pix
                                img = pix.toImage().convertToFormat(QImage.Format.Format_Grayscale8).convertToFormat(QImage.Format.Format_ARGB32)
                                gray_pix = QPixmap.fromImage(img)
                                
                                # Restore alpha channel since Grayscale8 strips it
                                p_temp = QPainter(gray_pix)
                                p_temp.setCompositionMode(QPainter.CompositionMode.CompositionMode_DestinationIn)
                                p_temp.drawPixmap(0, 0, original_pix)
                                p_temp.end()
                                
                                pix = gray_pix
                                # Subtly blend it into the background
                                p.setOpacity(opacity * 0.85)
                            else:
                                p.setOpacity(opacity)
                        else:
                            pix = VectorIcon.pixmap(render_icon, ic_col_final, 32)
                            p.setOpacity(opacity)
                        if prog < 0.5:
                            pass # Black circles removed per user request
                        
                        # Use hardware scaling to render the max-size pixmap at the animated pix_size
                        target_rect = QRectF(tx - pix_size/2, ty - pix_size/2, pix_size, pix_size)
                        p.drawPixmap(target_rect, pix, QRectF(pix.rect()))

        p.save()
        if layer_anim > 0.01:
            # Crossfade during spin
            draw_toolset(self._prev_tools, 0, layer_anim, is_outgoing=True)
            draw_toolset(self.current_tools, 0, progress_t, is_outgoing=False)
        else:
            draw_toolset(self.current_tools, 0, 1.0, False)
        p.setOpacity(fade)
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
            from utils import get_system_mute, get_wifi_state, get_bluetooth_state, get_mic_mute
            tool = self.current_tools[self.active_index]
            label = tool['label']
            tid = tool.get('id', '')
            if tid == "mute":
                label = "UNMUTE" if get_system_mute() else "MUTE"
            elif tid in ["wifi", "wi-fi"]:
                label = "DISABLE WI-FI" if get_wifi_state() else "ENABLE WI-FI"
            elif tid == "bluetooth":
                label = "DISABLE BLUETOOTH" if get_bluetooth_state() else "ENABLE BLUETOOTH"
            elif tid in ["mic", "microphone"]:
                label = "UNMUTE MIC" if get_mic_mute() else "MUTE MIC"
            elif tid in ["play/pause", "play"]:
                from utils import MediaSessionManager
                status = MediaSessionManager.instance().current_track.get('status', 'Stopped')
                label = "PAUSE MEDIA" if status == "Playing" else "PLAY MEDIA"
            
            if getattr(self, 'is_light', False):
                p.setPen(QColor(36, 41, 47))
            else:
                p.setPen(QColor(255,255,255))
            p.setFont(self.font_main)
            from PyQt6.QtGui import QFontMetrics
            fm = QFontMetrics(self.font_main)
            elided_label = elide_text_to_lines(fm, label.upper(), 220, 2)
            p.drawText(QRectF(cx-120, cy-38, 240, 54), Qt.AlignmentFlag.AlignCenter | Qt.TextFlag.TextWordWrap, elided_label)
            
            if getattr(self, 'is_light', False):
                p.setPen(QColor(36, 41, 47, 140))
            else:
                p.setPen(QColor(255,255,255,100))
            p.setFont(self.font_sub)
            sub_label = "SCROLL TO ADJUST" if tool['id'] in ['volume', 'timeline'] else "RELEASE TO EXECUTE"
            p.drawText(QRectF(cx-100, cy+20, 200, 18), Qt.AlignmentFlag.AlignCenter, sub_label)
        else:
            if hasattr(self, 'hub_manager'):
                self.hub_manager.draw_active(p, cx, cy, self.inner_radius)
            else:
                if hasattr(self, 'logo_renderer') and self.logo_renderer:
                    logo_size = 55 # 50% of previous 110
                    logo_rect = QRectF(cx - logo_size/2, cy - logo_size/2, logo_size, logo_size)
                    
                    pix = QPixmap(int(logo_rect.width()), int(logo_rect.height()))
                    pix.fill(Qt.GlobalColor.transparent)
                    p_pix = QPainter(pix)
                    p_pix.setRenderHint(QPainter.RenderHint.Antialiasing)
                    self.logo_renderer.render(p_pix, QRectF(pix.rect()))
                    p_pix.setCompositionMode(QPainter.CompositionMode.CompositionMode_SourceIn)
                    p_pix.fillRect(pix.rect(), QColor(255, 255, 255, 180))
                    p_pix.end()
                    p.drawPixmap(int(logo_rect.x()), int(logo_rect.y()), pix)
                else:
                    p.setPen(QColor(255,255,255,80))
                    p.setFont(QFont("Segoe UI Variable Display", 12, QFont.Weight.Bold))
                    p.drawText(QRectF(cx-100, cy-15, 200, 30), Qt.AlignmentFlag.AlignCenter, "PANDORA")
                
        # 4.5 Removed old layer indicator inside hub

        menus = getattr(self, 'menus', [])
        valid_indices = [i for i, m in enumerate(menus) if any(t.get('id') for t in m.get('tools', []))]
        num_layers = len(valid_indices)

        def draw_segmented_ring(p, v_rect, start_v, span_v, fill_level, track_opacity_mult, active_color, fill_pen_base=3):
            if num_layers <= 1:
                p.setPen(QPen(QColor(150, 150, 150, int(100 * track_opacity_mult)), fill_pen_base-1, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
                p.drawArc(v_rect, int(start_v * 16), int(span_v * 16))
                if fill_level > 0.001:
                    p.setPen(QPen(active_color, fill_pen_base, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
                    p.drawArc(v_rect, int(start_v * 16), int(span_v * fill_level * 16))
                return

            is_full_circle = abs(span_v) >= 359.9
            num_gaps = num_layers if is_full_circle else (num_layers - 1)
            seg_gap = -4
            segment_span = (span_v - num_gaps * seg_gap) / num_layers
            fill_span = span_v * fill_level

            for i, actual_idx in enumerate(valid_indices):
                seg_start_rel = i * (segment_span + seg_gap)
                seg_start = start_v + seg_start_rel
                
                is_active = (actual_idx == getattr(self, 'layer_index', 0))
                is_prev = (actual_idx == getattr(self, '_prev_layer_index', getattr(self, 'layer_index', 0)))
                anim_in_progress = layer_anim > 0.01

                if anim_in_progress and (is_active or is_prev):
                    t = eased_t if is_active else (1.0 - eased_t)
                    current_pen = fill_pen_base - 1 + (4 * t)
                    alpha = int(100 + (50 * t))
                    p.setPen(QPen(QColor(150, 150, 150, int(alpha * track_opacity_mult)), current_pen, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
                else:
                    if is_active:
                        p.setPen(QPen(QColor(150, 150, 150, int(150 * track_opacity_mult)), fill_pen_base+3, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
                    else:
                        p.setPen(QPen(QColor(150, 150, 150, int(100 * track_opacity_mult)), fill_pen_base-1, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
                p.drawArc(v_rect, int(seg_start * 16), int(segment_span * 16))

                if fill_span <= seg_start_rel and fill_level > 0.001:
                    overlap = min(abs(segment_span), abs(fill_span - seg_start_rel))
                    if overlap > 0:
                        if anim_in_progress and (is_active or is_prev):
                            t = eased_t if is_active else (1.0 - eased_t)
                            current_pen_fill = fill_pen_base + (3 * t)
                            p.setPen(QPen(active_color, current_pen_fill, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
                        else:
                            p.setPen(QPen(active_color, fill_pen_base+3 if is_active else fill_pen_base, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
                        p.drawArc(v_rect, int(seg_start * 16), int(-overlap * 16))

        # 4.6 Draw Volume Ring
        if self.vol_opacity > 0.01:
            p.setOpacity(self.vol_opacity * fade)
            v_radius = self.outer_radius + 12
            v_rect = QRectF(cx - v_radius, cy - v_radius, v_radius*2, v_radius*2)
            
            start_v = 270 - (getattr(self, 'gap_size', 75) / 2.0)
            span_v = -(360 - getattr(self, 'gap_size', 75))
            
            from utils import DisplayEffectsEngine
            engine = DisplayEffectsEngine.instance()
            is_night_active = self.vol_opacity > 0.5 and "night" in getattr(self, 'vol_hud_dir', "")
            
            if is_night_active:
                vol_color = QColor(255, 150, 50, 200) if not getattr(self, '_accent_color', None) else QColor(self._accent_color.red(), self._accent_color.green(), self._accent_color.blue(), 200)
            else:
                vol_color = QColor(0, 240, 255, 200) if not getattr(self, '_accent_color', None) else QColor(self._accent_color.red(), self._accent_color.green(), self._accent_color.blue(), 200)
            
            level = getattr(self, 'anim_hud_level', 0.0)
            
            if getattr(self, '_accent_colors', None) and len(self._accent_colors) > 1 and not is_night_active:
                from PyQt6.QtGui import QBrush
                grad = QConicalGradient(cx, cy, 90)
                acs = self._accent_colors
                n = len(acs)
                for idx, c in enumerate(acs):
                    grad.setColorAt(idx / n, QColor(c.red(), c.green(), c.blue(), 200))
                grad.setColorAt(1.0, QColor(acs[0].red(), acs[0].green(), acs[0].blue(), 200))
                active_brush = QBrush(grad)
            else:
                from PyQt6.QtGui import QBrush
                active_brush = QBrush(vol_color)
            
            draw_segmented_ring(p, v_rect, start_v, span_v, level, 1.0, active_brush, fill_pen_base=4)
            p.setOpacity(fade)
            
        if getattr(self, 'vol_opacity', 0) >= 0.99:
            self.is_slice_crossfading = False
            
        # 4.7 Draw Battery Ring (when volume is not fully visible)
        if getattr(self, 'vol_opacity', 0) >= 0.99:
            pass # Hide battery while vol is fully active
        else:
            if self.vol_opacity < 0.99 and not getattr(self, 'is_slice_crossfading', False):
                p.setOpacity((1.0 - self.vol_opacity) * fade)
            else:
                p.setOpacity(fade)
                
            v_radius = self.outer_radius + 12
            v_rect = QRectF(cx - v_radius, cy - v_radius, v_radius*2, v_radius*2)
            
            start_v = 270 - (getattr(self, 'gap_size', 75) / 2.0)
            span_v = -(360 - getattr(self, 'gap_size', 75))
            
            # Subtle track for battery
            batt_color = QColor(255, 255, 255, 180)
            ac = getattr(self, '_accent_color', None)
            is_critical = False
            if self.batt_plugged:
                batt_color = QColor(0, 255, 150, 180) if not ac else QColor(ac.red(), ac.green(), ac.blue(), 180)
            else:
                if self.batt_level > 50:
                    batt_color = QColor(0, 255, 120, 150) if not ac else QColor(ac.red(), ac.green(), ac.blue(), 180)
                elif self.batt_level > 20:
                    batt_color = QColor(255, 200, 0, 150) # Warning Yellow
                    is_critical = True
                else:
                    batt_color = QColor(255, 50, 50, 180) # Critical Red
                    is_critical = True
                    
            if getattr(self, '_accent_colors', None) and len(self._accent_colors) > 1 and not is_critical:
                from PyQt6.QtGui import QBrush
                grad = QConicalGradient(cx, cy, 90)
                acs = self._accent_colors
                n = len(acs)
                for idx, c in enumerate(acs):
                    grad.setColorAt(idx / n, QColor(c.red(), c.green(), c.blue(), 180))
                grad.setColorAt(1.0, QColor(acs[0].red(), acs[0].green(), acs[0].blue(), 180))
                active_brush = QBrush(grad)
            else:
                from PyQt6.QtGui import QBrush
                active_brush = QBrush(batt_color)
                    
            draw_segmented_ring(p, v_rect, start_v, span_v, getattr(self, 'anim_hud_level', 0.0), 0.5, active_brush, fill_pen_base=3)
            p.setOpacity(fade)
            
        # 4.8 Draw HUD Icon & Text in the Gap
        hud_opacity = max(self.vol_opacity, 1.0 - self.vol_opacity)
        show_arc_hud = getattr(self, 'show_arc_hud', True)
        gap = getattr(self, 'gap_size', 75)
        if hud_opacity > 0.01 and show_arc_hud:
            p.setOpacity(hud_opacity * fade)
            is_vol = self.vol_opacity > 0.5
            is_night = is_vol and "night" in getattr(self, 'vol_hud_dir', "")
            is_bright = is_vol and "brightness" in getattr(self, 'vol_hud_dir', "")
            
            if is_night:
                ic_name = "night"
                hud_col = QColor(255, 150, 50) if not getattr(self, '_accent_color', None) else self._accent_color
            elif is_bright:
                ic_name = "brightness"
                hud_col = QColor(255, 200, 50) if not getattr(self, '_accent_color', None) else self._accent_color
            elif is_vol:
                ic_name = "volume up" if getattr(self, 'vol_hud_dir', "up") == "up" else "volume down"
                hud_col = QColor(0, 240, 255) if not getattr(self, '_accent_color', None) else self._accent_color
            else:
                ic_name = "charging" if self.batt_plugged else "battery"
                hud_col = QColor(batt_color.red(), batt_color.green(), batt_color.blue(), 255)
                
            current_hud_val = int(getattr(self, 'anim_hud_level', 0.0) * 100)
            val_text = f"{current_hud_val}%"
            
            p.setFont(self.font_mini)
            tw = p.fontMetrics().horizontalAdvance(val_text)
            
            # Position at bottom
            tx, ty = cx, cy + self.outer_radius + 12
            
            # Prevent collision if the gap is too small to fit the text
            gap = getattr(self, 'gap_size', 75)
            if gap < 45:
                ty += 16
            
            pix = VectorIcon.pixmap(ic_name, hud_col.name(), 18)
            
            # The icon width is ~18px, text width is tw. Total width is approx 18 + 4 (padding) + tw
            total_w = 18 + 4 + tw
            
            # Start drawing from exactly centered left bound
            start_x = tx - total_w / 2.0
            
            p.drawPixmap(int(start_x), int(ty - 9), pix)
            p.setPen(hud_col)
            p.drawText(QRectF(start_x + 22, ty - 10, tw + 10, 20), Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft, val_text)
            p.setOpacity(fade)
                
        pass

    def keyPressEvent(self, event):
        if hasattr(self, 'hub_manager'):
            if self.hub_manager.handle_key_press(event):
                return
                
        if not hasattr(self, '_nav_keys'):
            self._nav_keys = set()
            
        key = event.key()
        if key in (Qt.Key.Key_W, Qt.Key.Key_Up): self._nav_keys.add('W')
        elif key in (Qt.Key.Key_A, Qt.Key.Key_Left): self._nav_keys.add('A')
        elif key in (Qt.Key.Key_S, Qt.Key.Key_Down): self._nav_keys.add('S')
        elif key in (Qt.Key.Key_D, Qt.Key.Key_Right): self._nav_keys.add('D')
        elif key in (Qt.Key.Key_Return, Qt.Key.Key_Enter, Qt.Key.Key_Space):
            self.execute_current()
            return
            
        super().keyPressEvent(event)

    def keyReleaseEvent(self, event):
        if hasattr(self, 'hub_manager'):
            if self.hub_manager.handle_key_release(event):
                return
                
        if not hasattr(self, '_nav_keys'):
            self._nav_keys = set()
            
        key = event.key()
        if key in (Qt.Key.Key_W, Qt.Key.Key_Up): self._nav_keys.discard('W')
        elif key in (Qt.Key.Key_A, Qt.Key.Key_Left): self._nav_keys.discard('A')
        elif key in (Qt.Key.Key_S, Qt.Key.Key_Down): self._nav_keys.discard('S')
        elif key in (Qt.Key.Key_D, Qt.Key.Key_Right): self._nav_keys.discard('D')
        
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

