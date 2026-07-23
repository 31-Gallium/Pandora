import os
import ctypes
from ctypes import wintypes
from PyQt6.QtCore import Qt, QFileInfo, QSize, QRect, QRectF, QObject, pyqtSignal, QVariantAnimation, QEasingCurve
from PyQt6.QtGui import QPixmap, QColor, QPainter, QPen, QIcon, QImage
from PyQt6.QtWidgets import QFileIconProvider, QApplication
from PyQt6.QtSvg import QSvgRenderer
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
    def set_modern_visuals(hwnd, blur=True, acrylic=False):
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
            
            # 2. Extend DWM Frame into Client Area
            class MARGINS(ctypes.Structure):
                _fields_ = [
                    ("cxLeftWidth", ctypes.c_int),
                    ("cxRightWidth", ctypes.c_int),
                    ("cyTopHeight", ctypes.c_int),
                    ("cyBottomHeight", ctypes.c_int),
                ]
            margins = MARGINS(-1, -1, -1, -1)
            dwmapi.DwmExtendFrameIntoClientArea(hwnd_int, ctypes.byref(margins))
            
            # Use BlurWindow library to apply Blur properly across Win10/11
            from BlurWindow.blurWindow import GlobalBlur
            
            theme = 'Dark'
            is_dark = theme in ['Dark', 'Default']
            dark_mode = ctypes.c_int(1 if is_dark else 0)
            dwmapi.DwmSetWindowAttribute(hwnd_int, 20, ctypes.byref(dark_mode), 4)
            
            GlobalBlur(hwnd_int, Acrylic=acrylic, hexColor='#10101440', Dark=True)
            
        except Exception as e:
            logger.error(f"WinAPI set_modern_visuals error: {e}")

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
        """Pin a window to the desktop layer using pure Z-order management.
        
        Instead of setting an owner relationship with WorkerW (which breaks when
        Explorer rebuilds WorkerW during boot), we simply push the window to
        HWND_BOTTOM and install a subclass that prevents Windows from changing
        our Z-order. This is the approach Rainmeter uses.
        """
        try:
            hwnd_int = int(hwnd)
            user32 = ctypes.windll.user32
            
            # Push to the absolute bottom of the Z-order
            # HWND_BOTTOM = 1
            # SWP_NOMOVE | SWP_NOSIZE | SWP_NOACTIVATE | SWP_SHOWWINDOW = 0x0053
            user32.SetWindowPos(hwnd_int, 1, 0, 0, 0, 0, 0x0053)
            
            # Track this window for automatic pinning
            DesktopPinner.track(hwnd_int)
            
        except Exception as e:
            logger.error(f"WinAPI pin_to_workerw error: {e}")

    @staticmethod
    def unpin_from_workerw(hwnd):
        """Remove a window from desktop pinning tracking."""
        try:
            hwnd_int = int(hwnd)
            DesktopPinner.untrack(hwnd_int)
        except Exception:
            pass


class DesktopPinner:
    """Uses GWLP_HWNDPARENT to natively pin windows to the Desktop, surviving Win+D flawlessly.
    Includes an auto-recovery timer to re-pin if the Desktop window changes (e.g., during Windows startup).
    """
    
    _tracked_windows = set()
    _timer = None
    _current_desktop_hwnd = 0
    
    @classmethod
    def _start_monitoring(cls):
        try:
            from PyQt6.QtCore import QTimer
            cls._timer = QTimer()
            cls._timer.setInterval(1000)
            cls._timer.timeout.connect(cls._check_desktop_state)
            cls._timer.start()
        except Exception as e:
            logger.error(f"_start_monitoring error: {e}")
            
    @classmethod
    def _stop_monitoring(cls):
        if cls._timer:
            cls._timer.stop()
            cls._timer = None
            
    @classmethod
    def _check_desktop_state(cls):
        if not cls._tracked_windows:
            return
        try:
            import ctypes
            import platform
            from ctypes import wintypes
            user32 = ctypes.windll.user32
            
            # Setup correct argtypes
            if not hasattr(user32.FindWindowW, 'argtypes'):
                user32.FindWindowW.argtypes = [ctypes.c_wchar_p, ctypes.c_wchar_p]
                user32.FindWindowW.restype = wintypes.HWND
                user32.FindWindowExW.argtypes = [wintypes.HWND, wintypes.HWND, ctypes.c_wchar_p, ctypes.c_wchar_p]
                user32.FindWindowExW.restype = wintypes.HWND
                
            hwnd_desktop = user32.FindWindowW("Progman", "Program Manager")
            workerw = user32.FindWindowExW(0, 0, "WorkerW", None)
            while workerw:
                if user32.FindWindowExW(workerw, 0, "SHELLDLL_DefView", None):
                    hwnd_desktop = workerw
                    break
                workerw = user32.FindWindowExW(0, workerw, "WorkerW", None)
                
            if not hwnd_desktop:
                user32.GetShellWindow.restype = wintypes.HWND
                hwnd_desktop = user32.GetShellWindow()
                if not hwnd_desktop:
                    return
                    
            if hwnd_desktop != cls._current_desktop_hwnd:
                cls._current_desktop_hwnd = hwnd_desktop
                
                # Setup SetWindowLongPtr based on architecture
                if platform.architecture()[0] == '64bit':
                    set_window_long = user32.SetWindowLongPtrW
                    set_window_long.argtypes = [wintypes.HWND, ctypes.c_int, ctypes.c_uint64]
                    set_window_long.restype = ctypes.c_uint64
                else:
                    set_window_long = user32.SetWindowLongW
                    set_window_long.argtypes = [wintypes.HWND, ctypes.c_int, wintypes.HWND]
                    set_window_long.restype = wintypes.HWND
                    
                dead = []
                for hwnd_int in list(cls._tracked_windows):
                    if user32.IsWindow(hwnd_int):
                        set_window_long(hwnd_int, -8, hwnd_desktop) # GWLP_HWNDPARENT
                        user32.SetWindowPos(hwnd_int, 1, 0, 0, 0, 0, 0x0413) # HWND_BOTTOM
                    else:
                        dead.append(hwnd_int)
                        
                for h in dead:
                    cls.untrack(h)
                    
        except Exception as e:
            pass
            
    @classmethod
    def track(cls, hwnd_int):
        cls._tracked_windows.add(hwnd_int)
        if cls._timer is None:
            cls._start_monitoring()
        cls._current_desktop_hwnd = 0 # Force a re-pin immediately
        cls._check_desktop_state()
        
    @classmethod
    def untrack(cls, hwnd_int):
        cls._tracked_windows.discard(hwnd_int)
        if not cls._tracked_windows and cls._timer is not None:
            cls._stop_monitoring()
            
    @classmethod
    def repin_all(cls):
        """Force a manual re-pin to current Desktop."""
        cls._current_desktop_hwnd = 0
        cls._check_desktop_state()


