import time
import math
import random
from PyQt6.QtCore import QRectF, Qt, QPointF, QTimer
from PyQt6.QtGui import (QPainter, QFont, QColor, QPen, QBrush, QPainterPath,
                          QRadialGradient, QPixmap, QImage)
from PyQt6.QtWidgets import QApplication, QGraphicsScene, QGraphicsPixmapItem, QGraphicsBlurEffect
from .base import BaseHubModule
from utils import VectorIcon, MediaSessionManager, IconExtractor

# Precomputed trigonometric values for shape vertex generation in 60FPS render loop
_CIRCLE_TRIG = [(math.cos(i * 2 * math.pi / 16) / 2.0, math.sin(i * 2 * math.pi / 16) / 2.0) for i in range(16)]
_HEX_TRIG = [(math.cos(math.radians(i * 60 + 30)) * 1.15 / 2.0, math.sin(math.radians(i * 60 + 30)) * 1.15 / 2.0) for i in range(6)]

_ROUNDED_TRIG = []
for i in range(4):
    a = math.radians(270 + i * 30)
    _ROUNDED_TRIG.append((math.cos(a), math.sin(a), 0.5, -0.5))
for i in range(4):
    a = math.radians(0 + i * 30)
    _ROUNDED_TRIG.append((math.cos(a), math.sin(a), 0.5, 0.5))
for i in range(4):
    a = math.radians(90 + i * 30)
    _ROUNDED_TRIG.append((math.cos(a), math.sin(a), -0.5, 0.5))
for i in range(4):
    a = math.radians(180 + i * 30)
    _ROUNDED_TRIG.append((math.cos(a), math.sin(a), -0.5, -0.5))

_DIAMOND_TRIG = [(math.cos(math.radians(i * 90)) / 2.0, math.sin(math.radians(i * 90)) / 2.0) for i in range(4)]

def get_shape_vertices(cx, cy, w, h, shape, gy, block_size):
    if shape == "Circles":
        return [QPointF(cx + ux * w, cy + uy * h) for ux, uy in _CIRCLE_TRIG]
    elif shape == "Hexagons":
        offset_x = (block_size / 2.0) if gy % 2 == 1 else 0.0
        cx_eff = cx + offset_x
        return [QPointF(cx_eff + ux * w, cy + uy * h) for ux, uy in _HEX_TRIG]
    elif shape == "Rounded":
        r = 4.0
        half_w_minus_r = w / 2.0 - r
        half_h_minus_r = h / 2.0 - r
        return [
            QPointF(cx + sx * half_w_minus_r + ca * r, cy + sy * half_h_minus_r + sa * r)
            for ca, sa, sx, sy in _ROUNDED_TRIG
        ]
    elif shape == "Diamonds":
        return [QPointF(cx + ux * w, cy + uy * h) for ux, uy in _DIAMOND_TRIG]
    else: # "Square"
        return [
            QPointF(cx - w / 2.0, cy - h / 2.0),
            QPointF(cx + w / 2.0, cy - h / 2.0),
            QPointF(cx + w / 2.0, cy + h / 2.0),
            QPointF(cx - w / 2.0, cy + h / 2.0)
        ]


