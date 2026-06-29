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
                    
                # Force DWM to recomposite the window by triggering a frame change
                # SWP_NOMOVE (0x0002) | SWP_NOSIZE (0x0001) | SWP_NOZORDER (0x0004) | SWP_FRAMECHANGED (0x0020) = 0x0027
                user32.SetWindowPos(hwnd_int, 0, 0, 0, 0, 0, 0x0027)
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
        
        # 1. Start Volume Callback (PyCaw) - Volume is still handled locally for now
        self._setup_volume_callback()
        
        # 2. Connect to the core MediaDaemon
        self._cached_vol_interface = None
        self._cached_vol_app_id = None
        
        if hasattr(self.app, 'media_daemon'):
            self.app.media_daemon.state_changed.connect(self._on_state_changed)
            self.app.media_daemon.thumbnail_ready.connect(self._on_thumbnail_ready)
            # Seed initial state if daemon is already running
            if hasattr(self.app.media_daemon, 'state'):
                self._on_state_changed(self.app.media_daemon._emit_update_as_dict())
            # Seed initial cached thumbnail if present
            if getattr(self.app.media_daemon, 'thumbnail', None) is not None:
                self.thumbnail = self.app.media_daemon.thumbnail
        else:
            print("[MediaSessionManager] WARNING: MediaDaemon not found in app instance.")

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
            interface = devices.Activate(IAudioEndpointVolume._iid_, CLSCTX_ALL, None)
            _volume_interface = cast(interface, POINTER(IAudioEndpointVolume))
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
        if not (svg_path.endswith(".svg") and os.path.exists(svg_path)):
            svg_path = os.path.join("assets", f"{actual_name}.svg")
            
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

def get_desktop_accent_colors(max_accents=4):
    try:
        from PIL import Image
        import ctypes
        import math
        
        def color_distance(c1, c2):
            return math.sqrt(sum((a - b)**2 for a, b in zip(c1, c2)))
        
        buffer = ctypes.create_unicode_buffer(512)
        ctypes.windll.user32.SystemParametersInfoW(0x0073, 512, buffer, 0)
        wallpaper_path = buffer.value
        
        if wallpaper_path in _wallpaper_cache:
            return _wallpaper_cache[wallpaper_path]
            
        img = Image.open(wallpaper_path).convert('RGB')
        img.thumbnail((150, 150))
        img = img.quantize(colors=16, method=Image.Quantize.FASTOCTREE).convert('RGB')
        colors = img.getcolors(150*150)
        
        scored_colors = []
        for count, color in colors:
            r, g, b = color
            max_c = max(r, g, b)
            min_c = min(r, g, b)
            saturation = (max_c - min_c) / 255.0
            brightness = max_c / 255.0
            
            if brightness < 0.2 or brightness > 0.95 or saturation < 0.2:
                continue
                
            score = count * (saturation ** 1.5)
            scored_colors.append((score, color))
            
        scored_colors.sort(key=lambda x: x[0], reverse=True)
        
        final_accents = []
        for score, color in scored_colors:
            too_close = False
            for ac in final_accents:
                if color_distance(color, ac) < 60:
                    too_close = True
                    break
            if not too_close:
                final_accents.append(color)
            if len(final_accents) >= max_accents:
                break
                
        if not final_accents:
            final_accents.append(max(colors, key=lambda x: x[0])[1])
            
        _wallpaper_cache.clear()
        _wallpaper_cache[wallpaper_path] = final_accents
        return final_accents
    except Exception as e:
        logger.error(f'Failed to get desktop accent colors: {e}')
        return [(0, 240, 255)]



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
            interface = devices.Activate(IAudioEndpointVolume._iid_, CLSCTX_ALL, None)
            _volume_interface = cast(interface, POINTER(IAudioEndpointVolume))
    except Exception as e:
        pass

_prewarm_heavy_modules()
