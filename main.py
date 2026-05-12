import sys
from PyQt6.QtWidgets import QApplication, QSystemTrayIcon, QMenu
from PyQt6.QtCore import QTimer
from config import ConfigManager
from folder_icon import FolderIcon
from utils import VectorIcon, IconExtractor, DesktopMonitor
from dashboard import DashboardUI
from grid_overlay import GridOverlay
from radial_menu import RadialMenu
import os
import math
import ctypes
from ctypes import wintypes
from PyQt6.QtGui import QCursor
from PyQt6.QtCore import QPoint, QTimer

class GlobalHook:
    def __init__(self, on_press, on_release, on_move, cfg=None):
        self.on_press = on_press; self.on_release = on_release; self.on_move = on_move
        self.hook_kb = None; self.hook_ms = None; self.tilde_pressed = False
        self.center = None; self.radius = None
        self.activation_key = 0xC0
        self.enabled = True
        self.hold_mode = 'Hold'
        self.menu_open = False
        if cfg: self.reload_config(cfg)
        
    def reload_config(self, cfg):
        rad_cfg = cfg.get('radial_menu', {})
        self.activation_key = rad_cfg.get('activation_key', 0xC0)
        self.enabled = rad_cfg.get('enabled', True)
        self.hold_mode = rad_cfg.get('hold_mode', 'Hold')
        
    def set_constraint(self, center, radius):
        self.center = center; self.radius = radius

    def start(self):
        CMPFUNC = ctypes.WINFUNCTYPE(ctypes.c_int, ctypes.c_int, ctypes.c_int, ctypes.POINTER(ctypes.c_void_p))
        
        class MSLLHOOKSTRUCT(ctypes.Structure):
            _fields_ = [("pt", wintypes.POINT), ("mouseData", ctypes.c_uint32),
                        ("flags", ctypes.c_uint32), ("time", ctypes.c_uint32),
                        ("dwExtraInfo", ctypes.POINTER(ctypes.c_ulong))]
                        
        def kb_callback(nCode, wParam, lParam):
            if nCode >= 0 and self.enabled:
                vkCode = ctypes.cast(lParam, ctypes.POINTER(ctypes.c_uint32))[0]
                
                active_key_str = str(self.activation_key)
                parts = active_key_str.split("+")
                try:
                    target_vk = int(parts[-1], 16) if parts[-1].startswith("0x") else int(parts[-1])
                except:
                    target_vk = 0xC0
                
                if vkCode == target_vk:
                    req_ctrl = "Ctrl" in parts
                    req_alt = "Alt" in parts
                    req_shift = "Shift" in parts
                    
                    user32 = ctypes.windll.user32
                    ctrl_pressed = (user32.GetAsyncKeyState(0x11) & 0x8000) != 0
                    alt_pressed = (user32.GetAsyncKeyState(0x12) & 0x8000) != 0
                    shift_pressed = (user32.GetAsyncKeyState(0x10) & 0x8000) != 0
                    
                    if ctrl_pressed == req_ctrl and alt_pressed == req_alt and shift_pressed == req_shift:
                        if wParam == 0x0100 or wParam == 0x0104: # WM_KEYDOWN or WM_SYSKEYDOWN
                            if not self.tilde_pressed: 
                                self.tilde_pressed = True
                                if self.hold_mode == 'Toggle':
                                    if self.menu_open:
                                        self.menu_open = False
                                        self.on_release()
                                    else:
                                        self.menu_open = True
                                        self.on_press()
                                else:
                                    self.menu_open = True
                                    self.on_press()
                        elif wParam == 0x0101 or wParam == 0x0105: # WM_KEYUP or WM_SYSKEYUP
                            self.tilde_pressed = False
                            if self.hold_mode != 'Toggle':
                                self.menu_open = False
                                self.on_release()
                        return 1
            return ctypes.windll.user32.CallNextHookEx(self.hook_kb, nCode, wParam, lParam)

        def ms_callback(nCode, wParam, lParam):
            if nCode >= 0 and self.menu_open and wParam == 0x0200: # WM_MOUSEMOVE
                ms_data = ctypes.cast(lParam, ctypes.POINTER(MSLLHOOKSTRUCT))[0]
                pos = ms_data.pt
                
                if self.center and self.radius:
                    dx, dy = pos.x - self.center.x(), pos.y - self.center.y()
                    dist = math.hypot(dx, dy)
                    if dist > self.radius:
                        angle = math.atan2(dy, dx)
                        new_x = self.center.x() + int(self.radius * math.cos(angle))
                        new_y = self.center.y() + int(self.radius * math.sin(angle))
                        ctypes.windll.user32.SetCursorPos(new_x, new_y)
                        return 1 

                self.on_move(QPoint(pos.x, pos.y))
            return ctypes.windll.user32.CallNextHookEx(self.hook_ms, nCode, wParam, lParam)
        self.proc_kb = CMPFUNC(kb_callback); self.proc_ms = CMPFUNC(ms_callback)
        self.hook_kb = ctypes.windll.user32.SetWindowsHookExW(13, self.proc_kb, None, 0)
        self.hook_ms = ctypes.windll.user32.SetWindowsHookExW(14, self.proc_ms, None, 0)

