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

def _get_desktop_path():
    try:
        import winreg
        key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Software\Microsoft\Windows\CurrentVersion\Explorer\Shell Folders")
        desktop, _ = winreg.QueryValueEx(key, "Desktop")
        winreg.CloseKey(key)
        return desktop
    except Exception:
        return os.path.join(os.path.expanduser('~'), 'Desktop')

DESKTOP_PATH = _get_desktop_path()
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
    def get_defaults():
        return {
            "general_settings": {
                "pagination_style": "Pill & Dots",
                "grid_size": 120,
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
                "launch_at_startup": False,
                "open_dashboard_startup": False,
                "theme_intensity": "Balanced",
                "dashboard_theme": "Dark",
                "folder_theme": "Default",
                "folder_custom_color": "#161B22FF",
                "gpu_preference": 0,
                "keybinds": {}
            },
            "display_effects": {
                "active_preset": "Sunset",
                "warmth_intensity": 50
            },
            "halo": {
                "enabled": True,
                "activation_key": 0xC0, # Tilde
                "activation_modifiers": 0,
                "max_bound": 300,
                "hub_ratio": 50,
                "brightness": 50,
                "blur_level": "High",
                "blur_mode": "live",
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
                            {"id": "next", "icon": "next", "label": "Next Media"},
                            {"id": "night", "icon": "night light", "label": "Night Light"},
                            {"id": "mute", "icon": "mute", "label": "Mute"},
                            {"id": "brightness", "icon": "brightness", "label": "Brightness"},
                            {"id": "prev", "icon": "prev", "label": "Prev Media"},
                            {"id": "settings", "icon": "Pandora", "label": "Pandora"}
                        ]
                    },
                    {
                        "name": "Layer 2",
                        "tools": [
                            {"id": "search", "icon": "search", "label": "Search"},
                            {"id": "screenshot", "icon": "screenshot", "label": "Snip"},
                            {"id": "grid", "icon": "toggle grid", "label": "Toggle Grid"},
                            {"id": "trash", "icon": "empty recycle bin", "label": "Empty Trash"},
                            {"id": "power", "icon": "power", "label": "Power"},
                            {"id": "notepad", "icon": "notepad", "label": "Notepad"},
                            {"id": "taskmgr", "icon": "task manager", "label": "Tasks"},
                            {"id": "terminal", "icon": "terminal", "label": "Terminal"}
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
                "mosaic_shape": "Square"
            },
            "folders": []
        }
        
    @staticmethod
    def load():
        defaults = ConfigManager.get_defaults()
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
                    
                    # 2. Ensure general_settings exists and prune orphaned settings
                    valid_keys = set(defaults['general_settings'].keys())
                    current_keys = list(data.get('general_settings', {}).keys())
                    
                    # Migrate gpu_preference from hub_config to general_settings
                    if "hub_config" in data and "gpu_preference" in data["hub_config"]:
                        data.setdefault("general_settings", {})["gpu_preference"] = data["hub_config"].pop("gpu_preference")
                        
                    for k in current_keys:
                        if k not in valid_keys:
                            del data['general_settings'][k]
                            
                    for k, v in defaults['general_settings'].items():
                        data.setdefault('general_settings', {}).setdefault(k, v)
                        
                    # 2.05 Sanitize theme_intensity
                    ti = data.get('general_settings', {}).get('theme_intensity')
                    if ti not in ["Subtle", "Balanced", "Intense", "Solid"]:
                        data.setdefault('general_settings', {})['theme_intensity'] = "Balanced"
                        
                    # 2.1 Ensure display_effects exists
                    for k, v in defaults.get('display_effects', {}).items():
                        data.setdefault('display_effects', {}).setdefault(k, v)
                        
                    data.setdefault('folders', [])
                    
                    # 3. Migrate folders
                    for folder in data.get('folders', []):
                        if 'show_title' not in folder: folder['show_title'] = False
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

                    # 5.1 Consolidate deprecated 'Storage' folder to 'internal_storage'
                    deprecated_storage = os.path.join(APPDATA_DIR, 'Storage')
                    if os.path.exists(deprecated_storage):
                        try:
                            for f_id in os.listdir(deprecated_storage):
                                old_f_dir = os.path.join(deprecated_storage, f_id)
                                if not os.path.isdir(old_f_dir): continue
                                new_f_dir = os.path.join(STORAGE_PATH, f_id)
                                if not os.path.exists(new_f_dir):
                                    os.makedirs(new_f_dir)
                                for fname in os.listdir(old_f_dir):
                                    old_file = os.path.join(old_f_dir, fname)
                                    new_file = os.path.join(new_f_dir, fname)
                                    if os.path.exists(old_file) and not os.path.exists(new_file):
                                        import shutil
                                        shutil.copy2(old_file, new_file)
                            import shutil
                            shutil.rmtree(deprecated_storage)
                        except Exception as e:
                            logger.error(f"Failed to consolidate deprecated Storage folder: {e}")

                    # 5.2 Correct config paths pointing to deprecated 'Storage'
                    for folder in data.get('folders', []):
                        for app in folder.get('apps', []):
                            p = app.get('path', '')
                            old_prefix = os.path.join(APPDATA_DIR, 'Storage')
                            if p.startswith(old_prefix):
                                app['path'] = p.replace(old_prefix, STORAGE_PATH)

                    # 5.3 Auto-register new non-empty directories in internal_storage
                    active_ids = {f.get('id') for f in data.get('folders', []) if f.get('id')}
                    if os.path.exists(STORAGE_PATH):
                        try:
                            for f_id in os.listdir(STORAGE_PATH):
                                f_dir = os.path.join(STORAGE_PATH, f_id)
                                if os.path.isdir(f_dir) and f_id not in active_ids:
                                    contents = [f for f in os.listdir(f_dir) if f.lower() != 'desktop.ini']
                                    
                                    # Auto-register as a new Pandora folder
                                    apps = []
                                    for fname in contents:
                                        p = os.path.join(f_dir, fname)
                                        name = os.path.splitext(fname)[0] if os.path.isfile(p) else fname
                                        if not name: name = fname
                                        apps.append({"name": name, "path": p})
                                    
                                    display_name = f_id.replace('_', ' ').title() if not f_id.startswith('folder_') else None
                                    if not display_name:
                                        greek_names = ["Alpha", "Beta", "Gamma", "Delta", "Epsilon", "Zeta", "Eta", "Theta", "Iota", "Kappa", "Lambda", "Mu", "Nu", "Xi", "Omicron", "Pi", "Rho", "Sigma", "Tau", "Upsilon", "Phi", "Chi", "Psi", "Omega"]
                                        existing_names = {f.get('name', '') for f in data.get('folders', [])}
                                        display_name = next((n for n in greek_names if n not in existing_names), "New Folder")
                                    
                                    data['folders'].append({
                                        "id": f_id,
                                        "name": display_name,
                                        "pos": [200, 200],
                                        "apps": apps,
                                        "show_title": False,
                                        "grid_cols": 2,
                                        "grid_rows": 2,
                                        "grid_snap": True
                                    })
                                    active_ids.add(f_id)
                                    logger.info(f"Auto-registered folder from storage at startup: {f_id}")
                        except Exception as e:
                            logger.error(f"Failed to process orphaned AppData folders: {e}")

                    # 5.4 Remove config entries whose storage directories were deleted externally
                    folders_to_keep = []
                    for folder in data.get('folders', []):
                        fid = folder.get('id')
                        if not fid:
                            folders_to_keep.append(folder)
                            continue
                        expected_dir = os.path.join(STORAGE_PATH, fid)
                        if not os.path.exists(expected_dir):
                            # Check if folder has external (non-storage) apps
                            has_external = any(
                                not app.get('path', '').startswith(expected_dir) and not app.get('path', '').startswith('pandora://')
                                for app in folder.get('apps', [])
                            )
                            if has_external:
                                folders_to_keep.append(folder)
                            else:
                                logger.info(f"Removed folder with deleted storage at startup: {fid}")
                        else:
                            folders_to_keep.append(folder)
                    data['folders'] = folders_to_keep

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
                                synced_apps.append({"name": name, "path": p})
                        
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
            tmp_path = CONFIG_PATH + '.tmp'
            with open(tmp_path, 'w', encoding='utf-8') as f: 
                json.dump(clean_data, f, indent=2)
            os.replace(tmp_path, CONFIG_PATH)
        except Exception as e: logger.error(f"Config Save error: {e}")

