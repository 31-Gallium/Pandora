import os
import ctypes
from ctypes import wintypes
from PyQt6.QtCore import Qt, QFileInfo, QSize, QRect, QRectF, QObject, pyqtSignal, QVariantAnimation, QEasingCurve
from PyQt6.QtGui import QPixmap, QColor, QPainter, QPen, QIcon, QImage
from PyQt6.QtWidgets import QFileIconProvider, QApplication
from config import logger

# ==========================================
# 1. WINDOWS API MANAGER
# ==========================================
class WinAPI:
    @staticmethod
    def allow_drag_drop(hwnd):
        try:
            WM_DROPFILES, WM_COPYDATA, WM_COPYGLOBALDATA = 0x0233, 0x004A, 0x0049
            MSGFLT_ALLOW = 1
            ctypes.windll.user32.ChangeWindowMessageFilterEx(int(hwnd), WM_DROPFILES, MSGFLT_ALLOW, None)
            ctypes.windll.user32.ChangeWindowMessageFilterEx(int(hwnd), WM_COPYDATA, MSGFLT_ALLOW, None)
            ctypes.windll.user32.ChangeWindowMessageFilterEx(int(hwnd), WM_COPYGLOBALDATA, MSGFLT_ALLOW, None)
        except: pass
        
    @staticmethod
    def set_modern_visuals(hwnd, blur=True):
        if not blur: return
        try:
            dwmapi = ctypes.windll.dwmapi
            hwnd_int = int(hwnd)
            # We handle rounding via setMask — tell DWM not to round
            corner = ctypes.c_int(1)  # DWMWCP_DONOTROUND
            dwmapi.DwmSetWindowAttribute(hwnd_int, 33, ctypes.byref(corner), 4)
            # Remove the 1px accent border
            border_color = ctypes.c_int(0xFFFFFFFE)
            dwmapi.DwmSetWindowAttribute(hwnd_int, 34, ctypes.byref(border_color), 4)
        except Exception as e: logger.error(f"WinAPI Visuals error: {e}")

    @staticmethod
    def register_appbar(hwnd):
        try:
            from ctypes import wintypes
            class APPBARDATA(ctypes.Structure):
                _fields_ = [("cbSize", wintypes.DWORD),
                            ("hWnd", wintypes.HWND),
                            ("uCallbackMessage", wintypes.UINT),
                            ("uEdge", wintypes.UINT),
                            ("rc", wintypes.RECT),
                            ("lParam", wintypes.LPARAM)]
            abd = APPBARDATA()
            abd.cbSize = ctypes.sizeof(APPBARDATA)
            abd.hWnd = int(hwnd)
            abd.uCallbackMessage = 0x0400 + 100  # WM_USER + 100
            ctypes.windll.shell32.SHAppBarMessage(0, ctypes.byref(abd)) # ABM_NEW = 0
        except Exception as e:
            logger.error(f"WinAPI register_appbar error: {e}")

    @staticmethod
    def unregister_appbar(hwnd):
        try:
            from ctypes import wintypes
            class APPBARDATA(ctypes.Structure):
                _fields_ = [("cbSize", wintypes.DWORD),
                            ("hWnd", wintypes.HWND),
                            ("uCallbackMessage", wintypes.UINT),
                            ("uEdge", wintypes.UINT),
                            ("rc", wintypes.RECT),
                            ("lParam", wintypes.LPARAM)]
            abd = APPBARDATA()
            abd.cbSize = ctypes.sizeof(APPBARDATA)
            abd.hWnd = int(hwnd)
            ctypes.windll.shell32.SHAppBarMessage(1, ctypes.byref(abd)) # ABM_REMOVE = 1
        except Exception as e:
            logger.error(f"WinAPI unregister_appbar error: {e}")

    @staticmethod
    def pin_to_workerw(hwnd):
        try:
            import ctypes
            import platform
            user32 = ctypes.windll.user32
            progman = user32.FindWindowW("Progman", None)
            
            # Send message to spawn WorkerW
            user32.SendMessageTimeoutW(progman, 0x052C, 0, 0, 0, 1000, None)
            
            workerw = [0]
            def enum_windows_callback(tophandle, topparamhandle):
                # Find the WorkerW containing SHELLDLL_DefView
                p = user32.FindWindowExW(tophandle, 0, "SHELLDLL_DefView", None)
                if p != 0:
                    workerw[0] = tophandle
                return True
                
            WNDENUMPROC = ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.c_int, ctypes.c_int)
            user32.EnumWindows(WNDENUMPROC(enum_windows_callback), 0)
            
            target = workerw[0] if workerw[0] else progman
            if target:
                hwnd_int = int(hwnd)
                # Instead of SetParent (which breaks DWM translucency), set the OWNER.
                # An owned window is forced to stay above its owner in the Z-order.
                if platform.architecture()[0] == '64bit':
                    user32.SetWindowLongPtrW(hwnd_int, -8, target)
                else:
                    user32.SetWindowLongW(hwnd_int, -8, target)
        except Exception as e:
            logger.error(f"WinAPI pin_to_workerw error: {e}")

