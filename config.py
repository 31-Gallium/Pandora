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
                "grid_size": 110,
                "edge_padding": 0,
                "show_grid_on_drag": True,
                "grid_animated_color": True,
                "grid_wave_entrance": True,
                "grid_wave_fade": True,
                "grid_opacity": 100,
                "preferred_template": None,
                "left_click_action": "Launch App (if fanned)",
                "middle_click_action": "Open Folder"
            },
            "radial_menu": {
                "enabled": True,
                "activation_key": 0xC0, # Tilde
                "activation_modifiers": 0,
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
            "templates": {
                "grid": {
                    "Default": {
                        "size_preset": "Medium",
                        "folder_size": 80,
                        "mini_icon_size": 18,
                        "font_size": 10,
                        "expanded_icon_size": 48,
                        "glow_intensity": 20,
                        "glow_color": "#ffffff",
                        "bg_color": "#141414",
                        "title_color": "#ffffff",
                        "highlight_color": "#ffffff",
                        "opacity": 80,
                        "radius": 20,
                        "cover_blur": 0,
                        "cover_opacity": 255,
                        "hover_speed": "Fluid",
                        "morph_speed": "Fluid",
                        "mini_highlight_shape": "Circle"
                    }
                },
                "flower": {
                    "Default": {
                        "size_preset": "Medium",
                        "folder_size": 80,
                        "mini_icon_size": 18,
                        "font_size": 10,
                        "expanded_icon_size": 48,
                        "glow_intensity": 20,
                        "glow_color": "#ffffff",
                        "bg_color": "#141414",
                        "title_color": "#ffffff",
                        "highlight_color": "#ffffff",
                        "opacity": 80,
                        "radius": 10,
                        "cover_blur": 0,
                        "cover_opacity": 255,
                        "hover_speed": "Fluid",
                        "morph_speed": "Fluid",
                        "mini_highlight_shape": "Circle"
                    }
                }
            },
            "folders": []
        }
        try:
            if os.path.exists(CONFIG_PATH):
                with open(CONFIG_PATH, 'r', encoding='utf-8') as f: 
                    data = json.load(f)
                    
                    # --- MIGRATION LOGIC ---
                    # 1. Migrate global_settings to general_settings and Default Grid template
                    if "global_settings" in data:
                        old = data.pop("global_settings")
                        data.setdefault("general_settings", {})
                        data["general_settings"]["grid_size"] = old.get("grid_size", 110)
                        data["general_settings"]["edge_padding"] = old.get("edge_padding", 0)
                        
                        # Use the rest for the default grid template
                        t_grid = data.setdefault("templates", {}).setdefault("grid", {})
                        t_grid["Default"] = {
                            k: v for k, v in old.items() 
                            if k not in ["grid_size", "edge_padding", "show_cover", "show_title", "grid_snap"]
                        }
                    
                    # 2. Ensure all default templates exist
                    for t_type, t_dict in defaults['templates'].items():
                        for t_name, t_vals in t_dict.items():
                            data.setdefault('templates', {}).setdefault(t_type, {}).setdefault(t_name, t_vals)
                    
                    # 3. Ensure general_settings exists
                    for k, v in defaults['general_settings'].items():
                        data.setdefault('general_settings', {}).setdefault(k, v)
                    
                    # 4. Migrate folders to have template info
                    for folder in data.get('folders', []):
                        if 'template_type' not in folder:
                            folder['template_type'] = 'grid'
                        if 'template_name' not in folder:
                            folder['template_name'] = 'Default'
                        # Promote root settings if they were in old global/custom
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
                            if os.path.exists(p):
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
                                    
                    # 7. Migrate radial_menu tools to menus array
                    rm = data.setdefault("radial_menu", {})
                    if "tools" in rm:
                        tools = rm.pop("tools")
                        rm["menus"] = [{"name": "Layer 1", "tools": tools}]
                    elif "menus" not in rm:
                        rm["menus"] = [{"name": "Layer 1", "tools": defaults["radial_menu"]["menus"][0]["tools"]}]
                        
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