def handle_radial_cmd(cmd, grid, dash):
    import subprocess
    import ctypes
    def send_key(vk):
        ctypes.windll.user32.keybd_event(vk, 0, 0, 0)
        ctypes.windll.user32.keybd_event(vk, 0, 2, 0)

    def send_win_key(vk):
        # LWIN (0x5B) + key
        ctypes.windll.user32.keybd_event(0x5B, 0, 0, 0)
        send_key(vk)
        ctypes.windll.user32.keybd_event(0x5B, 0, 2, 0)

    if cmd == "browser": subprocess.Popen(["cmd", "/c", "start", "https://www.google.com"])
    elif cmd == "explorer": subprocess.Popen("explorer.exe")
    elif cmd == "grid": grid.toggle()
    elif cmd == "screenshot":
        from PyQt6.QtWidgets import QApplication
        from PyQt6.QtCore import QTimer
        def do_capture():
            # Flush events to ensure menu is fully gone from compositor
            QApplication.processEvents()
            screen = QApplication.primaryScreen()
            if screen:
                # Grab native window (0) for highest quality
                pixmap = screen.grabWindow(0)
                QApplication.clipboard().setPixmap(pixmap)
                
                # Save to user's Pictures folder (Standard Windows location)
                save_dir = os.path.expanduser("~/Pictures/Pandora")
                if not os.path.exists(save_dir): os.makedirs(save_dir)
                
                import datetime
                timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
                save_path = os.path.join(save_dir, f"Pandora_{timestamp}.png")
                pixmap.save(save_path, "PNG", 100) # Max quality PNG
        # 200ms delay to ensure radial menu is fully hidden from screen
        QTimer.singleShot(200, do_capture)
    elif cmd == "night":
        from utils import DisplayEffectsEngine
        engine = DisplayEffectsEngine.instance()
        if not engine._is_enabled:
            val = cfg.get('display_effects', {}).get('warmth_intensity', 50) / 100.0
            engine.set_intensity(val)
            engine.set_enabled(True)
        else:
            engine.set_enabled(False)
    elif cmd == "taskmgr": subprocess.Popen("taskmgr")
    elif cmd == "settings": dash.show()
    elif cmd == "trash": subprocess.Popen(["powershell.exe", "-Command", "Clear-RecycleBin -Force -ErrorAction SilentlyContinue"])
    elif cmd == "search": send_win_key(0x53) # Win + S
    elif cmd == "power": subprocess.Popen(["shutdown", "/s", "/t", "60", "/c", "Pandora: Shutting down in 60s. Use 'shutdown /a' to cancel."])
    elif cmd == "calc": subprocess.Popen("calc")
    elif cmd == "cmd": subprocess.Popen(["cmd", "/c", "start", "cmd"])
    elif cmd == "notepad": subprocess.Popen(["cmd", "/c", "start", r"shell:AppsFolder\Microsoft.WindowsNotepad_8wekyb3d8bbwe!App"])
    elif cmd == "notes": subprocess.Popen(["cmd", "/c", "start", r"shell:AppsFolder\Microsoft.Office.OneNote.MemoryPreview"])
    elif cmd == "mute": send_key(0xAD) # VK_VOLUME_MUTE
    elif cmd == "prev": send_key(0xB1) # VK_MEDIA_PREV_TRACK
    elif cmd == "next": send_key(0xB0) # VK_MEDIA_NEXT_TRACK

