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
APPDATA_DIR = os.path.join(os.environ.get('APPDATA', os.path.expanduser('~')), "CusFolder")
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
logger = logging.getLogger("CusFolder")

# ==========================================
# CONSTANTS & PATHS
# ==========================================
BASE_DIR = getattr(sys, '_MEIPASS', os.path.dirname(os.path.abspath(__file__)))
# Wait, if we are in PyInstaller --onedir, sys._MEIPASS is the _internal folder, but we want the app folder if we need to migrate.
# Actually, os.path.dirname(os.path.abspath(__file__)) works for both script and onedir inside _internal.
# Let's just use the original project directory for migration if it exists.
ORIGINAL_PROJECT_DIR = r"C:\Users\Base\Desktop\Seb\CusFolder"

DESKTOP_PATH = os.path.join(os.path.expanduser('~'), 'Desktop')
STORAGE_PATH = os.path.join(APPDATA_DIR, 'internal_storage')
CONFIG_PATH = os.path.join(APPDATA_DIR, 'config.json')

if not os.path.exists(STORAGE_PATH): 
    os.makedirs(STORAGE_PATH)

# Migration logic: if APPDATA config doesn't exist, but original does, copy it.
import shutil
old_config = os.path.join(ORIGINAL_PROJECT_DIR, 'config.json')
if not os.path.exists(CONFIG_PATH) and os.path.exists(old_config):
    try:
        shutil.copy(old_config, CONFIG_PATH)
        logger.info("Migrated old config.json to AppData")
    except Exception as e:
        logger.error(f"Failed to migrate config: {e}")

old_storage = os.path.join(ORIGINAL_PROJECT_DIR, 'internal_storage')
if os.path.exists(old_storage):
    for item in os.listdir(old_storage):
        src = os.path.join(old_storage, item)
        dst = os.path.join(STORAGE_PATH, item)
        if not os.path.exists(dst):
            try:
                if os.path.isdir(src):
                    shutil.copytree(src, dst)
                else:
                    shutil.copy(src, dst)
            except Exception as e:
                logger.error(f"Failed to migrate storage item {item}: {e}")

# ==========================================
# 2. CONFIG MANAGER
# ==========================================
class ConfigManager:
    @staticmethod
    def load():
        defaults = {
            "global_settings": {
                "size_preset": "Medium",
                "folder_size": 80,
                "mini_icon_size": 27,
                "font_size": 10,
                "expanded_icon_size": 48,
                "glow_intensity": 40,
                "glow_color": "#ffffff",
                "bg_color": "#141414",
                "title_color": "#ffffff",
                "highlight_color": "#50FA7B",
                "opacity": 80,
                "radius": 20,
                "cover_blur": 0,
                "cover_opacity": 255,
                "hover_speed": "Fluid",
                "morph_speed": "Fluid",
                "grid_snap": False,
                "grid_size": 110,
                "edge_padding": 0,
                "show_cover": False,
                "show_title": True
            },
            "folders": []
        }
        try:
            if os.path.exists(CONFIG_PATH):
                with open(CONFIG_PATH, 'r', encoding='utf-8') as f: 
                    data = json.load(f)
                    # Merge with defaults to ensure new keys exist
                    for k, v in defaults['global_settings'].items():
                        if k not in data.get('global_settings', {}):
                            data.setdefault('global_settings', {})[k] = v
                    return data
            return defaults
        except: 
            return defaults

    @staticmethod
    def save(data):
        try:
            with open(CONFIG_PATH, 'w', encoding='utf-8') as f: json.dump(data, f, indent=2)
        except Exception as e: logger.error(f"Config Save error: {e}")
