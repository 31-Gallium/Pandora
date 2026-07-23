import sys
import os

if sys.stdout is None:
    sys.stdout = open(os.devnull, 'w')
if sys.stderr is None:
    sys.stderr = open(os.devnull, 'w')

if "--uninstall" in sys.argv:
    from PyQt6.QtWidgets import QApplication
    from uninstaller import UninstallerUI
    app = QApplication(sys.argv)
    font = app.font()
    font.setFamily("Segoe UI")
    app.setFont(font)
    ui = UninstallerUI()
    ui.show()
    sys.exit(app.exec())

import winreg

def force_high_performance_gpu():
    import json
    appdata = os.path.join(os.environ.get('APPDATA', os.path.expanduser('~')), "Pandora")
    config_path = os.path.join(appdata, 'config.json')
    pref = 0
    if os.path.exists(config_path):
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                pref = data.get('general_settings', {}).get('gpu_preference', 0)
        except Exception:
            pass

    paths_to_register = {sys.executable}
    base_exe_name = os.path.basename(sys.executable)
    if hasattr(sys, 'base_exec_prefix') and sys.base_exec_prefix:
        base_exe = os.path.join(sys.base_exec_prefix, base_exe_name)
        if os.path.exists(base_exe):
            paths_to_register.add(os.path.abspath(base_exe))
            paths_to_register.add(os.path.realpath(base_exe))
    paths_to_register.add(os.path.realpath(sys.executable))
    paths_to_register.add(os.path.abspath(sys.executable))

    key_path = r"Software\Microsoft\DirectX\UserGpuPreferences"
    try:
        key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, key_path, 0, winreg.KEY_ALL_ACCESS)
    except FileNotFoundError:
        if pref == 0: return
        key = winreg.CreateKey(winreg.HKEY_CURRENT_USER, key_path)
    
    try:
        for exe_path in paths_to_register:
            if not exe_path:
                continue
            norm_exe_path = os.path.normpath(exe_path)
            if pref == 0:
                try:
                    winreg.DeleteValue(key, norm_exe_path)
                except FileNotFoundError:
                    pass
            else:
                target_val = f"GpuPreference={pref};"
                try:
                    value, _ = winreg.QueryValueEx(key, norm_exe_path)
                    if target_val in str(value):
                        continue
                except FileNotFoundError:
                    pass
                winreg.SetValueEx(key, norm_exe_path, 0, winreg.REG_SZ, target_val)
    finally:
        winreg.CloseKey(key)

force_high_performance_gpu()

import faulthandler
try:
    faulthandler.enable(all_threads=True, file=sys.stderr)
except Exception:
    pass

if getattr(sys, 'frozen', False):
    os.chdir(os.path.dirname(sys.executable))

if "--startup" in sys.argv:
    import time
    import ctypes
    user32 = ctypes.windll.user32
    
    def wait_for_desktop():
        import ctypes
        import time
        from ctypes import wintypes
        
        user32 = ctypes.windll.user32
        wtsapi32 = ctypes.windll.wtsapi32
        WTS_CURRENT_SERVER_HANDLE = 0
        WTS_CURRENT_SESSION = -1
        WTSSessionInfoEx = 25

        # Define ctypes signatures to prevent handle truncation on 64-bit Python
        user32.FindWindowW.argtypes = [wintypes.LPCWSTR, wintypes.LPCWSTR]
        user32.FindWindowW.restype = wintypes.HWND
        
        user32.IsWindowVisible.argtypes = [wintypes.HWND]
        user32.IsWindowVisible.restype = wintypes.BOOL
        
        user32.OpenInputDesktop.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
        user32.OpenInputDesktop.restype = wintypes.HWND
        
        user32.CloseDesktop.argtypes = [wintypes.HWND]
        user32.CloseDesktop.restype = wintypes.BOOL
        
        user32.GetUserObjectInformationW.argtypes = [
            wintypes.HWND, ctypes.c_int, ctypes.c_void_p, wintypes.DWORD, ctypes.POINTER(wintypes.DWORD)
        ]
        user32.GetUserObjectInformationW.restype = wintypes.BOOL
        
        user32.SendMessageTimeoutW.argtypes = [
            wintypes.HWND, wintypes.UINT, wintypes.WPARAM, wintypes.LPARAM,
            wintypes.UINT, wintypes.UINT, ctypes.c_void_p
        ]
        user32.SendMessageTimeoutW.restype = wintypes.LPARAM
        
        user32.GetClassNameW.argtypes = [wintypes.HWND, wintypes.LPWSTR, ctypes.c_int]
        user32.GetClassNameW.restype = ctypes.c_int
        
        user32.FindWindowExW.argtypes = [wintypes.HWND, wintypes.HWND, wintypes.LPCWSTR, wintypes.LPCWSTR]
        user32.FindWindowExW.restype = wintypes.HWND
        
        wtsapi32.WTSQuerySessionInformationW.argtypes = [
            wintypes.HANDLE, wintypes.DWORD, wintypes.DWORD,
            ctypes.POINTER(ctypes.c_void_p), ctypes.POINTER(wintypes.DWORD)
        ]
        wtsapi32.WTSQuerySessionInformationW.restype = wintypes.BOOL
        
        wtsapi32.WTSFreeMemory.argtypes = [ctypes.c_void_p]
        wtsapi32.WTSFreeMemory.restype = None

        start_time = time.time()
        timeout = 60.0 # Wait up to 60 seconds for the desktop
        
        # Check if we are running in a user session and desktop is available
        while time.time() - start_time < timeout:
            hwnd = user32.FindWindowW("Progman", None)
            if hwnd:
                tray = user32.FindWindowW("Shell_TrayWnd", None)
                if tray and user32.IsWindowVisible(tray):
                    buffer = ctypes.c_void_p()
                    bytes_returned = ctypes.c_uint32()
                    
                    is_locked = False
                    try:
                        success = wtsapi32.WTSQuerySessionInformationW(
                            WTS_CURRENT_SERVER_HANDLE,
                            WTS_CURRENT_SESSION,
                            WTSSessionInfoEx,
                            ctypes.byref(buffer),
                            ctypes.byref(bytes_returned)
                        )
                        if success and buffer.value:
                            is_locked_array = ctypes.cast(buffer, ctypes.POINTER(ctypes.c_uint32))
                            is_locked = is_locked_array[3] == 1 
                            wtsapi32.WTSFreeMemory(buffer)
                    except Exception:
                        pass
                    
                    if not is_locked:
                        desk = user32.OpenInputDesktop(0, False, 0x0100)
                        if desk:
                            length = ctypes.c_ulong(0)
                            user32.GetUserObjectInformationW(desk, 2, None, 0, ctypes.byref(length))
                            name = ctypes.create_unicode_buffer(length.value)
                            user32.GetUserObjectInformationW(desk, 2, name, length.value, ctypes.byref(length))
                            user32.CloseDesktop(desk)
                            if name.value == "Default":
                                # 1. Wait until Windows officially registers the Shell Desktop Window
                                if not user32.GetShellWindow():
                                    continue
                                
                                # 2. Wait until the Taskbar is fully created and visible (past lock screen)
                                tray_hwnd = user32.FindWindowW("Shell_TrayWnd", None)
                                if not tray_hwnd or not user32.IsWindowVisible(tray_hwnd):
                                    continue
                                    
                                # Give Windows shell a moment to stabilize
                                time.sleep(1.5)
                                return
            time.sleep(0.5)
            
    wait_for_desktop()

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
from config import ConfigManager, STORAGE_PATH, logger
from ui.folder_panel import FolderPanel
from utils import VectorIcon, IconExtractor, DesktopMonitor
from ui.grid_overlay import GridOverlay
from ui.halo import Halo

