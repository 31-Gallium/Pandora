import sys

SCROLLBAR_CSS = '''
QScrollArea, QScrollArea > QWidget > QWidget, QListWidget, QListView, QTextEdit, QPlainTextEdit {
    background: transparent;
    border: none;
}
QScrollBar:vertical {
    width: 6px;
    background: transparent;
    margin: 0px;
}
QScrollBar::handle:vertical {
    background: rgba(255, 255, 255, 40);
    border-radius: 3px;
    min-height: 20px;
}
QScrollBar::handle:vertical:hover {
    background: rgba(255, 255, 255, 80);
}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical,
QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {
    background: none;
    border: none;
    height: 0px;
    width: 0px;
}

QScrollBar:horizontal {
    height: 6px;
    background: transparent;
    margin: 0px;
}
QScrollBar::handle:horizontal {
    background: rgba(255, 255, 255, 40);
    border-radius: 3px;
    min-width: 20px;
}
QScrollBar::handle:horizontal:hover {
    background: rgba(255, 255, 255, 80);
}
QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal,
QScrollBar::add-page:horizontal, QScrollBar::sub-page:horizontal {
    background: none;
    border: none;
    height: 0px;
    width: 0px;
}
'''


from PyQt6.QtWidgets import QApplication, QSystemTrayIcon, QMenu
from PyQt6.QtCore import QTimer
from config import ConfigManager
from folder_icon import FolderIcon
from utils import VectorIcon, IconExtractor, DesktopMonitor
from grid_overlay import GridOverlay
from halo import Halo
from core_services.media_daemon import MediaDaemon
import os
import math
import ctypes
import subprocess
from ctypes import wintypes
from PyQt6.QtGui import QCursor, QKeyEvent
from PyQt6.QtCore import (Qt, QEvent, QPoint, QTimer, qInstallMessageHandler, QtMsgType, QParallelAnimationGroup, QEasingCurve, QPropertyAnimation, QVariantAnimation, QObject, pyqtSignal)

def qt_message_handler(mode, context, message):
    if "QFont::setPointSize" in message or "Point size <= 0" in message:
        return
    # Ignore other harmless warnings if necessary, otherwise print
    print(message)

qInstallMessageHandler(qt_message_handler)

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
        rad_cfg = cfg.get('halo', {})
        self.activation_key = rad_cfg.get('activation_key', 0xC0)
        self.enabled = rad_cfg.get('enabled', True)
        self.hold_mode = rad_cfg.get('hold_mode', 'Hold')
        
        self.hub_cfg = cfg.get('hub_config', {})
        self.hub_up = self.hub_cfg.get('custom_up', '0x26')
        self.hub_down = self.hub_cfg.get('custom_down', '0x28')
        
    def _parse_key(self, key_str):
        parts = str(key_str).split("+")
        try:
            target_vk = int(parts[-1], 16) if parts[-1].startswith("0x") else int(parts[-1])
        except:
            target_vk = 0xC0
        return target_vk, "Ctrl" in parts, "Alt" in parts, "Shift" in parts

    def _check_mods(self, req_ctrl, req_alt, req_shift):
        user32 = ctypes.windll.user32
        ctrl_pressed = (user32.GetAsyncKeyState(0x11) & 0x8000) != 0
        alt_pressed = (user32.GetAsyncKeyState(0x12) & 0x8000) != 0
        shift_pressed = (user32.GetAsyncKeyState(0x10) & 0x8000) != 0
        return ctrl_pressed == req_ctrl and alt_pressed == req_alt and shift_pressed == req_shift

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
                
                # Check for Hub custom buttons first
                if self.menu_open and self.hub_cfg.get("switching_mode") == "custom_buttons":
                    if wParam == 0x0100 or wParam == 0x0104: # WM_KEYDOWN
                        up_vk, up_c, up_a, up_s = self._parse_key(self.hub_up)
                        dn_vk, dn_c, dn_a, dn_s = self._parse_key(self.hub_down)
                        
                        if vkCode == up_vk and self._check_mods(up_c, up_a, up_s):
                            app = QApplication.instance()
                            if hasattr(app, 'halo') and hasattr(app.halo, 'hub_manager'):
                                app.halo.hub_manager.cycle_layer(1)
                            return 1
                            
                        if vkCode == dn_vk and self._check_mods(dn_c, dn_a, dn_s):
                            app = QApplication.instance()
                            if hasattr(app, 'halo') and hasattr(app.halo, 'hub_manager'):
                                app.halo.hub_manager.cycle_layer(-1)
                            return 1

                if self.menu_open:
                    if vkCode == 0x20: # Spacebar
                        app = QApplication.instance()
                        if hasattr(app, 'halo'):
                            dx = app.halo.current_mouse_pos.x() - app.halo.center_pt.x()
                            dy = app.halo.current_mouse_pos.y() - app.halo.center_pt.y()
                            is_in_hub = math.hypot(dx, dy) < app.halo.inner_radius
                            
                            # When a spacebar hold is active, intercept ALL spacebar
                            # events (repeating keydowns + the final keyup) regardless
                            # of cursor position, so they never leak to background apps.
                            hub_holding = False
                            is_intercept_type = False
                            if hasattr(app.halo, 'hub_manager'):
                                mod = app.halo.hub_manager.get_active_module()
                                if mod:
                                    hub_holding = getattr(mod, '_space_pressed', False)
                                    if mod.__class__.__name__ in ["StopwatchHub", "MediaHub", "TimerHub", "TimeHub"]:
                                        is_intercept_type = True
                            
                            if is_in_hub or hub_holding or is_intercept_type:
                                from PyQt6.QtGui import QKeyEvent
                                from PyQt6.QtCore import QEvent
                                etype = QEvent.Type.KeyPress if (wParam == 0x0100 or wParam == 0x0104) else QEvent.Type.KeyRelease
                                key_event = QKeyEvent(etype, Qt.Key.Key_Space, Qt.KeyboardModifier.NoModifier)
                                QApplication.postEvent(app.halo, key_event)
                                return 1 # Block Windows from seeing it

                target_vk, req_ctrl, req_alt, req_shift = self._parse_key(self.activation_key)
                
                if vkCode == target_vk:
                    if self._check_mods(req_ctrl, req_alt, req_shift):
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
            if nCode >= 0 and self.menu_open:
                if wParam == 0x0200: # WM_MOUSEMOVE
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
                elif wParam == 0x020A: # WM_MOUSEWHEEL
                    ms_data = ctypes.cast(lParam, ctypes.POINTER(MSLLHOOKSTRUCT))[0]
                    delta = ctypes.c_short(ms_data.mouseData >> 16).value
                    app = QApplication.instance()
                    if hasattr(app, 'halo'):
                        # Call directly to handle_wheel in halo since we bypassed Qt's event loop
                        app.halo.handle_wheel(delta)
                    return 1

            return ctypes.windll.user32.CallNextHookEx(self.hook_ms, nCode, wParam, lParam)

        self.proc_kb = CMPFUNC(kb_callback); self.proc_ms = CMPFUNC(ms_callback)
        self.hook_kb = ctypes.windll.user32.SetWindowsHookExW(13, self.proc_kb, None, 0)
        self.hook_ms = ctypes.windll.user32.SetWindowsHookExW(14, self.proc_ms, None, 0)

