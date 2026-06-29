import math
import time as time_mod
from datetime import datetime
from zoneinfo import ZoneInfo
from PyQt6.QtCore import QRectF, Qt, QPointF
from PyQt6.QtGui import QPainter, QFont, QColor, QPen
from .base import BaseHubModule

class TimeHub(BaseHubModule):
    """Clock module with digital and analog modes, plus world timezone presets."""
    def __init__(self, manager):
        super().__init__(manager)
        
        # Spacebar / Halo Menu State
        self._holding = False
        self._space_pressed = False
        self._space_press_time = 0.0

        # Smooth animation timer
        from PyQt6.QtCore import QTimer
        self._smooth_timer = QTimer()
        self._smooth_timer.timeout.connect(self._on_smooth_tick)
        self._smooth_timer.start(16)

    def _on_smooth_tick(self):
        # Force a repaint at 60fps if halo is visible
        if hasattr(self.manager, 'halo') and self.manager.halo.isVisible():
            self.manager.halo.update()

    def draw(self, p, cx, cy, inner_radius):
        mode = self.settings.get('clock_mode', 'digital')
        
        # 1. Determine which timezone to display
        active_tz = self.settings.get('active_clock_tz', '')
        active_label = self.settings.get('active_clock_label', 'LOCAL TIME')
        
        # 2. Check if a world clock slice is currently hovered while space is held
        hovered_tz = None
        hovered_label = None
        
        if self._holding:
            if hasattr(self.manager.halo, 'active_index') and self.manager.halo.active_index != -1:
                active_idx = self.manager.halo.active_index
                tools = self.manager.halo.current_tools
                if active_idx < len(tools):
                    tool = tools[active_idx]
                    if tool['id'].startswith('world_tz_'):
                        # Format is world_tz_idx_tz_label
                        hovered_tz = tool.get('tz')
                        hovered_label = tool.get('label')
        
        # 3. Choose target timezone and preview status
        display_tz = hovered_tz if hovered_tz is not None else active_tz
        display_label = hovered_label if hovered_label is not None else active_label
        
        # Get localized time
        if display_tz:
            try:
                now = datetime.now(ZoneInfo(display_tz))
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
                offset = offsets.get(display_tz, 0.0)
                now = datetime.now(timezone.utc) + timedelta(hours=offset)
        else:
            now = datetime.now()
            display_label = "LOCAL TIME"
            
        # Theme integration
        theme = getattr(self.manager.halo, 'theme', 'Dark') if hasattr(self.manager, 'halo') else 'Dark'
        accent_color = None
        if theme == 'Desktop':
            try:
                from utils import get_desktop_accent_colors
                accents = get_desktop_accent_colors()
                if accents:
                    accent_color = QColor(*accents[0])
            except ImportError:
                pass
            
        # Draw target mode
        if mode == 'analog':
            self._draw_analog(p, cx, cy, inner_radius, now, display_label, theme, accent_color)
        else:
            self._draw_digital(p, cx, cy, inner_radius, now, display_label, theme, accent_color)

    def _draw_digital(self, p, cx, cy, inner_radius, now, label_text, theme='Dark', accent_color=None):
        fmt_24h = self.settings.get('format_24h', True)
        show_date = self.settings.get('show_date', True)
        show_seconds = self.settings.get('show_seconds', False)
        
        base_color = accent_color if (theme == 'Desktop' and accent_color) else QColor(0, 240, 255)
        comet_color = QColor(base_color.red(), base_color.green(), base_color.blue(), 255) if (theme == 'Desktop' and accent_color) else QColor(255, 255, 255, 255)

        r = inner_radius - 12
        p.save()
        p.setRenderHint(QPainter.RenderHint.Antialiasing)

        # Thick sweeping seconds arc for digital clock
        arc_radius = r - 4
        arc_width = 8.0
        # Faint track
        p.setPen(QPen(QColor(base_color.red(), base_color.green(), base_color.blue(), 15), arc_width))
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.drawEllipse(QPointF(cx, cy), arc_radius, arc_radius)
        
        # Sweeping progress (fill on even minutes, empty on odd)
        sec_progress = now.second + now.microsecond / 1000000.0
        span_deg = (sec_progress / 60.0) * 360.0
        is_filling = (now.minute % 2 == 0)
        
        if is_filling:
            start_angle = 90
            span_angle = -span_deg
        else:
            start_angle = 90 - span_deg
            span_angle = -(360.0 - span_deg)

        p.setPen(QPen(QColor(base_color.red(), base_color.green(), base_color.blue(), 180), arc_width, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
        if span_angle != 0:
            p.drawArc(QRectF(cx - arc_radius, cy - arc_radius, arc_radius*2, arc_radius*2), 
                      int(start_angle * 16), int(span_angle * 16))
                      
        # Premium indicator head at the moving edge
        head_angle = 90 - span_deg
        p.setPen(QPen(comet_color, arc_width + 3.0, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
        p.drawArc(QRectF(cx - arc_radius, cy - arc_radius, arc_radius*2, arc_radius*2), 
                  int((head_angle + 0.1) * 16), int(-0.2 * 16))
        p.restore()

        if fmt_24h:
            time_str = now.strftime("%H:%M")
        else:
            time_str = now.strftime("%I:%M %p")

        # Sleek timezone label inside digital clock
        p.setPen(QColor(base_color.red(), base_color.green(), base_color.blue(), 200))
        # Use a slightly smaller, more spaced out font for the label to look modern
        label_font = QFont("Segoe UI Variable Display", 9, QFont.Weight.Bold)
        label_font.setLetterSpacing(QFont.SpacingType.AbsoluteSpacing, 1.5)
        p.setFont(label_font)
        p.drawText(QRectF(cx - 100, cy - 45, 200, 16), Qt.AlignmentFlag.AlignCenter, label_text.upper())

        # Main Time Text - Large and Bold
        time_font = QFont("Segoe UI Variable Display", 32, QFont.Weight.Black)
        p.setFont(time_font)
        fm = p.fontMetrics()
        tw = fm.horizontalAdvance(time_str)

        tx = cx - tw // 2
        if show_seconds:
            tx = cx - tw // 2 - 10
        
        # Subtle Drop Shadow for depth
        p.setPen(QColor(0, 0, 0, 100))
        p.drawText(QRectF(tx, cy - 25 + 2, tw, 50), Qt.AlignmentFlag.AlignCenter, time_str)
        
        # Actual Time Text
        p.setPen(QColor(255, 255, 255))
        p.drawText(QRectF(tx, cy - 25, tw, 50), Qt.AlignmentFlag.AlignCenter, time_str)

        if show_seconds:
            sec_str = now.strftime(":%S")
            # Seconds (smaller, cyan, aligned to the baseline of the main time)
            p.setPen(QColor(base_color.red(), base_color.green(), base_color.blue(), 220))
            p.setFont(QFont("Segoe UI Variable Display", 14, QFont.Weight.Bold))
            p.drawText(QRectF(tx + tw + 2, cy - 8, 40, 20),
                       Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter, sec_str)

        # Date - Clean and modern
        if show_date:
            date_str = now.strftime("%A, %B %d").upper()
            p.setPen(QColor(255, 255, 255, 120))
            date_font = QFont("Segoe UI Variable Display", 8, QFont.Weight.Bold)
            date_font.setLetterSpacing(QFont.SpacingType.AbsoluteSpacing, 1.0)
            p.setFont(date_font)
            p.drawText(QRectF(cx - 100, cy + 28, 200, 15), Qt.AlignmentFlag.AlignCenter, date_str)

    def _draw_analog(self, p, cx, cy, inner_radius, now, label_text, theme='Dark', accent_color=None):
        base_color = accent_color if (theme == 'Desktop' and accent_color) else QColor(0, 240, 255)
        comet_color = QColor(base_color.red(), base_color.green(), base_color.blue(), 255) if (theme == 'Desktop' and accent_color) else QColor(255, 255, 255, 255)

        r = inner_radius - 12
        p.save()
        p.setRenderHint(QPainter.RenderHint.Antialiasing)

        # 1. Subtle Outer Dial Rim
        p.setPen(QPen(QColor(255, 255, 255, 10), 1))
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.drawEllipse(QPointF(cx, cy), r, r)
        
        # Thick Inner glow ring tracking seconds
        arc_radius = r - 12
        arc_width = 8.0
        p.setPen(QPen(QColor(base_color.red(), base_color.green(), base_color.blue(), 15), arc_width))
        p.drawEllipse(QPointF(cx, cy), arc_radius, arc_radius)
        
        # Sweeping progress (fill on even minutes, empty on odd)
        sec_progress = now.second + now.microsecond / 1000000.0
        span_deg = (sec_progress / 60.0) * 360.0
        is_filling = (now.minute % 2 == 0)
        
        if is_filling:
            start_angle = 90
            span_angle = -span_deg
        else:
            start_angle = 90 - span_deg
            span_angle = -(360.0 - span_deg)

        p.setPen(QPen(QColor(base_color.red(), base_color.green(), base_color.blue(), 180), arc_width, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
        if span_angle != 0:
            p.drawArc(QRectF(cx - arc_radius, cy - arc_radius, arc_radius*2, arc_radius*2), 
                      int(start_angle * 16), int(span_angle * 16))

        # Premium indicator head at the moving edge
        head_angle = 90 - span_deg
        p.setPen(QPen(comet_color, arc_width + 3.0, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
        p.drawArc(QRectF(cx - arc_radius, cy - arc_radius, arc_radius*2, arc_radius*2), 
                  int((head_angle + 0.1) * 16), int(-0.2 * 16))

        # 2. Clock face - tick marks
        for i in range(60):
            angle = math.radians(i * 6 - 90)
            is_hour = (i % 5 == 0)
            if is_hour:
                r1 = r - 8
                r2 = r
                w = 3.5
                alpha = 255
            else:
                r1 = r - 3
                r2 = r
                w = 1.5
                alpha = 100
                
            x1 = cx + math.cos(angle) * r1
            y1 = cy + math.sin(angle) * r1
            x2 = cx + math.cos(angle) * r2
            y2 = cy + math.sin(angle) * r2
            
            color = QColor(255, 255, 255, alpha)
            p.setPen(QPen(color, w, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
            p.drawLine(QPointF(x1, y1), QPointF(x2, y2))

        # 3. Timezone label inside analog face
        p.setPen(QColor(255, 255, 255, 140))
        label_font = QFont("Segoe UI Variable Display", 8, QFont.Weight.Bold)
        label_font.setLetterSpacing(QFont.SpacingType.AbsoluteSpacing, 1.2)
        p.setFont(label_font)
        p.drawText(QRectF(cx-60, cy - r * 0.45, 120, 16), Qt.AlignmentFlag.AlignCenter, label_text.upper())

        # 4. Day of the month elegant calendar date window
        show_date = self.settings.get('show_date', True)
        if show_date:
            date_num = now.strftime("%d")
            p.save()
            # Add subtle dark shadow to window
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(QColor(0, 0, 0, 40))
            date_rect_shadow = QRectF(cx - 11, cy + r * 0.4 + 1, 22, 16)
            p.drawRoundedRect(date_rect_shadow, 4, 4)
            
            p.setPen(QPen(QColor(255, 255, 255, 20), 1))
            p.setBrush(QColor(255, 255, 255, 10))
            date_rect = QRectF(cx - 11, cy + r * 0.4, 22, 16)
            p.drawRoundedRect(date_rect, 4, 4)
            
            p.setPen(QColor(0, 240, 255, 255))
            p.setFont(QFont("Segoe UI Variable Display", 8, QFont.Weight.Bold))
            p.drawText(date_rect, Qt.AlignmentFlag.AlignCenter, date_num)
            p.restore()

        # Helper to draw a rounded thick hand
        def draw_rounded_hand(angle_rad, length, tail_len, width, color):
            p.save()
            p.setPen(QPen(color, width, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
            dx = math.cos(angle_rad)
            dy = math.sin(angle_rad)
            p.drawLine(QPointF(cx - dx * tail_len, cy - dy * tail_len), 
                       QPointF(cx + dx * length, cy + dy * length))
            p.restore()

        # 5. Hour hand (Thick rounded line)
        h_angle = math.radians((now.hour % 12 + now.minute / 60) * 30 - 90)
        h_len = r * 0.45
        draw_rounded_hand(h_angle, h_len, 14, 6.0, QColor(255, 255, 255, 240))

        # 6. Minute hand (Medium thick rounded line)
        m_angle = math.radians((now.minute + now.second / 60) * 6 - 90)
        m_len = r * 0.70
        draw_rounded_hand(m_angle, m_len, 16, 4.0, QColor(255, 255, 255, 190))

        # 7. Second hand with tail (Cyan rounded)
        show_seconds = self.settings.get('show_seconds', False)
        if show_seconds:
            s_angle = math.radians(sec_progress * 6 - 90)
            s_len = r * 0.85
            draw_rounded_hand(s_angle, s_len, 24, 2.5, QColor(0, 240, 255, 255))

        # 8. Center pivot dot (layered glow matching layout)
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QColor(255, 255, 255, 255))
        p.drawEllipse(QPointF(cx, cy), 5, 5)
        p.setBrush(QColor(0, 240, 255, 255))
        p.drawEllipse(QPointF(cx, cy), 2.5, 2.5)

        p.restore()

    def _update_override_tools(self):
        world_clocks = self.settings.get('world_clocks', [])
        tools = []
        for i, wc in enumerate(world_clocks[:12]):
            tools.append({
                "id": f"world_tz_{i}",
                "icon": "clock",
                "label": wc['label'].upper(),
                "tz": wc['tz']
            })
            
        if not tools:
            # Fallback helper if no world clocks are configured yet
            tools.append({
                "id": "world_tz_none",
                "icon": "settings",
                "label": "ADD CLOCKS IN SETUP",
                "tz": ""
            })
            
        if hasattr(self.manager.halo, 'set_override_tools'):
            self.manager.halo.set_override_tools(tools)

    def on_key_press(self, event):
        if event.key() == Qt.Key.Key_Space:
            if not getattr(self, '_space_pressed', False):
                self._space_pressed = True
                self._space_press_time = time_mod.time()
                self._holding = True
                self._update_override_tools()
                self.manager.halo.update()
            return True
        return False

    def on_key_release(self, event):
        if event.key() == Qt.Key.Key_Space:
            self._space_pressed = False
            was_holding = self._holding
            self._holding = False
            
            used_tz = False
            if was_holding and time_mod.time() - getattr(self, '_space_press_time', 0) >= 0.3:
                # Long press: swap timezone on hover release
                if hasattr(self.manager.halo, 'active_index') and self.manager.halo.active_index != -1:
                    active_idx = self.manager.halo.active_index
                    tools = self.manager.halo.current_tools
                    if active_idx < len(tools):
                        tool = tools[active_idx]
                        if tool['id'].startswith('world_tz_') and tool['id'] != "world_tz_none":
                            idx_str = tool['id'].split('_')[-1]
                            try:
                                idx = int(idx_str)
                            except ValueError:
                                idx = -1
                            self._swap_timezones_with_slice(idx, tool.get('tz'), tool.get('label'))
                            used_tz = True

            if used_tz:
                if hasattr(self.manager.halo, 'clear_override_tools'):
                    self.manager.halo.clear_override_tools()
                self.manager.halo.active_index = -1
                self.manager.halo.execute_current()
                return True

            if hasattr(self.manager.halo, 'clear_override_tools'):
                self.manager.halo.clear_override_tools()

            # Short tap: cycle back to local system time
            if was_holding and time_mod.time() - getattr(self, '_space_press_time', 0) < 0.3:
                self._lock_timezone('', 'LOCAL TIME')
                
            self.manager.halo.update()
            return True
        return False

    def on_mouse_press(self, pos, button):
        if self._holding:
            if hasattr(self.manager.halo, 'active_index') and self.manager.halo.active_index != -1:
                active_idx = self.manager.halo.active_index
                tools = self.manager.halo.current_tools
                if active_idx < len(tools):
                    tool = tools[active_idx]
                    if tool['id'].startswith('world_tz_') and tool['id'] != "world_tz_none":
                        if button == Qt.MouseButton.LeftButton:
                            idx_str = tool['id'].split('_')[-1]
                            try:
                                idx = int(idx_str)
                            except ValueError:
                                idx = -1
                            self._swap_timezones_with_slice(idx, tool.get('tz'), tool.get('label'))
                            self.manager.halo.update()
                            return

    def _swap_timezones_with_slice(self, idx, tool_tz, tool_label):
        """Swaps the main clock's timezone with the world clock slice at idx."""
        old_active_tz = self.settings.get('active_clock_tz', '')
        old_active_label = self.settings.get('active_clock_label', 'LOCAL TIME')
        if not old_active_label:
            old_active_label = 'LOCAL TIME'
            
        # Swap settings in memory
        self.settings['active_clock_tz'] = tool_tz
        self.settings['active_clock_label'] = tool_label
        
        world_clocks = list(self.settings.get('world_clocks', []))
        if 0 <= idx < len(world_clocks):
            world_clocks[idx] = {
                "tz": old_active_tz,
                "label": old_active_label.upper()
            }
            self.settings['world_clocks'] = world_clocks
            
        # Save to config
        if hasattr(self.manager, 'cfg') and self.manager.cfg:
            hub_cfg = self.manager.cfg.get('hub_config', {})
            layers = hub_cfg.get('layers', [])
            for l in layers:
                if l and l['type'] == 'time':
                    l.setdefault('settings', {})['active_clock_tz'] = tool_tz
                    l['settings']['active_clock_label'] = tool_label
                    l['settings']['world_clocks'] = world_clocks
                    from config import ConfigManager
                    ConfigManager.save(self.manager.cfg)
                    break
                    
        self._update_override_tools()

    def _lock_timezone(self, tz, label):
        """Permanently locks the timezone to the selected clock, saving to config."""
        self.settings['active_clock_tz'] = tz
        self.settings['active_clock_label'] = label
        
        # Save timezone state back to the central configuration
        if hasattr(self.manager, 'cfg') and self.manager.cfg:
            hub_cfg = self.manager.cfg.get('hub_config', {})
            layers = hub_cfg.get('layers', [])
            for l in layers:
                if l and l['type'] == 'time':
                    l.setdefault('settings', {})['active_clock_tz'] = tz
                    l['settings']['active_clock_label'] = label
                    from config import ConfigManager
                    ConfigManager.save(self.manager.cfg)
                    break

    def cleanup(self):
        pass