import sys
import os

import faulthandler
_appdata_dir = os.path.join(os.environ.get('APPDATA', ''), 'Pandora')
os.makedirs(_appdata_dir, exist_ok=True)
try:
    _fault_file = open(os.path.join(_appdata_dir, "pandora_fault.log"), "w")
    faulthandler.enable(file=_fault_file, all_threads=True)
except Exception:
    pass

import math
import ctypes
import subprocess
from ctypes import wintypes
from PyQt6.QtGui import QCursor, QKeyEvent
from PyQt6.QtCore import (Qt, QEvent, QPoint, QTimer, qInstallMessageHandler, QtMsgType, QParallelAnimationGroup, QEasingCurve, QPropertyAnimation, QVariantAnimation, QObject, pyqtSignal)

def qt_message_handler(mode, context, message):
    if "QFont::setPointSize" in message or "Point size <= 0" in message:
        return
    if "must be a top level window" in message:
        return
    # Ignore other harmless warnings if necessary, otherwise print
    print(message)

qInstallMessageHandler(qt_message_handler)

from PyQt6.QtCore import QAbstractNativeEventFilter

class WallpaperNativeEventFilter(QAbstractNativeEventFilter):
    def __init__(self, callback):
        super().__init__()
        self.callback = callback

    def nativeEventFilter(self, eventType, message):
        if eventType == b"windows_generic_MSG" or eventType == "windows_generic_MSG":
            msg = wintypes.MSG.from_address(int(message))
            # WM_SETTINGCHANGE = 0x001A (26)
            if msg.message == 0x001A:
                # 0x0014 is SPI_SETDESKWALLPAPER
                if msg.wParam == 0x0014 or msg.wParam == 0:
                    self.callback()
        return False, 0

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
            if msg.message == 0x0012: # WM_QUIT
                break
            ctypes.windll.user32.TranslateMessage(ctypes.byref(msg))
            ctypes.windll.user32.DispatchMessageW(ctypes.byref(msg))
            
        if self.hook_kb: ctypes.windll.user32.UnhookWindowsHookEx(self.hook_kb)
        if self.hook_ms: ctypes.windll.user32.UnhookWindowsHookEx(self.hook_ms)

    def stop(self):
        if hasattr(self, 'thread') and self.thread.is_alive():
            # Post WM_QUIT to the thread's message queue to break the GetMessageW loop
            import ctypes.wintypes
            ctypes.windll.user32.PostThreadMessageW(self.thread.ident, 0x0012, 0, 0)

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
    elif cmd == "brightness":
        try:
            from utils import get_system_brightness, change_system_brightness
            current = get_system_brightness() * 100.0
            
            if current < 25: target = 25
            elif current < 50: target = 50
            elif current < 75: target = 75
            elif current < 100: target = 100
            else: target = 0
            
            delta = (target - current) / 100.0
            change_system_brightness(delta)
        except Exception as e:
            print(f"Failed to set brightness: {e}")
    elif cmd in ["taskmgr", "tasks"]: subprocess.Popen("taskmgr")
    elif cmd in ["pandora", "settings"]: dash.show()
    elif cmd in ["trash", "empty trash"]: subprocess.Popen(["powershell.exe", "-Command", "Clear-RecycleBin -Force -ErrorAction SilentlyContinue"])
    elif cmd == "search": send_win_key(0x53) # Win + S
    elif cmd == "power": subprocess.Popen(["shutdown", "/s", "/t", "60", "/c", "Pandora: Shutting down in 60s. Use 'shutdown /a' to cancel."])
    elif cmd in ["calc", "calculator"]: subprocess.Popen("calc")
    elif cmd in ["cmd", "terminal"]: subprocess.Popen(["cmd", "/c", "start", "cmd"])
    elif cmd == "notepad": subprocess.Popen("notepad.exe")
    elif cmd in ["notes", "sticky notes"]: subprocess.Popen(["cmd", "/c", "start", r"shell:AppsFolder\Microsoft.Office.OneNote.MemoryPreview"])
    elif cmd == "mute": send_key(0xAD) # VK_VOLUME_MUTE
    elif cmd in ["prev", "prev media"]:
        from utils import MediaSessionManager
        MediaSessionManager.instance().prev_track()
    elif cmd in ["next", "next media"]:
        from utils import MediaSessionManager
        MediaSessionManager.instance().next_track()
    elif cmd in ["play/pause", "play"]:
        from utils import MediaSessionManager
        MediaSessionManager.instance().play_pause()
    elif cmd in ["mic", "microphone"]: 
        from utils import toggle_mic_mute
        toggle_mic_mute()
    elif cmd in ["task view", "taskview"]: send_win_key(0x09) # Win + Tab
    elif cmd == "clipboard": send_win_key(0x56) # Win + V
    elif cmd in ["emoji", "emoji picker"]: send_win_key(0xBE) # Win + .
    elif cmd in ["lock", "lock pc"]: ctypes.windll.user32.LockWorkStation()
    elif cmd == "sleep": ctypes.windll.PowrProf.SetSuspendState(0, 1, 0)
    elif cmd in ["wifi", "wi-fi"]:
        from utils import toggle_wifi
        toggle_wifi()
    elif cmd == "bluetooth":
        from utils import toggle_bluetooth
        toggle_bluetooth()
    elif cmd in ["winsettings", "windows settings", "ms-settings"]: subprocess.Popen(["cmd", "/c", "start", "ms-settings:"])
    elif cmd in ["defender", "windows defender"]: subprocess.Popen(["cmd", "/c", "start", "windowsdefender:"])
    else:
        if cmd:
            resolved_path = os.path.expandvars(cmd)
            if os.path.exists(resolved_path):
                try:
                    os.startfile(resolved_path)
                except Exception:
                    try:
                        subprocess.Popen(resolved_path)
                    except Exception:
                        pass

def warm_up():
    queue = []
    for f in cfg.get('folders', []):
        for app_data in f.get('apps', []):
            queue.append(app_data.get('path', ''))
            
    def process_next():
        if not queue: return
        path = queue.pop(0)
        IconExtractor.get_icon_pixmap(path, 48)
        QTimer.singleShot(10, process_next)
        
    process_next()