def set_startup_registry(enable=True):
    try:
        import winreg
        
        # 1. Always ensure it is present in the standard Run key so Task Manager sees it
        if getattr(sys, 'frozen', False):
            run_key_path = r"Software\Microsoft\Windows\CurrentVersion\Run"
            try:
                run_key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, run_key_path, 0, winreg.KEY_SET_VALUE)
                exe_path = sys.executable
                winreg.SetValueEx(run_key, "Pandora", 0, winreg.REG_SZ, f'"{exe_path}" --startup')
                winreg.CloseKey(run_key)
            except Exception as e:
                logger.error(f"Failed to set Run key: {e}")

        # 2. Toggle the enabled/disabled state in StartupApproved
        approved_key_path = r"Software\Microsoft\Windows\CurrentVersion\Explorer\StartupApproved\Run"
        try:
            approved_key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, approved_key_path, 0, winreg.KEY_SET_VALUE)
            if enable:
                try:
                    winreg.DeleteValue(approved_key, "Pandora")
                except FileNotFoundError:
                    pass
            else:
                import time, struct
                # Calculate FILETIME (100-nanosecond intervals since Jan 1, 1601)
                filetime = int((time.time() + 11644473600) * 10000000)
                ft_bytes = struct.pack('<Q', filetime)
                val = b'\x03\x00\x00\x00' + ft_bytes
                winreg.SetValueEx(approved_key, "Pandora", 0, winreg.REG_BINARY, val)
            winreg.CloseKey(approved_key)
        except Exception as e:
            logger.error(f"Failed to set StartupApproved key: {e}")
            
    except Exception as e:
        logger.error(f"Startup registry error: {e}")
