import sys
import os
import math
from PyQt6.QtCore import Qt, QPoint, QPointF, QRect, QRectF, QSize, QPropertyAnimation, QEasingCurve, QEvent, pyqtProperty
from PyQt6.QtWidgets import QWidget, QApplication, QGraphicsOpacityEffect
from PyQt6.QtGui import QColor, QPainter, QBrush, QPen, QIcon, QPainterPath, QRegion, QTransform, QPixmap, QPainterPathStroker, QImage
from PyQt6.QtSvg import QSvgRenderer

class DashboardPillWindow(QWidget):
    def __init__(self, cfg, dashboard, grid_overlay, restart_func, quit_func):
        super().__init__()
        self.cfg = cfg
        self.dashboard = dashboard
        self.grid_overlay = grid_overlay
        self.restart_func = restart_func
        self.quit_func = quit_func
        
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnTopHint | Qt.WindowType.Tool)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setMouseTracking(True)
        
        # Load saved edge and orientation from config
        gen_settings = self.cfg.get('general_settings', {})
        self.edge = gen_settings.get('pill_edge', 'right')
        self.orientation = 'horizontal' if self.edge in ['top', 'bottom'] else 'vertical'
        self._rotation = -90.0 if self.edge in ['top', 'bottom'] else 0.0
        
        self.is_dragging = False
        self.drag_position = QPoint()
        self.drag_center_offset = QPoint(0, 0)
        self._expansion = 0.0
        self.hovered_btn_idx = -1
        
        # Opacity effect for transition animations
        self.opacity_effect = QGraphicsOpacityEffect(self)
        self.setGraphicsEffect(self.opacity_effect)
        self.opacity_effect.setOpacity(1.0)
        
        # Load theme base colors
        self.update_theme()
        
        # Set fixed window dimensions (capsule rotates inside this canvas)
        self.setFixedSize(640, 640)
        self.update_mask_and_geom()
        
    @pyqtProperty(float)
    def expansion(self):
        return self._expansion
        
    @expansion.setter
    def expansion(self, val):
        self._expansion = val
        self.update_mask_and_geom()
        self.update()
        
    def get_bent_path_and_centers(self):
        cx, cy = 320, 320
        # D is the drag button's location in local coordinates.
        # When collapsed (expansion=0), the pill draws at cx + full offset.
        # When expanded (expansion=1), the pill draws at cx (offset=0) since
        # buttons fan out from center. Interpolate:
        interp = 1.0 - self._expansion
        D = QPointF(cx + self.drag_center_offset.x() * interp,
                    cy + self.drag_center_offset.y() * interp)
        
        screen = QApplication.primaryScreen()
        geom = screen.availableGeometry()
        
        # Window top-left in screen coords
        wx, wy = self.x(), self.y()
        
        # Available range in LOCAL widget coordinates (27 = capsule radius)
        local_min_x = geom.x() + 27 - wx
        local_max_x = geom.x() + geom.width() - 27 - wx
        local_min_y = geom.y() + 27 - wy
        local_max_y = geom.y() + geom.height() - 27 - wy
        
        # V1 = primary expansion direction (along-edge), V2 = bend direction (into screen)
        # d_avail = how far along V1 we can go before hitting the screen boundary
        if self.edge == 'right':
            V1 = QPointF(0, 1)    # expand downward
            V2 = QPointF(-1, 0)   # bend leftward
            d_avail = local_max_y - D.y()
        elif self.edge == 'left':
            V1 = QPointF(0, 1)    # expand downward
            V2 = QPointF(1, 0)    # bend rightward
            d_avail = local_max_y - D.y()
        elif self.edge == 'top':
            V1 = QPointF(1, 0)    # expand rightward
            V2 = QPointF(0, 1)    # bend downward
            d_avail = local_max_x - D.x()
        else:  # bottom
            V1 = QPointF(1, 0)    # expand rightward
            V2 = QPointF(0, -1)   # bend upward
            d_avail = local_max_x - D.x()
            
        L = 264.0 * self._expansion  # total skeleton length (6 gaps × 44px)
        
        skeleton0 = QPainterPath()
        skeleton35 = QPainterPath()
        centers = []
        
        skeleton0.moveTo(D)
        skeleton35.moveTo(D)
        
        if L < 0.1:
            # Collapsed: just a point
            skeleton0.lineTo(D)
            skeleton35.lineTo(D)
            centers = [D] * 7
        elif d_avail >= L:
            # Straight: plenty of room, no bend needed
            end_pt = D + V1 * L
            skeleton0.lineTo(end_pt)
            skeleton35.lineTo(end_pt)
            for i in range(7):
                centers.append(D + V1 * (i * 44.0 * self._expansion))
        else:
            # Bend needed: go straight for d_avail, then turn 90° along V2
            # Snap d_straight to nearest icon grid step (44px * expansion)
            # so icons on both legs align cleanly at the corner
            step = 44.0 * self._expansion
            if step > 0.1:
                d_straight = max(0.0, math.floor(d_avail / step) * step)
            else:
                d_straight = 0.0
            d_bent = L - d_straight
            
            corner_pt = D + V1 * d_straight
            end_pt = corner_pt + V2 * d_bent
            
            # Sharp skeleton
            skeleton0.lineTo(corner_pt)
            skeleton0.lineTo(end_pt)
            
            # Rounded skeleton (smooth corner)
            R = min(35.0, d_straight, d_bent)
            if R > 1.0:
                arc_start = corner_pt - V1 * R
                arc_end = corner_pt + V2 * R
                skeleton35.lineTo(arc_start)
                skeleton35.quadTo(corner_pt, arc_end)
                skeleton35.lineTo(end_pt)
            else:
                skeleton35.lineTo(corner_pt)
                skeleton35.lineTo(end_pt)
            
            # Place button centers on the simple L-path (straight lines only).
            # The capsule shape wraps around the icons, not vice versa.
            for i in range(7):
                dist = i * 44.0 * self._expansion
                if dist <= d_straight:
                    centers.append(D + V1 * dist)
                else:
                    centers.append(corner_pt + V2 * (dist - d_straight))
                    
        return skeleton0, skeleton35, centers

    def update_mask_and_geom(self):
        skeleton0, skeleton35, centers = self.get_bent_path_and_centers()
        
        if self._expansion < 0.01:
            c_path = QPainterPath()
            c_path.addEllipse(centers[0], 30, 30)  # slightly larger for AA
            self.setMask(QRegion(c_path.toFillPolygon().toPolygon()))
        else:
            # Use a slightly wider stroke (58px vs 54px visual) for the mask
            # so anti-aliased edges of the visual capsule aren't clipped
            stroker = QPainterPathStroker()
            stroker.setWidth(60)
            stroker.setCapStyle(Qt.PenCapStyle.RoundCap)
            stroker.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
            
            mask_img = QImage(640, 640, QImage.Format.Format_ARGB32_Premultiplied)
            mask_img.fill(Qt.GlobalColor.transparent)
            painter = QPainter(mask_img)
            painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
            # Paint both skeleton strokes individually (avoids jagged united())
            painter.fillPath(stroker.createStroke(skeleton0), Qt.GlobalColor.black)
            painter.fillPath(stroker.createStroke(skeleton35), Qt.GlobalColor.black)
            painter.end()
            self.setMask(QPixmap.fromImage(mask_img).mask())

    def update_theme(self):
        gen_settings = self.cfg.get('general_settings', {})
        dash_theme = gen_settings.get('dashboard_theme', 'Dark')
        
        # Base defaults (Dark theme)
        bg_rgb = (10, 10, 12)
        is_light = False
        self.border_color = QColor(255, 255, 255, int(255 * 0.15))
        self.text_color = "#e2e2e2"
        self.text_muted = "#8a8a93"
        self.accent_color = "#26c0d3" # Dashboard Cyan
        self.accent_btn_hover = QColor(255, 255, 255, int(255 * 0.08))
        self.power_hover_color = "#f43f5e"
        
        if dash_theme == 'Light':
            bg_rgb = (226, 228, 233)
            is_light = True
            self.border_color = QColor(0, 0, 0, int(255 * 0.08))
            self.text_color = "#24292f"
            self.text_muted = "#57606a"
            self.accent_color = "#0969da"
            self.accent_btn_hover = QColor(0, 0, 0, int(255 * 0.05))
        elif dash_theme == 'Gray':
            bg_rgb = (37, 37, 41) # Matched with body.gray-theme #252529
            self.border_color = QColor(255, 255, 255, int(255 * 0.08))
            self.text_color = "#ececef"
            self.text_muted = "#a0a0aa"
            self.accent_color = "#d0d0d8"
            self.accent_btn_hover = QColor(255, 255, 255, int(255 * 0.05))
        elif dash_theme == 'Desktop':
            # Check wallpaper light/dark vibe
            try:
                from utils import is_desktop_light_vibe
                is_light = is_desktop_light_vibe()
            except Exception:
                is_light = False
            
            accents = gen_settings.get('desktop_accents', [])
            if accents:
                # 1. Apply contrast logic identical to electron_dashboard/ui_dashboard_general.js
                final_accents = []
                for (r, g, b) in accents:
                    luma = (r * 0.299 + g * 0.587 + b * 0.114)
                    if is_light:
                        if luma > 140:
                            factor = 100 / (luma + 1)
                            final_accents.append((int(r * factor), int(g * factor), int(b * factor)))
                        else:
                            final_accents.append((r, g, b))
                    else:
                        if luma < 110:
                            factor = 140 / (luma + 1)
                            final_accents.append((min(255, int(r * factor)), min(255, int(g * factor)), min(255, int(b * factor))))
                        else:
                            final_accents.append((r, g, b))
                            
                # 2. Sort accents by most contrast for the primary accent (darkest for light vibe, brightest for dark vibe)
                def get_luma(c): return c[0]*0.299 + c[1]*0.587 + c[2]*0.114
                final_accents.sort(key=get_luma, reverse=not is_light)
                
                ar, ag, ab = final_accents[0]
                self.accent_color = f"rgb({ar}, {ag}, {ab})"
            else:
                ar, ag, ab = 59, 130, 246
                self.accent_color = "#3b82f6"
                
            if is_light:
                # Light theme: mix 5% accent with #E2E4E9 (226, 228, 233)
                bg_rgb = (int(ar * 0.05 + 226 * 0.95), int(ag * 0.05 + 228 * 0.95), int(ab * 0.05 + 233 * 0.95))
                self.border_color = QColor(ar, ag, ab, int(255 * 0.15))
                self.text_color = "#24292f"
                self.text_muted = "#57606a"
                self.accent_btn_hover = QColor(0, 0, 0, int(255 * 0.05))
                self.accent_color = f"rgb({ar}, {ag}, {ab})"
            else:
                # Dark theme: mix 12% accent with #121216 (18, 18, 22)
                bg_rgb = (int(ar * 0.12 + 18 * 0.88), int(ag * 0.12 + 18 * 0.88), int(ab * 0.12 + 22 * 0.88))
                # Border: mix 25% accent with white 8% 
                self.border_color = QColor(ar, ag, ab, int(255 * 0.35)) # Simplified for QPen
                self.text_color = "#e2e2e2"
                self.text_muted = "#8a8a93"
                self.accent_btn_hover = QColor(255, 255, 255, int(255 * 0.06))
                
        # Set base background color using QColor
        self.bg_color_base = QColor(bg_rgb[0], bg_rgb[1], bg_rgb[2])

    def create_themed_icon(self, svg_name, normal_color, hover_color):
        from config import BASE_DIR
        svg_path = os.path.join(BASE_DIR, "assets", svg_name)
        if not os.path.exists(svg_path):
            svg_path = os.path.join(BASE_DIR, "electron_dashboard", "assets", svg_name)
            
        if not os.path.exists(svg_path):
            return QIcon()
            
        pix_normal = QPixmap(18, 18)
        pix_normal.fill(Qt.GlobalColor.transparent)
        p1 = QPainter(pix_normal)
        renderer = QSvgRenderer(svg_path)
        renderer.render(p1)
        p1.setCompositionMode(QPainter.CompositionMode.CompositionMode_SourceIn)
        p1.fillRect(pix_normal.rect(), QColor(normal_color))
        p1.end()
        
        pix_hover = QPixmap(18, 18)
        pix_hover.fill(Qt.GlobalColor.transparent)
        p2 = QPainter(pix_hover)
        renderer.render(p2)
        p2.setCompositionMode(QPainter.CompositionMode.CompositionMode_SourceIn)
        p2.fillRect(pix_hover.rect(), QColor(hover_color))
        p2.end()
        
        icon = QIcon()
        icon.addPixmap(pix_normal, QIcon.Mode.Normal)
        icon.addPixmap(pix_hover, QIcon.Mode.Active)
        return icon

    def get_button_icon(self, idx, hovered):
        if idx == 0:
            return self.create_themed_icon("drag.svg", self.text_muted, self.accent_color)
        elif idx == 1:
            return self.create_themed_icon("Pandora.svg", self.text_muted, self.accent_color)
        elif idx == 2:
            return self.create_themed_icon("add.svg", self.text_muted, self.accent_color)
        elif idx == 3:
            return self.create_themed_icon("toggle grid.svg", self.text_muted, self.accent_color)
        elif idx == 4:
            return self.create_themed_icon("reset.svg", self.text_muted, self.accent_color)
        elif idx == 5:
            return self.create_themed_icon("power.svg", self.text_muted, self.power_hover_color)
        elif idx == 6:
            return self.create_close_icon(self.text_muted, self.accent_color)
        return QIcon()

    def create_close_icon(self, normal_color, hover_color):
        pix_normal = QPixmap(18, 18)
        pix_normal.fill(Qt.GlobalColor.transparent)
        p1 = QPainter(pix_normal)
        p1.setRenderHint(QPainter.RenderHint.Antialiasing)
        p1.setPen(QPen(QColor(normal_color), 2))
        p1.drawLine(4, 4, 14, 14)
        p1.drawLine(14, 4, 4, 14)
        p1.end()
        
        pix_hover = QPixmap(18, 18)
        pix_hover.fill(Qt.GlobalColor.transparent)
        p2 = QPainter(pix_hover)
        p2.setRenderHint(QPainter.RenderHint.Antialiasing)
        p2.setPen(QPen(QColor(hover_color), 2))
        p2.drawLine(4, 4, 14, 14)
        p2.drawLine(14, 4, 4, 14)
        p2.end()
        
        icon = QIcon()
        icon.addPixmap(pix_normal, QIcon.Mode.Normal)
        icon.addPixmap(pix_hover, QIcon.Mode.Active)
        return icon

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        alpha = int(180 + (255 - 180) * self._expansion)
        bg = QColor(self.bg_color_base.red(), self.bg_color_base.green(), self.bg_color_base.blue(), alpha)
        
        skeleton0, skeleton35, centers = self.get_bent_path_and_centers()
        
        if self._expansion < 0.05:
            # Collapsed Form: Draw only the single center icon (pill.svg, or drag.svg during drag operations)
            c_path = QPainterPath()
            c_path.addEllipse(centers[0], 27, 27)
            painter.fillPath(c_path, QBrush(bg))
            pen = QPen(QColor(self.border_color), 1.5)
            painter.strokePath(c_path, pen)
            
            icon_name = "drag.svg" if self.is_dragging else "pill.svg"
            icon = self.create_themed_icon(icon_name, self.text_muted, self.accent_color)
            icon.paint(painter, int(centers[0].x() - 9), int(centers[0].y() - 9), 18, 18)
        else:
            # Expanded Form: Draw bent capsule with smooth anti-aliased edges.
            # Instead of stroking the jagged united() path, we stroke the
            # smooth skeleton paths directly for a crisp border.
            
            # 1. Draw border first: stroke skeletons with wider pen (54 + 3 = 57)
            border_pen = QPen(QColor(self.border_color), 57)
            border_pen.setCapStyle(Qt.PenCapStyle.RoundCap)
            border_pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
            painter.strokePath(skeleton0, border_pen)
            painter.strokePath(skeleton35, border_pen)
            
            # 2. Draw fill on top: stroke skeletons with exact width (54)
            #    Uses CompositionMode_Source to avoid double-alpha in overlap region
            painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_Source)
            fill_pen = QPen(QBrush(bg), 54)
            fill_pen.setCapStyle(Qt.PenCapStyle.RoundCap)
            fill_pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
            painter.strokePath(skeleton0, fill_pen)
            painter.strokePath(skeleton35, fill_pen)
            painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_SourceOver)
            
            # Reveal buttons
            btn_opacity = self._expansion
            for i, pt in enumerate(centers):
                is_btn_hovered = (i == self.hovered_btn_idx)
                
                if is_btn_hovered:
                    pass # Just icon color change, no background circle
                
                icon = self.get_button_icon(i, is_btn_hovered)
                painter.save()
                painter.setOpacity(btn_opacity)
                # Paint icon with Mode.Active for correct active/hover states
                icon.paint(painter, int(pt.x() - 9), int(pt.y() - 9), 18, 18, Qt.AlignmentFlag.AlignCenter, QIcon.Mode.Active if is_btn_hovered else QIcon.Mode.Normal)
                painter.restore()
                
            # Draw Separator Line between button 5 (Power Off) and button 6 (Close)
            p5 = centers[5]
            p6 = centers[6]
            mid_x = (p5.x() + p6.x()) / 2.0
            mid_y = (p5.y() + p6.y()) / 2.0
            
            dx = p6.x() - p5.x()
            dy = p6.y() - p5.y()
            len_d = math.hypot(dx, dy)
            if len_d > 0:
                perp_x = -dy / len_d
                perp_y = dx / len_d
                
                x1 = mid_x - perp_x * 10 * self._expansion
                y1 = mid_y - perp_y * 10 * self._expansion
                x2 = mid_x + perp_x * 10 * self._expansion
                y2 = mid_y + perp_y * 10 * self._expansion
                
                painter.save()
                painter.setOpacity(btn_opacity)
                painter.setPen(QPen(QColor(self.border_color), 1.0))
                painter.drawLine(int(x1), int(y1), int(x2), int(y2))
                painter.restore()
            
    def enterEvent(self, event):
        if not self.is_dragging:
            self.animate_expansion(1.0)
            
    def leaveEvent(self, event):
        if not self.is_dragging:
            self.hovered_btn_idx = -1
            self.animate_expansion(0.0)
            self.update()
            
    def mouseMoveEvent(self, event):
        cx, cy = 320, 320
        off_x = self.drag_center_offset.x() * (1.0 - self._expansion)
        off_y = self.drag_center_offset.y() * (1.0 - self._expansion)
        
        if self.is_dragging:
            g_pos = event.globalPosition().toPoint()
            target_pos = g_pos - self.drag_position
            
            screen = QApplication.screenAt(g_pos)
            if not screen:
                screen = QApplication.primaryScreen()
            geom = screen.availableGeometry()
            
            # Only clamp the drag button circle (27px radius) to stay on screen
            R = 29
            
            v_cx = cx + off_x
            v_cy = cy + off_y
            
            ccx = target_pos.x() + v_cx
            ccy = target_pos.y() + v_cy
            
            ccx_clamped = max(geom.x() + R, min(geom.x() + geom.width() - R, ccx))
            ccy_clamped = max(geom.y() + R, min(geom.y() + geom.height() - R, ccy))
            
            self.move(int(ccx_clamped - v_cx), int(ccy_clamped - v_cy))
            event.accept()
        elif self._expansion > 0.9:
            lp = event.position()
            new_hover = -1
            
            _, _, centers = self.get_bent_path_and_centers()
            for i, pt in enumerate(centers):
                dist = math.hypot(lp.x() - pt.x(), lp.y() - pt.y())
                if dist <= 19:
                    new_hover = i
                    break
                        
            if new_hover != self.hovered_btn_idx:
                self.hovered_btn_idx = new_hover
                self.update()
                
    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            if self._expansion < 0.1:
                # Collapsed: click starts dragging
                self.is_dragging = True
                self.drag_position = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
                self.update()
            elif self.hovered_btn_idx == 0:
                # Drag button clicked: collapse and drag
                self.is_dragging = True
                self.drag_position = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
                
                # Offset center to the drag button coordinates (collapse physically to drag button)
                cx, cy = 320, 320
                _, _, centers = self.get_bent_path_and_centers()
                self.drag_center_offset = (centers[0] - QPointF(cx, cy)).toPoint()
                self.animate_expansion(0.0)
            elif self.hovered_btn_idx > 0:
                self.trigger_button_action(self.hovered_btn_idx)
            event.accept()
            
    def mouseReleaseEvent(self, event):
        if self.is_dragging:
            self.is_dragging = False
            self.snap_to_closest_edge()
            
            # Check if mouse is still within the widget's bounds to decide expansion
            lp = self.mapFromGlobal(event.globalPosition().toPoint())
            if self.rect().contains(lp):
                self.animate_expansion(1.0)
            else:
                self.animate_expansion(0.0)
            self.update()
            event.accept()
            
    def trigger_button_action(self, idx):
        if idx == 1:
            self.restore_dashboard()
        elif idx == 2:
            self.add_folder()
        elif idx == 3:
            self.toggle_grid()
        elif idx == 4:
            self.restart_app()
        elif idx == 5:
            self.power_off()
        elif idx == 6:
            self.hide_pill()
            
    def animate_expansion(self, target):
        if hasattr(self, 'exp_anim') and self.exp_anim.state() == QPropertyAnimation.State.Running:
            self.exp_anim.stop()
            
        self.exp_anim = QPropertyAnimation(self, b"expansion")
        self.exp_anim.setDuration(220)
        self.exp_anim.setStartValue(self._expansion)
        self.exp_anim.setEndValue(target)
        self.exp_anim.setEasingCurve(QEasingCurve.Type.OutCubic)
        self.exp_anim.start()
        
    def snap_to_closest_edge(self):
        cx, cy = 320, 320
        screen = QApplication.screenAt(self.pos() + QPoint(cx, cy))
        if not screen:
            screen = QApplication.primaryScreen()
        geom = screen.availableGeometry()
        
        # Center of visible capsule relative to screen
        ccx = self.x() + cx + self.drag_center_offset.x()
        ccy = self.y() + cy + self.drag_center_offset.y()
        
        dist_left = ccx - geom.x()
        dist_right = (geom.x() + geom.width()) - ccx
        dist_top = ccy - geom.y()
        dist_bottom = (geom.y() + geom.height()) - ccy
        
        min_dist = min(dist_left, dist_right, dist_top, dist_bottom)
        
        target_edge = 'right'
        if min_dist == dist_left:
            target_edge = 'left'
        elif min_dist == dist_right:
            target_edge = 'right'
        elif min_dist == dist_top:
            target_edge = 'top'
        elif min_dist == dist_bottom:
            target_edge = 'bottom'
            
        self.animate_snap(target_edge, geom)
        
    def animate_snap(self, edge, geom):
        cx, cy = 320, 320
        # Current drag button position in screen coordinates
        interp = 1.0 - self._expansion
        ccx = self.x() + cx + self.drag_center_offset.x() * interp
        ccy = self.y() + cy + self.drag_center_offset.y() * interp
        
        self.edge = edge
        self._rotation = -90.0 if edge in ['top', 'bottom'] else 0.0
        self.orientation = 'horizontal' if edge in ['top', 'bottom'] else 'vertical'
        
        # Reset offset — when expanded, D = (cx, cy), which IS centers[0]
        self.drag_center_offset = QPoint(0, 0)
        
        self.move_to_edge(edge, geom, ccx, ccy)
        self.update_mask_and_geom()
        self.update()
        
        # Save snapped edge and center coordinates ratios to config
        try:
            from config import ConfigManager
            cfg = ConfigManager.load()
            gen_settings = cfg.setdefault('general_settings', {})
            gen_settings['pill_edge'] = self.edge
            
            ccx = self.x() + 320
            ccy = self.y() + 320
            gen_settings['pill_center_x_ratio'] = (ccx - geom.x()) / geom.width()
            gen_settings['pill_center_y_ratio'] = (ccy - geom.y()) / geom.height()
            
            ConfigManager.save(cfg)
        except Exception as e:
            print(f"Failed to save snap config: {e}")
        
    def move_to_edge(self, edge, geom, cap_x=None, cap_y=None):
        cx, cy = 320, 320
        S = 44   # grid step for quantized positioning along edge
        M = 29   # capsule radius — how close center gets to the edge
        
        if cap_x is None:
            cap_x = self.x() + cx
        if cap_y is None:
            cap_y = self.y() + cy
        
        if edge == 'right' or edge == 'left':
            # Quantize Y position along edge to nearest grid step
            target_y = cap_y  # just keep where the user dropped it
            
            # Snap to nearest grid step relative to screen center
            screen_mid_y = geom.y() + geom.height() / 2.0
            k = round((target_y - screen_mid_y) / S)
            target_y = screen_mid_y + k * S
            
            # Clamp so the capsule center stays on screen
            target_y = max(geom.y() + M, min(geom.y() + geom.height() - M, target_y))
            
            if edge == 'right':
                target_x = geom.x() + geom.width() - M
            else:
                target_x = geom.x() + M
                
        elif edge == 'top' or edge == 'bottom':
            # Quantize X position along edge to nearest grid step
            target_x = cap_x
            
            screen_mid_x = geom.x() + geom.width() / 2.0
            k = round((target_x - screen_mid_x) / S)
            target_x = screen_mid_x + k * S
            
            # Clamp
            target_x = max(geom.x() + M, min(geom.x() + geom.width() - M, target_x))
            
            if edge == 'top':
                target_y = geom.y() + M
            else:
                target_y = geom.y() + geom.height() - M
            
        self.setGeometry(int(target_x - cx), int(target_y - cy), 640, 640)
        
    def restore_dashboard(self):
        self.hide()
        self.dashboard.show()
        
    def add_folder(self):
        if hasattr(self.dashboard, 'create_folder_callback') and self.dashboard.create_folder_callback:
            self.dashboard.create_folder_callback("Normal")
            
    def toggle_grid(self):
        self.grid_overlay.toggle()
        
    def restart_app(self):
        self.restart_func()
        
    def power_off(self):
        self.quit_func()
        
    def hide_pill(self):
        self.hide()