class MediaHub(BaseHubModule):
    def __init__(self, manager):
        super().__init__(manager)
        self.media_mgr = MediaSessionManager.instance()
        
        self._smoothed_peak = 0.0
        self._average_peak = 0.15
        self._voxel_physics = {}
        
        self._cached_thumb = None
        self._cached_round_thumb = None
        self._cached_thumb_id = ""
        self._cached_size = 0
        self._cached_strength = -1
        self._cached_art_style = ""
        self._dominant_color = QColor(189, 147, 249, 180) # Default
        
        self._prev_thumb = None
        self._prev_color_map = None
        self._thumb_anim_progress = 1.0
        self._prev_timeline_progress = 0.0
        
        # Caching for 8-Bit Mosaic Scale
        self._cached_mosaic_thumb_id = ""
        self._cached_block_size = -1
        self._cached_mosaic_color_map = None
        self._cached_mosaic_prev_thumb_id = ""
        self._cached_mosaic_prev_block_size = -1
        self._cached_mosaic_prev_color_map = None
        
        # New State for Spacebar Override
        self._holding = False
        self._space_pressed = False
        self._space_press_time = 0.0
        
        self.settings = {}
        
        self.media_tools = [
            {"id": "volume", "icon": "volume up", "label": "Volume"},
            {"id": "next", "icon": "next", "label": "Next Track"},
            {"id": "timeline", "icon": "clock", "label": "Timeline"},
            {"id": "prev", "icon": "prev", "label": "Prev Track"}
        ]

    def _clear_cache(self, track_info=None):
        # We handle this manually in _get_round_thumbnail for smoother transitions
        pass

    def load_settings(self, settings):
        self.settings = settings
        self._clear_cache()
        self._cached_thumb_id = ""
        self._cached_art_style = ""
        self._cached_mosaic_thumb_id = ""
        self._cached_block_size = -1
        self._cached_mosaic_color_map = None

    def cleanup(self):
        self._holding = False
        self._space_pressed = False
        self._space_press_time = 0.0

    def _extract_color(self, img: QImage):
        if img.isNull(): return QColor(189, 147, 249, 180)
        scaled = img.scaled(1, 1, Qt.AspectRatioMode.IgnoreAspectRatio, Qt.TransformationMode.SmoothTransformation)
        return QColor(scaled.pixel(0, 0))

    def _get_pandora_icon_image(self):
        if not hasattr(self, '_pandora_icon_img') or self._pandora_icon_img is None:
            try:
                import os
                from PyQt6.QtSvg import QSvgRenderer
                from PyQt6.QtGui import QImage, QPainter
                from PyQt6.QtCore import QRectF, Qt
                
                svg_path = "assets/Pandora.svg"
                if not os.path.exists(svg_path):
                    svg_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "assets", "Pandora.svg")
                
                img = QImage(256, 256, QImage.Format.Format_ARGB32)
                img.fill(Qt.GlobalColor.transparent)
                renderer = QSvgRenderer(svg_path)
                if renderer.isValid():
                    p = QPainter(img)
                    renderer.render(p, QRectF(0, 0, 256, 256))
                    p.end()
                    self._pandora_icon_img = img
                else:
                    self._pandora_icon_img = None
            except Exception as e:
                print(f"[MediaHub] Failed to load Pandora SVG: {e}")
                self._pandora_icon_img = None
        return self._pandora_icon_img

    def _get_fallback_thumbnail(self, track):
        has_media = track.get('title') and track['title'] != "No Media" and track['title'] != ""
        if not has_media:
            return self._get_pandora_icon_image(), "pandora_default_icon"
            
        thumb = self.media_mgr.thumbnail
        if thumb is not None and not thumb.isNull():
            return thumb, track.get('thumb_id', '')
            
        # Track changed grace period - removed the 1.5s hard delay
        # We rely strictly on `is_thumbnail_loading` from the daemon.
        is_loading = track.get('is_thumbnail_loading', False)
        
        # Hold onto last valid thumb for THIS session ONLY while the daemon explicitly says it's loading a new one
        session_id = track.get('session_id', '')
        if is_loading:
            last_session_thumbs = getattr(self.media_mgr, '_last_session_thumbs', {})
            if session_id and session_id in last_session_thumbs:
                return last_session_thumbs[session_id], getattr(self, '_prev_track_id', '')
            
        # Fallback to the media source app icon
        app_id = track.get('app_id', '')
        app_icon_pix = IconExtractor.get_app_icon_pixmap(app_id, 256)
        if app_icon_pix and not app_icon_pix.isNull():
            return app_icon_pix.toImage(), f"app_icon_{app_id}"
            
        return self._get_pandora_icon_image(), "pandora_fallback_icon"

    def _get_round_thumbnail(self, size, track, override_strength=None):
        thumb, thumb_id = self._get_fallback_thumbnail(track)
        has_media = track.get('title') and track['title'] != "No Media" and track['title'] != ""
        
        if thumb is None:
            if getattr(self, '_cached_thumb_id', '') != "":
                if self._cached_round_thumb and not self._cached_round_thumb.isNull():
                    self._prev_thumb = self._cached_round_thumb
                self._thumb_anim_progress = 0.0
            self._cached_thumb_id = ""
            self._cached_thumb = None
            self._cached_round_thumb = None
            return None
            
        blur_strength = override_strength if override_strength is not None else self.settings.get('effect_strength')
        if blur_strength is None: blur_strength = 25

        track_id = f"{track.get('title', '')}_{track.get('artist', '')}_{track.get('app_id', '')}"
        art_style = self.settings.get('art_style', 'Gaussian Blur')
        
        # Check cache against track_id, thumb_id, size, blur, and style
        if getattr(self, '_cached_track_id', '') == track_id and getattr(self, '_cached_thumb_id', '') == thumb_id and self._cached_round_thumb is not None and size == self._cached_size and getattr(self, '_cached_strength', -1) == blur_strength and getattr(self, '_cached_art_style', '') == art_style:
            return self._cached_round_thumb

        # Trigger animation when track_id changes OR thumb_id changes
        if getattr(self, '_cached_track_id', '') != "" and (self._cached_track_id != track_id or getattr(self, '_cached_thumb_id', '') != thumb_id):
            if self._cached_round_thumb and not self._cached_round_thumb.isNull():
                self._prev_thumb = self._cached_round_thumb
            if self._cached_thumb and not self._cached_thumb.isNull():
                self._prev_raw_thumb = self._cached_thumb
                self._prev_track_id = self._cached_track_id
            self._thumb_anim_progress = 0.0

        self._cached_track_id = track_id
        self._cached_thumb_id = thumb_id
        self._cached_thumb = thumb
        self._cached_size = size
        self._cached_strength = blur_strength
        self._cached_art_style = art_style
        self._dominant_color = self._extract_color(thumb)
        
        result = QPixmap(size, size)
        result.fill(Qt.GlobalColor.transparent)
        p = QPainter(result)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
        path = QPainterPath()
        path.addEllipse(0, 0, size, size)
        p.setClipPath(path)
        
        if art_style == "Gaussian Blur" and blur_strength > 0:
            scaled = thumb.scaled(size, size, Qt.AspectRatioMode.KeepAspectRatioByExpanding, Qt.TransformationMode.SmoothTransformation)
            x = (scaled.width() - size) // 2
            y = (scaled.height() - size) // 2
            cropped = scaled.copy(x, y, size, size)
            
            scene = QGraphicsScene()
            item = QGraphicsPixmapItem(QPixmap.fromImage(cropped))
            blur = QGraphicsBlurEffect()
            blur.setBlurRadius(blur_strength * 0.5)
            item.setGraphicsEffect(blur)
            scene.addItem(item)
            
            blurred_pixmap = QPixmap(size, size)
            blurred_pixmap.fill(Qt.GlobalColor.transparent)
            blur_painter = QPainter(blurred_pixmap)
            scene.render(blur_painter)
            blur_painter.end()
            p.drawPixmap(0, 0, blurred_pixmap)
        else:
            scaled = thumb.scaled(size, size, Qt.AspectRatioMode.KeepAspectRatioByExpanding, Qt.TransformationMode.SmoothTransformation)
            x = (scaled.width() - size) // 2
            y = (scaled.height() - size) // 2
            cropped = scaled.copy(x, y, size, size)
            p.drawImage(0, 0, cropped)

        p.end()
        self._cached_round_thumb = result
        return result

    def draw(self, p, cx, cy, inner_radius):
        track = self.media_mgr.current_track
        has_media = track.get('title') and track['title'] != "No Media" and track['title'] != ""
        
        # Smoothly interpolate dominant color on every frame for gradual color shifts
        if has_media:
            curr_raw = self.media_mgr.thumbnail
            if curr_raw is None:
                app_id = track.get('app_id', '')
                app_icon_pix = IconExtractor.get_app_icon_pixmap(app_id, 256)
                if app_icon_pix and not app_icon_pix.isNull():
                    curr_raw = app_icon_pix.toImage()
                else:
                    curr_raw = self._get_pandora_icon_image()
            if curr_raw and not curr_raw.isNull():
                if curr_raw is self.media_mgr.thumbnail:
                    session_id = track.get('session_id', '')
                    if session_id:
                        if not hasattr(self.media_mgr, '_last_session_thumbs'):
                            self.media_mgr._last_session_thumbs = {}
                        self.media_mgr._last_session_thumbs[session_id] = curr_raw
                if getattr(self, '_cached_raw_for_color', None) != curr_raw:
                    self._cached_raw_for_color = curr_raw
                    self._target_color = self._extract_color(curr_raw)
                    
                target_color = getattr(self, '_target_color', QColor(189, 147, 249, 180))
                
                if not hasattr(self, '_dominant_color') or self._dominant_color is None:
                    self._dominant_color = target_color
                else:
                    r = self._dominant_color.red() + (target_color.red() - self._dominant_color.red()) * 0.08
                    g = self._dominant_color.green() + (target_color.green() - self._dominant_color.green()) * 0.08
                    b = self._dominant_color.blue() + (target_color.blue() - self._dominant_color.blue()) * 0.08
                    self._dominant_color = QColor(int(r), int(g), int(b))
        
        sessions = track.get('available_sessions', [])
        multi_session = len(sessions) > 1
        
        visualizer = self.settings.get('visualizer', 'None')
        is_playing = track.get('status') == 'Playing'
        
        if visualizer != "None" and self.manager.halo.isVisible() and has_media:
            peak = 0.0
            app_inst = QApplication.instance()
            if hasattr(app_inst, 'media_daemon'):
                peak = getattr(app_inst.media_daemon.state, 'audio_peak', 0.0)
                
            # If the peak is zero or extremely low (e.g. sandbox VM or driver limitations)
            # but a track is actively playing, generate an organic simulated peak so the visualizer animates
            if peak <= 0.01 and is_playing:
                t_now = time.time()
                peak = 0.12 + 0.08 * math.sin(t_now * 5.0) + 0.04 * math.sin(t_now * 11.0)
                peak += random.uniform(-0.02, 0.02)
                peak = max(0.0, min(1.0, peak))
                
            # Dynamic Normalization (Automatic Gain Control) based on slow moving average of peaks
            if peak > 0.005:
                self._average_peak += (peak - self._average_peak) * 0.01
                self._average_peak = max(0.05, min(1.0, self._average_peak))
                
            normalized_peak = peak / self._average_peak
            normalized_peak = max(0.0, min(1.0, normalized_peak))
            
            self._smoothed_peak += (normalized_peak - self._smoothed_peak) * 0.4
        else:
            self._smoothed_peak = 0.0
            self._average_peak = 0.15

        # Exponent 0.8 makes the curve rise quickly at low/med values, but keeps them distinct
        eased_peak = max(0.0, self._smoothed_peak) ** 0.8
        active_id = None
        if self._holding:
            if hasattr(self.manager.halo, 'active_index') and self.manager.halo.active_index != -1:
                tools = self.manager.halo.current_tools
                if self.manager.halo.active_index < len(tools):
                    active_id = tools[self.manager.halo.active_index]['id']

        # 1. Base Hub (Album Art Background)
        size = int(inner_radius * 2) - 8
        art_style = self.settings.get('art_style', 'Gaussian Blur')
        effect_strength = self.settings.get('effect_strength')
        if effect_strength is None: effect_strength = 25
        
        global_op = p.opacity()

        # Edge Ring EQ (Wavy Line)
        if visualizer == "Edge Ring EQ" and eased_peak > 0.01:
            p.setBrush(Qt.GlobalColor.transparent)
            glow_c = QColor(self._dominant_color)
            glow_c.setAlpha(int(eased_peak * 180 * global_op))
            p.setPen(QPen(glow_c, 2 + int(eased_peak * 12), Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
            
            ring_r = size//2 + 10
            path = QPainterPath(); pts = 120; t_now = time.time()
            
            p1_level = eased_peak
            p2_level = max(0.0, (eased_peak - 0.3) / 0.7)
            p3_level = max(0.0, (eased_peak - 0.6) / 0.4)
            
            targets = [math.radians(30-90), math.radians(150-90), math.radians(270-90)]
            levels = [p1_level, p2_level, p3_level]
            
            for i in range(pts + 1):
                angle = (i / pts) * 2 * math.pi - (math.pi / 2)
                wave_sum = 0
                for tidx, target_rad in enumerate(targets):
                    if levels[tidx] <= 0: continue
                    diff = abs(angle - target_rad)
                    if diff > math.pi: diff = 2 * math.pi - diff
                    spread = 0.4 + (levels[tidx] * 0.2)
                    bump = math.exp(-(diff**2) / spread)
                    fluid_motion = 1.0 + math.sin(t_now * 10 + angle * 4) * 0.15
                    wave_sum += bump * levels[tidx] * 50 * fluid_motion
                
                wave_sum += math.sin(angle * 12 + t_now * 15) * (eased_peak * 3)
                r = ring_r + wave_sum
                tx = cx + math.cos(angle) * r
                ty = cy + math.sin(angle) * r
                if i == 0: path.moveTo(tx, ty)
                else: path.lineTo(tx, ty)
            path.closeSubpath(); p.drawPath(path)

        # Draw the Thumbnail/Art
        if art_style == "8-Bit Mosaic" and effect_strength > 0:
            thumb, thumb_id = self._get_fallback_thumbnail(track)
            mosaic_style = self.settings.get('mosaic_style', 'Flat')
            mosaic_shape = self.settings.get('mosaic_shape', 'Square')
            if thumb:
                block_size = int(12 + (effect_strength / 100.0) * 32)
                grid_dim = size // block_size
                
                if getattr(self, '_cached_mosaic_thumb_id', '') == thumb_id and getattr(self, '_cached_block_size', -1) == block_size and self._cached_mosaic_color_map is not None:
                    color_map = self._cached_mosaic_color_map
                else:
                    self._cached_mosaic_thumb_id = thumb_id
                    self._cached_block_size = block_size
                    color_map = thumb.scaled(grid_dim, grid_dim, Qt.AspectRatioMode.IgnoreAspectRatio, Qt.TransformationMode.SmoothTransformation)
                    self._cached_mosaic_color_map = color_map
                
                anim_prog = getattr(self, '_thumb_anim_progress', 1.0)
                prev_color_map = None
                if anim_prog < 1.0 and hasattr(self, '_prev_raw_thumb') and self._prev_raw_thumb:
                    prev_track_id = getattr(self, '_prev_track_id', '')
                    if getattr(self, '_cached_mosaic_prev_thumb_id', '') == prev_track_id and getattr(self, '_cached_mosaic_prev_block_size', -1) == block_size and self._cached_mosaic_prev_color_map is not None:
                        prev_color_map = self._cached_mosaic_prev_color_map
                    else:
                        self._cached_mosaic_prev_thumb_id = prev_track_id
                        self._cached_mosaic_prev_block_size = block_size
                        prev_color_map = self._prev_raw_thumb.scaled(grid_dim, grid_dim, Qt.AspectRatioMode.IgnoreAspectRatio, Qt.TransformationMode.SmoothTransformation)
                        self._cached_mosaic_prev_color_map = prev_color_map
                    self._thumb_anim_progress = min(1.0, anim_prog + 0.1)
                    self.manager.halo.update()

                p.save()
                p.translate(cx - size//2, cy - size//2)
                path = QPainterPath(); path.addEllipse(0, 0, size, size); p.setClipPath(path)
                
                grid_offset = (size - (grid_dim * block_size)) / 2.0
                p.translate(grid_offset, grid_offset)
                
                p.setPen(Qt.PenStyle.NoPen)
                
                cache_key = (grid_dim, block_size)
                if getattr(self, '_cached_grid_dim_key', None) == cache_key and hasattr(self, '_cached_blocks'):
                    blocks = self._cached_blocks
                    physics_states = self._cached_physics_states
                else:
                    blocks = []
                    max_dist = grid_dim / 2.0
                    margin = 3.0
                    for gy in range(grid_dim):
                        for gx in range(grid_dim):
                            dcx = gx - grid_dim / 2 + 0.5
                            dcy = gy - grid_dim / 2 + 0.5
                            dist = math.hypot(dcx, dcy)
                            if dist > max_dist + margin:
                                continue
                            pdx = dcx / dist if dist > 0 else 0.0
                            pdy = dcy / dist if dist > 0 else 0.0
                            pa = (dist / max_dist) * (block_size * 0.8) if max_dist > 0 else 0.0
                            blocks.append((gx, gy, dist, pdx, pdy, pa))
                    
                    blocks.sort(key=lambda item: item[2], reverse=True)
                    self._cached_grid_dim_key = cache_key
                    self._cached_blocks = blocks
                    self._cached_physics_states = [{'vx': 0.0, 'vy': 0.0, 'ox': 0.0, 'oy': 0.0} for _ in range(len(blocks))]
                    physics_states = self._cached_physics_states

                for idx, (gx, gy, dist, pdx, pdy, pa) in enumerate(blocks):
                    base_bx = gx * block_size
                    base_by = gy * block_size
                    bx, by = base_bx, base_by
                    if mosaic_style == "Extrusion":
                        bx += pdx * pa
                        by += pdy * pa

                    col = QColor(color_map.pixel(gx, gy))
                    if global_op < 1.0:
                        col.setAlpha(int(col.alpha() * global_op))
                        
                    if prev_color_map and anim_prog < 1.0:
                        p_col = QColor(prev_color_map.pixel(gx, gy))
                        # Radial color wave sweep from center outwards
                        max_d = grid_dim / 2.0
                        d_norm = dist / max_d if max_d > 0 else 0.0
                        local_prog = anim_prog * 1.4 - d_norm * 0.4
                        local_prog = max(0.0, min(1.0, local_prog))
                        e_prog = 1.0 - (1.0 - local_prog) ** 2
                        col = QColor(int(p_col.red() + (col.red() - p_col.red()) * e_prog), int(p_col.green() + (col.green() - p_col.green()) * e_prog), int(p_col.blue() + (col.blue() - p_col.blue()) * e_prog))
                    
                    draw_w = block_size - 2
                    draw_h = block_size - 2
                    
                    t_now = time.time()
                    ripple = 0.5 + 0.5 * math.sin(t_now * 15.0 - dist * 0.8)
                    local_peak = eased_peak * ripple

                    if visualizer == "Voxel Wiggle":
                        state = physics_states[idx]
                        force = (local_peak * 4.0 + (random.random() - 0.5) * local_peak * 10.0) if dist > 0 else 0.0
                        fx = pdx * force
                        fy = pdy * force
                        state['vx'] = (state['vx'] + fx - 0.35 * state['ox']) * 0.7
                        state['vy'] = (state['vy'] + fy - 0.35 * state['oy']) * 0.7
                        state['ox'] += state['vx']
                        state['oy'] += state['vy']
                        bx += state['ox']
                        by += state['oy']
                    elif visualizer == "Size Pulsing":
                        shrink = (1.0 - local_peak) * (block_size * 0.4)
                        bx += shrink/2.0
                        by += shrink/2.0
                        draw_w -= shrink
                        draw_h -= shrink
                        if mosaic_style == "Extrusion":
                            bx += pdx * local_peak * 15.0
                            by += pdy * local_peak * 15.0
                    elif visualizer == "Brightness Strobing":
                        br = 1.0 + local_peak * 1.0
                        col = QColor(min(255, int(col.red()*br)), min(255, int(col.green()*br)), min(255, int(col.blue()*br)), col.alpha())

                    if draw_w > 0 and draw_h > 0:
                        base_cx = base_bx + draw_w / 2.0
                        base_cy = base_by + draw_h / 2.0
                        front_cx = bx + draw_w / 2.0
                        front_cy = by + draw_h / 2.0
                        
                        if mosaic_style == "Extrusion":
                            p.setBrush(col.darker(150))
                            dist_ext = math.hypot(front_cx - base_cx, front_cy - base_cy)
                            steps = max(1, int(dist_ext))
                            dx = (front_cx - base_cx) / steps
                            dy = (front_cy - base_cy) / steps
                            
                            for step in range(steps):
                                e_cx = base_cx + dx * step
                                e_cy = base_cy + dy * step
                                e_bx = e_cx - draw_w / 2.0
                                e_by = e_cy - draw_h / 2.0
                                if mosaic_shape == "Circles":
                                    p.drawEllipse(int(e_bx), int(e_by), int(draw_w), int(draw_h))
                                elif mosaic_shape == "Rounded":
                                    p.drawRoundedRect(int(e_bx), int(e_by), int(draw_w), int(draw_h), 4.0, 4.0)
                                elif mosaic_shape in ["Hexagons", "Diamonds"]:
                                    pts = get_shape_vertices(e_cx, e_cy, draw_w, draw_h, mosaic_shape, gy, block_size)
                                    path = QPainterPath()
                                    path.moveTo(pts[0])
                                    for pt in pts[1:]: path.lineTo(pt)
                                    path.closeSubpath()
                                    p.drawPath(path)
                                else: # Square
                                    p.drawRect(int(e_bx), int(e_by), int(draw_w), int(draw_h))
                                
                        p.setBrush(col)
                        if mosaic_shape == "Circles":
                            p.drawEllipse(int(bx), int(by), int(draw_w), int(draw_h))
                        elif mosaic_shape == "Rounded":
                            p.drawRoundedRect(int(bx), int(by), int(draw_w), int(draw_h), 4.0, 4.0)
                        elif mosaic_shape in ["Hexagons", "Diamonds"]:
                            front_pts = get_shape_vertices(front_cx, front_cy, draw_w, draw_h, mosaic_shape, gy, block_size)
                            path_front = QPainterPath()
                            path_front.moveTo(front_pts[0])
                            for pt in front_pts[1:]:
                                path_front.lineTo(pt)
                            path_front.closeSubpath()
                            p.drawPath(path_front)
                        else: # Square
                            p.drawRect(int(bx), int(by), int(draw_w), int(draw_h))
                p.restore()
            else:
                pix = VectorIcon.pixmap("music", self._dominant_color.name(), 40)
                p.drawPixmap(int(cx - 20), int(cy - 40), pix)
        else:
            thumb = self._get_round_thumbnail(size, track, override_strength=effect_strength)
            if thumb:
                p.save()
                
                # Advance thumbnail transition animation
                anim_prog = getattr(self, '_thumb_anim_progress', 1.0)
                if anim_prog < 1.0:
                    self._thumb_anim_progress = min(1.0, anim_prog + 0.08)
                    self.manager.halo.update()
                
                # Apply scale transform for Breathing Blur, Size Pulsing, or Voxel Wiggle fallbacks on standard art
                global_op = p.opacity()
                if (visualizer in ["Breathing Blur", "Size Pulsing", "Voxel Wiggle"]) and eased_peak > 0.01:
                    scale = 1.0 + (eased_peak * 0.08)
                    p.translate(cx, cy)
                    p.scale(scale, scale)
                    
                    if anim_prog < 1.0 and hasattr(self, '_prev_thumb') and self._prev_thumb:
                        p.setOpacity(global_op * (1.0 - anim_prog))
                        p.drawPixmap(int(-size//2), int(-size//2), self._prev_thumb)
                        
                    p.setOpacity(global_op * anim_prog)
                    p.drawPixmap(int(-size//2), int(-size//2), thumb)
                else:
                    if anim_prog < 1.0 and hasattr(self, '_prev_thumb') and self._prev_thumb:
                        p.setOpacity(global_op * (1.0 - anim_prog))
                        p.drawPixmap(int(cx - size//2), int(cy - size//2), self._prev_thumb)
                        
                    p.setOpacity(global_op * anim_prog)
                    p.drawPixmap(int(cx - size//2), int(cy - size//2), thumb)
                
                p.setOpacity(global_op)
                p.restore()
                
                # Apply Brightness Strobing overlay if selected
                if visualizer == "Brightness Strobing" and eased_peak > 0.01:
                    p.save()
                    p.setBrush(QColor(255, 255, 255, int(eased_peak * 60)))
                    p.setPen(Qt.PenStyle.NoPen)
                    p.drawEllipse(QPointF(cx, cy), size//2, size//2)
                    p.restore()
            else:
                pix = VectorIcon.pixmap("music", self._dominant_color.name(), 40)
                p.drawPixmap(int(cx - 20), int(cy - 40), pix)

        if thumb:
            grad = QRadialGradient(cx, cy, inner_radius)
            grad.setColorAt(0.4, QColor(0, 0, 0, 40)); grad.setColorAt(0.9, QColor(0, 0, 0, 200))
            p.setBrush(QBrush(grad)); p.setPen(Qt.PenStyle.NoPen); p.drawEllipse(QPointF(cx, cy), size//2, size//2)

        # 2. Arcs & Info
        arc_r = inner_radius - 6; arc_rect = QRectF(cx - arc_r, cy - arc_r, arc_r * 2, arc_r * 2)
        show_timeline = self.settings.get('show_timeline', True)
        if show_timeline:
            pos = track.get('position', 0); dur = track.get('duration', 0); sync_time = track.get('sync_time', 0)
            if is_playing and sync_time > 0 and dur > 0:
                pos += time.time() - sync_time
                if pos > dur: pos = dur
            progress = min(1.0, pos / dur) if dur > 0 else 0
            anim_prog = getattr(self, '_thumb_anim_progress', 1.0)
            if anim_prog < 1.0:
                e_prog = 1.0 - (1.0 - anim_prog) ** 2; prev_prog = getattr(self, '_prev_timeline_progress', 0.0)
                progress = prev_prog + (progress - prev_prog) * e_prog
            else: self._prev_timeline_progress = progress
            is_timeline_hover = (active_id == 'timeline'); arc_w = 6 if is_timeline_hover else 3
            p.setPen(QPen(QColor(255, 255, 255, 25), arc_w, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap)); p.drawArc(arc_rect, 90 * 16, -360 * 16)
            if progress > 0.001:
                tc = QColor(0, 240, 255) if is_timeline_hover else self._dominant_color
                if is_timeline_hover:
                    for i in range(2):
                        gp = QPen(QColor(0, 240, 255, 30), arc_w + (i+1)*3); p.setPen(gp); p.drawArc(arc_rect, 90 * 16, int(-360 * progress * 16))
                p.setPen(QPen(QColor(tc.red(), tc.green(), tc.blue(), 230), arc_w, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap)); p.drawArc(arc_rect, 90 * 16, int(-360 * progress * 16))

        if self.settings.get('show_title', True):
            title = track.get('title', ''); artist = track.get('artist', '')
            p.setPen(QColor(255, 255, 255)); p.setFont(QFont("Segoe UI Variable Display", 9, QFont.Weight.Bold))
            p.drawText(QRectF(cx-80, cy + 5, 160, 18), Qt.AlignmentFlag.AlignCenter, title if len(title) <= 20 else title[:19] + "..")
            p.setPen(QColor(255, 255, 255, 160)); p.setFont(QFont("Segoe UI Variable Display", 7))
            p.drawText(QRectF(cx-80, cy + 22, 160, 14), Qt.AlignmentFlag.AlignCenter, artist if len(artist) <= 25 else artist[:24] + "..")

        if self.settings.get('show_controls', True):
            action_text = ""
            if active_id in ['prev', 'next']: action_text = "SKIP NEXT" if active_id == 'next' else "SKIP PREV"
            elif active_id in ['volume', 'timeline']:
                vol = track.get('app_volume', 0.5)
                if active_id == 'volume': action_text = f"VOLUME {int(vol * 100)}%"
                else:
                    pos = track.get('position', 0); dur = track.get('duration', 0)
                    if is_playing and sync_time > 0 and dur > 0: pos += time.time() - sync_time
                    def fmt(s): m, s = int(s // 60), int(s % 60); return f"{m}:{s:02d}"
                    action_text = f"{fmt(pos)} / {fmt(dur)}"
            if action_text:
                p.setPen(QColor(0, 240, 255)); p.setFont(QFont("Segoe UI Variable Display", 8, QFont.Weight.Bold))
                p.drawText(QRectF(cx-80, cy - 25, 160, 15), Qt.AlignmentFlag.AlignCenter, action_text)
            elif not self._holding and has_media:
                ic = "pause" if is_playing else "play"; p.drawPixmap(int(cx - 8), int(cy - 20), VectorIcon.pixmap(ic, "#ffffff", 16))

        if multi_session and not self._holding:
            num = len(sessions)
            curr_session_id = track.get('session_id')
            idx = next((i for i,s in enumerate(sessions) if s.get('session_id') == curr_session_id), 0)
            
            arc_r = inner_radius - 15
            arc_rect = QRectF(cx - arc_r, cy - arc_r, arc_r * 2, arc_r * 2)
            span = min(60, num * 15)
            seg_span = span / num
            gap = 2.5 if num > 1 else 0
            
            p.setBrush(Qt.GlobalColor.transparent)
            for i in range(num):
                a_start = 270 - (span / 2.0) + (i * seg_span) + (gap / 2.0)
                a_len = seg_span - gap
                color = QColor(255, 255, 255) if i == idx else QColor(255, 255, 255, 60)
                p.setPen(QPen(color, 4, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
                p.drawArc(arc_rect, int(a_start * 16), int(a_len * 16))

    def on_key_press(self, event):
        try:
            if hasattr(event, 'isAutoRepeat') and event.isAutoRepeat(): return False
        except Exception as e:
            with open('c:\\\\Users\\\\Base\\\\Desktop\\\\Seb\\\\Pandora\\\\crash_log.txt', 'a') as f:
                f.write(str(e) + '\\n')
        if event.key() == Qt.Key.Key_Space:
            if not getattr(self, '_space_pressed', False):
                self._space_pressed = True; self._space_press_time = time.time()
                def check_hold():
                    if getattr(self, '_space_pressed', False):
                        self._holding = True
                        if hasattr(self.manager.halo, 'set_override_tools'):
                            self.manager.halo.set_override_tools(self.media_tools)
                        self.manager.halo.update()
                from PyQt6.QtCore import QTimer
                QTimer.singleShot(150, check_hold)
                return True
        return False

    def on_key_release(self, event):
        try:
            if hasattr(event, 'isAutoRepeat') and event.isAutoRepeat(): return False
        except Exception as e:
            pass
        if event.key() == Qt.Key.Key_Space:
            was_holding = getattr(self, '_holding', False)
            self._space_pressed = False; self._holding = False
            if was_holding:
                active_id = None
                if hasattr(self.manager.halo, 'active_index') and self.manager.halo.active_index != -1:
                    tools = self.manager.halo.current_tools
                    if self.manager.halo.active_index < len(tools): active_id = tools[self.manager.halo.active_index]['id']
                if active_id and active_id in ['prev', 'next']:
                    if active_id == 'next': self.media_mgr.next_track()
                    elif active_id == 'prev': self.media_mgr.prev_track()
                    self.manager.halo.hide()
                if hasattr(self.manager.halo, 'clear_override_tools'): self.manager.halo.clear_override_tools()
            else:
                if time.time() - getattr(self, '_space_press_time', 0) < 0.3: self.media_mgr.play_pause()
            self.manager.halo.update(); return True
        return False

    def on_mouse_press(self, pos, button):
        if button == Qt.MouseButton.MiddleButton:
            self.media_mgr.switch_session(1); self.manager.halo.update(); return
        elif button == Qt.MouseButton.RightButton:
            app_id = self.media_mgr.current_track.get('app_id', '').lower()
            if app_id:
                try:
                    import pythoncom; from pycaw.pycaw import AudioUtilities; pythoncom.CoInitialize()
                    sessions = AudioUtilities.GetAllSessions(); target = app_id.lower()
                    for session in sessions:
                        if session.Process:
                            name = session.Process.name().lower()
                            if name.replace(".exe", "") in target or target in name:
                                vol = session.SimpleAudioVolume; vol.SetMute(1 if vol.GetMute() == 0 else 0, None); break
                except: pass
            self.manager.halo.update()

    def on_mouse_move(self, pos): pass
    def on_mouse_leave(self): pass
    def on_mouse_release(self, pos, button):
        if button == Qt.MouseButton.LeftButton:
            active_id = None
            if hasattr(self.manager.halo, 'active_index') and self.manager.halo.active_index != -1:
                tools = self.manager.halo.current_tools
                if self.manager.halo.active_index < len(tools): active_id = tools[self.manager.halo.active_index]['id']
            if self._holding:
                if active_id in ['prev', 'next']:
                    if active_id == 'next': self.media_mgr.next_track()
                    else: self.media_mgr.prev_track()
                return
            else: self.media_mgr.play_pause(); return

    def on_wheel(self, delta):
        if not self._holding: return False
        active_id = None
        if hasattr(self.manager.halo, 'active_index') and self.manager.halo.active_index != -1:
            tools = self.manager.halo.current_tools
            if self.manager.halo.active_index < len(tools): active_id = tools[self.manager.halo.active_index]['id']
        if active_id == 'volume':
            vol_delta = 0.02 if delta > 0 else -0.02
            new_vol = self.media_mgr.change_app_volume(vol_delta)
            if new_vol is not None:
                self.manager.halo.vol_level = new_vol
                self.manager.halo.vol_target_opacity = 1.0; self.manager.halo.vol_opacity = 1.0
                self.manager.halo.vol_hud_val = int(new_vol * 100)
                self.manager.halo.vol_hud_dir = "up" if delta > 0 else "down"
                self.manager.halo.last_adjusted_id = "volume"
                self.manager.halo.vol_fade_timer.start(1500)
                self.manager.halo.update()
            return True
        elif active_id == 'timeline':
            time_delta = 5.0 if delta > 0 else -5.0
            self.media_mgr.scrub_timeline(time_delta)
            return True
        return False
