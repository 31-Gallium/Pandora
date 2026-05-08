import os
import ctypes
from ctypes import wintypes
from PyQt6.QtCore import Qt, QFileInfo, QSize, QRect
from PyQt6.QtGui import QPixmap, QColor, QPainter, QPen, QIcon, QImage
from PyQt6.QtWidgets import QFileIconProvider
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

class VectorIcon:
    @staticmethod
    def icon(name, color="#ffffff"):
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
        p.end(); return QIcon(pix)