def handle_halo_cmd(cmd, grid, dash):
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
        # 200ms delay to ensure halo menu is fully hidden from screen
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

class ElectronDashboardManager(QObject):
    configUpdated = pyqtSignal(dict)
    
    def __init__(self, cfg, app_instances):
        super().__init__()
        self.cfg = cfg
        self.app_instances = app_instances
        self.grid_overlay = None
        self.electron_process = None
        
        # Start WebSocket Server
        from ws_server import WebSocketServerThread
        self.ws_thread = WebSocketServerThread(self.cfg)
        self.ws_thread.config_received.connect(self.handle_config_update)
        self.ws_thread.start()

    def handle_config_update(self, new_cfg):
        # Update our running config dictionary
        self.cfg.clear()
        self.cfg.update(new_cfg)
        
        # Save to disk
        ConfigManager.save(self.cfg)
        
        app = QApplication.instance()
        
        # 1. Update Display Engine
        disp_cfg = self.cfg.get('display_effects', {})
        from utils import DisplayEffectsEngine
        engine = DisplayEffectsEngine.instance()
        engine._active_preset = disp_cfg.get('active_preset', 'Sunset')
        engine._target_intensity = disp_cfg.get('warmth_intensity', 60) / 100.0
        if engine._is_enabled:
            engine.set_intensity(engine._target_intensity)
            
        # 2. Update Halo Menu Settings
        if hasattr(app, 'halo'):
            app.halo.reload_tools(self.cfg)
            
        # 3. Update Global Hook Settings
        if hasattr(app, 'global_hook'):
            app.global_hook.reload_config(self.cfg)
            
        # Emit signal in case any other modular UI components need to react
        self.configUpdated.emit(self.cfg)
        
        # 4. Refresh all folder icon visuals on the desktop
        for w in self.app_instances:
            if hasattr(w, 'data') and 'id' in w.data:
                for f in self.cfg.get('folders', []):
                    if f.get('id') == w.data.get('id'):
                        w.data.clear()
                        w.data.update(f)
                        break
            if hasattr(w, 'view') and w.view and not w.view.isHidden():
                w.view.refresh()
                w.view.update()
            if hasattr(w, 'update'):
                w.update()

    def prewarm(self):
        pass
        
    def show(self):
        # Spawn Electron
        if self.electron_process is None or self.electron_process.poll() is not None:
            electron_path = os.path.abspath(r"electron_dashboard\node_modules\.bin\electron.cmd")
            if not os.path.exists(electron_path):
                print("Electron not found! Run npm install in electron_dashboard")
                return
            self.electron_process = subprocess.Popen([electron_path, "."], cwd="electron_dashboard")

    def show_folder(self, fid):
        """Open the Electron dashboard and navigate to a specific folder's settings."""
        self.show()
        # Send a WebSocket command to Electron to switch to the Folders tab and open the editor
        self.ws_thread.send_command_to_clients({
            "type": "show_folder",
            "folder_id": fid
        })

    def handle_folder_deleted(self, folder_widget):
        """Remove a folder widget from the app_instances list."""
        self.app_instances = [w for w in self.app_instances if w is not folder_widget]

if __name__ == "__main__":
    app = QApplication(sys.argv)
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
    
    # Initialize Core Services
    app.media_daemon = MediaDaemon()
    
    QTimer.singleShot(500, warm_up)
    
    dashboard = ElectronDashboardManager(cfg, [])
    dashboard.prewarm()
    
    grid_overlay = GridOverlay(cfg)
    grid_overlay.show(); grid_overlay.hide() # Force initialization
    dashboard.grid_overlay = grid_overlay
    
    # Initialize Halo Menu
    halo = Halo()
    halo.reload_tools(cfg)
    halo.command_triggered.connect(lambda cmd: handle_halo_cmd(cmd, grid_overlay, dashboard))
    app.halo = halo # Store for settings updates
    
    hook = GlobalHook(
        on_press=halo.show_center,
        on_release=halo.execute_current,
        on_move=halo.update_mouse,
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
