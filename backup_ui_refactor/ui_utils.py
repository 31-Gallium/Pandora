import os
import math
from PyQt6.QtCore import Qt, QRectF, QPointF
from PyQt6.QtGui import QPainter, QColor, QRadialGradient, QLinearGradient, QPainterPath, QPixmap, QPen
from utils import IconExtractor, VectorIcon

def draw_folder_thumbnail(p, rect, data, cfg, local_settings=None, hover_progress=0.0, paging_params=None):
    """Shared drawing logic for folder thumbnails."""
    p.setRenderHint(QPainter.RenderHint.Antialiasing)
    p.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
    
    cx, cy = rect.center().x(), rect.center().y()
    t_type = data.get('template_type', 'grid')
    t_name = data.get('template_name', 'Default')
    t_data = cfg.get('templates', {}).get(t_type, {}).get(t_name, {})
    
    def get_val(key, default):
        INSTANCE_KEYS = ('show_title', 'grid_snap', 'show_cover')
        if key in INSTANCE_KEYS and key in data: return data[key]
        if local_settings and key in local_settings: return local_settings[key]
        
        lookup_keys = [key]
        if key in ('cover_image', 'cover_path'):
            lookup_keys = ['cover_path', 'cover_image']
        use_custom = data.get('use_custom', False)
        preset = t_data.get('size_preset', 'Medium')
        if use_custom: preset = data.get('size_preset', preset)
        SIZE_PRESETS = {
            "Small": {"folder_size": 60, "mini_icon_size": 20, "font_size": 9, "expanded_icon_size": 32},
            "Medium": {"folder_size": 80, "mini_icon_size": 27, "font_size": 10, "expanded_icon_size": 48},
            "Large": {"folder_size": 110, "mini_icon_size": 34, "font_size": 12, "expanded_icon_size": 64}
        }
        
        # Sizing keys take absolute priority from fixed presets if not set to Custom
        PRESET_KEYS = ('folder_size', 'mini_icon_size', 'font_size', 'expanded_icon_size')
        if key in PRESET_KEYS and preset in SIZE_PRESETS:
            return SIZE_PRESETS[preset][key]
            
        if use_custom:
            val = next((data[lk] for lk in lookup_keys if lk in data), None)
            if val is not None: return val
            
        val = next((t_data[lk] for lk in lookup_keys if lk in t_data), None)
        if val is not None: return val
        
        return cfg.get('general_settings', {}).get(key, default)

    folder_size = get_val('folder_size', 80)
    glow_intensity = get_val('glow_intensity', 20)
    glow_color = get_val('glow_color', '#ffffff')
    bg_color = get_val('bg_color', '#141414')
    opacity = get_val('opacity', 80)
    radius = get_val('radius', 20)
    show_cover = get_val('show_cover', False)

    # Draw Glow
    if glow_intensity > 0:
        p.save()
        p.setPen(Qt.PenStyle.NoPen)
        alpha = int(max(glow_intensity * 0.2, glow_intensity * hover_progress))
        glow_c = QColor(glow_color)
        grad = QRadialGradient(cx, cy, folder_size * 0.8)
        grad.setColorAt(0.0, QColor(glow_c.red(), glow_c.green(), glow_c.blue(), alpha))
        grad.setColorAt(1.0, Qt.GlobalColor.transparent)
        p.setBrush(grad)
        g_path = QPainterPath(); g_size = folder_size * 1.5
        if t_type == "flower":
            points = 60; base_r = g_size * 0.55; amp = g_size * 0.18 * (radius / 50.0)
            for i in range(points + 1):
                ang = math.radians(i * (360 / points) - 90); r = base_r + amp * math.cos(6 * math.radians(i * (360 / points)))
                px = cx + math.cos(ang) * r; py = cy + math.sin(ang) * r
                if i == 0: g_path.moveTo(px, py)
                else: g_path.lineTo(px, py)
            g_path.closeSubpath()
        else:
            g_radius = radius * 1.5
            g_path.addRoundedRect(QRectF(cx - g_size / 2, cy - g_size / 2, g_size, g_size), g_radius, g_radius)
        p.drawPath(g_path); p.restore()

    # Apply Hover Zoom
    hover_zoom = 1.0 + (0.15 * hover_progress)
    p.save(); p.translate(cx, cy); p.scale(hover_zoom, hover_zoom); p.translate(-cx, -cy)

    # foil path
    foil_path = QPainterPath()
    if t_type == "flower":
        points = 60; base_r = folder_size * 0.55; amp = folder_size * 0.18 * (radius / 50.0)
        for i in range(points + 1):
            ang = math.radians(i * (360 / points) - 90); r = base_r + amp * math.cos(6 * math.radians(i * (360 / points)))
            px = cx + math.cos(ang) * r; py = cy + math.sin(ang) * r
            if i == 0: foil_path.moveTo(px, py)
            else: foil_path.lineTo(px, py)
        foil_path.closeSubpath()
    else:
        foil_path.addRoundedRect(QRectF(cx - folder_size/2, cy - folder_size/2, folder_size, folder_size), radius, radius)

    # Draw Background
    if not show_cover or hover_progress > 0:
        bg_c = QColor(bg_color); bg_c.setAlpha(int(opacity * (hover_progress if show_cover else 1.0)))
        p.setBrush(bg_c); p.setPen(Qt.PenStyle.NoPen); p.drawPath(foil_path)

    # Draw Cover
    cover_path = data.get('cover_path') or data.get('cover_image')
    if show_cover:
        p.save(); p.setClipPath(foil_path)
        current_frame = data.get('_current_cover_frame')
        pix = current_frame if current_frame else (QPixmap(cover_path) if cover_path and os.path.exists(cover_path) else None)
        if pix and not pix.isNull():
            cover_opacity = get_val('cover_opacity', 100) / 100.0
            p.setOpacity((1.0 - hover_progress) * cover_opacity)
            p.drawPixmap(int(cx - folder_size/2), int(cy - folder_size/2), int(folder_size), int(folder_size), pix.scaled(int(folder_size), int(folder_size), Qt.AspectRatioMode.KeepAspectRatioByExpanding, Qt.TransformationMode.SmoothTransformation))
        else:
            p.setOpacity((1.0 - hover_progress) * (get_val('cover_opacity', 100) / 100.0))
            # Try template cover image
            tpl_cover = t_data.get('cover_image') or t_data.get('cover_path')
            pix = QPixmap(tpl_cover) if tpl_cover and os.path.exists(tpl_cover) else None
            if pix and not pix.isNull():
                p.drawPixmap(int(cx - folder_size/2), int(cy - folder_size/2), int(folder_size), int(folder_size), pix.scaled(int(folder_size), int(folder_size), Qt.AspectRatioMode.KeepAspectRatioByExpanding, Qt.TransformationMode.SmoothTransformation))
            else:
                pix = QPixmap("assets/Pandora.svg")
                if not pix.isNull(): p.drawPixmap(int(cx - folder_size/2), int(cy - folder_size/2), int(folder_size), int(folder_size), pix.scaled(int(folder_size), int(folder_size), Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation))
        p.restore()

    # Draw Grid/Icons
    if not show_cover or hover_progress > 0:
        mini_icon_size = get_val('mini_icon_size', 18)
        from layout_logic import get_engine
        engine = get_engine(t_type)
        apps = data.get('apps', [])
        
        isz = mini_icon_size * (1.0 + 0.5 * hover_progress)
        hc = QColor(get_val('highlight_color', '#50FA7B'))
        h_shape = get_val('mini_highlight_shape', 'Rounded Square')

        if paging_params and paging_params['progress'] < 1.0:
            # Use Paging Logic
            p_list = engine.get_paging_positions(cx, cy, folder_size, mini_icon_size, len(apps), 
                                                paging_params['page'], paging_params['next_page'], 
                                                paging_params['progress'], paging_params.get('direction', 1), hover_progress)
            for app_idx, p_pos, op in p_list:
                if app_idx >= len(apps): continue
                p.save()
                p.setOpacity(op * (hover_progress if show_cover else 1.0))
                x, y = p_pos.x() + (mini_icon_size - isz) / 2, p_pos.y() + (mini_icon_size - isz) / 2
                app = apps[app_idx]
                raw_pix = IconExtractor.get_icon_pixmap(app['path'], int(isz))
                if not raw_pix.isNull(): p.drawPixmap(int(x), int(y), int(isz), int(isz), raw_pix.scaled(int(isz), int(isz), Qt.AspectRatioMode.IgnoreAspectRatio, Qt.TransformationMode.SmoothTransformation))
                p.restore()
        else:
            # Normal Static Display (Adjusted for current page)
            page_idx = paging_params['page'] if paging_params else 0
            page_size = 7 if t_type == "flower" else 9
            start_idx = page_idx * page_size
            current_apps = apps[start_idx : start_idx + page_size]
            
            pos_list = engine.get_collapsed_positions(cx, cy, folder_size, mini_icon_size, len(current_apps), hover_progress)
            for i, p_pos in enumerate(pos_list):
                if i >= len(current_apps): break
                x, y = p_pos.x() + (mini_icon_size - isz) / 2, p_pos.y() + (mini_icon_size - isz) / 2
                app = current_apps[i]
                p.save()
                if show_cover: p.setOpacity(hover_progress)
                raw_pix = IconExtractor.get_icon_pixmap(app['path'], int(isz))
                if not raw_pix.isNull(): p.drawPixmap(int(x), int(y), int(isz), int(isz), raw_pix.scaled(int(isz), int(isz), Qt.AspectRatioMode.IgnoreAspectRatio, Qt.TransformationMode.SmoothTransformation))
                p.restore()
    
    p.restore()
