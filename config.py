import os
import json
import logging
from datetime import datetime

# ==========================================
# LOGGING SETUP
# ==========================================
import sys

# When running from Program Files (PyInstaller), we cannot write to the installation directory.
# Use AppData for all user-writable data.
APPDATA_DIR = os.path.join(os.environ.get('APPDATA', os.path.expanduser('~')), "Pandora")
if not os.path.exists(APPDATA_DIR):
    os.makedirs(APPDATA_DIR)

LOG_DIR = os.path.join(APPDATA_DIR, "logs")
if not os.path.exists(LOG_DIR): os.makedirs(LOG_DIR)
log_file = os.path.join(LOG_DIR, f"session_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log")
logging.basicConfig(
    filename=log_file,
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    datefmt='%H:%M:%S'
)
logger = logging.getLogger("Pandora")

# ==========================================
# CONSTANTS & PATHS
# ==========================================
BASE_DIR = getattr(sys, '_MEIPASS', os.path.dirname(os.path.abspath(__file__)))
# Wait, if we are in PyInstaller --onedir, sys._MEIPASS is the _internal folder, but we want the app folder if we need to migrate.
# Actually, os.path.dirname(os.path.abspath(__file__)) works for both script and onedir inside _internal.
# Let's just use the original project directory for migration if it exists.
ORIGINAL_PROJECT_DIR = r"C:\Users\Base\Desktop\Seb\Pandora"

DESKTOP_PATH = os.path.join(os.path.expanduser('~'), 'Desktop')
STORAGE_PATH = os.path.join(APPDATA_DIR, 'internal_storage')
CONFIG_PATH = os.path.join(APPDATA_DIR, 'config.json')

if not os.path.exists(STORAGE_PATH): 
    os.makedirs(STORAGE_PATH)

# ==========================================
# MIGRATION LOGIC (Unified)
# ==========================================
import shutil
old_config = os.path.join(ORIGINAL_PROJECT_DIR, 'config.json')
old_storage = os.path.join(ORIGINAL_PROJECT_DIR, 'internal_storage')

# 1. Move config.json if it exists and AppData one doesn't
if not os.path.exists(CONFIG_PATH) and os.path.exists(old_config):
    try:
        shutil.move(old_config, CONFIG_PATH)
        logger.info("Moved config.json to AppData storage")
    except Exception as e:
        logger.error(f"Failed to move config: {e}")

# 2. Move internal_storage contents
if os.path.exists(old_storage):
    for item in os.listdir(old_storage):
        src = os.path.join(old_storage, item)
        dst = os.path.join(STORAGE_PATH, item)
        if not os.path.exists(dst):
            try:
                shutil.move(src, dst)
            except Exception as e:
                logger.error(f"Failed to migrate storage item {item}: {e}")
    # Cleanup empty old storage if possible
    try:
        if not os.listdir(old_storage): os.rmdir(old_storage)
    except: pass