class ElectronDashboardManager(QObject):
    configUpdated = pyqtSignal(dict)
    
    def __init__(self, cfg, app_instances):
        super().__init__()
        self.cfg = cfg
        self.app_instances = app_instances
        self.grid_overlay = None
        self.electron_process = None
        self.ws_port = None
        
        # Initialize visualizer engine at startup to bind and discover the active GPU
        try:
            import hub_modules.vis_engine_bridge as vis
            pref_gpu = int(self.cfg.get('general_settings', {}).get('gpu_preference', 0))
            vis.init_vis_engine(512, 512, pref_gpu)
            self.cfg['system_gpu_name'] = vis.get_bound_gpu_name()
        except Exception as e:
            self.cfg['system_gpu_name'] = "Default Hardware GPU"

        # Inject app version into config for dashboard display
        from config import APP_VERSION
        self.cfg['app_version'] = APP_VERSION

        # Update state
        self._update_checker = None
        self._update_worker = None
        self._pending_download_url = None

        # Start WebSocket Server
        from core_services.ws_server import WebSocketServerThread
        self.ws_thread = WebSocketServerThread(self.cfg, port=0)
        self.ws_thread.config_received.connect(self.handle_config_update)
        self.ws_thread.port_bound.connect(self._handle_port_bound)
        self.ws_thread.create_folder_requested.connect(self._on_create_folder_requested)
        self.ws_thread.create_folder_action_received.connect(self._on_dashboard_create_folder)
        self.ws_thread.delete_folder_action_received.connect(self._on_dashboard_delete_folder)
        self.ws_thread.reset_config_requested.connect(self._on_reset_config)
        self.ws_thread.start()

        # Register native Windows event filter for automatic wallpaper change detection
        self._wp_filter = WallpaperNativeEventFilter(self.on_wallpaper_changed)
        app_inst = QApplication.instance()
        if app_inst:
            app_inst.installNativeEventFilter(self._wp_filter)

        # Watch root internal_storage directory for new/deleted folder directories
        from PyQt6.QtCore import QFileSystemWatcher
        self.storage_watcher = QFileSystemWatcher(self)
        self.storage_watcher.addPath(STORAGE_PATH)
        self.storage_watcher.directoryChanged.connect(self._on_storage_root_changed)
        self._storage_sync_timer = QTimer(self)
        self._storage_sync_timer.setSingleShot(True)
        self._storage_sync_timer.timeout.connect(self._sync_storage_root)
        self.pill_window = None

    def _on_storage_root_changed(self, path):
        """Debounce root storage directory changes (500ms)."""
        self._storage_sync_timer.start(500)

    def _sync_storage_root(self):
        """Compare physical directories in internal_storage against config folders."""
        if not os.path.exists(STORAGE_PATH):
            return

        config_ids = {f.get('id') for f in self.cfg.get('folders', []) if f.get('id')}
        physical_dirs = set()
        try:
            for name in os.listdir(STORAGE_PATH):
                full = os.path.join(STORAGE_PATH, name)
                if os.path.isdir(full):
                    physical_dirs.add(name)
        except OSError:
            return

        # 1. Detect NEW directories (on disk but not in config)
        new_dirs = physical_dirs - config_ids
        for dir_name in new_dirs:
            dir_path = os.path.join(STORAGE_PATH, dir_name)
            try:
                contents = os.listdir(dir_path)
            except OSError:
                continue
                
            # Filter out desktop.ini
            contents = [f for f in contents if f.lower() != 'desktop.ini']

            # Use the directory name directly as the folder ID to avoid renaming and confusing the user
            new_id = dir_name

            # Build apps list from directory contents
            apps = []
            for f in contents:
                p = os.path.join(dir_path, f)
                name = os.path.splitext(f)[0] if os.path.isfile(p) else f
                if not name: name = f
                apps.append({"name": name, "path": p})

            # Use the directory name as the display name (cleaned up)
            display_name = dir_name.replace('_', ' ').title() if not dir_name.startswith('folder_') else None
            if not display_name:
                greek_names = ["Alpha", "Beta", "Gamma", "Delta", "Epsilon", "Zeta", "Eta", "Theta", "Iota", "Kappa", "Lambda", "Mu", "Nu", "Xi", "Omicron", "Pi", "Rho", "Sigma", "Tau", "Upsilon", "Phi", "Chi", "Psi", "Omega"]
                existing_names = {f.get('name', '') for f in self.cfg.get('folders', [])}
                display_name = next((n for n in greek_names if n not in existing_names), "New Folder")

            new_f = {
                "id": new_id,
                "name": display_name,
                "pos": [200, 200],
                "apps": apps,
                "show_title": False,
                "grid_cols": 2,
                "grid_rows": 2,
                "grid_snap": True
            }
            self.cfg['folders'].append(new_f)

            # Create a FolderPanel for it
            if hasattr(self, 'create_folder_callback'):
                from ui.folder_panel import FolderPanel
                panel = FolderPanel(new_f, self.cfg, self)
                self.app_instances.append(panel)
                # Auto-snap to a free grid position using spiral search
                gs = self.cfg.get('general_settings', {}).get('grid_size', 120)
                pad = 8
                screen = QApplication.primaryScreen()
                scr_geom = screen.availableGeometry()
                scr_cx = scr_geom.center().x()
                scr_cy = scr_geom.center().y()
                target_cols = new_f['grid_cols']
                target_rows = new_f['grid_rows']
                
                # Build occupied grid positions from existing panels
                occupied = []
                for other in self.app_instances:
                    if other is panel:
                        continue
                    try:
                        ox = other.pos().x() - pad
                        oy = other.pos().y() - pad
                        c = round((ox - scr_cx) / gs)
                        r = round((oy - scr_cy) / gs)
                        occupied.append((c, r, other.grid_cols, other.grid_rows))
                    except RuntimeError:
                        pass
                
                def is_free(c, r):
                    px = c * gs + scr_cx + pad
                    py = r * gs + scr_cy + pad
                    tw = target_cols * gs - 16
                    th = target_rows * gs - 16
                    if px < scr_geom.left() + 40 or px + tw > scr_geom.right() - 40: return False
                    if py < scr_geom.top() + 40 or py + th > scr_geom.bottom() - 40: return False
                    for (oc, orow, ocols, orows) in occupied:
                        if not (c + target_cols <= oc or c >= oc + ocols or r + target_rows <= orow or r >= orow + orows):
                            return False
                    return True
                
                found = None
                for radius in range(0, 30):
                    for dc in range(-radius, radius + 1):
                        for dr in range(-radius, radius + 1):
                            if max(abs(dc), abs(dr)) == radius and is_free(dc, dr):
                                found = (dc, dr)
                                break
                        if found: break
                    if found: break
                
                if found:
                    col, row = found
                    px = int(col * gs + scr_cx + pad)
                    py = int(row * gs + scr_cy + pad)
                    new_f['pos'] = [px, py]
                    panel.move(px, py)
                panel.show()

            logger.info(f"Auto-registered new folder from storage: {new_id}")

        # 2. Detect DELETED directories (in config but not on disk, only internal-storage-based folders)
        for folder in list(self.cfg.get('folders', [])):
            fid = folder.get('id')
            if not fid:
                continue
            expected_dir = os.path.join(STORAGE_PATH, fid)
            if fid not in physical_dirs and not os.path.exists(expected_dir):
                # Only auto-remove if the folder has no external apps (non-internal-storage paths)
                has_external = any(
                    not app.get('path', '').startswith(expected_dir) and not app.get('path', '').startswith('pandora://')
                    for app in folder.get('apps', [])
                )
                if has_external:
                    continue

                # Remove the panel from the desktop
                target_panel = next((p for p in self.app_instances if p.data.get('id') == fid), None)
                if target_panel:
                    try:
                        target_panel.hide()
                        target_panel.close()
                        target_panel.deleteLater()
                        self.app_instances.remove(target_panel)
                    except (RuntimeError, ValueError):
                        pass

                # Remove from config
                self.cfg['folders'] = [f for f in self.cfg['folders'] if f.get('id') != fid]
                logger.info(f"Auto-removed deleted folder from config: {fid}")

        if new_dirs or any(not os.path.exists(os.path.join(STORAGE_PATH, f.get('id', ''))) for f in self.cfg.get('folders', [])):
            self.save_and_broadcast()

        # Re-register the watcher (Windows may drop the watch after a change)
        if STORAGE_PATH not in self.storage_watcher.directories():
            self.storage_watcher.addPath(STORAGE_PATH)

    def _on_create_folder_requested(self):
        if hasattr(self, 'create_folder_callback'):
            self.create_folder_callback("grid")
            
    def _on_dashboard_create_folder(self, folder_name):
        if hasattr(self, 'create_folder_callback'):
            self.create_folder_callback("dashboard", custom_name=folder_name)

    def _on_dashboard_delete_folder(self, folder_id, action):
        target_panel = next((p for p in self.app_instances if p.data.get('id') == folder_id), None)
        if target_panel:
            try:
                target_panel.execute_remove(spill_regular=(action == "spill"))
            except RuntimeError:
                pass
        else:
            # Handle deleting a nested folder (which has no active panel)
            target_f = next((f for f in self.cfg.get('folders', []) if f.get('id') == folder_id), None)
            if not target_f:
                return
                
            # Remove from parent folder's apps
            parent_f = next((f for f in self.cfg.get('folders', []) for app in f.get('apps', []) if app.get('path') == f"pandora://folder/{folder_id}"), None)
            if parent_f:
                parent_f['apps'] = [app for app in parent_f.get('apps', []) if app.get('path') != f"pandora://folder/{folder_id}"]
                
            # If spill, move files to desktop
            if action == "spill":
                regular_apps = [app for app in target_f.get('apps', []) if not app.get('path', '').startswith('pandora://folder/')]
                if regular_apps:
                    import os, shutil
                    from config import DESKTOP_PATH
                    for ad in regular_apps:
                        try:
                            bn = os.path.basename(ad['path'])
                            dest = os.path.join(DESKTOP_PATH, bn)
                            if os.path.exists(ad['path']):
                                dest_norm = os.path.normcase(os.path.abspath(dest))
                                src_norm = os.path.normcase(os.path.abspath(ad['path']))
                                if os.path.exists(dest) and dest_norm != src_norm:
                                    name_part, ext_part = os.path.splitext(bn)
                                    counter = 1
                                    while os.path.exists(os.path.join(DESKTOP_PATH, f"{name_part} ({counter}){ext_part}")):
                                        counter += 1
                                    dest = os.path.join(DESKTOP_PATH, f"{name_part} ({counter}){ext_part}")
                                if os.path.normcase(os.path.abspath(dest)) != src_norm:
                                    shutil.move(ad['path'], dest)
                        except Exception as ex:
                            import logging
                            logging.getLogger(__name__).error(f"Error moving file to desktop: {ex}")
                            
            # Remove storage directory
            from config import STORAGE_PATH
            import os, shutil
            target_storage = os.path.join(STORAGE_PATH, folder_id)
            if os.path.exists(target_storage):
                try:
                    if action != "spill":
                        import send2trash
                        send2trash.send2trash(target_storage)
                    else:
                        shutil.rmtree(target_storage)
                except Exception:
                    try: shutil.rmtree(target_storage)
                    except: pass
                    
            # Remove from config and broadcast
            self.cfg['folders'] = [f for f in self.cfg['folders'] if f.get('id') != folder_id]
            self.save_and_broadcast()
            
            # Refresh parent panel if active
            if parent_f:
                parent_panel = next((p for p in self.app_instances if p.data.get('id') == parent_f.get('id')), None)
                if parent_panel:
                    try:
                        parent_panel.refresh()
                    except RuntimeError:
                        pass

    def _handle_port_bound(self, port):
        self.ws_port = port
        port_file = os.path.join(os.environ['APPDATA'], 'Pandora', 'ws_port.txt')
        try:
            with open(port_file, 'w') as f:
                f.write(str(port))
        except Exception as e:
            print(f"Failed to write ws_port.txt: {e}")

    def on_wallpaper_changed(self):
        gen = self.cfg.setdefault('general_settings', {})
        if gen.get('dashboard_theme') == 'Desktop' or gen.get('folder_theme') == 'Desktop':
            from PyQt6.QtCore import QTimer
            # Delay by 1.5 seconds to give Windows time to flush the new wallpaper to disk
            QTimer.singleShot(1500, self._process_wallpaper_change)

    def _process_wallpaper_change(self):
        gen = self.cfg.setdefault('general_settings', {})
        from utils import get_desktop_accent_colors, _wallpaper_cache, animate_theme_change
        _wallpaper_cache.clear()
        accents = get_desktop_accent_colors()
        gen['desktop_accents'] = [list(c) for c in accents]
        self.ws_thread.send_config_to_clients(self.cfg)
        
        # Force a full repaint on folders and their internal icons
        for w in self.app_instances:
            try:
                animate_theme_change(w)
                w.update()
                if hasattr(w, 'findChildren'):
                    from PyQt6.QtWidgets import QWidget
                    for child in w.findChildren(QWidget):
                        child.update()
            except Exception:
                pass
                
        # Also update the pill window
        if hasattr(self, 'pill_window') and self.pill_window:
            try:
                self.pill_window.cfg = self.cfg
                self.pill_window.update_theme()
                self.pill_window.update()
            except Exception as e:
                print(f"Error updating pill window on wallpaper change: {e}")

    def _on_reset_config(self, section):
        from config import ConfigManager
        defaults = ConfigManager.get_defaults()
        
        # Hardcoded mappings of UI sections to config keys
        mapping = {
            "Appearance": [
                "general_settings.grid_size", "general_settings.edge_padding", 
                "general_settings.edge_padding_t", "general_settings.edge_padding_b",
                "general_settings.edge_padding_l", "general_settings.edge_padding_r",
                "general_settings.edge_padding_v", "general_settings.edge_padding_h",
                "general_settings.theme_intensity", "general_settings.folder_theme",
                "general_settings.folder_custom_color", "general_settings.dashboard_theme",
                "general_settings.pagination_style", "general_settings.color"
            ],
            "Grid Behavior": [
                "general_settings.show_grid_on_drag", "general_settings.grid_animated_color",
                "general_settings.grid_wave_entrance", "general_settings.grid_wave_fade",
                "general_settings.grid_opacity"
            ],
            "System": [
                "general_settings.launch_at_startup", "general_settings.open_dashboard_startup", "general_settings.gpu_preference"
            ],
            "Display Effects": [
                "general_settings.warmth_intensity", "display_effects.active_preset"
            ],
            "Media Widget Settings": [
                "general_settings.art_style", "general_settings.visualizer",
                "general_settings.mosaic_shape", "general_settings.show_timeline",
                "general_settings.show_title", "general_settings.show_controls"
            ],
            "Time Widget Settings": [
                "general_settings.clock_mode", "general_settings.format_24h",
                "general_settings.show_date", "general_settings.show_seconds"
            ],
            "Activation & Behavior": [
                "halo.activation_key", "halo.activation_modifiers", "halo.theme",
                "halo.brightness", "halo.blur_level", "halo.gap_size", 
                "halo.show_arc_hud", "halo.blend_icons"
            ],
            "Dimensions & Feel": [
                "halo.max_bound", "halo.hub_ratio", "halo.opacity",
                "halo.mouse_sens", "halo.scroll_sens"
            ]
        }
        
        import copy
        if section == "all":
            for k in ["general_settings", "halo", "hub_config"]:
                if k in defaults:
                    self.cfg[k] = copy.deepcopy(defaults[k])
        elif section in mapping:
            for key_path in mapping[section]:
                parts = key_path.split('.')
                parent_cfg = self.cfg
                parent_def = defaults
                for part in parts[:-1]:
                    parent_cfg = parent_cfg.setdefault(part, {})
                    parent_def = parent_def.get(part, {})
                last = parts[-1]
                if last in parent_def:
                    parent_cfg[last] = copy.deepcopy(parent_def[last])
        else:
            return
            
        self.handle_config_update(self.cfg)

    def handle_config_update(self, new_cfg):
        try:
            # Update our running config dictionary
            self.cfg.clear()
            self.cfg.update(new_cfg)
            
            # Re-initialize visualizer engine if GPU preference changed
            try:
                import hub_modules.vis_engine_bridge as vis
                pref_gpu = int(self.cfg.get('general_settings', {}).get('gpu_preference', 0))
                vis.init_vis_engine(512, 512, pref_gpu)
                self.cfg['system_gpu_name'] = vis.get_bound_gpu_name()
            except Exception as e:
                self.cfg['system_gpu_name'] = "Default Hardware GPU"
            
            # Update Windows Startup Registry
            launch_at_startup = self.cfg.get('general_settings', {}).get('launch_at_startup', False)
            try:
                from config import set_startup_registry
                set_startup_registry(launch_at_startup)
            except Exception as e:
                print(f"Error updating registry for startup: {e}")
            
            # Inject desktop wallpaper accent colors if Dashboard or Folder theme is Desktop
            gen = self.cfg.setdefault('general_settings', {})
            if gen.get('dashboard_theme') == 'Desktop' or gen.get('folder_theme') == 'Desktop':
                try:
                    from utils import get_desktop_accent_colors
                    accents = get_desktop_accent_colors()
                    gen['desktop_accents'] = [list(c) for c in accents]
                except Exception as e:
                    print(f"Error getting desktop accents: {e}")
                
            # Push updated config back to the Electron dashboard clients to keep them in sync
            self.ws_thread.send_config_to_clients(self.cfg)
            
            # Save to disk
            ConfigManager.save(self.cfg)
            
            # Apply GPU Preference registry settings immediately
            try:
                force_high_performance_gpu()
            except Exception as e:
                print(f"Error applying GPU preference: {e}")
            
            app = QApplication.instance()
            # 1. Update Display Engine
            try:
                disp_cfg = self.cfg.get('display_effects', {})
                from utils import DisplayEffectsEngine
                engine = DisplayEffectsEngine.instance()
                engine._active_preset = disp_cfg.get('active_preset', 'Sunset')
                engine._target_intensity = disp_cfg.get('warmth_intensity', 60) / 100.0
                if engine._is_enabled:
                    engine.set_intensity(engine._target_intensity)
            except Exception as e:
                print(f"Error updating Display Engine: {e}")
                
            # 2. Update Halo Menu Settings
            try:
                if hasattr(app, 'halo'):
                    app.halo.reload_tools(self.cfg)
            except Exception as e:
                print(f"Error updating Halo Menu Settings: {e}")
                
            # 3. Update Global Hook Settings
            try:
                if hasattr(app, 'global_hook'):
                    app.global_hook.reload_config(self.cfg)
            except Exception as e:
                print(f"Error updating Global Hook Settings: {e}")
                
            # Emit signal in case any other modular UI components need to react
            self.configUpdated.emit(self.cfg)
            
            from utils import animate_theme_change
            
            # 4. Refresh Pill Window Theme
            if hasattr(self, 'pill_window') and self.pill_window:
                try:
                    self.pill_window.cfg = self.cfg
                    self.pill_window.update_theme()
                    self.pill_window.update()
                except Exception as e:
                    print(f"Error updating pill window theme: {e}")
                    
            # 5. Refresh all folder icon visuals on the desktop
            for w in self.app_instances[:]:
                try:
                    animate_theme_change(w)
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
                        print(f"RuntimeError updating folder: {e}")
                except Exception as e:
                    print(f"Error updating folder {getattr(w, 'data', {}).get('id', 'unknown')}: {e}")
                    import traceback
                    traceback.print_exc()
        except Exception as e:
            print(f"FATAL ERROR in handle_config_update: {e}")
            import traceback
            traceback.print_exc()
                    
    def save_and_broadcast(self, new_cfg=None):
        if new_cfg is not None:
            self.cfg.clear()
            self.cfg.update(new_cfg)
        ConfigManager.save(self.cfg)
        self.ws_thread.send_config_to_clients(self.cfg)

    def prewarm(self):
        pass
        
    def show(self):
        try:
            # Spawn Electron
            if self.electron_process is None or self.electron_process.poll() is not None:
                env = os.environ.copy()
                if self.ws_port is not None:
                    env['PANDORA_WS_PORT'] = str(self.ws_port)
                    
                if getattr(sys, 'frozen', False):
                    # PyInstaller bundled mode
                    base_dir = os.path.dirname(sys.executable)
                    electron_path = os.path.join(base_dir, 'electron_dashboard', 'PandoraUI-win32-x64', 'PandoraUI.exe')
                    if not os.path.exists(electron_path):
                        print(f"Packaged Electron not found at {electron_path}!")
                        return
                    # Do not pass "." when running pre-packaged app
                    self.electron_process = subprocess.Popen([electron_path], cwd=os.path.dirname(electron_path), env=env)
                else:
                    electron_path = os.path.abspath(r"electron_dashboard\node_modules\.bin\electron.cmd")
                    if not os.path.exists(electron_path):
                        print("Electron not found! Run npm install in electron_dashboard")
                        return
                    
                    # Copy assets to electron_dashboard/assets for dev mode
                    src_assets = os.path.abspath("assets")
                    dest_assets = os.path.abspath(r"electron_dashboard\assets")
                    if os.path.exists(src_assets):
                        import shutil
                        if os.path.exists(dest_assets):
                            try:
                                shutil.rmtree(dest_assets)
                            except Exception:
                                pass
                        try:
                            shutil.copytree(src_assets, dest_assets, dirs_exist_ok=True)
                        except Exception as e:
                            print(f"Failed to copy assets in dev mode: {e}")
                            
                    self.electron_process = subprocess.Popen([electron_path, "."], cwd="electron_dashboard", env=env)
        except Exception as e:
            print(f"FATAL ERROR in dashboard.show(): {e}")
            import traceback
            traceback.print_exc()
            
    def hide(self):
        if self.electron_process and self.electron_process.poll() is None:
            try:
                import subprocess
                subprocess.run(['taskkill', '/F', '/T', '/PID', str(self.electron_process.pid)], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, creationflags=0x08000000)
            except Exception:
                try:
                    self.electron_process.terminate()
                except Exception:
                    pass
            self.electron_process = None

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
    import sys
    import os
    

    _app_mutex_handle = None
    if sys.platform == 'win32':
        import ctypes
        # Enforce single instance using a Windows Named Mutex
        mutex_name = "Global\\PandoraAppSingleInstanceMutex"
        _app_mutex_handle = ctypes.windll.kernel32.CreateMutexW(None, False, mutex_name)
        if ctypes.windll.kernel32.GetLastError() == 183: # ERROR_ALREADY_EXISTS
            print("Pandora is already running. Exiting.")
            sys.exit(0)
            
        myappid = 'seb.pandora.v1' 
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(myappid)

    app = QApplication(sys.argv)
    app.setStyleSheet(SCROLLBAR_CSS)
    
    # Store mutex handle on app so restart_app() can release it
    app._mutex_handle = _app_mutex_handle
    
    app.setQuitOnLastWindowClosed(False)
    
    from PyQt6.QtGui import QIcon
    from utils import get_resource_path
    app_icon = QIcon(get_resource_path("assets/Pandora.svg"))
    app.setWindowIcon(app_icon)
    
    cfg = ConfigManager.load()
    
    # Initialize / Refresh desktop accents on startup
    gen = cfg.setdefault('general_settings', {})
    if gen.get('dashboard_theme') == 'Desktop' or gen.get('folder_theme') == 'Desktop':
        def _load_accents():
            try:
                from utils import get_desktop_accent_colors
                accents = get_desktop_accent_colors()
                gen['desktop_accents'] = [list(c) for c in accents]
            except Exception as e:
                print(f"Error getting desktop accents on startup: {e}")
        
        import threading
        threading.Thread(target=_load_accents, daemon=True).start()
    
    # Initialize Core Services lazily
    def _init_media_daemon():
        from core_services.media_daemon import MediaDaemon
        app.media_daemon = MediaDaemon()
        import utils
        if utils.MediaSessionManager._instance is not None:
            utils.MediaSessionManager._instance._connect_to_daemon()
        
    app.media_daemon = None
    QTimer.singleShot(100, _init_media_daemon)
    
    QTimer.singleShot(500, warm_up)
    
    dashboard = ElectronDashboardManager(cfg, [])
    dashboard.prewarm()
    if cfg.get('general_settings', {}).get('open_dashboard_startup', False):
        QTimer.singleShot(2000, lambda: dashboard.show())
    
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
    QTimer.singleShot(1000, hook.start)
    
    wins = []
    dashboard.app_instances = wins
    
    def build_folders(folder_list, idx=0):
        if idx >= len(folder_list):
            return
        try:
            f = folder_list[idx]
            if not f.get('is_nested', False):
                w = FolderPanel(f, cfg, dashboard)
                wins.append(w)
                w.show()
        except Exception as e:
            print(f"Error creating folder {idx}: {e}")
            import traceback
            traceback.print_exc()
        finally:
            QTimer.singleShot(20, lambda: build_folders(folder_list, idx + 1))
        
    from PyQt6.QtCore import QTimer, QThread
        
    build_folders(cfg['folders'])
    
    # Robust zero-CPU registry watcher instead of polling
    class RegistryWatcherThread(QThread):
        def run(self):
            import win32api
            import win32con
            import win32event
            import winreg
            try:
                key_path = r"Software\Microsoft\Windows\CurrentVersion\Explorer\StartupApproved\Run"
                key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, key_path, 0, winreg.KEY_READ | win32con.KEY_NOTIFY)
                evt = win32event.CreateEvent(None, 0, 0, None)
                
                while not self.isInterruptionRequested():
                    # 1 = REG_NOTIFY_CHANGE_NAME, 4 = REG_NOTIFY_CHANGE_LAST_SET
                    win32api.RegNotifyChangeKeyValue(key, True, 1 | 4, evt, True)
                    res = win32event.WaitForSingleObject(evt, 1000)
                    if res == win32con.WAIT_OBJECT_0:
                        enabled = True
                        try:
                            val, _ = winreg.QueryValueEx(key, "Pandora")
                            if val and len(val) > 0 and val[0] == 0x03:
                                enabled = False
                        except Exception:
                            pass
                        
                        current = cfg.get('general_settings', {}).get('launch_at_startup', False)
                        if current != enabled:
                            cfg.setdefault('general_settings', {})['launch_at_startup'] = enabled
                            from config import ConfigManager
                            ConfigManager.save(cfg)
                            dashboard.ws_thread.send_config_to_clients(cfg)
            except Exception:
                pass

    reg_watcher = RegistryWatcherThread(app)
    reg_watcher.start()
    
    tray = QSystemTrayIcon(app_icon)
    tray.show()
    
    from PyQt6.QtWidgets import QWidget, QHBoxLayout, QPushButton, QVBoxLayout
    from PyQt6.QtCore import Qt, QSize
    from PyQt6.QtGui import QIcon, QCursor
    import os
    
    class CustomTrayMenu(QWidget):
        def __init__(self, app, create_folder, restart_app, quit_app, dashboard):
            super().__init__()
            self.setWindowFlags(Qt.WindowType.Popup | Qt.WindowType.FramelessWindowHint | Qt.WindowType.NoDropShadowWindowHint)
            self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
            
            self.app = app
            self.create_folder = create_folder
            self.restart_app = restart_app
            self.quit_app = quit_app
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
            make_btn('power.svg', "Quit", self.quit_app)

            
            layout.addWidget(self.bg)
            
        def on_click(self, callback):
            self.hide()
            callback()

    def create_folder(t_type, custom_name=None):
        from ui.folder_panel import FolderPanel
        from PyQt6.QtGui import QCursor
        from PyQt6.QtWidgets import QApplication
        existing_ids = [int(f['id'].split('_')[1]) for f in cfg['folders'] if f['id'].startswith('folder_') and f['id'].split('_')[1].isdigit()]
        new_id_num = (max(existing_ids) + 1) if existing_ids else (len(cfg['folders']) + 1)
        new_id = f"folder_{new_id_num}"
        
        gs = cfg.get('general_settings', {}).get('grid_size', 110)
        pad = 8  # Hardcoded in FolderPanel
        margin_y_top = 0  # 0 because show_title is False for new folders
        
        from PyQt6.QtGui import QCursor
        from PyQt6.QtWidgets import QApplication
        screen = QApplication.screenAt(QCursor.pos())
        if not screen:
            screen = QApplication.primaryScreen()
        scr_geom = screen.availableGeometry()
        scr_cx = scr_geom.center().x()
        scr_cy = scr_geom.center().y()
        
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
            
            gen = cfg.get('general_settings', {})
            pad_t = gen.get('edge_padding_t', gen.get('edge_padding', 0))
            pad_b = gen.get('edge_padding_b', gen.get('edge_padding', 0))
            pad_l = gen.get('edge_padding_l', gen.get('edge_padding', 0))
            pad_r = gen.get('edge_padding_r', gen.get('edge_padding', 0))
            m_t = int(40 + pad_t)
            m_b = int(40 + pad_b)
            m_l = int(40 + pad_l)
            m_r = int(40 + pad_r)

            if px < scr_geom.left() + m_l or px + target_w > scr_geom.right() - m_r: return False
            if py < scr_geom.top() + m_t or py + target_h > scr_geom.bottom() - m_b: return False
            
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
            if t_type == "dashboard":
                px = int(scr_cx - 50)
                py = int(scr_cy - 50)
                from ui.ui_common import ToastNotification
                toast = ToastNotification("No space left on grid. Snap-to-grid disabled.")
                toast.show()
            else:
                pos = QCursor.pos()
                px = pos.x() - 50
                py = pos.y() - 50
            
        greek_names = ["Alpha", "Beta", "Gamma", "Delta", "Epsilon", "Zeta", "Eta", "Theta", "Iota", "Kappa", "Lambda", "Mu", "Nu", "Xi", "Omicron", "Pi", "Rho", "Sigma", "Tau", "Upsilon", "Phi", "Chi", "Psi", "Omega"]
        existing_names = {f.get('name', '') for f in cfg.get('folders', [])}
        folder_name = custom_name if custom_name else next((n for n in greek_names if n not in existing_names), "New Folder")
            
        new_f = {
            "id": new_id, 
            "name": folder_name, 
            "pos": [int(px), int(py)], 
            "apps": [],
            "show_title": False,
            "grid_cols": final_cols,
            "grid_rows": final_rows,
            "grid_snap": snap
        }
        cfg['folders'].append(new_f)
        dashboard.save_and_broadcast()
        w = FolderPanel(new_f, cfg, dashboard)
        dashboard.app_instances.append(w)
        w.show()
        
        # Removed extra resize poke here, handled natively in showEvent
        
    dashboard.create_folder_callback = create_folder
    
    def quit_app():
        try:
            tray.hide()
        except Exception:
            pass
        cleanup_app()
        # Process pending events to flush deleteLater calls
        app.processEvents()
        QApplication.quit()

    def restart_app():
        import subprocess
        try:
            tray.hide()
        except Exception:
            pass
        cleanup_app()
        # Process pending events to flush deleteLater calls
        app.processEvents()
        
        # Release the single-instance mutex BEFORE spawning the new process
        # so the new instance doesn't see ERROR_ALREADY_EXISTS
        try:
            import ctypes
            if hasattr(app, '_mutex_handle') and app._mutex_handle:
                ctypes.windll.kernel32.ReleaseMutex(app._mutex_handle)
                ctypes.windll.kernel32.CloseHandle(app._mutex_handle)
                app._mutex_handle = None
        except Exception:
            pass
            
        # Handle restart correctly whether running from python script or compiled binary
        script_path = getattr(dashboard, '_update_script_path', None)
        if script_path and os.path.exists(script_path):
            subprocess.Popen([script_path], shell=True, creationflags=0x08000000)
        elif getattr(sys, 'frozen', False):
            subprocess.Popen(sys.argv, creationflags=0x08000000)
        else:
            subprocess.Popen([sys.executable] + sys.argv, creationflags=0x08000000)
        
        # Small delay to allow new process to start before we exit
        import time
        time.sleep(0.3)
        QApplication.quit()

    app.create_folder_callback = create_folder
    custom_tray_menu = CustomTrayMenu(app, create_folder, restart_app, quit_app, dashboard)
    
    def enter_pill_mode():
        dashboard.hide()
        from config import ConfigManager
        active_cfg = ConfigManager.load()
        if not hasattr(dashboard, 'pill_window') or dashboard.pill_window is None:
            from ui.pill_window import DashboardPillWindow
            dashboard.pill_window = DashboardPillWindow(active_cfg, dashboard, grid_overlay, restart_app, quit_app)
        else:
            dashboard.pill_window.cfg = active_cfg
        
        screen = QApplication.primaryScreen()
        if screen:
            geom = screen.availableGeometry()
            # Read saved position from config
            gen_settings = active_cfg.get('general_settings', {})
            edge = gen_settings.get('pill_edge', 'right')
            rx = gen_settings.get('pill_center_x_ratio')
            ry = gen_settings.get('pill_center_y_ratio')
            
            # Restore saved orientation and rotation
            dashboard.pill_window.edge = edge
            dashboard.pill_window.orientation = 'horizontal' if edge in ['top', 'bottom'] else 'vertical'
            dashboard.pill_window._rotation = -90.0 if edge in ['top', 'bottom'] else 0.0
            
            cx, cy = 320, 320
            if rx is not None and ry is not None:
                ccx = geom.x() + int(rx * geom.width())
                ccy = geom.y() + int(ry * geom.height())
                tx = ccx - cx
                ty = ccy - cy
            else:
                # Default position: right edge, centered vertically
                tx = geom.x() + geom.width() - 29 - cx
                ty = geom.y() + (geom.height() - 640) // 2
                
            dashboard.pill_window.setGeometry(tx, ty, 640, 640)
            dashboard.pill_window.move_to_edge(edge, geom)
            dashboard.pill_window.update_mask_and_geom()
            dashboard.pill_window.update_theme()
            dashboard.pill_window.expansion = 0.0
            
        dashboard.pill_window.show()
        dashboard.pill_window.raise_()
        dashboard.pill_window.activateWindow()

    dashboard.ws_thread.restart_app_requested.connect(restart_app)
    dashboard.ws_thread.quit_app_requested.connect(quit_app)
    dashboard.ws_thread.toggle_grid_requested.connect(grid_overlay.toggle)
    dashboard.ws_thread.enter_pill_mode_requested.connect(enter_pill_mode)

    # ── Auto-Update Handlers ──
    def on_check_updates():
        from core_services.update_checker import UpdateChecker
        from config import APP_VERSION
        dashboard._update_checker = UpdateChecker(APP_VERSION)
        dashboard._update_checker.result.connect(on_update_check_result)
        dashboard._update_checker.start()

    def on_update_check_result(result):
        if result.get('available') and result.get('download_url'):
            dashboard._pending_download_url = result['download_url']
        dashboard.ws_thread.send_command_to_clients({
            'type': 'update_check_result',
            'data': result
        })

    def on_apply_update():
        url = getattr(dashboard, '_pending_download_url', None)
        if not url:
            dashboard.ws_thread.send_command_to_clients({
                'type': 'update_complete',
                'data': {'success': False, 'message': 'No update URL available. Check for updates first.'}
            })
            return
        from core_services.update_checker import UpdateWorker
        dashboard._update_worker = UpdateWorker(url)
        dashboard._update_worker.progress.connect(on_update_progress)
        dashboard._update_worker.finished.connect(on_update_finished)
        dashboard._update_worker.start()

    def on_update_progress(percent, status):
        dashboard.ws_thread.send_command_to_clients({
            'type': 'update_progress',
            'data': {'percent': percent, 'status': status}
        })

    def on_update_finished(success, message):
        if success:
            dashboard._update_script_path = message
            dashboard.ws_thread.send_command_to_clients({
                'type': 'update_complete',
                'data': {'success': success, 'message': "Update ready! Restart to apply."}
            })
        else:
            dashboard.ws_thread.send_command_to_clients({
                'type': 'update_complete',
                'data': {'success': success, 'message': message}
            })

    dashboard.ws_thread.check_updates_requested.connect(on_check_updates)
    dashboard.ws_thread.apply_update_requested.connect(on_apply_update)
    
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
        if getattr(cleanup_app, '_done', False): return
        cleanup_app._done = True

        # 1. Stop hub module timers (e.g. clock's 60fps smooth timer)
        try:
            if hasattr(app, 'halo') and hasattr(app.halo, 'hub_manager'):
                mgr = app.halo.hub_manager
                for mod in getattr(mgr, '_modules', {}).values():
                    for attr_name in dir(mod):
                        attr = getattr(mod, attr_name, None)
                        if hasattr(attr, 'stop') and hasattr(attr, 'isActive'):
                            try:
                                attr.stop()
                            except Exception:
                                pass
        except Exception:
            pass

        # 2. Close all folder panels
        if hasattr(dashboard, 'app_instances') and dashboard.app_instances:
            for panel in list(dashboard.app_instances):
                try:
                    panel._is_closing = True
                    from utils import WinAPI as _WinAPI
                    _WinAPI.unpin_from_workerw(panel.winId())
                    panel.close()
                    panel.deleteLater()
                except Exception:
                    pass
            dashboard.app_instances.clear()

        # 3. Close Halo and Grid overlay
        try:
            if hasattr(app, 'halo') and app.halo is not None:
                app.halo.close()
                app.halo.deleteLater()
            if hasattr(app, 'grid_overlay') and app.grid_overlay is not None:
                app.grid_overlay.close()
                app.grid_overlay.deleteLater()
        except Exception:
            pass

        # 4. Restore display effects (gamma ramps etc)
        restore_display_effects()
        
        # 5. Stop global keyboard/mouse hook and wait for thread to finish
        if hasattr(app, 'global_hook') and app.global_hook:
            try:
                app.global_hook.stop()
                if hasattr(app.global_hook, 'thread') and app.global_hook.thread.is_alive():
                    app.global_hook.thread.join(timeout=2.0)
            except Exception:
                pass
            
        # 6. Stop media daemon and wait for its threads to finish
        if hasattr(app, 'media_daemon') and app.media_daemon:
            try:
                app.media_daemon.stop()
                if hasattr(app.media_daemon, '_thread') and app.media_daemon._thread is not None:
                    app.media_daemon._thread.join(timeout=2.0)
                if hasattr(app.media_daemon, '_peak_thread') and app.media_daemon._peak_thread is not None:
                    app.media_daemon._peak_thread.join(timeout=1.0)
            except Exception:
                pass
            
        # 7. Stop WebSocket server thread
        if hasattr(dashboard, 'ws_thread') and dashboard.ws_thread:
            try:
                dashboard.ws_thread.stop()
                dashboard.ws_thread.wait(2000)
            except Exception:
                pass
            
        # 8. Remove ws_port.txt so stale ports don't confuse future launches
        try:
            port_file = os.path.join(os.environ.get('APPDATA', ''), 'Pandora', 'ws_port.txt')
            if os.path.exists(port_file):
                os.remove(port_file)
        except Exception:
            pass

        # 9. Terminate the Electron dashboard process tree
        if hasattr(dashboard, 'electron_process') and dashboard.electron_process:
            try:
                # Use taskkill /T first to ensure the entire tree (cmd.exe -> electron.exe) is killed. 
                # If we use .terminate() on the parent, it dies and orphans the children.
                import subprocess
                subprocess.run(['taskkill', '/F', '/T', '/PID', str(dashboard.electron_process.pid)], 
                               capture_output=True, timeout=5, creationflags=0x08000000)
                dashboard.electron_process.terminate()
                dashboard.electron_process.wait(timeout=3)
            except Exception:
                pass
            dashboard.electron_process = None

        # 10. Release the single-instance mutex on final exit
        try:
            import ctypes
            if hasattr(app, '_mutex_handle') and app._mutex_handle:
                ctypes.windll.kernel32.ReleaseMutex(app._mutex_handle)
                ctypes.windll.kernel32.CloseHandle(app._mutex_handle)
                app._mutex_handle = None
        except Exception:
            pass

    atexit.register(cleanup_app)
    app.aboutToQuit.connect(cleanup_app)
    
    # Handle Ctrl+C (SIGINT) gracefully so that cleanup routines (like killing Electron) are called
    import signal
    def handle_sigint(signum, frame):
        print("Interrupt received, quitting...")
        app.quit()
    
    signal.signal(signal.SIGINT, handle_sigint)
    signal.signal(signal.SIGTERM, handle_sigint)

    # QTimer allows Python interpreter to run occasionally and process the signal
    from PyQt6.QtCore import QTimer
    sig_timer = QTimer()
    sig_timer.timeout.connect(lambda: None)
    sig_timer.start(200)
    
    exit_code = app.exec()
    import sys
    sys.exit(exit_code)