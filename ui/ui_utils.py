import os
import math
from PyQt6.QtCore import Qt, QRectF, QPointF
from PyQt6.QtGui import QPainter, QColor, QRadialGradient, QLinearGradient, QPainterPath, QPixmap, QPen
from utils import IconExtractor, VectorIcon

# Hardcoded defaults — no templates, no themes, no per-folder overrides
_DEFAULTS = {
    'bg_color': '#1a1a1e',
    'title_color': '#ffffff',
    'glow_color': '#50fa7b',
    'highlight_color': '#26c0d3',
    'glow_intensity': 20,
    'opacity': 80,
    'radius': 20,
    'morph_speed': 'Fluid',
    'folder_size': 80,
    'mini_icon_size': 27,
    'font_size': 10,
    'expanded_icon_size': 48,
    'show_title': True,
    'show_cover': False,
    'grid_snap': False,
    'mini_highlight_shape': 'Rounded Square',
}

SIZE_PRESETS = {
    "Small":  {"folder_size": 60, "mini_icon_size": 20, "font_size": 9, "expanded_icon_size": 32},
    "Medium": {"folder_size": 80, "mini_icon_size": 27, "font_size": 10, "expanded_icon_size": 48},
    "Large":  {"folder_size": 110, "mini_icon_size": 34, "font_size": 12, "expanded_icon_size": 64},
}

def resolve_folder_setting(data, cfg, key, default, local_settings=None):
    """
    Simplified setting resolution.
    Only resolves size presets and general_settings fallback.
    No templates, no themes, no per-folder overrides.
    """
    # Instance-level overrides (show_title, grid_snap)
    INSTANCE_KEYS = ('show_title', 'grid_snap')
    if key in INSTANCE_KEYS and key in data:
        return data[key]

    if local_settings and key in local_settings:
        return local_settings[key]

    # Size preset resolution
    preset = data.get('size_preset', 'Medium')
    PRESET_KEYS = ('folder_size', 'mini_icon_size', 'font_size', 'expanded_icon_size')
    if key in PRESET_KEYS and preset in SIZE_PRESETS:
        return SIZE_PRESETS[preset][key]

    # Hardcoded defaults
    if key in _DEFAULTS:
        return _DEFAULTS[key]

    # General settings fallback
    return cfg.get('general_settings', {}).get(key, default)


def draw_folder_thumbnail(p, rect, data, cfg, local_settings=None, hover_progress=0.0, paging_params=None):
    """Shared drawing logic for folder thumbnails — simplified, grid-only."""
    p.setRenderHint(QPainter.RenderHint.Antialiasing)
    p.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)

    cx, cy = rect.center().x(), rect.center().y()

    def get_val(key, default):
        return resolve_folder_setting(data, cfg, key, default, local_settings)

    folder_size = get_val('folder_size', 80)
    glow_intensity = get_val('glow_intensity', 20)
    glow_color = get_val('glow_color', '#50fa7b')
    bg_color = get_val('bg_color', '#1a1a1e')
    opacity = get_val('opacity', 80)
    radius = get_val('radius', 20)

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
        g_path = QPainterPath()
        g_radius = radius * 1.5
        g_size = folder_size * 1.5
        g_path.addRoundedRect(QRectF(cx - g_size / 2, cy - g_size / 2, g_size, g_size), g_radius, g_radius)
        p.drawPath(g_path)
        p.restore()

    # Apply Hover Zoom
    hover_zoom = 1.0 + (0.15 * hover_progress)
    p.save()
    p.translate(cx, cy)
    p.scale(hover_zoom, hover_zoom)
    p.translate(-cx, -cy)

    # Background path — always rounded rect
    foil_path = QPainterPath()
    foil_path.addRoundedRect(QRectF(cx - folder_size/2, cy - folder_size/2, folder_size, folder_size), radius, radius)

    # Draw Background
    bg_c = QColor(bg_color)
    bg_c.setAlpha(int(opacity))
    p.setBrush(bg_c)
    p.setPen(Qt.PenStyle.NoPen)
    p.drawPath(foil_path)

    # Draw Grid Icons
    mini_icon_size = get_val('mini_icon_size', 18)
    from ui.layout_logic import get_engine
    engine = get_engine('grid')
    apps = data.get('apps', [])

    isz = mini_icon_size * (1.0 + 0.5 * hover_progress)

    if paging_params and paging_params['progress'] < 1.0:
        p_list = engine.get_paging_positions(cx, cy, folder_size, mini_icon_size, len(apps),
                                            paging_params['page'], paging_params['next_page'],
                                            paging_params['progress'], paging_params.get('direction', 1), hover_progress)
        for app_idx, p_pos, op in p_list:
            if app_idx >= len(apps): continue
            p.save()
            p.setOpacity(op)
            x, y = p_pos.x() + (mini_icon_size - isz) / 2, p_pos.y() + (mini_icon_size - isz) / 2
            app = apps[app_idx]
            raw_pix = IconExtractor.get_icon_pixmap(app['path'], int(isz))
            if not raw_pix.isNull():
                p.drawPixmap(int(x), int(y), int(isz), int(isz), raw_pix.scaled(int(isz), int(isz), Qt.AspectRatioMode.IgnoreAspectRatio, Qt.TransformationMode.SmoothTransformation))
            p.restore()
    else:
        page_idx = paging_params['page'] if paging_params else 0
        page_size = 9
        start_idx = page_idx * page_size
        current_apps = apps[start_idx : start_idx + page_size]

        pos_list = engine.get_collapsed_positions(cx, cy, folder_size, mini_icon_size, len(current_apps), hover_progress)
        for i, p_pos in enumerate(pos_list):
            if i >= len(current_apps): break
            x, y = p_pos.x() + (mini_icon_size - isz) / 2, p_pos.y() + (mini_icon_size - isz) / 2
            app = current_apps[i]
            p.save()
            raw_pix = IconExtractor.get_icon_pixmap(app['path'], int(isz))
            if not raw_pix.isNull():
                p.drawPixmap(int(x), int(y), int(isz), int(isz), raw_pix.scaled(int(isz), int(isz), Qt.AspectRatioMode.IgnoreAspectRatio, Qt.TransformationMode.SmoothTransformation))
            p.restore()

    p.restore()
