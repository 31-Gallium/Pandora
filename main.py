import faulthandler
faulthandler.enable(all_threads=True)
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
from ui.folder_panel import FolderPanel
from utils import VectorIcon, IconExtractor, DesktopMonitor
from ui.grid_overlay import GridOverlay
from ui.halo import Halo
from core_services.media_daemon import MediaDaemon
import sys
import os

import faulthandler
_fault_file = open("pandora_fault.log", "w")
faulthandler.enable(file=_fault_file, all_threads=True)

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

class HookSignals(QObject):
    press = pyqtSignal()
    release = pyqtSignal()
    mouse_move = pyqtSignal(object)
    mouse_wheel = pyqtSignal(int)
    key_event = pyqtSignal(int, int, int)
    cycle_layer = pyqtSignal(int)

class GlobalHook:
    def __init__(self, signals, cfg=None):
        self.signals = signals
        self.hook_kb = None; self.hook_ms = None; self.tilde_pressed = False
        self.center_x = None; self.center_y = None; self.radius = None
        self.activation_key = 0xC0
        self.enabled = True
        self.hold_mode = 'Hold'
        self.menu_open = False
        self.blocked_keys = set()
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
        if center:
            self.center_x = center.x()
            self.center_y = center.y()
        else:
            self.center_x = None
            self.center_y = None
        self.radius = radius

    def start(self):
        import threading
        self.thread = threading.Thread(target=self._run_hook_loop, daemon=True)
        self.thread.start()

    def _run_hook_loop(self):
        CMPFUNC = ctypes.WINFUNCTYPE(ctypes.c_int, ctypes.c_int, ctypes.c_int, ctypes.POINTER(ctypes.c_void_p))
        
        class MSLLHOOKSTRUCT(ctypes.Structure):
            _fields_ = [("pt", wintypes.POINT), ("mouseData", ctypes.c_uint32),
                        ("flags", ctypes.c_uint32), ("time", ctypes.c_uint32),
                        ("dwExtraInfo", ctypes.POINTER(ctypes.c_ulong))]
                        
        def kb_callback(nCode, wParam, lParam):
            if getattr(self, '_ignore_synthetic', False):
                return ctypes.windll.user32.CallNextHookEx(self.hook_kb, nCode, wParam, lParam)
                
            if nCode >= 0 and self.enabled:
                vkCode = ctypes.cast(lParam, ctypes.POINTER(ctypes.c_uint32))[0]
                is_keydown = (wParam == 0x0100 or wParam == 0x0104)
                is_keyup = (wParam == 0x0101 or wParam == 0x0105)
                
                nav_vks = {
                    0x57: Qt.Key.Key_W.value, 0x41: Qt.Key.Key_A.value,
                    0x53: Qt.Key.Key_S.value, 0x44: Qt.Key.Key_D.value,
                    0x26: Qt.Key.Key_Up.value, 0x28: Qt.Key.Key_Down.value,
                    0x25: Qt.Key.Key_Left.value, 0x27: Qt.Key.Key_Right.value,
                    0x0D: Qt.Key.Key_Return.value
                }
                
                if vkCode in nav_vks:
                    from PyQt6.QtCore import QEvent
                    if is_keydown:
                        if self.menu_open:
                            self.blocked_keys.add(vkCode)
                            self.signals.key_event.emit(int(QEvent.Type.KeyPress), nav_vks[vkCode], Qt.KeyboardModifier.NoModifier.value)
                            return 1
                        elif vkCode in self.blocked_keys:
                            return 1
                    elif is_keyup:
                        if vkCode in self.blocked_keys:
                            self.blocked_keys.remove(vkCode)
                            if self.menu_open:
                                self.signals.key_event.emit(int(QEvent.Type.KeyRelease), nav_vks[vkCode], Qt.KeyboardModifier.NoModifier.value)
                            return 1
                
                # Check for Hub custom buttons first
                if self.menu_open and self.hub_cfg.get("switching_mode") == "custom_buttons":
                    if wParam == 0x0100 or wParam == 0x0104: # WM_KEYDOWN
                        up_vk, up_c, up_a, up_s = self._parse_key(self.hub_up)
                        dn_vk, dn_c, dn_a, dn_s = self._parse_key(self.hub_down)
                        
                        if vkCode == up_vk and self._check_mods(up_c, up_a, up_s):
                            app = QApplication.instance()
                            if hasattr(app, 'halo') and hasattr(app.halo, 'hub_manager'):
                                self.signals.cycle_layer.emit(1)
                            return 1
                            
                        if vkCode == dn_vk and self._check_mods(dn_c, dn_a, dn_s):
                            app = QApplication.instance()
                            if hasattr(app, 'halo') and hasattr(app.halo, 'hub_manager'):
                                self.signals.cycle_layer.emit(-1)
                            return 1

                if self.menu_open:
                    if vkCode == 0x20: # Spacebar
                        app = QApplication.instance()
                        if hasattr(app, 'halo'):
                            dx = app.halo.current_mouse_pos.x() - app.halo.center_pt.x()
                            dy = app.halo.current_mouse_pos.y() - app.halo.center_pt.y()
                            is_in_hub = math.hypot(dx, dy) < app.halo.inner_radius
                            
                            hub_holding = False
                            is_intercept_type = False
                            if hasattr(app.halo, 'hub_manager'):
                                mod = app.halo.hub_manager.get_active_module()
                                if mod:
                                    hub_holding = getattr(mod, '_space_pressed', False)
                                    if mod.__class__.__name__ in ["StopwatchHub", "MediaHub", "TimerHub", "TimeHub"]:
                                        is_intercept_type = True
                            
                            if is_in_hub or hub_holding or is_intercept_type:
                                from PyQt6.QtCore import QEvent
                                is_keydown_ev = (wParam == 0x0100 or wParam == 0x0104)
                                
                                if is_keydown_ev:
                                    if 0x20 in self.blocked_keys:
                                        return 1 # Block auto-repeat
                                    self.blocked_keys.add(0x20)
                                else:
                                    if 0x20 in self.blocked_keys:
                                        self.blocked_keys.remove(0x20)
                                        
                                etype = QEvent.Type.KeyPress if is_keydown_ev else QEvent.Type.KeyRelease
                                self.signals.key_event.emit(int(etype), Qt.Key.Key_Space.value, Qt.KeyboardModifier.NoModifier.value)
                                return 1 # Block Windows from seeing it

                target_vk, req_ctrl, req_alt, req_shift = self._parse_key(self.activation_key)
                
                if vkCode == target_vk:
                    if self._check_mods(req_ctrl, req_alt, req_shift):
                        if wParam == 0x0100 or wParam == 0x0104: # WM_KEYDOWN or WM_SYSKEYDOWN
                            if not getattr(self, 'tilde_pressed', False): 
                                self.tilde_pressed = True
                                self._activation_passed_time = False
                                
                                def _wait_and_fire():
                                    import time
                                    time.sleep(0.25)
                                    if getattr(self, 'tilde_pressed', False):
                                        self._activation_passed_time = True
                                        if self.hold_mode == 'Toggle':
                                            if self.menu_open:
                                                self.menu_open = False
                                                self.signals.release.emit()
                                            else:
                                                self.menu_open = True
                                                self.signals.press.emit()
                                        else:
                                            if not self.menu_open:
                                                self.menu_open = True
                                                self.signals.press.emit()
                                                
                                import threading
                                threading.Thread(target=_wait_and_fire, daemon=True).start()
                                
                        elif wParam == 0x0101 or wParam == 0x0105: # WM_KEYUP or WM_SYSKEYUP
                            self.tilde_pressed = False
                            
                            if not getattr(self, '_activation_passed_time', False) and not self.menu_open:
                                # The user tapped it! Pass through the keystroke.
                                self._ignore_synthetic = True
                                ctypes.windll.user32.keybd_event(vkCode, 0, 0, 0) # KeyDown
                                ctypes.windll.user32.keybd_event(vkCode, 0, 2, 0) # KeyUp
                                self._ignore_synthetic = False
                                
                            if self.hold_mode != 'Toggle':
                                if self.menu_open:
                                    self.menu_open = False
                                    self.signals.release.emit()
                        return 1
            return ctypes.windll.user32.CallNextHookEx(self.hook_kb, nCode, wParam, lParam)

        def ms_callback(nCode, wParam, lParam):
            if nCode >= 0 and self.menu_open:
                if wParam == 0x0200: # WM_MOUSEMOVE
                    ms_data = ctypes.cast(lParam, ctypes.POINTER(MSLLHOOKSTRUCT))[0]
                    pos = ms_data.pt

                    if self.center_x is not None and self.radius:
                        dx, dy = pos.x - self.center_x, pos.y - self.center_y
                        dist = math.hypot(dx, dy)
                        if dist > self.radius:
                            angle = math.atan2(dy, dx)
                            new_x = self.center_x + int(self.radius * math.cos(angle))
                            new_y = self.center_y + int(self.radius * math.sin(angle))
                            ctypes.windll.user32.SetCursorPos(new_x, new_y)
                            return 1

                    app = QApplication.instance()
                    if hasattr(app, 'halo'):
                        app.halo.last_global_mouse_pos = QPoint(pos.x, pos.y)
                elif wParam == 0x020A: # WM_MOUSEWHEEL
                    ms_data = ctypes.cast(lParam, ctypes.POINTER(MSLLHOOKSTRUCT))[0]
                    delta = ctypes.c_short(ms_data.mouseData >> 16).value
                    app = QApplication.instance()
                    if hasattr(app, 'halo'):
                        self.signals.mouse_wheel.emit(delta)
                    return 1

            return ctypes.windll.user32.CallNextHookEx(self.hook_ms, nCode, wParam, lParam)

        self.proc_kb = CMPFUNC(kb_callback); self.proc_ms = CMPFUNC(ms_callback)
        self.hook_kb = ctypes.windll.user32.SetWindowsHookExW(13, self.proc_kb, None, 0)
        self.hook_ms = ctypes.windll.user32.SetWindowsHookExW(14, self.proc_ms, None, 0)

        # Pump message loop in this thread
        msg = ctypes.wintypes.MSG()
        while ctypes.windll.user32.GetMessageW(ctypes.byref(msg), 0, 0, 0) != 0:
            ctypes.windll.user32.TranslateMessage(ctypes.byref(msg))
            ctypes.windll.user32.DispatchMessageW(ctypes.byref(msg))

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
    elif cmd in ["explorer", "files"]: subprocess.Popen("explorer.exe")
    elif cmd in ["grid", "toggle grid"]: grid.toggle()
    elif cmd in ["screenshot", "snip"]:
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
    elif cmd in ["night", "night light"]:
        from utils import DisplayEffectsEngine
        engine = DisplayEffectsEngine.instance()
        if not engine._is_enabled:
            val = cfg.get('display_effects', {}).get('warmth_intensity', 50) / 100.0
            engine.set_intensity(val)
            engine.set_enabled(True)
        else:
            engine.set_enabled(False)
    elif cmd in ["taskmgr", "tasks"]: subprocess.Popen("taskmgr")
    elif cmd in ["settings", "pandora"]: dash.show()
    elif cmd in ["trash", "empty trash"]: subprocess.Popen(["powershell.exe", "-Command", "Clear-RecycleBin -Force -ErrorAction SilentlyContinue"])
    elif cmd == "search": send_win_key(0x53) # Win + S
    elif cmd == "power": subprocess.Popen(["shutdown", "/s", "/t", "60", "/c", "Pandora: Shutting down in 60s. Use 'shutdown /a' to cancel."])
    elif cmd == "calc": subprocess.Popen("calc")
    elif cmd == "cmd": subprocess.Popen(["cmd", "/c", "start", "cmd"])
    elif cmd == "notepad": subprocess.Popen(["cmd", "/c", "start", r"shell:AppsFolder\Microsoft.WindowsNotepad_8wekyb3d8bbwe!App"])
    elif cmd in ["notes", "sticky notes"]: subprocess.Popen(["cmd", "/c", "start", r"shell:AppsFolder\Microsoft.Office.OneNote.MemoryPreview"])
    elif cmd == "mute": send_key(0xAD) # VK_VOLUME_MUTE
    elif cmd in ["prev", "prev media"]: send_key(0xB1) # VK_MEDIA_PREV_TRACK
    elif cmd in ["next", "next media"]: send_key(0xB0) # VK_MEDIA_NEXT_TRACK

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
        self.ws_port = None
        
        # Start WebSocket Server
        from core_services.ws_server import WebSocketServerThread
        self.ws_thread = WebSocketServerThread(self.cfg, port=0)
        self.ws_thread.config_received.connect(self.handle_config_update)
        self.ws_thread.port_bound.connect(self._handle_port_bound)
        self.ws_thread.create_folder_requested.connect(self._on_create_folder_requested)
        self.ws_thread.start()

    def _on_create_folder_requested(self):
        if hasattr(self, 'create_folder_callback'):
            self.create_folder_callback("grid")

    def _handle_port_bound(self, port):
        self.ws_port = port
        port_file = os.path.join(os.environ['APPDATA'], 'Pandora', 'ws_port.txt')
        try:
            with open(port_file, 'w') as f:
                f.write(str(port))
        except Exception as e:
            print(f"Failed to write ws_port.txt: {e}")

    def handle_config_update(self, new_cfg):
        # Update our running config dictionary
        self.cfg.clear()
        self.cfg.update(new_cfg)
        
        # Inject desktop wallpaper accent colors if Dashboard theme is Desktop
        gen = self.cfg.setdefault('general_settings', {})
        if gen.get('dashboard_theme') == 'Desktop':
            from utils import get_desktop_accent_colors
            accents = get_desktop_accent_colors()
            gen['desktop_accents'] = [list(c) for c in accents]
            
        # Push updated config back to the Electron dashboard clients to keep them in sync
        self.ws_thread.send_config_to_clients(self.cfg)
        
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
        for w in self.app_instances[:]:
            try:
                # Use root_data to match the panel's top-level folder, even when
                # the user has navigated into a nested folder (self.data != root)
                root = getattr(w, 'root_data', w.data) if hasattr(w, 'root_data') else w.data
                if 'id' in root:
                    for f in self.cfg.get('folders', []):
                        if f.get('id') == root.get('id'):
                            root.clear()
                            root.update(f)
                            break
                if hasattr(w, 'update_geometry'):
                    w.update_geometry()
                if hasattr(w, 'refresh'):
                    w.refresh()
                if hasattr(w, 'update'):
                    w.update()
            except RuntimeError as e:
                if "has been deleted" in str(e):
                    if w in self.app_instances:
                        self.app_instances.remove(w)
                else:
                    raise
                


    def prewarm(self):
        pass
        
    def show(self):
        # Spawn Electron
        if self.electron_process is None or self.electron_process.poll() is not None:
            electron_path = os.path.abspath(r"electron_dashboard\node_modules\.bin\electron.cmd")
            if not os.path.exists(electron_path):
                print("Electron not found! Run npm install in electron_dashboard")
                return
            env = os.environ.copy()
            if self.ws_port is not None:
                env['PANDORA_WS_PORT'] = str(self.ws_port)
            self.electron_process = subprocess.Popen([electron_path, "."], cwd="electron_dashboard", env=env)
            




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
    
    # Preload volume to eliminate 70ms import/COM lag on first run
    from utils import get_system_volume_level
    get_system_volume_level()
    
    # Preload Halo window buffers for instant popup (eliminates 170ms Qt window allocation lag)
    halo.show()
    QApplication.processEvents()
    halo.hide()
    
    halo.command_triggered.connect(lambda cmd: handle_halo_cmd(cmd, grid_overlay, dashboard))
    app.halo = halo # Store for settings updates
    
    signals = HookSignals()
    signals.press.connect(halo.show_center, Qt.ConnectionType.QueuedConnection)
    signals.release.connect(halo.execute_current, Qt.ConnectionType.QueuedConnection)
    signals.mouse_wheel.connect(halo.handle_wheel, Qt.ConnectionType.QueuedConnection)
    signals.cycle_layer.connect(halo._cycle_layer, Qt.ConnectionType.QueuedConnection)
    
    def on_key_event_routed(etype_val, key_val, mod_val):
        from PyQt6.QtGui import QKeyEvent
        from PyQt6.QtCore import QEvent, Qt
        ev = QKeyEvent(QEvent.Type(etype_val), Qt.Key(key_val), Qt.KeyboardModifier(mod_val))
        QApplication.postEvent(halo, ev)
        
    signals.key_event.connect(on_key_event_routed)
    
    hook = GlobalHook(
        signals=signals,
        cfg=cfg
    )
    app.global_hook = hook
    hook.start()
    
    wins = []
    for f in cfg['folders']:
        if not f.get('is_nested', False):
            w = FolderPanel(f, cfg, dashboard)
            wins.append(w)
            w.show()
        
    dashboard.app_instances = wins
    
    tray = QSystemTrayIcon(app_icon)
    tray.show()
    
    from PyQt6.QtWidgets import QWidget, QHBoxLayout, QPushButton, QVBoxLayout
    from PyQt6.QtCore import Qt, QSize
    from PyQt6.QtGui import QIcon, QCursor
    import os
    
    class CustomTrayMenu(QWidget):
        def __init__(self, app, create_folder, restart_app, dashboard):
            super().__init__()
            self.setWindowFlags(Qt.WindowType.Popup | Qt.WindowType.FramelessWindowHint | Qt.WindowType.NoDropShadowWindowHint)
            self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
            
            self.app = app
            self.create_folder = create_folder
            self.restart_app = restart_app
            self.dashboard = dashboard
            
            layout = QHBoxLayout(self)
            layout.setContentsMargins(10, 10, 10, 10)
            layout.setSpacing(0)
            
            self.bg = QWidget(self)
            self.bg.setStyleSheet("""
                QWidget {
                    background-color: rgba(20, 20, 25, 230);
                    border: 1px solid rgba(255, 255, 255, 20);
                    border-radius: 25px;
                }
            """)
            bg_layout = QHBoxLayout(self.bg)
            bg_layout.setContentsMargins(5, 5, 5, 5)
            bg_layout.setSpacing(5)
            
            base_dir = os.path.dirname(os.path.abspath(__file__))
            
            def make_btn(icon_name, tooltip, callback):
                btn = QPushButton()
                btn.setFixedSize(40, 40)
                btn.setCursor(Qt.CursorShape.PointingHandCursor)
                btn.setToolTip(tooltip)
                
                # Load the SVG, convert to pixmap and tint it white so it doesn't get washed out
                icon_path = os.path.join(base_dir, 'assets', icon_name)
                from PyQt6.QtGui import QPixmap, QPainter, QColor, QIcon
                
                original_icon = QIcon(icon_path)
                pixmap = original_icon.pixmap(24, 24)
                
                # Tinting logic
                painter = QPainter(pixmap)
                painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_SourceIn)
                painter.fillRect(pixmap.rect(), QColor(255, 255, 255, 220)) # Crisp soft white
                painter.end()
                
                btn.setIcon(QIcon(pixmap))
                btn.setIconSize(QSize(20, 20))
                btn.setStyleSheet("""
                    QPushButton {
                        background-color: transparent;
                        border: none;
                        border-radius: 20px;
                    }
                    QPushButton:hover {
                        background-color: rgba(255, 255, 255, 20);
                    }
                    QPushButton:pressed {
                        background-color: rgba(255, 255, 255, 10);
                    }
                    QToolTip {
                        background-color: #1b1b1b;
                        color: white;
                        border: 1px solid #333;
                        border-radius: 4px;
                    }
                """)
                btn.clicked.connect(lambda checked=False, cb=callback: self.on_click(cb))
                bg_layout.addWidget(btn)
                return btn
                
            make_btn('general.svg', "Settings", self.dashboard.show)
            make_btn('add.svg', "Add Folder", lambda: self.create_folder("grid"))
            make_btn('toggle grid.svg', "Toggle Grid", lambda: self.dashboard.grid_overlay.toggle() if hasattr(self.dashboard, 'grid_overlay') and self.dashboard.grid_overlay else None)
            make_btn('reset.svg', "Restart", self.restart_app)
            make_btn('power.svg', "Quit", self.app.quit)
            
            layout.addWidget(self.bg)
            
        def on_click(self, callback):
            self.hide()
            callback()

    def create_folder(t_type):
        from PyQt6.QtGui import QCursor
        from PyQt6.QtWidgets import QApplication
        existing_ids = [int(f['id'].split('_')[1]) for f in cfg['folders'] if f['id'].startswith('folder_') and f['id'].split('_')[1].isdigit()]
        new_id_num = (max(existing_ids) + 1) if existing_ids else (len(cfg['folders']) + 1)
        new_id = f"folder_{new_id_num}"
        
        # Grid parameters
        gs = cfg.get('general_settings', {}).get('grid_size', 100)
        pad = cfg.get('general_settings', {}).get('grid_padding', 20)
        margin_y_top = cfg.get('general_settings', {}).get('margin_y_top', 40)
        
        screen = QApplication.primaryScreen().geometry()
        scr_geom = screen
        scr_cx = scr_geom.width() / 2
        scr_cy = scr_geom.height() / 2
        
        # Get occupied grid rects
        occupied = []
        for other in getattr(dashboard, 'app_instances', []):
            snap = other.data.get('grid_snap', cfg.get('general_settings', {}).get('snap_to_grid', True))
            if snap:
                try:
                    ox = other.pos().x() - pad
                    oy = other.pos().y() - pad + margin_y_top
                    c = round((ox - scr_cx) / gs)
                    r = round((oy - scr_cy) / gs)
                    occupied.append((c, r, other.grid_cols, other.grid_rows))
                except RuntimeError:
                    pass
                    
        def is_free(c, r, target_cols, target_rows):
            px = c * gs + scr_cx + pad
            py = r * gs + scr_cy + pad - margin_y_top
            target_w = target_cols * gs - 16
            target_h = target_rows * gs - 16
            if px < scr_geom.left() or px + target_w > scr_geom.right(): return False
            if py < scr_geom.top() or py + target_h > scr_geom.bottom(): return False
            
            for (oc, orow, ocols, orows) in occupied:
                if not (c + target_cols <= oc or c >= oc + ocols or r + target_rows <= orow or r >= orow + orows):
                    return False
            return True

        found_pos = None
        final_cols = 2
        final_rows = 2
        
        def find_space(cols, rows):
            for radius in range(0, 30):
                for dc in range(-radius, radius + 1):
                    for dr in range(-radius, radius + 1):
                        if max(abs(dc), abs(dr)) == radius:
                            if is_free(dc, dr, cols, rows):
                                return dc, dr
            return None

        # Try sizes: 2x2 -> 2x1 -> 1x2 -> 1x1
        for (c_test, r_test) in [(2,2), (2,1), (1,2), (1,1)]:
            res = find_space(c_test, r_test)
            if res:
                found_pos = res
                final_cols = c_test
                final_rows = r_test
                break
                
        snap = True
        if found_pos:
            c, r = found_pos
            px = c * gs + scr_cx + pad
            py = r * gs + scr_cy + pad - margin_y_top
        else:
            snap = False
            final_cols = 2
            final_rows = 2
            pos = QCursor.pos()
            px = pos.x() - 50
            py = pos.y() - 50
            
        new_f = {
            "id": new_id, 
            "name": f"New Folder", 
            "pos": [int(px), int(py)], 
            "apps": [],
            "show_title": True,
            "grid_cols": final_cols,
            "grid_rows": final_rows,
            "grid_snap": snap
        }
        cfg['folders'].append(new_f)
        from config import ConfigManager
        ConfigManager.save(cfg)
        w = FolderPanel(new_f, cfg, dashboard)
        dashboard.app_instances.append(w)
        w.show()
        
    def restart_app():
        import subprocess
        cleanup_app()
        subprocess.Popen([sys.executable] + sys.argv)
        app.quit()

    app.create_folder_callback = create_folder
    custom_tray_menu = CustomTrayMenu(app, create_folder, restart_app, dashboard)
    
    def on_tray_activated(reason):
        if reason == QSystemTrayIcon.ActivationReason.Trigger:
            dashboard.show()
        elif reason == QSystemTrayIcon.ActivationReason.Context:
            pos = QCursor.pos()
            custom_tray_menu.adjustSize()
            w = custom_tray_menu.width()
            h = custom_tray_menu.height()
            
            x = pos.x() - w // 2
            y = pos.y() - h - 10
            
            screen = QApplication.screenAt(pos)
            if screen:
                rect = screen.availableGeometry()
                if x + w > rect.right(): x = rect.right() - w - 10
                if y + h > rect.bottom(): y = rect.bottom() - h - 10
                if y < rect.top(): y = rect.top() + 10
                if x < rect.left(): x = rect.left() + 10
                
            custom_tray_menu.move(x, y)
            custom_tray_menu.show()
            custom_tray_menu.raise_()
            custom_tray_menu.activateWindow()
            
    tray.activated.connect(on_tray_activated)
    from utils import DisplayEffectsEngine, restore_display_effects
    engine = DisplayEffectsEngine.instance()
    
    # Dynamically install context menu while app is running
    disp_cfg = cfg.get('display_effects', {})
    engine._active_preset = disp_cfg.get('active_preset', 'Sunset')
    engine._target_intensity = disp_cfg.get('warmth_intensity', 60) / 100.0
    
    # Cleanup on exit
    import atexit
    
    def cleanup_app():
        restore_display_effects()
        if hasattr(dashboard, 'electron_process') and dashboard.electron_process:
            try:
                import subprocess
                subprocess.run(['taskkill', '/F', '/T', '/PID', str(dashboard.electron_process.pid)], capture_output=True)
            except Exception:
                pass
                
        # Remove context menu so it hides when app is closed

    atexit.register(cleanup_app)
    app.aboutToQuit.connect(cleanup_app)
    
    exit_code = app.exec()
    import os
    os._exit(exit_code)