class DesktopMonitor:
    @staticmethod
    def unregister(widget): pass

# ==========================================
# 3. ICON HELPERS
# ==========================================
class IconExtractor:
    _cache = {}

    @staticmethod
    def autocrop(pixmap):
        img = pixmap.toImage()
        min_x, min_y = img.width(), img.height()
        max_x, max_y = 0, 0
        has_pixels = False
        
        for y in range(img.height()):
            for x in range(img.width()):
                if img.pixelColor(x, y).alpha() > 8:
                    has_pixels = True
                    min_x, min_y = min(min_x, x), min(min_y, y)
                    max_x, max_y = max(max_x, x), max(max_y, y)
                    
        if has_pixels:
            w, h = max_x - min_x + 1, max_y - min_y + 1
            side = max(w, h)
            # Create a square centered on the original icon's center
            cx, cy = min_x + w // 2, min_y + h // 2
            rect = QRect(max(0, cx - side // 2), max(0, cy - side // 2), side, side)
            # Ensure the rect is within bounds
            if rect.right() >= img.width(): rect.moveRight(img.width() - 1)
            if rect.bottom() >= img.height(): rect.moveBottom(img.height() - 1)
            if rect.left() < 0: rect.moveLeft(0)
            if rect.top() < 0: rect.moveTop(0)
            return QPixmap.fromImage(img.copy(rect))
        return pixmap

    @staticmethod
    def get_icon_pixmap(path, size=48):
        # Normalize path for caching and comparison
        norm_path = os.path.normpath(path).lower()
        if norm_path not in IconExtractor._cache:
            icon_path = path
            info = QFileInfo(path)
            ext = info.suffix().lower()
            
            if ext == 'lnk':
                try:
                    import pythoncom
                    pythoncom.CoInitialize()
                    import win32com.client
                    shell = win32com.client.Dispatch("WScript.Shell")
                    shortcut = shell.CreateShortCut(path)
                    if shortcut.IconLocation and ',' in shortcut.IconLocation:
                        loc = shortcut.IconLocation.split(',')[0]
                        if os.path.exists(loc): icon_path = loc
                    if icon_path == path and shortcut.TargetPath and os.path.exists(shortcut.TargetPath):
                        icon_path = shortcut.TargetPath
                except: pass
            elif ext == 'url':
                try:
                    with open(path, 'r', encoding='utf-8', errors='ignore') as f:
                        for line in f:
                            if line.startswith('IconFile='):
                                loc = line.strip().split('=', 1)[1]
                                if os.path.exists(loc): icon_path = loc; break
                except: pass
            
            try:
                provider = QFileIconProvider()
                icon = provider.icon(QFileInfo(icon_path))
                pix = icon.pixmap(256, 256)
                
                # If target icon is empty/invalid, try the original file (the shortcut itself)
                if pix.isNull() or pix.toImage().allGray():
                    if os.path.normpath(icon_path).lower() != norm_path:
                        icon = provider.icon(QFileInfo(path))
                        pix = icon.pixmap(256, 256)
                
                if pix.isNull():
                    pix = QPixmap(256, 256)
                    pix.fill(Qt.GlobalColor.transparent)
                else:
                    pix = IconExtractor.autocrop(pix)
                
                IconExtractor._cache[norm_path] = pix
            except: 
                pix = QPixmap(256, 256)
                pix.fill(Qt.GlobalColor.transparent)
                IconExtractor._cache[norm_path] = pix

        return IconExtractor._cache[norm_path]

_volume_interface = None
_mute_cache = {'state': False, 'last_check': 0}

def get_system_mute():
    global _volume_interface
    import time
    now = time.time()
    if now - _mute_cache['last_check'] < 0.3: # Faster check
        return _mute_cache['state']
        
    try:
        import pythoncom
        pythoncom.CoInitialize()
        if _volume_interface is None:
            from pycaw.pycaw import AudioUtilities
            devices = AudioUtilities.GetSpeakers()
            _volume_interface = devices.EndpointVolume
        
        is_muted = (_volume_interface.GetMute() == 1)
        if not is_muted:
            is_muted = (_volume_interface.GetMasterVolumeLevelScalar() < 0.01)
            
        if is_muted != _mute_cache['state']:
            print(f"DEBUG: Mute state changed to: {is_muted}")
            
        _mute_cache['state'] = is_muted
        _mute_cache['last_check'] = now
    except Exception as e:
        print(f"MUTE ERROR: {e}")
        _volume_interface = None # Reset on error to try re-init next time
        
    return _mute_cache['state']

def change_system_volume(delta):
    global _volume_interface
    try:
        import pythoncom
        pythoncom.CoInitialize()
        if _volume_interface is None:
            from pycaw.pycaw import AudioUtilities
            devices = AudioUtilities.GetSpeakers()
            _volume_interface = devices.EndpointVolume
            
        current = _volume_interface.GetMasterVolumeLevelScalar()
        new_vol = max(0.0, min(1.0, current + delta))
        _volume_interface.SetMasterVolumeLevelScalar(new_vol, None)
        # Clear cache to force immediate update
        _mute_cache['last_check'] = 0
        return True
    except Exception as e:
        print(f"VOL ERROR: {e}")
        _volume_interface = None
        return False

def get_system_volume_level():
    global _volume_interface
    try:
        import pythoncom
        pythoncom.CoInitialize()
        if _volume_interface is None:
            from pycaw.pycaw import AudioUtilities
            devices = AudioUtilities.GetSpeakers()
            _volume_interface = devices.EndpointVolume
        return _volume_interface.GetMasterVolumeLevelScalar()
    except:
        return 0.0

def get_battery_info():
    try:
        import psutil
        battery = psutil.sensors_battery()
        if battery:
            return battery.percent, battery.power_plugged
        return 100, True
    except:
        return 100, True


# ==========================================
# 4. DISPLAY EFFECTS ENGINE (SOLID STATE)
# ==========================================
class DisplayEffectsEngine(QObject):
    """
    Pandora's internal hardware-accelerated screen filter engine.
    Uses WinAPI Gamma Ramps for zero-latency, anti-cheat-safe visual effects.
    """
    _instance = None
    
    @staticmethod
    def instance():
        if DisplayEffectsEngine._instance is None:
            DisplayEffectsEngine._instance = DisplayEffectsEngine()
        return DisplayEffectsEngine._instance

    def __init__(self):
        super().__init__()
        self._original_ramp = self.get_current_ramp()
        self._current_intensity = 0.0
        self._target_intensity = 0.0
        self._active_preset = "Sunset"
        self._is_enabled = False
        
        self.anim = QVariantAnimation(self)
        self.anim.setDuration(300)
        self.anim.setEasingCurve(QEasingCurve.Type.OutQuad)
        self.anim.valueChanged.connect(self._apply_frame)

    def get_current_ramp(self):
        try:
            hdc = ctypes.windll.user32.GetDC(0)
            ramp = (wintypes.WORD * 768)()
            if ctypes.windll.gdi32.GetDeviceGammaRamp(hdc, ctypes.byref(ramp)):
                ctypes.windll.user32.ReleaseDC(0, hdc)
                return bytes(ramp)
            ctypes.windll.user32.ReleaseDC(0, hdc)
        except: pass
        return None

    def restore_original(self):
        if self._original_ramp:
            hdc = ctypes.windll.user32.GetDC(0)
            ramp = (wintypes.WORD * 768).from_buffer_copy(self._original_ramp)
            ctypes.windll.gdi32.SetDeviceGammaRamp(hdc, ctypes.byref(ramp))
            ctypes.windll.user32.ReleaseDC(0, hdc)

    def set_enabled(self, enabled, instant=False):
        self._is_enabled = enabled
        target = 1.0 if enabled else 0.0
        if instant:
            self._current_intensity = target
            self._apply_frame(target)
        else:
            self.anim.stop()
            self.anim.setStartValue(self._current_intensity)
            self.anim.setEndValue(target)
            self.anim.start()

    def set_intensity(self, val):
        """Sets the warmth intensity (0.0 to 1.0)"""
        self._target_intensity = max(0.0, min(1.0, val))
        if self._is_enabled:
            self._current_intensity = self._target_intensity
            self._apply_frame(self._current_intensity)

    def set_preset(self, name):
        self._active_preset = name
        if self._is_enabled:
            self._apply_frame(self._current_intensity)

    def _apply_frame(self, intensity):
        self._current_intensity = intensity
        if intensity <= 0.001 and not self._is_enabled:
            self.restore_original()
            return

        # Preset Multipliers [Blue Reduction, Green Reduction]
        presets = {
            "Reading": [0.45, 0.75],
            "Sunset": [0.60, 0.85],
            "Movie": [0.85, 0.95],
            "Eye Saver": [0.75, 0.90]
        }
        b_mul, g_mul = presets.get(self._active_preset, [0.60, 0.85])
        
        # Scale by intensity
        b_final = 1.0 - (1.0 - b_mul) * intensity
        g_final = 1.0 - (1.0 - g_mul) * intensity
        
        ramp = (wintypes.WORD * 768)()
        for i in range(256):
            v = i * 256
            ramp[i] = v                   # Red
            ramp[i + 256] = int(v * g_final) # Green
            ramp[i + 512] = int(v * b_final) # Blue
            
        hdc = ctypes.windll.user32.GetDC(0)
        ctypes.windll.gdi32.SetDeviceGammaRamp(hdc, ctypes.byref(ramp))
        ctypes.windll.user32.ReleaseDC(0, hdc)

# Global helper for cleanup
def restore_display_effects():
    if DisplayEffectsEngine._instance:
        DisplayEffectsEngine.instance().restore_original()

class VectorIcon:
    @staticmethod
    def icon(name, color="#ffffff"):
        actual_name = name
        if name == "mute":
            # If muted, show 'unmute' icon. If unmuted, show 'mute' icon.
            actual_name = "unmute" if get_system_mute() else "mute"
            
        svg_path = actual_name
        if not (svg_path.endswith(".svg") and os.path.exists(svg_path)):
            svg_path = os.path.join("assets", f"{actual_name}.svg")
            
        if os.path.exists(svg_path):
            from PyQt6.QtSvg import QSvgRenderer
            renderer = QSvgRenderer(svg_path)
            if renderer.isValid():
                pix = QPixmap(64, 64); pix.fill(Qt.GlobalColor.transparent); p = QPainter(pix)
                renderer.render(p, QRectF(pix.rect())); p.setCompositionMode(QPainter.CompositionMode.CompositionMode_SourceIn); p.fillRect(pix.rect(), QColor(color)); p.end()
                return QIcon(pix)
            
        pix = QPixmap(32, 32); pix.fill(Qt.GlobalColor.transparent); p = QPainter(pix)
        p.setRenderHint(QPainter.RenderHint.Antialiasing); p.setPen(QPen(QColor(color), 2))
        if name=="search": p.drawEllipse(7, 7, 12, 12); p.drawLine(18, 18, 24, 24)
        elif name=="sort_asc": p.drawLine(16, 8, 16, 24); p.drawLine(16, 8, 10, 14); p.drawLine(16, 8, 22, 14)
        elif name=="sort_desc": p.drawLine(16, 8, 16, 24); p.drawLine(16, 24, 10, 18); p.drawLine(16, 24, 22, 18)
        elif name=="pin": p.drawRect(12, 8, 8, 10); p.drawLine(16, 18, 16, 24)
        elif name=="check": p.drawLine(8, 16, 14, 22); p.drawLine(14, 22, 24, 10)
        elif name=="add": p.drawLine(16, 8, 16, 24); p.drawLine(8, 16, 24, 16)
        elif name=="folder": p.drawRect(8, 10, 16, 12); p.drawRect(8, 8, 6, 2)
        elif name=="rocket": p.drawLine(16, 6, 10, 20); p.drawLine(16, 6, 22, 20); p.drawLine(10, 20, 22, 20); p.drawLine(16, 20, 16, 26)
        elif name=="reset": p.drawArc(8, 8, 16, 16, 45*16, 270*16); p.drawLine(16, 8, 20, 4); p.drawLine(16, 8, 20, 12)
        elif name=="back": p.drawLine(20, 8, 12, 16); p.drawLine(12, 16, 20, 24); p.drawLine(12, 16, 28, 16)
        elif name=="settings": p.drawEllipse(10, 10, 12, 12); p.drawLine(16, 4, 16, 8); p.drawLine(16, 24, 16, 28); p.drawLine(4, 16, 8, 16); p.drawLine(24, 16, 28, 16); p.drawLine(8, 8, 11, 11); p.drawLine(21, 21, 24, 24); p.drawLine(24, 8, 21, 11); p.drawLine(8, 24, 11, 21)
        elif name=="folders": p.drawRect(6, 12, 20, 14); p.drawRect(6, 8, 8, 4)
        elif name=="template": p.drawRect(6, 6, 20, 20); p.drawLine(6, 12, 26, 12); p.drawLine(13, 12, 13, 26)
        elif name=="upload": p.drawLine(16, 8, 16, 24); p.drawLine(16, 8, 10, 14); p.drawLine(16, 8, 22, 14); p.drawLine(10, 24, 22, 24)
        p.end(); return QIcon(pix)