# ==========================================
# 2. CONFIG MANAGER
# ==========================================
class ConfigManager:
    @staticmethod
    def load():
        defaults = {
            "general_settings": {
                "sync_grid_size": True,
                "pagination_style": "Pill & Dots",
                "grid_size": 115,
                "edge_padding": 0,
                "edge_padding_t": 0,
                "edge_padding_b": 0,
                "edge_padding_l": 0,
                "edge_padding_r": 0,
                "edge_padding_v": 0,
                "edge_padding_h": 0,
                "show_grid_on_drag": True,
                "grid_animated_color": True,
                "grid_wave_entrance": True,
                "grid_wave_fade": True,
                "grid_opacity": 100,
                "preferred_template": None,
                "left_click_action": "Launch App (if fanned)",
                "middle_click_action": "Open Folder",
                "theme": "Dark",
                "theme_intensity": 100,
                "warmth_intensity": 60,
                "folder_darkness": "Dark",
                "gap_size": 75,
                "art_style": "Gaussian Blur",
                "color": "#ffffff",
                "display_effects": {},
                "sort_order": "asc",
                "sort_type": "name",
                "clock_mode": "digital",
                "format_24h": True,
                "show_date": True,
                "show_seconds": False,
                "world_clocks": [],
                "active_clock_label": "LOCAL TIME",
                "active_clock_tz": "",
                "show_controls": True,
                "show_timeline": True,
                "visualizer": "None",
                "show_arc_hud": True,
                "dashboard_theme": "Dark",
                "desktop_accents": [],
                "dashboard_blur_level": "Low",
                "link_pad_v": True,
                "link_pad_h": True,
                "folder_theme": "Default",
                "folder_custom_color": "#161B22FF",
                "keybinds": {}
            },
            "halo": {
                "enabled": True,
                "activation_key": 0xC0, # Tilde
                "activation_modifiers": 0,
                "max_bound": 300,
                "hub_ratio": 50,
                "brightness": 50,
                "blur_level": "High",
                "layer_anim_style": "Z-Depth + Spring",
                "pill_mode": "Name",
                "pill_icon_path": "",
                "hold_mode": "Hold",
                "theme": "Dark",
                "gap_size": 90,
                "opacity": 185,
                "show_arc_hud": False,
                "indicator_anim": "Crossfade",
                "menus": [
                    {
                        "name": "Layer 1",
                        "tools": [
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
                    }
                ]
            },
            "hub_config": {
                "switching_mode": "middle_click", # middle_click, custom_buttons, region_scroll
                "custom_up": "0x26", # Up Arrow
                "custom_down": "0x28", # Down Arrow
                "scroll_region": "upper", # upper, lower
                "layers": [],
                "low_res_blur_strength": 25,
                "low_res_art_style": "Gaussian Blur",
                "mouse_sens": 100,
                "scroll_sens": 50,
                "hold_mode": "Hold",
                "mosaic_shape": "Square",
                "mosaic_style": "Flat"
            },
            "folders": []
        }
        try:
            if os.path.exists(CONFIG_PATH):
                with open(CONFIG_PATH, 'r', encoding='utf-8') as f: 
                    data = json.load(f)
                    
                    # --- MIGRATION LOGIC ---
                    # 1. Migrate global_settings to general_settings
                    if "global_settings" in data:
                        old = data.pop("global_settings")
                        data.setdefault("general_settings", {})
                        data["general_settings"]["grid_size"] = old.get("grid_size", 110)
                        data["general_settings"]["edge_padding"] = old.get("edge_padding", 0)
                        data["general_settings"]["edge_padding_t"] = old.get("edge_padding_t", old.get("edge_padding", 0))
                        data["general_settings"]["edge_padding_b"] = old.get("edge_padding_b", old.get("edge_padding", 0))
                        data["general_settings"]["edge_padding_l"] = old.get("edge_padding_l", old.get("edge_padding", 0))
                        data["general_settings"]["edge_padding_r"] = old.get("edge_padding_r", old.get("edge_padding", 0))
                    
                    # 2. Ensure general_settings exists
                    for k, v in defaults['general_settings'].items():
                        data.setdefault('general_settings', {}).setdefault(k, v)
                    
                    data.setdefault('folders', [])
                    
                    # 3. Migrate folders
                    for folder in data.get('folders', []):
                        if 'show_title' not in folder: folder['show_title'] = True
                        if 'show_cover' not in folder: folder['show_cover'] = False
                        if 'grid_snap' not in folder: folder['grid_snap'] = False
                        
                    # 5. Auto Path Correction: Update old project paths to AppData storage
                    for folder in data.get('folders', []):
                        for app in folder.get('apps', []):
                            p = app.get('path', '')
                            if p.startswith(os.path.join(ORIGINAL_PROJECT_DIR, 'internal_storage')):
                                rel = os.path.relpath(p, os.path.join(ORIGINAL_PROJECT_DIR, 'internal_storage'))
                                new_p = os.path.join(STORAGE_PATH, rel)
                                if os.path.exists(new_p):
                                    app['path'] = new_p

                    # 6. Storage-to-Config Synchronization: Sync UI with actual disk state
                    for folder in data.get('folders', []):
                        fid = folder.get('id')
                        if not fid: continue
                        f_storage = os.path.join(STORAGE_PATH, fid)
                        if not os.path.exists(f_storage): 
                            os.makedirs(f_storage)
                            continue
                        
                        files = os.listdir(f_storage)
                        existing_apps = folder.get('apps', [])
                        synced_apps = []
                        seen_files = set()
                        
                        # Validate existing entries
                        for app in existing_apps:
                            p = app.get('path', '')
                            if p.startswith('pandora://') or os.path.exists(p):
                                synced_apps.append(app)
                                seen_files.add(os.path.basename(p))
                        
                        # Auto-import missing items from disk
                        for f in files:
                            if f not in seen_files:
                                p = os.path.join(f_storage, f)
                                name = os.path.splitext(f)[0] if os.path.isfile(p) else f
                                if not name: name = f
                                synced_apps.append({"name": name, "path": p, "pinned": False})
                        
                        folder['apps'] = synced_apps
                                    
                    # 7. Migrate branding names (radial_menu -> halo, dead_zones_config -> hub_config)
                    if "radial_menu" in data:
                        data["halo"] = data.pop("radial_menu")
                    if "dead_zones_config" in data:
                        data["hub_config"] = data.pop("dead_zones_config")
                        
                    # 8. Migrate halo tools to menus array (9 fixed layers)
                    halo = data.setdefault("halo", {})
                    if "tools" in halo:
                        tools = halo.pop("tools")
                        halo["menus"] = [{"name": "L1", "tools": tools}]
                    elif "menus" not in halo:
                        halo["menus"] = [{"name": "L1", "tools": defaults["halo"]["menus"][0]["tools"]}]
                        
                    while len(halo["menus"]) < 9:
                        idx = len(halo["menus"]) + 1
                        halo["menus"].append({"name": f"L{idx}", "tools": []})
                    
                    if "deadzone" in halo:
                        halo.pop("deadzone")
                    if "max_bound" not in halo:
                        halo["max_bound"] = 300
                    if "hub_ratio" not in halo:
                        halo["hub_ratio"] = 50
                    if "brightness" not in halo:
                        halo["brightness"] = 50
                        
                    return data
            return defaults
        except Exception as e:
            logger.error(f"Config load error: {e}")
            return defaults

    @staticmethod
    def save(data):
        def clean(obj):
            if isinstance(obj, dict):
                return {k: clean(v) for k, v in obj.items() if not k.startswith('_')}
            elif isinstance(obj, list):
                return [clean(v) for v in obj]
            return obj
        try:
            clean_data = clean(data)
            with open(CONFIG_PATH, 'w', encoding='utf-8') as f: 
                json.dump(clean_data, f, indent=2)
        except Exception as e: logger.error(f"Config Save error: {e}")