def warm_up():
    for f in cfg.get('folders', []):
        for app_data in f.get('apps', []):
            IconExtractor.get_icon_pixmap(app_data.get('path', ''), 48)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    from dashboard import SCROLLBAR_CSS
    app.setStyleSheet(SCROLLBAR_CSS)
    
    app.setQuitOnLastWindowClosed(False)
    
    if sys.platform == 'win32':
        import ctypes
        myappid = 'seb.pandora.v1' 
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(myappid)
    
    from PyQt6.QtGui import QIcon
    app_icon = QIcon("assets/Pandora.svg")
    app.setWindowIcon(app_icon)
    
    cfg = ConfigManager.load()
    
    QTimer.singleShot(500, warm_up)
    
    dashboard = DashboardUI(cfg, [])
    dashboard.prewarm()
    
    grid_overlay = GridOverlay(cfg)
    grid_overlay.show(); grid_overlay.hide() # Force initialization
    dashboard.grid_overlay = grid_overlay
    
    # Initialize Radial Menu
    radial_menu = RadialMenu()
    radial_menu.reload_tools(cfg)
    radial_menu.command_triggered.connect(lambda cmd: handle_radial_cmd(cmd, grid_overlay, dashboard))
    app.radial_menu = radial_menu # Store for settings updates
    
    hook = GlobalHook(
        on_press=radial_menu.show_center,
        on_release=radial_menu.execute_current,
        on_move=radial_menu.update_mouse,
        cfg=cfg
    )
    app.global_hook = hook
    hook.start()
    
    wins = []
    for f in cfg['folders']:
        w = FolderIcon(f, cfg, dashboard)
        wins.append(w)
        w.show()
        
    dashboard.app_instances = wins
    
    tray = QSystemTrayIcon(app_icon)
    tray.show()
    tray.activated.connect(lambda reason: dashboard.show() if reason == QSystemTrayIcon.ActivationReason.Trigger else None)
    
    m = QMenu()
    
    def toggle_grid():
        is_visible = grid_overlay.toggle()
        grid_action.setText("Hide Grid" if is_visible else "Show Grid")
    
    grid_action = m.addAction("Show Grid")
    grid_action.triggered.connect(toggle_grid)
    m.addSeparator()
    add_menu = m.addMenu("Add Folder")
    def create_folder(t_type):
        existing_ids = [int(f['id'].split('_')[1]) for f in cfg['folders'] if f['id'].startswith('folder_') and f['id'].split('_')[1].isdigit()]
        new_id_num = (max(existing_ids) + 1) if existing_ids else (len(cfg['folders']) + 1)
        new_id = f"folder_{new_id_num}"
        
        pref = cfg.get('general_settings', {}).get('preferred_template')
        final_type = pref['type'] if pref else t_type
        final_name = pref['name'] if pref else "Default"
        
        new_f = {
            "id": new_id, 
            "name": f"New {final_type.title()}", 
            "pos": [100,100], 
            "apps": [], 
            "template_type": final_type, 
            "template_name": final_name
        }
        cfg['folders'].append(new_f)
        ConfigManager.save(cfg)
        w = FolderIcon(new_f, cfg, dashboard)
        dashboard.app_instances.append(w)
        w.show()
        
    add_menu.addAction("Grid Folder", lambda: create_folder("grid"))
    add_menu.addAction("Flower Folder", lambda: create_folder("flower"))
    m.addAction("Quit", app.quit)
    tray.setContextMenu(m)
    
    # Init Display Engine with saved settings
    from utils import DisplayEffectsEngine, restore_display_effects
    engine = DisplayEffectsEngine.instance()
    disp_cfg = cfg.get('display_effects', {})
    engine._active_preset = disp_cfg.get('active_preset', 'Sunset')
    engine._target_intensity = disp_cfg.get('warmth_intensity', 60) / 100.0
    
    # Cleanup on exit
    import atexit
    atexit.register(restore_display_effects)
    app.aboutToQuit.connect(restore_display_effects)
    
    sys.exit(app.exec())