class DesktopMonitor:
    @staticmethod
    def unregister(widget): pass

# ==========================================
# 3. ICON HELPERS
# ==========================================
class IconExtractor:
    _cache = {}
    _app_icon_cache = {}

    @staticmethod
    def autocrop(pixmap):
        img = pixmap.toImage()
        width, height = img.width(), img.height()
        
        # 1. Top-to-bottom scan for min_y
        min_y = -1
        for y in range(height):
            for x in range(width):
                if ((img.pixel(x, y) >> 24) & 0xFF) > 8:
                    min_y = y
                    break
            if min_y != -1:
                break
                
        # If no visible pixels found, return original pixmap
        if min_y == -1:
            return pixmap
            
        # 2. Bottom-to-top scan for max_y
        max_y = -1
        for y in range(height - 1, min_y - 1, -1):
            for x in range(width):
                if ((img.pixel(x, y) >> 24) & 0xFF) > 8:
                    max_y = y
                    break
            if max_y != -1:
                break
                
        # 3. Left-to-right scan for min_x
        min_x = -1
        for x in range(width):
            for y in range(min_y, max_y + 1):
                if ((img.pixel(x, y) >> 24) & 0xFF) > 8:
                    min_x = x
                    break
            if min_x != -1:
                break
                
        # 4. Right-to-left scan for max_x
        max_x = -1
        for x in range(width - 1, min_x - 1, -1):
            for y in range(min_y, max_y + 1):
                if ((img.pixel(x, y) >> 24) & 0xFF) > 8:
                    max_x = x
                    break
            if max_x != -1:
                break
                
        w, h = max_x - min_x + 1, max_y - min_y + 1
        side = max(w, h)
        # Create a square centered on the original icon's center
        cx, cy = min_x + w // 2, min_y + h // 2
        rect = QRect(max(0, cx - side // 2), max(0, cy - side // 2), side, side)
        # Ensure the rect is within bounds
        if rect.right() >= width: rect.moveRight(width - 1)
        if rect.bottom() >= height: rect.moveBottom(height - 1)
        if rect.left() < 0: rect.moveLeft(0)
        if rect.top() < 0: rect.moveTop(0)
        return QPixmap.fromImage(img.copy(rect))

    @staticmethod
    def _get_uwp_icon(path, size=48):
        try:
            import ctypes
            from ctypes import wintypes
            from PyQt6.QtGui import QImage, QPixmap
            from PyQt6.QtCore import Qt
            shell32 = ctypes.windll.shell32
            ole32 = ctypes.windll.ole32

            class GUID(ctypes.Structure):
                _fields_ = [
                    ('Data1', wintypes.DWORD), ('Data2', wintypes.WORD),
                    ('Data3', wintypes.WORD), ('Data4', ctypes.c_byte * 8)
                ]
            class SIZE(ctypes.Structure):
                _fields_ = [('cx', ctypes.c_long), ('cy', ctypes.c_long)]

            ole32.CoInitialize(None)
            iid = GUID(0xbcc18b79, 0xba16, 0x442f, (0x80, 0xc4, 0x8a, 0x59, 0xc3, 0x0c, 0x46, 0x3b))
            factory = ctypes.c_void_p()
            hr = shell32.SHCreateItemFromParsingName(ctypes.c_wchar_p(path), None, ctypes.byref(iid), ctypes.byref(factory))

            if hr == 0 and factory:
                GetImageType = ctypes.WINFUNCTYPE(ctypes.HRESULT, ctypes.c_void_p, SIZE, wintypes.DWORD, ctypes.POINTER(wintypes.HBITMAP))
                vtable = ctypes.cast(factory, ctypes.POINTER(ctypes.POINTER(ctypes.c_void_p)))
                GetImage = ctypes.cast(vtable.contents[3], GetImageType)
                hbitmap = wintypes.HBITMAP()
                hr = GetImage(factory, SIZE(size, size), 0, ctypes.byref(hbitmap))
                if hr == 0 and hbitmap.value:
                    img = QImage.fromHBITMAP(hbitmap.value)
                    return QPixmap.fromImage(img)
        except: pass
        return None

    @staticmethod
    def get_icon_pixmap(path, size=48):
        # Normalize path for caching and comparison
        norm_path = os.path.normpath(path).lower()
        if norm_path not in IconExtractor._cache:
            if norm_path.startswith("shell:appsfolder"):
                pix = IconExtractor._get_uwp_icon(path, 256)
                if pix and not pix.isNull():
                    IconExtractor._cache[norm_path] = IconExtractor.autocrop(pix)
                    return IconExtractor._cache[norm_path]

            icon_path = path
            
            info = QFileInfo(path)
            ext = info.suffix().lower()
            
            is_missing = False
            if not os.path.exists(path):
                is_missing = True
            
            if ext == 'lnk':
                try:
                    import pythoncom
                    pythoncom.CoInitialize()
                    import win32com.client
                    shell = win32com.client.Dispatch("WScript.Shell")
                    shortcut = shell.CreateShortCut(path)
                    
                    if os.path.exists(path) and shortcut.TargetPath:
                        # Check if target is a standard file path and is missing
                        if ":" in shortcut.TargetPath and not os.path.exists(shortcut.TargetPath):
                            is_missing = True
                            
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
                    
                if is_missing:
                    # Apply missing file visual indicator: Grayscale + 50% opacity + Red Badge
                    from PyQt6.QtGui import QImage, QPainter, QColor, QPen
                    img = pix.toImage().convertToFormat(QImage.Format.Format_Grayscale8).convertToFormat(QImage.Format.Format_ARGB32)
                    res_pix = QPixmap(pix.size())
                    res_pix.fill(Qt.GlobalColor.transparent)
                    painter = QPainter(res_pix)
                    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
                    painter.setOpacity(0.5)
                    painter.drawImage(0, 0, img)
                    
                    # Draw red badge
                    painter.setOpacity(1.0)
                    r = pix.width() // 5
                    cx = pix.width() - r - 4
                    cy = pix.height() - r - 4
                    
                    # White border
                    painter.setBrush(QColor(255, 60, 60))
                    painter.setPen(QPen(QColor(255, 255, 255), max(2, pix.width()//30)))
                    painter.drawEllipse(cx, cy, r, r)
                    painter.end()
                    pix = res_pix
                
                IconExtractor._cache[norm_path] = pix
            except: 
                pix = QPixmap(256, 256)
                pix.fill(Qt.GlobalColor.transparent)
                IconExtractor._cache[norm_path] = pix

        return IconExtractor._cache[norm_path]

    @staticmethod
    def get_app_icon_pixmap(app_id, size=256):
        if not app_id:
            return None
        
        cache_key = (app_id, size)
        if cache_key in IconExtractor._app_icon_cache:
            return IconExtractor._app_icon_cache[cache_key]
            
        pix = None
        
        # 1. Try UWP format if it contains "!" or looks like a UWP ID
        if "!" in app_id or ("_" in app_id and "microsoft" in app_id.lower()):
            uwp_path = f"shell:AppsFolder\\{app_id}"
            pix = IconExtractor.get_icon_pixmap(uwp_path, size)
            
        # 2. Try process scan if UWP failed/skipped
        if not pix or pix.isNull():
            proc_name = app_id
            if not proc_name.lower().endswith(".exe") and "!" not in proc_name:
                proc_name += ".exe"
            
            # Find running process path
            import psutil
            exe_path = None
            for p in psutil.process_iter(['name', 'exe']):
                try:
                    if p.info['name'] and p.info['name'].lower() == proc_name.lower():
                        exe_path = p.info['exe']
                        if exe_path and os.path.exists(exe_path):
                            break
                except:
                    pass
            
            if exe_path:
                pix = IconExtractor.get_icon_pixmap(exe_path, size)
                
        # 3. Fallback: try UWP again just in case (e.g. app_id has no "!" but is UWP)
        if not pix or pix.isNull():
            uwp_path = f"shell:AppsFolder\\{app_id}"
            pix = IconExtractor.get_icon_pixmap(uwp_path, size)
            
            # If that failed and it doesn't have a "!", try appending "!App"
            if (not pix or pix.isNull()) and "!" not in app_id:
                uwp_path_suffix = f"shell:AppsFolder\\{app_id}!App"
                pix = IconExtractor.get_icon_pixmap(uwp_path_suffix, size)

        # 4. Save to cache and return
        if pix and not pix.isNull():
            IconExtractor._app_icon_cache[cache_key] = pix
            return pix
            
        return None

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
            from pycaw.pycaw import AudioUtilities, IAudioEndpointVolume
            from ctypes import cast, POINTER
            from comtypes import CLSCTX_ALL
            devices = AudioUtilities.GetSpeakers()
            if hasattr(devices, 'EndpointVolume'):
                _volume_interface = devices.EndpointVolume
            else:
                interface = devices.Activate(IAudioEndpointVolume._iid_, CLSCTX_ALL, None)
                _volume_interface = cast(interface, POINTER(IAudioEndpointVolume))
        
        is_muted = (_volume_interface.GetMute() == 1)
        if not is_muted:
            is_muted = (_volume_interface.GetMasterVolumeLevelScalar() < 0.01)
            
        if is_muted != _mute_cache['state']:
            print(f"DEBUG: Mute state changed to: {is_muted}")
            
        _mute_cache['state'] = is_muted
        _mute_cache['last_check'] = now
    except Exception as e:
        _volume_interface = None # Reset on error to try re-init next time
        
    return _mute_cache['state']

# ==========================================
# 4. MEDIA & VOLUME EVENT MANAGER
# ==========================================
class VolumeChangeHandler:
    """COM Callback for Master Volume/Mute changes"""
    def __init__(self, callback):
        self.callback = callback

    def OnNotify(self, pNotify):
        # Trigger the callback with new volume and mute state
        # pNotify.fMuted is a bool, pNotify.fMasterVolume is a float
        self.callback(pNotify.fMasterVolume, bool(pNotify.fMuted))

class MediaSessionManager(QObject):
    """
    Reactive wrapper for the centralized MediaDaemon service.
    Decouples UI modules from direct Windows API interaction.
    """
    media_changed = pyqtSignal(dict)
    volume_changed = pyqtSignal(float, bool)
    _instance = None

    @staticmethod
    def instance():
        if MediaSessionManager._instance is None:
            MediaSessionManager._instance = MediaSessionManager()
        return MediaSessionManager._instance

    def __init__(self):
        super().__init__()
        from PyQt6.QtWidgets import QApplication
        self.app = QApplication.instance()
        
        self.current_track = {"title": "No Media", "artist": "", "status": "Stopped",
                              "position": 0.0, "duration": 0.0, "sync_time": 0.0}
        self.thumbnail = None
        self._last_app_thumbs = {}
        self.master_volume = 0.0
        self.is_muted = False
        
        self.audio_features = None
        
        # 1. Start Volume Callback (PyCaw) - Volume is still handled locally for now
        self._setup_volume_callback()
        
        # 2. Connect to the core MediaDaemon
        self._cached_vol_interface = None
        self._cached_vol_app_id = None
        
        if getattr(self.app, 'media_daemon', None) is not None:
            self._connect_to_daemon()
        else:
            print("[MediaSessionManager] MediaDaemon not initialized yet, waiting for lazy load.")

    def _connect_to_daemon(self):
        if getattr(self.app, 'media_daemon', None) is not None:
            self.app.media_daemon.state_changed.connect(self._on_state_changed)
            self.app.media_daemon.thumbnail_ready.connect(self._on_thumbnail_ready)
            if hasattr(self.app.media_daemon, 'audio_features_updated'):
                self.app.media_daemon.audio_features_updated.connect(self._on_audio_features)
            # Seed initial state if daemon is already running
            if hasattr(self.app.media_daemon, 'state'):
                self._on_state_changed(self.app.media_daemon._emit_update_as_dict())
            # Seed initial cached thumbnail if present
            if getattr(self.app.media_daemon, 'thumbnail', None) is not None:
                self.thumbnail = self.app.media_daemon.thumbnail

    def _on_audio_features(self, features):
        self.audio_features = features

    def _on_state_changed(self, state):
        # Clear thumbnail immediately if the track has changed (title or artist differs)
        if self.current_track.get("title") != state.get("title") or self.current_track.get("artist") != state.get("artist"):
            self.thumbnail = None
            
        self.current_track = state
        
        # Clear thumbnail if the state explicitly reports no thumbnail
        if not state.get("has_thumbnail", False):
            self.thumbnail = None
            
        self.media_changed.emit(state)

    def _on_thumbnail_ready(self, image):
        self.thumbnail = image
        app_id = self.current_track.get('app_id', '')
        if app_id and image and not image.isNull():
            self._last_app_thumbs[app_id] = image
        self.media_changed.emit(self.current_track)

    def _setup_volume_callback(self):
        try:
            import pythoncom
            from pycaw.pycaw import AudioUtilities, IAudioEndpointVolume
            from ctypes import cast, POINTER
            from comtypes import CLSCTX_ALL
            pythoncom.CoInitialize()
            devices = AudioUtilities.GetSpeakers()
            if hasattr(devices, 'EndpointVolume'):
                self._volume_interface = devices.EndpointVolume
            else:
                interface = devices.Activate(IAudioEndpointVolume._iid_, CLSCTX_ALL, None)
                self._volume_interface = cast(interface, POINTER(IAudioEndpointVolume))
            self.master_volume = self._volume_interface.GetMasterVolumeLevelScalar()
            self.is_muted = self._volume_interface.GetMute() == 1
        except: pass

    # ── Playback Controls (Delegated to Daemon) ──
    def change_app_volume(self, delta):
        app_id = self.current_track.get('app_id', '').lower()
        if not app_id: return None
        
        try:
            import pythoncom
            pythoncom.CoInitialize()
            
            volume = None
            # Check Cache
            if app_id == self._cached_vol_app_id and self._cached_vol_interface:
                try:
                    volume = self._cached_vol_interface
                    # Test if still valid
                    current = volume.GetMasterVolume()
                except:
                    volume = None
                    self._cached_vol_interface = None
            
            if not volume:
                from pycaw.pycaw import AudioUtilities
                sessions = AudioUtilities.GetAllSessions()
                target = app_id.lower()
                for session in sessions:
                    if session.Process:
                        name = session.Process.name().lower()
                        if name.replace(".exe", "") in target or target in name:
                            volume = session.SimpleAudioVolume
                            self._cached_vol_interface = volume
                            self._cached_vol_app_id = app_id
                            break
            
            if volume:
                current = volume.GetMasterVolume()
                new_vol = max(0.0, min(1.0, current + delta))
                volume.SetMasterVolume(new_vol, None)
                if new_vol > 0.0 and volume.GetMute() == 1:
                    volume.SetMute(0, None)
                
                # Eager update for instant UI feedback
                self.current_track['app_volume'] = new_vol
                self.media_changed.emit(self.current_track)

                # Notify daemon to suppress polling and update state
                if hasattr(self.app, 'media_daemon'):
                    self.app.media_daemon.notify_vol_change(new_vol)
                return new_vol
        except Exception as e:
            print(f"VOL ERR: {e}")
            self._cached_vol_interface = None
        return None

    def get_app_volume(self):
        app_id = self.current_track.get('app_id', '').lower()
        if not app_id: return None
        
        try:
            import pythoncom
            from pycaw.pycaw import AudioUtilities
            pythoncom.CoInitialize()
            sessions = AudioUtilities.GetAllSessions()
            target = app_id.lower()
            
            for session in sessions:
                if session.Process:
                    name = session.Process.name().lower()
                    clean_name = name.replace(".exe", "")
                    if clean_name in target or target in clean_name:
                        return session.SimpleAudioVolume.GetMasterVolume()
        except: pass
        return None

    def scrub_timeline(self, delta_seconds):
        if hasattr(self.app, 'media_daemon') and self.app.media_daemon._current_session:
            import asyncio
            async def _do():
                try: 
                    timeline = self.app.media_daemon._current_session.get_timeline_properties()
                    pos = timeline.position.total_seconds()
                    dur = timeline.end_time.total_seconds()
                    new_pos = max(0.0, min(dur, pos + delta_seconds))
                    
                    import datetime
                    ts = datetime.timedelta(seconds=new_pos)
                    # Convert to ticks (100-nanosecond intervals)
                    ticks = int(ts.total_seconds() * 10000000)
                    
                    await self.app.media_daemon._current_session.try_change_playback_position_async(ticks)
                    self.app.media_daemon.state.position = new_pos
                    self.app.media_daemon.state.sync_time = __import__('time').time()
                    self.app.media_daemon._emit_update()
                except: pass
            asyncio.run_coroutine_threadsafe(_do(), self.app.media_daemon._loop)

    def play_pause(self):
        if hasattr(self.app, 'media_daemon'):
            self.app.media_daemon.play_pause()

    def next_track(self):
        if hasattr(self.app, 'media_daemon'):
            self.app.media_daemon.next_track()

    def prev_track(self):
        if hasattr(self.app, 'media_daemon'):
            self.app.media_daemon.prev_track()

    def switch_session(self, direction=1):
        if hasattr(self.app, 'media_daemon'):
            self.app.media_daemon.switch_session(direction)

    def set_session_by_id(self, app_id):
        if hasattr(self.app, 'media_daemon'):
            self.app.media_daemon.set_session_by_id(app_id)

def change_system_volume(delta):
    global _volume_interface
    try:
        import pythoncom
        pythoncom.CoInitialize()
        if _volume_interface is None:
            from pycaw.pycaw import AudioUtilities, IAudioEndpointVolume
            from ctypes import cast, POINTER
            from comtypes import CLSCTX_ALL
            devices = AudioUtilities.GetSpeakers()
            if hasattr(devices, 'EndpointVolume'):
                _volume_interface = devices.EndpointVolume
            else:
                interface = devices.Activate(IAudioEndpointVolume._iid_, CLSCTX_ALL, None)
                _volume_interface = cast(interface, POINTER(IAudioEndpointVolume))
            
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
            from pycaw.pycaw import AudioUtilities, IAudioEndpointVolume
            from ctypes import cast, POINTER
            from comtypes import CLSCTX_ALL
            devices = AudioUtilities.GetSpeakers()
            if hasattr(devices, 'EndpointVolume'):
                _volume_interface = devices.EndpointVolume
            else:
                interface = devices.Activate(IAudioEndpointVolume._iid_, CLSCTX_ALL, None)
                _volume_interface = cast(interface, POINTER(IAudioEndpointVolume))
        return _volume_interface.GetMasterVolumeLevelScalar()
    except:
        return 0.0

_cached_brightness = None

def get_system_brightness():
    global _cached_brightness
    if _cached_brightness is not None:
        return _cached_brightness
    try:
        import screen_brightness_control as sbc
        _cached_brightness = sbc.get_brightness()[0] / 100.0
        return _cached_brightness
    except:
        return 0.5

def change_system_brightness(delta):
    global _cached_brightness
    try:
        import screen_brightness_control as sbc
        current = get_system_brightness()
        new_val = max(0.0, min(1.0, current + delta))
        _cached_brightness = new_val
        sbc.set_brightness(int(new_val * 100))
        return new_val
    except Exception as e:
        print(f"Brightness Error: {e}")
        return False

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
    _icon_cache = {}
    _pixmap_cache = {}

    @staticmethod
    def icon(name, color="#ffffff"):
        # We still need this for places that explicitly expect a QIcon,
        # but we'll just wrap the 32x32 pixmap.
        pix = VectorIcon.pixmap(name, color, 32)
        cache_key = f"{name}_{color}_icon"
        if cache_key in VectorIcon._icon_cache:
            return VectorIcon._icon_cache[cache_key]
        icon = QIcon(pix)
        VectorIcon._icon_cache[cache_key] = icon
        return icon

    @staticmethod
    def pixmap(name, color="#ffffff", size=32):
        cache_key = f"{name}_{color}_{size}"
        if cache_key in VectorIcon._pixmap_cache:
            return VectorIcon._pixmap_cache[cache_key]
        
        # Sanitize name if it comes from the Electron frontend (e.g. "../assets/browser.svg")
        if "/" in name or "\\" in name:
            name = os.path.basename(name)
        if name.endswith(".svg"):
            name = name[:-4]
            
        actual_name = name
        if name == "mute":
            actual_name = "unmute" if get_system_mute() else "mute"
            
        svg_path = actual_name
        
        # If it explicitly includes the assets directory, resolve it properly
        if svg_path.startswith("assets/") or svg_path.startswith("assets\\"):
            svg_path = get_resource_path(svg_path)
            
        if not (svg_path.endswith(".svg") and os.path.exists(svg_path)):
            svg_path = get_resource_path(os.path.join("assets", f"{actual_name}.svg"))
            
        if os.path.exists(svg_path):
            renderer = QSvgRenderer(svg_path)
            if renderer.isValid():
                pix = QPixmap(size, size); pix.fill(Qt.GlobalColor.transparent); p = QPainter(pix)
                p.setRenderHint(QPainter.RenderHint.Antialiasing)
                renderer.render(p, QRectF(pix.rect())); p.setCompositionMode(QPainter.CompositionMode.CompositionMode_SourceIn); p.fillRect(pix.rect(), QColor(color)); p.end()
                VectorIcon._pixmap_cache[cache_key] = pix
                return pix

        pix = QPixmap(size, size)
        pix.fill(Qt.GlobalColor.transparent)
        p = QPainter(pix)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.setPen(QPen(QColor(color), max(1, size//16)))
        scale = size / 32.0
        p.scale(scale, scale)

        try:
            if name=="play": p.drawPolygon(QPointF(10, 8), QPointF(24, 16), QPointF(10, 24))
            elif name=="pause": p.drawLine(12, 8, 12, 24); p.drawLine(20, 8, 20, 24)
            elif name=="next": p.drawPolygon(QPointF(8, 10), QPointF(18, 16), QPointF(8, 22)); p.drawLine(20, 10, 20, 22)
            elif name=="prev": p.drawPolygon(QPointF(24, 10), QPointF(14, 16), QPointF(24, 22)); p.drawLine(12, 10, 12, 22)
            elif name=="volume up": p.drawPolygon(QPointF(6, 12), QPointF(12, 12), QPointF(18, 6), QPointF(18, 26), QPointF(12, 20), QPointF(6, 20)); p.drawArc(14, 10, 8, 12, -45*16, 90*16); p.drawArc(10, 6, 16, 20, -45*16, 90*16)
            elif name=="volume down": p.drawPolygon(QPointF(6, 12), QPointF(12, 12), QPointF(18, 6), QPointF(18, 26), QPointF(12, 20), QPointF(6, 20)); p.drawArc(14, 10, 8, 12, -45*16, 90*16)
            elif name=="mute": p.drawPolygon(QPointF(6, 12), QPointF(12, 12), QPointF(18, 6), QPointF(18, 26), QPointF(12, 20), QPointF(6, 20)); p.drawLine(22, 12, 28, 18); p.drawLine(28, 12, 22, 18)
            elif name=="battery": p.drawRect(4, 10, 20, 12); p.fillRect(24, 14, 2, 4, QColor(color))
            elif name=="charging": p.drawRect(4, 10, 20, 12); p.fillRect(24, 14, 2, 4, QColor(color)); p.drawLine(14, 10, 10, 16); p.drawLine(10, 16, 16, 16); p.drawLine(16, 16, 12, 22)
            elif name=="close": p.drawLine(8, 8, 24, 24); p.drawLine(24, 8, 8, 24)
            elif name=="add": p.drawLine(16, 8, 16, 24); p.drawLine(8, 16, 24, 16)
            elif name=="check": p.drawLine(8, 16, 14, 22); p.drawLine(14, 22, 24, 10)
            elif name=="folder": p.drawRect(8, 10, 16, 12); p.drawRect(8, 8, 6, 2)
            elif name=="rocket": p.drawLine(16, 6, 10, 20); p.drawLine(16, 6, 22, 20); p.drawLine(10, 20, 22, 20); p.drawLine(16, 20, 16, 26)
            elif name=="reset": p.drawArc(8, 8, 16, 16, 45*16, 270*16); p.drawLine(16, 8, 20, 4); p.drawLine(16, 8, 20, 12)
            elif name=="back": p.drawLine(20, 8, 12, 16); p.drawLine(12, 16, 20, 24); p.drawLine(12, 16, 28, 16)
            elif name=="settings": p.drawEllipse(10, 10, 12, 12); p.drawLine(16, 4, 16, 8); p.drawLine(16, 24, 16, 28); p.drawLine(4, 16, 8, 16); p.drawLine(24, 16, 28, 16); p.drawLine(8, 8, 11, 11); p.drawLine(21, 21, 24, 24); p.drawLine(24, 8, 21, 11); p.drawLine(8, 24, 11, 21)
            elif name=="folders": p.drawRect(6, 12, 20, 14); p.drawRect(6, 8, 8, 4)
            elif name=="template": p.drawRect(6, 6, 20, 20); p.drawLine(6, 12, 26, 12); p.drawLine(13, 12, 13, 26)
            elif name=="upload": p.drawLine(16, 8, 16, 24); p.drawLine(16, 8, 10, 14); p.drawLine(16, 8, 22, 14); p.drawLine(10, 24, 22, 24)
            elif name=="search": p.drawEllipse(7, 7, 12, 12); p.drawLine(18, 18, 24, 24)
            elif name=="sort_asc": p.drawLine(16, 8, 16, 24); p.drawLine(16, 8, 10, 14); p.drawLine(16, 8, 22, 14)
            elif name=="sort_desc": p.drawLine(16, 8, 16, 24); p.drawLine(16, 24, 10, 18); p.drawLine(16, 24, 22, 18)
            elif name=="pin": p.drawRect(12, 8, 8, 10); p.drawLine(16, 18, 16, 24)
            else:
                from PyQt6.QtGui import QFont
                p.setFont(QFont("Arial", 8))
                p.drawText(QRectF(0, 0, 32, 32), Qt.AlignmentFlag.AlignCenter, str(name)[:3])
        except Exception as e:
            print(f"Icon drawing error: {e}")
        finally:
            if p.isActive():
                p.end()

        VectorIcon._pixmap_cache[cache_key] = pix
        return pix

_wallpaper_cache = {}

def get_resource_path(relative_path):
    """Get absolute path to resource, works for dev and for PyInstaller"""
    import sys
    import os
    if hasattr(sys, '_MEIPASS'):
        return os.path.join(sys._MEIPASS, relative_path)
    return os.path.join(os.path.abspath(os.path.dirname(__file__)), relative_path)

def get_desktop_accent_colors(max_accents=5):
    try:
        from PIL import Image
        import ctypes
        import math
        import colorsys
        
        # Perceptual weighted RGB distance (humans are more sensitive to green)
        def color_distance(c1, c2):
            rmean = (c1[0] + c2[0]) / 2.0
            r = c1[0] - c2[0]
            g = c1[1] - c2[1]
            b = c1[2] - c2[2]
            return math.sqrt((((512+rmean)*r*r)/256.0) + 4*g*g + (((767-rmean)*b*b)/256.0))
        
        buffer = ctypes.create_unicode_buffer(512)
        ctypes.windll.user32.SystemParametersInfoW(0x0073, 512, buffer, 0)
        wallpaper_path = buffer.value
        
        if wallpaper_path in _wallpaper_cache:
            return _wallpaper_cache[wallpaper_path]
            
        img = Image.open(wallpaper_path).convert('RGB')
        img.thumbnail((150, 150))
        # Quantize to 32 colors for a slightly richer palette before filtering
        img = img.quantize(colors=32, method=Image.Quantize.FASTOCTREE).convert('RGB')
        colors = img.getcolors(150*150)
        
        scored_colors = []
        for count, color in colors:
            r_norm, g_norm, b_norm = [x / 255.0 for x in color]
            h, l, s = colorsys.rgb_to_hls(r_norm, g_norm, b_norm)
            
            # Penalize absolute greys, blacks, and whites, but don't outright skip them
            # This allows monochromatic wallpapers to still return 5 distinct shades
            if s < 0.15 or l < 0.15 or l > 0.9:
                score = count * 0.001
            else:
                # Favor vibrant colors (s^2) and colors with balanced lightness
                l_weight = 1.0 - abs(l - 0.5) * 2  # Peaks at l=0.5
                score = count * (s ** 2) * (l_weight + 0.5)
                
            scored_colors.append((score, color))
            
        scored_colors.sort(key=lambda x: x[0], reverse=True)
        
        final_accents = []
        for score, color in scored_colors:
            too_close = False
            for ac in final_accents:
                # 150 perceptual distance is a solid threshold for distinct colors
                if color_distance(color, ac) < 150:
                    too_close = True
                    break
            if not too_close:
                final_accents.append(color)
            if len(final_accents) >= max_accents:
                break
                
        # If we didn't find enough distinct colors, lower the distance threshold 
        # and try again to fill the remaining slots with variations
        if len(final_accents) < max_accents:
            for score, color in scored_colors:
                if len(final_accents) >= max_accents:
                    break
                if color not in final_accents:
                    too_close = False
                    for ac in final_accents:
                        if color_distance(color, ac) < 50: # Much lower threshold
                            too_close = True
                            break
                    if not too_close:
                        final_accents.append(color)
            
        if len(final_accents) == 1:
            r, g, b = final_accents[0]
            final_accents.append((255 - r, 255 - g, 255 - b))
            
        if len(final_accents) == 5:
            # Alternating trick to separate similar colors
            final_accents = [final_accents[0], final_accents[2], final_accents[4], final_accents[1], final_accents[3]]
            
        _wallpaper_cache.clear()
        _wallpaper_cache[wallpaper_path] = final_accents
        return final_accents
    except Exception as e:
        logger.error(f'Failed to get desktop accent colors: {e}')
        return [(0, 240, 255)]

def is_desktop_light_vibe():
    """Returns True if the desktop wallpaper has a bright/light vibe."""
    accents = get_desktop_accent_colors()
    if not accents:
        return False
    # Calculate average luminance of the extracted colors
    total_luma = 0
    for r, g, b in accents:
        total_luma += (r * 299 + g * 587 + b * 114) / 1000
    avg_luma = total_luma / len(accents)
    return avg_luma > 130

def order_accents_by_vibe(accents, is_light):
    """Sorts accents: darkest first for light vibe, brightest first for dark vibe."""
    if not accents:
        return []
    def luma(c):
        return (c[0] * 299 + c[1] * 587 + c[2] * 114) / 1000
    return sorted(accents, key=luma, reverse=not is_light)



# ==========================================
# PRE-WARM HEAVY DLLs AND MODULES
# ==========================================
def _prewarm_heavy_modules():
    try:
        import pythoncom
        pythoncom.CoInitialize()
        from pycaw.pycaw import AudioUtilities, IAudioEndpointVolume
        from ctypes import cast, POINTER
        from comtypes import CLSCTX_ALL
        import win32com.client
        import psutil
        
        # Pre-initialize audio COM interface to prevent lag on first use
        global _volume_interface
        if _volume_interface is None:
            devices = AudioUtilities.GetSpeakers()
            if hasattr(devices, 'EndpointVolume'):
                _volume_interface = devices.EndpointVolume
            else:
                interface = devices.Activate(IAudioEndpointVolume._iid_, CLSCTX_ALL, None)
                _volume_interface = cast(interface, POINTER(IAudioEndpointVolume))
    except Exception as e:
        pass

_prewarm_heavy_modules()

# ==========================================
# NEW HARDWARE AND COMMUNICATION TOGGLES
# ==========================================
_mic_interface = None
_mic_mute_cache = {'state': False, 'last_check': 0}

def get_mic_mute():
    global _mic_interface
    import time
    now = time.time()
    if now - _mic_mute_cache['last_check'] < 0.3:
        return _mic_mute_cache['state']
        
    try:
        from pycaw.pycaw import AudioUtilities, IAudioEndpointVolume
        from ctypes import cast, POINTER
        from comtypes import CLSCTX_ALL
        import pythoncom
        pythoncom.CoInitialize()
        if _mic_interface is None:
            mic = AudioUtilities.GetMicrophone()
            if mic is None: return False
            interface = mic.Activate(IAudioEndpointVolume._iid_, CLSCTX_ALL, None)
            _mic_interface = cast(interface, POINTER(IAudioEndpointVolume))
            
        _mic_mute_cache['state'] = bool(_mic_interface.GetMute())
        _mic_mute_cache['last_check'] = now
    except:
        _mic_interface = None
        
    return _mic_mute_cache['state']

def toggle_mic_mute():
    global _mic_interface
    try:
        from pycaw.pycaw import AudioUtilities, IAudioEndpointVolume
        from ctypes import cast, POINTER
        from comtypes import CLSCTX_ALL
        import pythoncom
        pythoncom.CoInitialize()
        if _mic_interface is None:
            mic = AudioUtilities.GetMicrophone()
            if mic is None: return
            interface = mic.Activate(IAudioEndpointVolume._iid_, CLSCTX_ALL, None)
            _mic_interface = cast(interface, POINTER(IAudioEndpointVolume))
            
        current = _mic_interface.GetMute()
        _mic_interface.SetMute(0 if current else 1, None)
        _mic_mute_cache['state'] = not current
    except Exception as e:
        logger.error(f"Failed to toggle mic: {e}")
        _mic_interface = None

_radio_cache = {'wifi': False, 'bluetooth': False}
_last_radio_time = 0

def _fetch_radios_sync():
    import asyncio
    try:
        from winsdk.windows.devices.radios import Radio, RadioKind, RadioState
        async def fetch():
            radios = await Radio.get_radios_async()
            w = False
            b = False
            for r in radios:
                if r.kind == RadioKind.WI_FI:
                    w = (r.state == RadioState.ON)
                elif r.kind == RadioKind.BLUETOOTH:
                    b = (r.state == RadioState.ON)
            return {'wifi': w, 'bluetooth': b}
        return asyncio.run(fetch())
    except Exception as e:
        return {'wifi': False, 'bluetooth': False}

def _update_radio_cache():
    global _last_radio_time, _radio_cache
    import time
    if time.time() - _last_radio_time > 2.0:
        _radio_cache = _fetch_radios_sync()
        _last_radio_time = time.time()
    return _radio_cache

def get_wifi_state():
    return _update_radio_cache()['wifi']

def get_bluetooth_state():
    return _update_radio_cache()['bluetooth']

def toggle_wifi():
    global _radio_cache
    import asyncio
    try:
        from winsdk.windows.devices.radios import Radio, RadioKind, RadioState
        async def toggle():
            radios = await Radio.get_radios_async()
            for r in radios:
                if r.kind == RadioKind.WI_FI:
                    new_state = RadioState.ON if r.state == RadioState.OFF else RadioState.OFF
                    await r.set_state_async(new_state)
        asyncio.run(toggle())
        _radio_cache['wifi'] = not _radio_cache['wifi']
    except Exception as e:
        logger.error(f"Failed to toggle wifi: {e}")

def toggle_bluetooth():
    global _radio_cache
    import asyncio
    try:
        from winsdk.windows.devices.radios import Radio, RadioKind, RadioState
        async def toggle():
            radios = await Radio.get_radios_async()
            for r in radios:
                if r.kind == RadioKind.BLUETOOTH:
                    new_state = RadioState.ON if r.state == RadioState.OFF else RadioState.OFF
                    await r.set_state_async(new_state)
        asyncio.run(toggle())
        _radio_cache['bluetooth'] = not _radio_cache['bluetooth']
    except Exception as e:
        logger.error(f"Failed to toggle bluetooth: {e}")

def animate_theme_change(w):
    try:
        from PyQt6.QtWidgets import QLabel, QGraphicsOpacityEffect
        from PyQt6.QtCore import QPropertyAnimation, Qt
        pixmap = w.grab()
        overlay = QLabel(w)
        overlay.setPixmap(pixmap)
        overlay.setGeometry(w.rect())
        overlay.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        effect = QGraphicsOpacityEffect(overlay)
        overlay.setGraphicsEffect(effect)
        overlay.show()
        anim = QPropertyAnimation(effect, b"opacity", overlay)
        anim.setDuration(600)
        anim.setStartValue(1.0)
        anim.setEndValue(0.0)
        anim.finished.connect(overlay.deleteLater)
        anim.start()
        if not hasattr(w, '_theme_anims'):
            w._theme_anims = []
        w._theme_anims.append(anim)
    except Exception as e:
        if "has been deleted" in str(e):
            raise RuntimeError(str(e))
        print("Failed to animate theme:", e)
