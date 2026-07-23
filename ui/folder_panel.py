import os
import shutil
import math
import time
import logging
from PyQt6.QtWidgets import QWidget, QApplication
from PyQt6.QtCore import Qt, QPoint, QRect, QRectF, QFileInfo, QTimer, QPropertyAnimation, QEasingCurve, QEvent, QFileSystemWatcher, pyqtProperty
from PyQt6.QtGui import QPainter, QColor, QPainterPath, QPen

from ui.app_icon import AppIcon
from utils import WinAPI
from ui.ui_common import AnimatedMenu
from ui.logic import handle_app_drop
from config import ConfigManager, DESKTOP_PATH, STORAGE_PATH

logger = logging.getLogger("Pandora")

class FolderPanel(QWidget):
    def __init__(self, folder_data, config, dashboard=None):
        super().__init__()
        self.data = folder_data
        self.cfg = config
        self.dashboard = dashboard
        
        # UI State
        self.is_dragging = False
        self.is_resizing = False
        self._is_closing = False
        self.resize_edges = '' # e.g. 'tl', 'r', 'b'
        self.dsp = QPoint()
        self.wsp = QPoint()
        
        # Paging State
        self.page_idx = 0
        self.selected_apps = set()
        self.history = [] # Stack of parent folder data for nested navigation
        self.back_btn = None
        
        # Drag Edge Scroll
        self._drag_scroll_timer = QTimer(self)
        self._drag_scroll_timer.timeout.connect(self._on_drag_scroll_timeout)
        self._drag_scroll_dir = 0
        
        from PyQt6.QtCore import QVariantAnimation
        self._glow_anim = QVariantAnimation(self)
        self._glow_anim.setDuration(800)
        self._glow_anim.setStartValue(0.0)
        self._glow_anim.setEndValue(1.0)
        self._glow_anim.valueChanged.connect(lambda _: self.update())
        
        self.setWindowFlags(Qt.WindowType.WindowStaysOnBottomHint | Qt.WindowType.FramelessWindowHint | Qt.WindowType.Tool)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAcceptDrops(True)
        self.setMouseTracking(True)
        
        # Setup Grid Size
        self.grid_cols = self.data.get('grid_cols', 4)
        self.grid_rows = self.data.get('grid_rows', 3)
        
        # Start at 1x1 to prevent Windows from shifting the window if it spawns near the edge of the screen (due to default 640x480 size)
        self.resize(1, 1)
        self.update_geometry(animate=False)
        
        # Ensure position
        pos_list = self.data.get('pos', [200, 200])
        if len(pos_list) == 2:
            self.move(int(pos_list[0]), int(pos_list[1]))
            # Handle early-boot startup clamping: Windows DWM might clamp owned windows
            # to an incorrect screen resolution before display drivers fully initialize. 
            # We enforce the position repeatedly for 10 seconds to guarantee it overrides the OS.
            self._startup_enforce_ticks = 0
            self._startup_enforce_timer = QTimer(self)
            self._startup_enforce_timer.setInterval(500)
            self._startup_enforce_timer.timeout.connect(self._enforce_startup_pos)
            self._startup_enforce_timer.start()
            
        # File System Watcher for internal storage
        self.watcher = QFileSystemWatcher(self)
        target_storage = os.path.join(STORAGE_PATH, self.data.get('id', ''))
        if not os.path.exists(target_storage): 
            try:
                os.makedirs(target_storage)
            except:
                pass
        if os.path.exists(target_storage):
            self.watcher.addPath(target_storage)
        self.watcher.directoryChanged.connect(self._on_internal_storage_changed)
        
        self._sync_debounce_timer = QTimer(self)
        self._sync_debounce_timer.setSingleShot(True)
        self._sync_debounce_timer.timeout.connect(self._sync_with_disk)
            
        self.refresh()
        self._sync_with_disk()
        
    def _on_internal_storage_changed(self, path):
        # Debounce the directory change signal
        self._sync_debounce_timer.start(250)

    def _enforce_startup_pos(self):
        self._startup_enforce_ticks += 1
        if self._startup_enforce_ticks > 20: # 10 seconds
            self._startup_enforce_timer.stop()
            return
            
        if self.is_dragging or self.is_resizing:
            self._startup_enforce_timer.stop()
            return
            
        pos_list = self.data.get('pos', [200, 200])
        if len(pos_list) == 2:
            x, y = int(pos_list[0]), int(pos_list[1])
            try:
                import ctypes
                # 0x0015 = SWP_NOZORDER | SWP_NOACTIVATE | SWP_NOSIZE
                ctypes.windll.user32.SetWindowPos(int(self.winId()), 0, x, y, 0, 0, 0x0015)
            except:
                self.move(x, y)
        
    def _sync_with_disk(self):
        target_storage = os.path.join(STORAGE_PATH, self.data.get('id', ''))
        if not os.path.exists(target_storage): return
        
        current_apps = self.data.get('apps', [])
        
        # Build set of physical files
        physical_files = set()
        for f in os.listdir(target_storage):
            if f.lower() == 'desktop.ini':
                continue
            full_path = os.path.join(target_storage, f)
            if os.path.isfile(full_path):
                physical_files.add(full_path)
                
        changed = False
        new_apps = []
        
        logger.info(f"Syncing folder {self.data.get('id')}. Physical files: {physical_files}")
        
        # 1. Retain existing apps whose files still exist
        # Also, non-internal apps (like standard desktop shortcuts) remain untouched
        for app in current_apps:
            path = app.get('path', '')
            
            if 'desktop.ini' in path.lower():
                changed = True
                continue
                
            if path.startswith('pandora://folder/'):
                new_apps.append(app)
                continue
                
            norm_path = os.path.normcase(os.path.normpath(path))
            norm_target = os.path.normcase(os.path.normpath(target_storage))
            
            if norm_path.startswith(norm_target) or (os.path.normcase(os.path.normpath(STORAGE_PATH)) in norm_path and self.data.get('id', '') in norm_path):
                if path in physical_files or norm_path in [os.path.normcase(os.path.normpath(p)) for p in physical_files]:
                    new_apps.append(app)
                    match = next((p for p in physical_files if os.path.normcase(os.path.normpath(p)) == norm_path), None)
                    if match:
                        physical_files.remove(match)
                else:
                    logger.info(f"App deleted (not found on disk): {path}")
                    changed = True # App was deleted
            else:
                new_apps.append(app) # External app, keep it
                
        # 2. Add new physical files that didn't have an entry
        for path in physical_files:
            fi = QFileInfo(path)
            name = fi.completeBaseName() if fi.isFile() else os.path.basename(path)
            if not name: name = os.path.basename(path)
            new_apps.append({"name": name, "path": path})
            changed = True
            
        if changed:
            self.data['apps'] = new_apps
            if self.dashboard:
                self.dashboard.save_and_broadcast()
            self.refresh()

    def _update_watcher_path(self, old_data, new_data):
        if not hasattr(self, 'watcher'): return
        
        old_path = os.path.join(STORAGE_PATH, old_data.get('id', ''))
        new_path = os.path.join(STORAGE_PATH, new_data.get('id', ''))
        
        if os.path.exists(old_path) and old_path in self.watcher.directories():
            self.watcher.removePath(old_path)
            
        if not os.path.exists(new_path):
            try:
                os.makedirs(new_path)
            except:
                pass
                
        if os.path.exists(new_path):
            self.watcher.addPath(new_path)

    def open_nested_folder(self, folder_id):
        nested_data = next((f for f in self.cfg['folders'] if f['id'] == folder_id), None)
        if not nested_data: return
        
        # Inline navigation: push current data onto history stack and swap content
        self.history.append(self.data)
        self._update_watcher_path(self.data, nested_data)
        self.data = nested_data
        self.page_idx = 0
        self.refresh(animate=True, scroll_dx=self.width(), scroll_dy=0)

    def go_back(self):
        if not self.history:
            return
            
        parent_data = self.history.pop()
        self._update_watcher_path(self.data, parent_data)
        self.data = parent_data
        self.page_idx = 0
        self.refresh(animate=True, scroll_dx=-self.width(), scroll_dy=0)

    @property
    def root_data(self):
        """The root (top-level) folder data for this panel, even when navigated into a nested folder."""
        return self.history[0] if self.history else self.data

    @property
    def margin_y_top(self):
        return 0

    def _get_page_size(self):
        """Effective page size, accounting for the back-button slot when inside a nested folder."""
        total_slots = self.grid_cols * self.grid_rows
        if self.history and total_slots > 1:
            return total_slots - 1
        return total_slots

    def get_setting(self, key, default=None):
        return self.data.get(key, default)

    def get_inner_dimensions(self):
        gs = self.cfg.get('general_settings', {}).get('grid_size', 110)
        inner_w = self.grid_cols * gs
        inner_h = self.grid_rows * gs
        return inner_w, inner_h, gs, gs

    def update_geometry(self, animate=True):
        gs = self.cfg.get('general_settings', {}).get('grid_size', 110)
        margin_y_top = self.margin_y_top
        pad = 8
        scale = gs / 110.0
        w = self.grid_cols * gs - pad * 2
        h = self.grid_rows * gs + margin_y_top - pad * 2
        
        from PyQt6.QtCore import QSize
        if animate:
            self.anim = QPropertyAnimation(self, b"size")
            self.anim.setDuration(300)
            self.anim.setEasingCurve(QEasingCurve.Type.OutBack)
            self.anim.setEndValue(QSize(int(w), int(h)))
            self.anim.start()
        else:
            self.resize(int(w), int(h))

    def resizeEvent(self, e):
        super().resizeEvent(e)
        self._apply_rounded_mask()
        self._layout_icons()
        if hasattr(self, 'back_btn') and self.back_btn and self.back_btn.isVisible():
            self.back_btn.move(10, 10)

    def _layout_icons(self, animate=False):
        icon_cols = max(1, self.grid_cols)
        icon_rows = max(1, self.grid_rows)
        margin_y_top = self.margin_y_top
        pad = 8
        
        gs = self.cfg.get('general_settings', {}).get('grid_size', 110)
        slot_w = gs
        slot_h = gs
        
        for icon in self.findChildren(AppIcon):
            if getattr(icon, '_is_outgoing', False):
                continue
                
            if hasattr(icon, '_grid_r') and hasattr(icon, '_grid_c'):
                x = int(-pad + icon._grid_c * slot_w + (slot_w - icon.width()) / 2.0)
                y = int(margin_y_top - pad + icon._grid_r * slot_h + slot_h / 2.0 - icon.box_center_y())
                target = QPoint(x, y)
                
                if animate and icon.pos() != target and icon.isVisible():
                    # Stop any existing layout animation
                    if hasattr(icon, '_layout_anim') and icon._layout_anim is not None:
                        icon._layout_anim.stop()
                    
                    anim = QPropertyAnimation(icon, b"pos")
                    anim.setDuration(300)
                    anim.setEasingCurve(QEasingCurve.Type.OutCubic)
                    anim.setEndValue(target)
                    icon._layout_anim = anim
                    anim.start()
                else:
                    icon.move(target)

    def _apply_rounded_mask(self):
        from PyQt6.QtGui import QRegion
        path = QPainterPath()
        path.addRoundedRect(QRectF(0, 0, self.width(), self.height()), 8, 8)
        self.setMask(QRegion(path.toFillPolygon().toPolygon()))

    def refresh(self, animate=True, scroll_dx=0, scroll_dy=0):
        apps = self.data.get('apps', [])
        
        gs = self.cfg.get('general_settings', {}).get('grid_size', 110)
        margin_y_top = 0 # 35 if self.data.get('show_title', True) else 0
        
        icon_cols = self.grid_cols
        icon_rows = self.grid_rows
        total_slots = icon_cols * icon_rows
        
        # Use centralized page-size calculation
        in_nested = len(self.history) > 0
        page_size = self._get_page_size()
            
        # Adjust page_idx if it's out of bounds after resize
        max_pages = max(1, (len(apps) + page_size - 1) // page_size)
        if getattr(self, 'page_idx', 0) >= max_pages:
            self.page_idx = max_pages - 1
            
        start_idx = getattr(self, 'page_idx', 0) * page_size
        end_idx = min(start_idx + page_size, len(apps))
        
        page_apps = apps[start_idx:end_idx]
        page_app_paths = [a.get('path') for a in page_apps]
        
        # Append back button in the last grid slot when inside a nested folder
        if in_nested and total_slots > 1:
            page_apps = list(page_apps)
            # Pad with placeholders so back button lands in the last slot
            while len(page_apps) < page_size:
                page_apps.append({"is_placeholder": True})
            page_apps.append({
                "name": "Back",
                "path": "pandora://system/back",
                "is_back_btn": True
            })
            end_idx = start_idx + len(page_apps) # Override for the loop below
        
        expected_icon_size = max(24, int(32 * (gs / 110.0)))
        
        # Exclude icons that are currently animating out from a previous scroll
        existing_icons = [c for c in self.findChildren(AppIcon) if not getattr(c, '_is_outgoing', False)]
        matched_icons = set()
                
        # Update or create icons
        for local_i, app_data in enumerate(page_apps):
            if app_data.get("is_placeholder"):
                continue
                
            if 'desktop.ini' in app_data.get('path', '').lower():
                continue
            
            r = local_i // icon_cols
            c = local_i % icon_cols
            
            # Find existing
            icon = None
            for child in existing_icons:
                if child not in matched_icons and child.app_data.get('path') == app_data.get('path'):
                    icon = child
                    break
            
            # Recreate if scaled size doesn't match
            if icon and getattr(icon, '_icon_size', None) != expected_icon_size:
                icon.hide()
                icon.deleteLater()
                matched_icons.add(icon)  # prevent cleanup loop from double-processing
                icon = None
                
            if not icon:
                icon = AppIcon(app_data, self)
                icon._is_new = True
            
            matched_icons.add(icon)
            
            icon.set_grid_position(r, c)
            
            # Snap new icons to grid instantly so they don't fly from 0,0
            if getattr(icon, '_is_new', False):
                icon._is_new = False
                pad = 8
                slot_w = self.cfg.get('general_settings', {}).get('grid_size', 110)
                slot_h = slot_w
                margin_y_top = self.margin_y_top
                x = int(-pad + c * slot_w + (slot_w - icon.width()) / 2.0)
                y = int(margin_y_top - pad + r * slot_h + slot_h / 2.0 - icon.box_center_y())
                icon.move(x, y)
            
            if getattr(self, 'active_drag_app', None) != icon.app_data:
                if not icon.isVisible():
                    icon.show()
            else:
                icon.hide()
                
        active_app = getattr(self, 'active_drag_app', None)
        active_drag_path = active_app.get('path') if active_app else None
        
        # Remove icons not in current page or duplicate (with exit animation if scrolling)
        for child in existing_icons:
            if child not in matched_icons:
                if active_drag_path and child.app_data.get('path') == active_drag_path:
                    # CRITICAL: Do NOT delete the icon initiating the drag! QDrag will crash if source is destroyed.
                    child.hide()
                    continue
                    
                if (scroll_dx != 0 or scroll_dy != 0) and animate:
                    start_pos = child.pos()
                    end_pos = start_pos - QPoint(scroll_dx, scroll_dy)
                    
                    if hasattr(child, '_scroll_anim') and child._scroll_anim:
                        child._scroll_anim.stop()
                    
                    anim = QPropertyAnimation(child, b"pos")
                    anim.setDuration(350)
                    anim.setEasingCurve(QEasingCurve.Type.OutBack)
                    anim.setEndValue(end_pos)
                    anim.finished.connect(child.hide)
                    anim.finished.connect(child.deleteLater)
                    child._scroll_anim = anim
                    child._is_outgoing = True
                    anim.start()
                else:
                    child.hide()
                    child.deleteLater()
                
        # Layout icons — animate if dragging to show gap-fill effect
        is_drag_layout = getattr(self, 'active_drag_app', None) is not None
        self._layout_icons(animate=is_drag_layout)
        
        # Animate entering icons if scrolling
        if (scroll_dx != 0 or scroll_dy != 0) and animate:
            for icon in matched_icons:
                # Stop any layout animation that might conflict with the scroll animation
                if hasattr(icon, '_layout_anim') and icon._layout_anim:
                    icon._layout_anim.stop()
                    
                final_pos = icon.pos()
                start_pos = final_pos + QPoint(scroll_dx, scroll_dy)
                icon.move(start_pos)
                
                if hasattr(icon, '_scroll_anim') and icon._scroll_anim:
                    icon._scroll_anim.stop()
                    
                anim = QPropertyAnimation(icon, b"pos")
                anim.setDuration(350)
                anim.setEasingCurve(QEasingCurve.Type.OutBack)
                anim.setEndValue(final_pos)
                icon._scroll_anim = anim
                anim.start()
        
        if self.underMouse():
            self._show_hover_ui()
            
        self.update()
        self._sync_desktop_ini()

    def _sync_desktop_ini(self, folder_data=None):
        try:
            if folder_data is None:
                folder_data = self.data
            import subprocess
            target_storage = os.path.join(STORAGE_PATH, folder_data.get('id', ''))
            if not os.path.exists(target_storage): return
            
            ini_path = os.path.join(target_storage, "desktop.ini")
            target_name = folder_data.get('name', 'Folder')
            
            content = f"[.ShellClassInfo]\nLocalizedResourceName={target_name}\n"
            
            # Check if it already exists with correct content
            if os.path.exists(ini_path):
                try:
                    with open(ini_path, 'r', encoding='utf-8-sig') as f:
                        if f.read() == content:
                            return # Already synced
                except:
                    pass
                    
            # Need to update
            if os.path.exists(ini_path):
                subprocess.run(['attrib', '-s', '-h', ini_path], capture_output=True, creationflags=subprocess.CREATE_NO_WINDOW)
                
            with open(ini_path, 'w', encoding='utf-8-sig') as f:
                f.write(content)
                
            subprocess.run(['attrib', '+s', '+h', ini_path], capture_output=True, creationflags=subprocess.CREATE_NO_WINDOW)
            subprocess.run(['attrib', '+r', target_storage], capture_output=True, creationflags=subprocess.CREATE_NO_WINDOW)
            
            os.utime(target_storage, None) # Touch the directory
            
            # Force Windows Explorer to refresh the folder immediately
            try:
                import ctypes
                SHCNE_UPDATEDIR = 0x00001000
                SHCNF_PATHW = 0x0005
                ctypes.windll.shell32.SHChangeNotify(SHCNE_UPDATEDIR, SHCNF_PATHW, target_storage, None)
            except Exception:
                pass
        except Exception:
            pass

    def showEvent(self, e):
        self._enable_windows_blur()
        WinAPI.allow_drag_drop(self.winId())
        
        # Pin to the desktop layer via Z-order (no owner relationship needed).
        # The DesktopPinner handles Win+D recovery automatically.
        def _deferred_pin():
            WinAPI.pin_to_workerw(self.winId())
            self._enable_windows_blur()
            self.repaint()
            self._dwm_resize_poke()
            
        QTimer.singleShot(150, _deferred_pin)
    
    def _dwm_resize_poke(self):
        try:
            self.resize(self.width() + 1, self.height())
            self.resize(self.width() - 1, self.height())
        except: pass

    def _enable_windows_blur(self):
        try:
            import ctypes
            from ctypes import c_int, c_uint, Structure, POINTER, pointer, sizeof

            class MARGINS(Structure):
                _fields_ = [
                    ("cxLeftWidth", c_int),
                    ("cxRightWidth", c_int),
                    ("cyTopHeight", c_int),
                    ("cyBottomHeight", c_int)
                ]

            class ACCENTPOLICY(Structure):
                _fields_ = [
                    ("AccentState", c_uint),
                    ("AccentFlags", c_uint),
                    ("GradientColor", c_uint),
                    ("AnimationId", c_uint)
                ]

            class WINDOWCOMPOSITIONATTRIBDATA(Structure):
                _fields_ = [
                    ("Attribute", c_int),
                    ("Data", POINTER(ACCENTPOLICY)),
                    ("SizeOfData", c_uint)
                ]

            hwnd = int(self.winId())

            # 1. Extend the DWM frame to client area to support blur/translucency
            margins = MARGINS(-1, -1, -1, -1)
            ctypes.windll.dwmapi.DwmExtendFrameIntoClientArea(hwnd, pointer(margins))

            # 2. Apply SetWindowCompositionAttribute Acrylic policy
            blur_level = self.cfg.get('halo', {}).get('blur_level', 'High')

            policy = ACCENTPOLICY()
            policy.AccentState = 4  # ACCENT_ENABLE_ACRYLICBLURBEHIND
            
            if blur_level == 'Low':
                policy.AccentFlags = 0x1E0
                policy.GradientColor = 0x30555555
            elif blur_level == 'Medium':
                policy.AccentFlags = 0x1E0
                policy.GradientColor = 0x01000000
            else:  # High
                policy.AccentFlags = 0
                policy.GradientColor = 0x01000000
                
            policy.AnimationId = 0

            data = WINDOWCOMPOSITIONATTRIBDATA()
            data.Attribute = 19  # WCA_ACCENT_POLICY
            data.Data = pointer(policy)
            data.SizeOfData = sizeof(policy)

            # Set argtypes to generic types to bypass ctypes type checking mismatches between modules
            ctypes.windll.user32.SetWindowCompositionAttribute.argtypes = [ctypes.c_int, ctypes.c_void_p]
            ctypes.windll.user32.SetWindowCompositionAttribute(hwnd, pointer(data))
            
            # Tell Windows 11 to round the window corners (clips the acrylic too)
            # DWMWCP_ROUND = 2, DWMWA_WINDOW_CORNER_PREFERENCE = 33
            corner_pref = c_int(2)
            ctypes.windll.dwmapi.DwmSetWindowAttribute(
                hwnd, 33, ctypes.byref(corner_pref), ctypes.sizeof(corner_pref)
            )
        except Exception as e:
            logger.error(f"Failed to enable Windows blur: {e}")
            
    def get_folder_color(self):
        # Returns (base_color, alpha) representing the folder's theme color and opacity
        gen_settings = self.cfg.get('general_settings', {})
        intensity_setting = gen_settings.get('theme_intensity')
        if not intensity_setting:
            old_darkness = gen_settings.get('folder_darkness', 'Dark')
            intensity_setting = 'Subtle' if old_darkness == 'Light' else 'Balanced' if old_darkness == 'Medium' else 'Solid' if old_darkness == 'Pitch Black' else 'Intense'
        
        intensity_map = {'Subtle': 100, 'Balanced': 150, 'Intense': 180, 'Solid': 230}
        darkness = intensity_map.get(intensity_setting, 180)
        
        folder_theme = gen_settings.get('folder_theme', 'Default')
        
        if folder_theme == 'Desktop':
            accents = gen_settings.get('desktop_accents', [])
            if accents and len(accents) > 0:
                from utils import is_desktop_light_vibe
                if is_desktop_light_vibe():
                    ar, ag, ab = accents[0]
                    return QColor(min(255, int(ar*0.05 + 240)), min(255, int(ag*0.05 + 240)), min(255, int(ab*0.05 + 245))), darkness
                else:
                    r_avg = int(sum(c[0] for c in accents) / len(accents))
                    g_avg = int(sum(c[1] for c in accents) / len(accents))
                    b_avg = int(sum(c[2] for c in accents) / len(accents))
                    return QColor(r_avg, g_avg, b_avg), darkness
        elif folder_theme == 'Custom':
            custom_hex = gen_settings.get('folder_custom_color', '#161B22FF')
            try:
                hex_str = custom_hex.lstrip('#')
                if len(hex_str) == 8:
                    r = int(hex_str[0:2], 16)
                    g = int(hex_str[2:4], 16)
                    b = int(hex_str[4:6], 16)
                    return QColor(r, g, b), darkness
                else:
                    c = QColor(custom_hex)
                    return c, darkness
            except Exception:
                pass
        # Default / Fallback
        return QColor(20, 20, 20), darkness

    @pyqtProperty(float)
    def hover_progress(self):
        return getattr(self, '_hover_progress', 0.0)
        
    @hover_progress.setter
    def hover_progress(self, val):
        self._hover_progress = val
        self.update()

    def _start_hover_timer(self):
        self._hover_progress = 0.0
        self._hover_anim = QPropertyAnimation(self, b"hover_progress")
        self._hover_anim.setDuration(750)
        self._hover_anim.setStartValue(0.0)
        self._hover_anim.setEndValue(1.0)
        self._hover_anim.setEasingCurve(QEasingCurve.Type.InCubic)
        self._hover_anim.start()
        
    def _stop_hover_timer(self):
        if hasattr(self, '_hover_anim') and self._hover_anim:
            self._hover_anim.stop()
        self._hover_progress = 0.0
        self.update()

    def paintEvent(self, e):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        margin_y_top = self.margin_y_top
        panel_rect = QRectF(0, margin_y_top, self.width(), self.height() - margin_y_top)
        
        # Draw Acrylic Base (It's already transparent so DWM handles it, but we can tint it)
        path = QPainterPath()
        path.addRoundedRect(panel_rect, 8, 8)
        
        # Read new setting with fallback to old setting for backwards compatibility
        gen_settings = self.cfg.get('general_settings', {})
        intensity_setting = gen_settings.get('theme_intensity')
        if not intensity_setting:
            old_darkness = gen_settings.get('folder_darkness', 'Dark')
            intensity_setting = 'Subtle' if old_darkness == 'Light' else 'Balanced' if old_darkness == 'Medium' else 'Solid' if old_darkness == 'Pitch Black' else 'Intense'
        
        intensity_map = {'Subtle': 100, 'Balanced': 150, 'Intense': 180, 'Solid': 230}
        darkness = intensity_map.get(intensity_setting, 180)
        
        folder_theme = self.cfg.get('general_settings', {}).get('folder_theme', 'Default')
        
        self.is_light = False
        if folder_theme == 'Desktop':
            accents = self.cfg.get('general_settings', {}).get('desktop_accents', [])
            from utils import is_desktop_light_vibe
            self.is_light = is_desktop_light_vibe()
            
            if self.is_light and accents:
                ar, ag, ab = accents[0]
                # Light frosted glass tinted with accent
                bg_c = QColor(min(255, int(ar*0.05 + 240)), min(255, int(ag*0.05 + 240)), min(255, int(ab*0.05 + 245)), darkness)
                p.fillPath(path, bg_c)
            elif accents and len(accents) > 1:
                r_avg = int(sum(c[0] for c in accents) / len(accents))
                g_avg = int(sum(c[1] for c in accents) / len(accents))
                b_avg = int(sum(c[2] for c in accents) / len(accents))
                p.fillPath(path, QColor(r_avg, g_avg, b_avg, darkness))
            elif accents and len(accents) == 1:
                c = accents[0]
                p.fillPath(path, QColor(c[0], c[1], c[2], darkness))
            else:
                p.fillPath(path, QColor(20, 20, 20, darkness)) # Fallback
        elif folder_theme == 'Custom':
            custom_hex = self.cfg.get('general_settings', {}).get('folder_custom_color', '#161B22FF')
            try:
                hex_str = custom_hex.lstrip('#')
                if len(hex_str) == 8:
                    r = int(hex_str[0:2], 16)
                    g = int(hex_str[2:4], 16)
                    b = int(hex_str[4:6], 16)
                    a = int(hex_str[6:8], 16)
                    base_color = QColor(r, g, b, a)
                else:
                    base_color = QColor(custom_hex)
                    base_color.setAlpha(darkness)
                p.fillPath(path, base_color)
            except Exception:
                p.fillPath(path, QColor(20, 20, 20, darkness)) # Fallback
        else: # Default
            p.fillPath(path, QColor(20, 20, 20, darkness)) # Frosted tint
        
        # Draw pagination dots (only when multiple pages)
        apps = self.data.get('apps', [])
        page_size = self._get_page_size()
        max_pages = max(1, (len(apps) + page_size - 1) // page_size)
        
        if max_pages > 1:
            pag_style = self.cfg.get('general_settings', {}).get('pagination_style', 'Pill & Dots')
            is_vertical = self.grid_rows > self.grid_cols
            show_app_names = getattr(self, 'data', {}).get('show_app_names', False)
            move_pagination_to_top = show_app_names and not is_vertical
            
            p.setRenderHint(QPainter.RenderHint.Antialiasing)
            
            if pag_style == 'Pill & Dots':
                dot_r = 2.5
                pill_w = 12.0
                spacing = 10.0
                total_len = (max_pages - 1) * spacing + pill_w
                
                if is_vertical:
                    start_y = (self.height() - total_len) / 2.0
                    cx = self.width() - 8.0
                    curr_y = start_y
                    for i in range(max_pages):
                        if i == self.page_idx:
                            p.setPen(Qt.PenStyle.NoPen)
                            p.setBrush(QColor(36, 41, 47, 220) if self.is_light else QColor(255, 255, 255, 220))
                            p.drawRoundedRect(QRectF(cx - dot_r, curr_y, dot_r * 2, pill_w), dot_r, dot_r)
                            curr_y += pill_w + (spacing - dot_r*2)
                        else:
                            p.setPen(Qt.PenStyle.NoPen)
                            p.setBrush(QColor(36, 41, 47, 60) if self.is_light else QColor(255, 255, 255, 60))
                            p.drawEllipse(QRectF(cx - dot_r, curr_y, dot_r * 2, dot_r * 2))
                            curr_y += dot_r * 2 + (spacing - dot_r*2)
                else:
                    start_x = (self.width() - total_len) / 2.0
                    cy = 8.0 if move_pagination_to_top else self.height() - 8.0
                    curr_x = start_x
                    for i in range(max_pages):
                        if i == self.page_idx:
                            p.setPen(Qt.PenStyle.NoPen)
                            p.setBrush(QColor(36, 41, 47, 220) if self.is_light else QColor(255, 255, 255, 220))
                            p.drawRoundedRect(QRectF(curr_x, cy - dot_r, pill_w, dot_r * 2), dot_r, dot_r)
                            curr_x += pill_w + (spacing - dot_r*2)
                        else:
                            p.setPen(Qt.PenStyle.NoPen)
                            p.setBrush(QColor(36, 41, 47, 60) if self.is_light else QColor(255, 255, 255, 60))
                            p.drawEllipse(QRectF(curr_x, cy - dot_r, dot_r * 2, dot_r * 2))
                            curr_x += dot_r * 2 + (spacing - dot_r*2)
                            
            elif pag_style == 'Progress Line':
                line_thickness = 2.0
                bg_c = QColor(36, 41, 47, 40) if self.is_light else QColor(255, 255, 255, 40)
                fg_c = QColor(36, 41, 47, 220) if self.is_light else QColor(255, 255, 255, 220)
                
                if is_vertical:
                    total_len = self.height() * 0.4
                    start_y = (self.height() - total_len) / 2.0
                    cx = self.width() - 6.0
                    
                    p.setPen(Qt.PenStyle.NoPen)
                    p.setBrush(bg_c)
                    p.drawRoundedRect(QRectF(cx - line_thickness/2, start_y, line_thickness, total_len), line_thickness/2, line_thickness/2)
                    
                    seg_len = total_len / max_pages
                    active_y = start_y + self.page_idx * seg_len
                    p.setBrush(fg_c)
                    p.drawRoundedRect(QRectF(cx - line_thickness/2, active_y, line_thickness, seg_len), line_thickness/2, line_thickness/2)
                else:
                    total_len = self.width() * 0.4
                    start_x = (self.width() - total_len) / 2.0
                    cy = 6.0 if move_pagination_to_top else self.height() - 6.0
                    
                    p.setPen(Qt.PenStyle.NoPen)
                    p.setBrush(bg_c)
                    p.drawRoundedRect(QRectF(start_x, cy - line_thickness/2, total_len, line_thickness), line_thickness/2, line_thickness/2)
                    
                    seg_len = total_len / max_pages
                    active_x = start_x + self.page_idx * seg_len
                    p.setBrush(fg_c)
                    p.drawRoundedRect(QRectF(active_x, cy - line_thickness/2, seg_len, line_thickness), line_thickness/2, line_thickness/2)
                    
            elif pag_style == 'None':
                pass
            
        # Draw Title Pill
        if False: # self.data.get('show_title', True):
            title = self.data.get('name', 'Folder')
            from PyQt6.QtGui import QFont, QFontMetrics
            font = QFont("Segoe UI", 10, QFont.Weight.Medium)
            fm = QFontMetrics(font)
            tw = fm.horizontalAdvance(title)
            th = fm.height()
            
            pw = tw + 24
            ph = th + 8
            px = (self.width() - pw) / 2.0
            py = 6.0
            
            pill_path = QPainterPath()
            pill_path.addRoundedRect(QRectF(px, py, pw, ph), ph/2.0, ph/2.0)
            
            # Semi-transparent dark overlay to give it a distinct frosted pill look
            p.fillPath(pill_path, QColor(0, 0, 0, 100))
            p.setPen(QColor(255, 255, 255, 40))
            p.drawPath(pill_path)
            
            p.setFont(font)
            p.setPen(Qt.GlobalColor.white)
            p.drawText(QRectF(px, py, pw, ph), Qt.AlignmentFlag.AlignCenter, title)

        if getattr(self, 'is_hover_target', False):
            prog = getattr(self, 'hover_progress', 0.0)
            
            p.setPen(QPen(QColor(100, 200, 255, 50), 4))
            p.setBrush(Qt.BrushStyle.NoBrush)
            r = panel_rect.adjusted(2, 2, -2, -2)
            p.drawRoundedRect(r, 8, 8)
            
            if prog > 0:
                perimeter = 2 * (r.width() + r.height())
                dash_len = (perimeter / 4) * prog
                space_len = perimeter / 4
                
                pen = QPen(QColor(100, 200, 255, 255), 4)
                pen.setDashPattern([dash_len, space_len])
                p.setPen(pen)
                p.drawRoundedRect(r, 8, 8)
            
        # Draw drag scroll liquid indicators
        drag_dir = getattr(self, '_drag_scroll_dir', 0)
        if drag_dir != 0 and not getattr(self, '_drag_cooldown', False):
            try:
                is_vertical = self.grid_rows > self.grid_cols
                
                apps = self.data.get('apps', [])
                if len(apps) <= self._get_page_size():
                    pass # Don't draw indicator if there are no multiple pages
                else:
                    progress = self._glow_anim.currentValue()
                    
                    p.setPen(Qt.PenStyle.NoPen)
                    p.setBrush(QColor(150, 200, 255, int(150 * progress)))
                    
                    # Localized liquid drop
                    w, h = float(self.width()), float(self.height())
                    max_margin = 15.0 * progress
                    
                    drop_path = QPainterPath()
                    if is_vertical:
                        bump_width = min(200.0, w)
                        start_x = w/2.0 - bump_width/2.0
                        end_x = w/2.0 + bump_width/2.0
                        
                        if drag_dir == -1:
                            drop_path.moveTo(0, 0)
                            drop_path.lineTo(start_x, 0)
                            drop_path.cubicTo(start_x + bump_width/4.0, 0, w/2.0 - bump_width/4.0, max_margin, w/2.0, max_margin)
                            drop_path.cubicTo(w/2.0 + bump_width/4.0, max_margin, end_x - bump_width/4.0, 0, end_x, 0)
                            drop_path.lineTo(w, 0)
                        else:
                            drop_path.moveTo(0, h)
                            drop_path.lineTo(start_x, h)
                            drop_path.cubicTo(start_x + bump_width/4.0, h, w/2.0 - bump_width/4.0, h - max_margin, w/2.0, h - max_margin)
                            drop_path.cubicTo(w/2.0 + bump_width/4.0, h - max_margin, end_x - bump_width/4.0, h, end_x, h)
                            drop_path.lineTo(w, h)
                    else:
                        bump_width = min(200.0, h)
                        start_y = h/2.0 - bump_width/2.0
                        end_y = h/2.0 + bump_width/2.0
                        
                        if drag_dir == -1:
                            drop_path.moveTo(0, 0)
                            drop_path.lineTo(0, start_y)
                            drop_path.cubicTo(0, start_y + bump_width/4.0, max_margin, h/2.0 - bump_width/4.0, max_margin, h/2.0)
                            drop_path.cubicTo(max_margin, h/2.0 + bump_width/4.0, 0, end_y - bump_width/4.0, 0, end_y)
                            drop_path.lineTo(0, h)
                        else:
                            drop_path.moveTo(w, 0)
                            drop_path.lineTo(w, start_y)
                            drop_path.cubicTo(w, start_y + bump_width/4.0, w - max_margin, h/2.0 - bump_width/4.0, w - max_margin, h/2.0)
                            drop_path.cubicTo(w - max_margin, h/2.0 + bump_width/4.0, w, end_y - bump_width/4.0, w, end_y)
                            drop_path.lineTo(w, h)
                            
                    drop_path.closeSubpath()
                    p.drawPath(drop_path)
                    
            except Exception as e:
                import traceback
                from config import APPDATA_DIR
                import os
                with open(os.path.join(APPDATA_DIR, "liquid_crash.txt"), "w") as f:
                    traceback.print_exc(file=f)
                self._drag_scroll_dir = 0 # stop drawing to avoid infinite crash loop

    def enterEvent(self, e):
        super().enterEvent(e)
        self._cancel_hide_timer()
        if not self.is_dragging and not self.is_resizing:
            self._show_hover_ui()

    def leaveEvent(self, e):
        super().leaveEvent(e)
        from PyQt6.QtGui import QCursor
        if self.rect().contains(self.mapFromGlobal(QCursor.pos())):
            return
        self._start_hide_timer()

    def _start_hide_timer(self):
        if not hasattr(self, '_hide_timer'):
            self._hide_timer = QTimer(self)
            self._hide_timer.setSingleShot(True)
            self._hide_timer.timeout.connect(self._hide_hover_ui)
        self._hide_timer.start(100)

    def _cancel_hide_timer(self):
        if hasattr(self, '_hide_timer'):
            self._hide_timer.stop()

    def _show_hover_ui(self):
        self._show_pill()
        self._show_page_badge()

    def _hide_hover_ui(self):
        from PyQt6.QtWidgets import QApplication
        from PyQt6.QtGui import QCursor
        hovered_widget = QApplication.widgetAt(QCursor.pos())
        if hovered_widget:
            current = hovered_widget
            while current:
                if current == self:
                    return
                current = current.parentWidget()

        self._hide_pill()
        self._hide_page_badge()

    def _show_pill(self):
        if self.data.get('show_title', True) == False:
            return
            
        title = self.data.get('name', 'Folder')
        icon_path = self.data.get('pill_icon_path', '') if self.data.get('pill_mode', 'Name') == 'Icon' else ''
        
        from ui.ui_common import GlobalHoverManager
        GlobalHoverManager.instance().show_text(title, icon_path)

    def _hide_pill(self):
        title = self.data.get('name', 'Folder')
        from ui.ui_common import GlobalHoverManager
        GlobalHoverManager.instance().request_hide(title)


    def _show_page_badge(self):
        pag_style = self.cfg.get('general_settings', {}).get('pagination_style', 'Pill & Dots')
        if pag_style not in ('Floating Progress Arc', 'Floating Mini Preview'):
            self._hide_page_badge()
            return
            
        apps = self.data.get('apps', [])
        page_size = self._get_page_size()
        max_pages = max(1, (len(apps) + page_size - 1) // page_size)
        
        if max_pages <= 1:
            self._hide_page_badge()
            return

        if not hasattr(self, '_page_badge') or self._page_badge is None:
            self._page_badge = QWidget(self.parentWidget() if self.parentWidget() else None)
            self._page_badge.setWindowFlags(
                Qt.WindowType.WindowStaysOnTopHint |
                Qt.WindowType.FramelessWindowHint |
                Qt.WindowType.Tool
            )
            self._page_badge.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
            self._page_badge.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
            
            from types import MethodType
            def badge_paint(badge_self, event):
                p = QPainter(badge_self)
                p.setRenderHint(QPainter.RenderHint.Antialiasing)
                
                # Draw frosted background pill
                path = QPainterPath()
                radius = badge_self.height()/2.0 if badge_self.height() < badge_self.width() else badge_self.width()/2.0
                path.addRoundedRect(QRectF(0, 0, badge_self.width(), badge_self.height()), radius, radius)
                p.fillPath(path, QColor(0, 0, 0, 160))
                p.setPen(QPen(QColor(255, 255, 255, 40), 1.0))
                p.drawPath(path)
                
                style = getattr(badge_self, '_pag_style', '')
                max_p = getattr(badge_self, '_max_pages', 1)
                p_idx = getattr(badge_self, '_page_idx', 0)
                
                if style == 'Floating Progress Arc':
                    cx = badge_self.width() / 2.0
                    cy = badge_self.height() / 2.0
                    r = (min(badge_self.width(), badge_self.height()) - 10) / 2.0
                    
                    # Inactive track
                    p.setPen(QPen(QColor(255, 255, 255, 40), 2.5, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
                    p.drawArc(QRectF(cx - r, cy - r, r*2, r*2), 0, 360 * 16)
                    
                    # Active segment
                    p.setPen(QPen(QColor(255, 255, 255, 220), 2.5, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
                    span_angle = (360.0 / max_p)
                    # 90 degrees is top in standard math, but Qt 0 is 3 o'clock, positive is counter-clockwise
                    start_angle = 90.0 - (p_idx * span_angle) - span_angle
                    p.drawArc(QRectF(cx - r, cy - r, r*2, r*2), int(start_angle * 16), int(span_angle * 16))
                    
                elif style == 'Floating Mini Preview':
                    is_vert = getattr(badge_self, '_is_vertical', False)
                    cols = getattr(badge_self, '_grid_cols', 1)
                    rows = getattr(badge_self, '_grid_rows', 1)
                    n_apps = getattr(badge_self, '_num_apps', 1)
                    
                    dot_size = 2.5
                    spacing = 2.0
                    
                    if is_vert:
                        total_rows = max_p * rows
                        total_cols = cols
                    else:
                        total_cols = max_p * cols
                        total_rows = rows
                        
                    pw = total_cols * dot_size + (total_cols - 1) * spacing
                    ph = total_rows * dot_size + (total_rows - 1) * spacing
                    
                    start_x = (badge_self.width() - pw) / 2.0
                    start_y = (badge_self.height() - ph) / 2.0
                    
                    active_w = cols * dot_size + (cols - 1) * spacing + 4
                    active_h = rows * dot_size + (rows - 1) * spacing + 4
                    if is_vert:
                        active_x = start_x - 2
                        active_y = start_y + p_idx * (rows * (dot_size + spacing)) - 2
                    else:
                        active_x = start_x + p_idx * (cols * (dot_size + spacing)) - 2
                        active_y = start_y - 2
                        
                    p.setPen(Qt.PenStyle.NoPen)
                    p.setBrush(QColor(255, 255, 255, 40))
                    p.drawRoundedRect(QRectF(active_x, active_y, active_w, active_h), 4, 4)
                    
                    for page in range(max_p):
                        for r in range(rows):
                            for c in range(cols):
                                slot_in_page = r * cols + c
                                
                                is_occupied = False
                                in_nested = getattr(badge_self, '_in_nested', False)
                                
                                if in_nested and (rows * cols > 1) and slot_in_page == (rows * cols - 1):
                                    is_occupied = True
                                else:
                                    page_size = getattr(badge_self, '_page_size', rows * cols)
                                    if page * page_size + slot_in_page < n_apps:
                                        is_occupied = True
                                        
                                if not is_occupied:
                                    continue
                                
                                if is_vert:
                                    dot_x = start_x + c * (dot_size + spacing)
                                    dot_y = start_y + (page * rows + r) * (dot_size + spacing)
                                else:
                                    dot_x = start_x + (page * cols + c) * (dot_size + spacing)
                                    dot_y = start_y + r * (dot_size + spacing)
                                    
                                if page == p_idx:
                                    p.setBrush(QColor(255, 255, 255, 220))
                                else:
                                    p.setBrush(QColor(255, 255, 255, 80))
                                    
                                p.drawRoundedRect(QRectF(dot_x, dot_y, dot_size, dot_size), 1, 1)

            self._page_badge.paintEvent = MethodType(badge_paint, self._page_badge)
            
        is_vertical = self.grid_rows > self.grid_cols
        self._page_badge._pag_style = pag_style
        self._page_badge._is_vertical = is_vertical
        self._page_badge._page_idx = self.page_idx
        self._page_badge._max_pages = max_pages
        self._page_badge._grid_cols = self.grid_cols
        self._page_badge._grid_rows = self.grid_rows
        self._page_badge._num_apps = len(apps)
        self._page_badge._in_nested = len(self.history) > 0
        self._page_badge._page_size = self._get_page_size()
        self._page_badge.update()
        
        if pag_style == 'Floating Progress Arc':
            badge_w = 28
            badge_h = 28
        elif pag_style == 'Floating Mini Preview':
            cols = self.grid_cols
            rows = self.grid_rows
            dot_size = 2.5
            spacing = 2.0
            
            if is_vertical:
                total_rows = max_pages * rows
                total_cols = cols
            else:
                total_cols = max_pages * cols
                total_rows = rows
                
            pw = total_cols * dot_size + (total_cols - 1) * spacing
            ph = total_rows * dot_size + (total_rows - 1) * spacing
            
            badge_w = max(24, int(pw + 20))
            badge_h = max(24, int(ph + 20))
        
        target_x = self.pos().x()
        target_y = self.pos().y()
        target_w = self.width()
        target_h = self.height()
        
        if hasattr(self, 'anim') and self.anim.state() == QPropertyAnimation.State.Running:
            if self.anim.propertyName() == b"pos":
                target_x = self.anim.endValue().x()
                target_y = self.anim.endValue().y()
            elif self.anim.propertyName() == b"size":
                target_w = self.anim.endValue().width()
                target_h = self.anim.endValue().height()
                
        if hasattr(self, 'anim_pos') and self.anim_pos.state() == QPropertyAnimation.State.Running:
            target_x = self.anim_pos.endValue().x()
            target_y = self.anim_pos.endValue().y()
            
        is_vertical = self.grid_rows > self.grid_cols
        
        if is_vertical:
            px = target_x + target_w + 8
            py = target_y + (target_h - badge_h) // 2
        else:
            px = target_x + (target_w - badge_w) // 2
            py = target_y + target_h + 8
            
        # Check if title pill is pushed to the bottom (e.g. folder touches top of screen)
        pill_is_at_bottom = False
        if hasattr(self, '_pill') and self._pill is not None:
            pill_py = self._pill_anim_pos.endValue().y() if hasattr(self, '_pill_anim_pos') else self._pill.y()
            if pill_py > target_y + target_h / 2:
                pill_is_at_bottom = True
                
        if pill_is_at_bottom:
            if not is_vertical:
                py += 36  # Push it below the title pill
            
        screen = self.screen().availableGeometry()
        self._page_badge._y_anim_offset = -10
        if py < screen.top(): py = screen.top() + 4
        elif py + badge_h > screen.bottom(): py = screen.bottom() - badge_h - 4
        if px < screen.left(): px = screen.left() + 4
        if px + badge_w > screen.right(): px = screen.right() - badge_w - 4
        
        was_visible = False
        if hasattr(self, '_page_badge') and self._page_badge is not None:
            if self._page_badge.windowOpacity() > 0.0:
                was_visible = True

        if not was_visible:
            self._page_badge.setGeometry(int(px), int(py - self._page_badge._y_anim_offset), badge_w, badge_h)
            self._page_badge.show()
            self._page_badge.setWindowOpacity(0.0)
            
            self._badge_anim_pos = QPropertyAnimation(self._page_badge, b"pos")
            self._badge_anim_pos.setDuration(250)
            self._badge_anim_pos.setEasingCurve(QEasingCurve.Type.OutBack)
            self._badge_anim_pos.setEndValue(QPoint(int(px), int(py)))
            self._badge_anim_pos.start()
            
            self._badge_anim_op = QPropertyAnimation(self._page_badge, b"windowOpacity")
            self._badge_anim_op.setDuration(200)
            self._badge_anim_op.setEndValue(1.0)
            self._badge_anim_op.start()
        else:
            self._page_badge.setGeometry(int(px), int(py), badge_w, badge_h)
            self._page_badge.show()

    def _hide_page_badge(self):
        if hasattr(self, '_page_badge') and self._page_badge is not None:
            badge = self._page_badge
            self._page_badge = None
            
            self._badge_fade = QPropertyAnimation(badge, b"windowOpacity")
            self._badge_fade.setDuration(150)
            self._badge_fade.setStartValue(1.0)
            self._badge_fade.setEndValue(0.0)
            self._badge_fade.finished.connect(badge.deleteLater)
            self._badge_fade.start()
            
            self._badge_hide_pos = QPropertyAnimation(badge, b"pos")
            self._badge_hide_pos.setDuration(150)
            self._badge_hide_pos.setEasingCurve(QEasingCurve.Type.InCubic)
            y_offset = getattr(badge, '_y_anim_offset', -10)
            self._badge_hide_pos.setEndValue(QPoint(badge.x(), badge.y() + y_offset))
            self._badge_hide_pos.start()

    def hideEvent(self, e):
        super().hideEvent(e)
        self._hide_hover_ui()
        if hasattr(self, '_pill') and self._pill:
            self._pill.deleteLater()
            self._pill = None
        if hasattr(self, '_page_badge') and self._page_badge:
            self._page_badge.deleteLater()
            self._page_badge = None

    def changeEvent(self, e):
        # Fallback: prevent minimize from any other source (e.g. taskbar grouping)
        if e.type() == QEvent.Type.WindowStateChange:
            if self.windowState() & Qt.WindowState.WindowMinimized:
                self.setWindowState(self.windowState() & ~Qt.WindowState.WindowMinimized)
        super().changeEvent(e)

    def _get_resize_edges(self, pos):
        margin = 12
        edges = ''
        if pos.y() < margin: edges += 't'
        elif pos.y() > self.height() - margin: edges += 'b'
        if pos.x() < margin: edges += 'l'
        elif pos.x() > self.width() - margin: edges += 'r'
        return edges

    def mousePressEvent(self, e):
        if e.button() == Qt.MouseButton.LeftButton:
            edges = self._get_resize_edges(e.pos())
            if edges:
                self.is_resizing = True
                self.resize_edges = edges
                self.dsp = e.globalPosition().toPoint()
                self.wsp = self.pos()
                self.osz = (self.width(), self.height())
                self._target_cols = self.grid_cols
                self._target_rows = self.grid_rows
                self._target_pos = (self.wsp.x(), self.wsp.y())
                self._hide_pill()
                self._hide_page_badge()
                self._show_resize_ghost()
            else:
                self.is_dragging = True
                self._scroll_accum = 0
                self.dsp = e.globalPosition().toPoint()
                self.wsp = self.pos()
                self._hide_pill()
                self._hide_page_badge()
        elif e.button() == Qt.MouseButton.RightButton:
            self.show_context_menu(e.globalPosition().toPoint())

    def mouseReleaseEvent(self, e):
        if self.is_dragging:
            self.is_dragging = False
            
            target_folder = getattr(self, 'current_hover_target', None)
            if target_folder:
                is_ready = target_folder.hover_progress >= 1.0
                target_folder.is_hover_target = False
                target_folder._stop_hover_timer()
                self.current_hover_target = None
                
                if is_ready:
                    if target_folder.data.get('is_nested'):
                        from ui.ui_common import ToastNotification
                        toast = ToastNotification("Max nesting depth is 1. Cannot nest further.")
                        toast.show()
                    else:
                        # Always use the root folder data for nesting, not whatever nested view we're in
                        root = self.root_data
                        root['is_nested'] = True
                        target_folder.data['apps'].append({
                            "name": root.get('name', 'Folder'),
                            "path": f"pandora://folder/{root['id']}"
                        })
                        
                        self.dashboard.save_and_broadcast()
                        target_folder.refresh()
                        self._is_closing = True
                        self.deleteLater()
                        
                        if hasattr(self, 'dashboard') and self.dashboard:
                            if self in self.dashboard.app_instances:
                                self.dashboard.app_instances.remove(self)
                        return
            


            snap = self.data.get('grid_snap', self.cfg.get('general_settings', {}).get('snap_to_grid', True))
            if snap:
                gs = self.cfg.get('general_settings', {}).get('grid_size', 110)
                margin_y_top = self.margin_y_top
                
                screen = self.screen()
                scr_geom = screen.availableGeometry()
                scr_cx = scr_geom.center().x()
                scr_cy = scr_geom.center().y()
                
                visual_y = self.pos().y() + margin_y_top
                pad = 8
                
                raw_x = self.pos().x() - pad
                raw_y = visual_y - pad
                
                col = round((raw_x - scr_cx) / gs)
                row = round((raw_y - scr_cy) / gs)
                
                col, row = self._get_free_snap_pos(col, row, self.grid_cols, self.grid_rows, gs, scr_geom, scr_cx, scr_cy, margin_y_top, pad)
                
                if col is None:
                    from ui.ui_common import ToastNotification
                    toast = ToastNotification("No space left on grid. Snap-to-grid has been disabled.")
                    toast.show()
                    
                    self.data['grid_snap'] = False
                    self.data['pos'] = [self.wsp.x(), self.wsp.y()]
                    self.dashboard.save_and_broadcast()
                    return
                
                px = col * gs + scr_cx + pad
                py = row * gs + scr_cy + pad - margin_y_top
                
                if px < scr_geom.left(): px = scr_geom.left()
                if px + self.width() > scr_geom.right(): px = scr_geom.right() - self.width()
                if py < scr_geom.top(): py = scr_geom.top()
                if py + self.height() > scr_geom.bottom(): py = scr_geom.bottom() - self.height()
                
                self.anim = QPropertyAnimation(self, b"pos")
                self.anim.setDuration(200)
                self.anim.setEasingCurve(QEasingCurve.Type.OutCubic)
                self.anim.setEndValue(QPoint(int(px), int(py)))
                self.anim.start()
                
                self.data['pos'] = [int(px), int(py)]
            else:
                self.data['pos'] = [self.pos().x(), self.pos().y()]
                
            self.dashboard.save_and_broadcast()
            if self.underMouse():
                self._show_hover_ui()
                
        elif self.is_resizing:
            self.is_resizing = False
            self._hide_resize_ghost()
            
            if hasattr(self, '_target_cols'):
                self.grid_cols = self._target_cols
                self.grid_rows = self._target_rows
                self.data['grid_cols'] = self.grid_cols
                self.data['grid_rows'] = self.grid_rows
                self.data['pos'] = [self._target_pos[0], self._target_pos[1]]
                
                self.anim_pos = QPropertyAnimation(self, b"pos")
                self.anim_pos.setDuration(300)
                self.anim_pos.setEasingCurve(QEasingCurve.Type.OutBack)
                self.anim_pos.setEndValue(QPoint(self._target_pos[0], self._target_pos[1]))
                self.anim_pos.start()
                
                self.update_geometry(animate=True)
                self.refresh(animate=True)
                
            snap = self.data.get('grid_snap', self.cfg.get('general_settings', {}).get('snap_to_grid', True))
            if not snap and 'size' in self.data:
                del self.data['size']
                
            self.dashboard.save_and_broadcast()
            if self.underMouse():
                self._show_hover_ui()

    def mouseMoveEvent(self, e):
        if not self.is_resizing and not self.is_dragging:
            edges = self._get_resize_edges(e.pos())
            if edges in ('tl', 'br'):
                self.setCursor(Qt.CursorShape.SizeFDiagCursor)
            elif edges in ('tr', 'bl'):
                self.setCursor(Qt.CursorShape.SizeBDiagCursor)
            elif 'l' in edges or 'r' in edges:
                self.setCursor(Qt.CursorShape.SizeHorCursor)
            elif 't' in edges or 'b' in edges:
                self.setCursor(Qt.CursorShape.SizeVerCursor)
            else:
                self.setCursor(Qt.CursorShape.ArrowCursor)
            return

        if self.is_dragging:
            from PyQt6.QtGui import QGuiApplication
            mods = QGuiApplication.keyboardModifiers()
            is_alt = (mods & Qt.KeyboardModifier.AltModifier) == Qt.KeyboardModifier.AltModifier

            delta = e.globalPosition().toPoint() - self.dsp
            new_pos = self.wsp + delta
            
            screen = self.screen().availableGeometry()
            new_x = new_pos.x()
            new_y = new_pos.y()
            if new_x < screen.left(): new_x = screen.left()
            if new_x + self.width() > screen.right(): new_x = screen.right() - self.width()
            if new_y < screen.top(): new_y = screen.top()
            if new_y + self.height() > screen.bottom(): new_y = screen.bottom() - self.height()
            
            self.move(new_x, new_y)
            
            # Check for drop target
            target_found = None
            if hasattr(self, 'dashboard') and self.dashboard:
                for other in getattr(self.dashboard, 'app_instances', []):
                    if other == self: continue
                    try:
                        if other.geometry().contains(e.globalPosition().toPoint()):
                            target_found = other
                            break
                    except RuntimeError:
                        continue
                        
            if getattr(self, 'current_hover_target', None) != target_found:
                if getattr(self, 'current_hover_target', None):
                    try:
                        self.current_hover_target.is_hover_target = False
                        self.current_hover_target._stop_hover_timer()
                    except RuntimeError:
                        pass
                if target_found and not is_alt:
                    try:
                        target_found.is_hover_target = True
                        target_found._start_hover_timer()
                    except RuntimeError:
                        pass
                self.current_hover_target = target_found if not is_alt else None
            elif target_found and is_alt:
                try:
                    target_found.is_hover_target = False
                    target_found._stop_hover_timer()
                except RuntimeError:
                    pass
                self.current_hover_target = None
            elif target_found and not is_alt and not getattr(target_found, 'is_hover_target', False):
                try:
                    target_found.is_hover_target = True
                    target_found._start_hover_timer()
                except RuntimeError:
                    pass
                self.current_hover_target = target_found
                
            return

        if self.is_resizing:
            delta = e.globalPosition().toPoint() - self.dsp
            new_w, new_h = self.osz[0], self.osz[1]
            
            screen = self.screen().availableGeometry()
            
            if 'r' in self.resize_edges: 
                new_w += delta.x()
                if self.wsp.x() + new_w > screen.right():
                    new_w = screen.right() - self.wsp.x()
            if 'l' in self.resize_edges: 
                new_w -= delta.x()
                if self.wsp.x() + delta.x() < screen.left():
                    new_w = self.osz[0] + (self.wsp.x() - screen.left())
            if 'b' in self.resize_edges: 
                new_h += delta.y()
                if self.wsp.y() + new_h > screen.bottom():
                    new_h = screen.bottom() - self.wsp.y()
            if 't' in self.resize_edges: 
                new_h -= delta.y()
                if self.wsp.y() + delta.y() < screen.top():
                    new_h = self.osz[1] + (self.wsp.y() - screen.top())
                    
            if new_w < 100: new_w = 100
            if new_h < 100: new_h = 100
            
            gs = self.cfg.get('general_settings', {}).get('grid_size', 110)
            margin_y_top = self.margin_y_top
            
            new_cols = max(1, round(new_w / gs))
            new_rows = max(1, round((new_h - margin_y_top) / gs))
            
            if new_cols != getattr(self, '_target_cols', -1) or new_rows != getattr(self, '_target_rows', -1):
                target_w = new_cols * gs - 16
                target_h = new_rows * gs - 16
                
                target_x = self.wsp.x()
                target_y = self.wsp.y()
                
                if 'l' in self.resize_edges:
                    target_x = self.wsp.x() + (self.osz[0] - target_w)
                if 't' in self.resize_edges:
                    target_y = self.wsp.y() + (self.osz[1] - target_h)
                
                pad = 8
                scr_geom = screen
                scr_cx = scr_geom.center().x()
                scr_cy = scr_geom.center().y()
                
                snap = self.data.get('grid_snap', self.cfg.get('general_settings', {}).get('snap_to_grid', True))
                if snap:
                    target_col = round((target_x - pad - scr_cx) / gs)
                    target_row = round((target_y - pad + margin_y_top - scr_cy) / gs)
                    
                    # Check if the requested resize dimensions are actually free.
                    # If they are NOT free, we simply do not allow the resize to progress further,
                    # acting as a hard wall.
                    if not self._is_grid_rect_free(target_col, target_row, new_cols, new_rows, gs, scr_geom, scr_cx, scr_cy, margin_y_top, pad):
                        return
                    
                    target_x = target_col * gs + scr_cx + pad
                    target_y = target_row * gs + scr_cy + pad - margin_y_top
                    
                if target_x < screen.left(): target_x = screen.left()
                if target_x + target_w > screen.right(): target_x = screen.right() - target_w
                if target_y < screen.top(): target_y = screen.top()
                if target_y + target_h > screen.bottom(): target_y = screen.bottom() - target_h
                    
                self._target_cols = new_cols
                self._target_rows = new_rows
                self._target_pos = (int(target_x), int(target_y))
                
                self._update_resize_ghost(new_cols, new_rows, int(target_x), int(target_y))

    def _show_resize_ghost(self):
        """Create a ghost overlay that animates to snap targets during resize."""
        if self.dashboard and hasattr(self.dashboard, 'grid_overlay'):
            self.dashboard.grid_overlay.set_drag_state(True)
        
        if not hasattr(self, '_ghost') or self._ghost is None:
            self._ghost = QWidget(self.parentWidget() if self.parentWidget() else None)
            self._ghost.setWindowFlags(
                Qt.WindowType.WindowStaysOnTopHint |
                Qt.WindowType.FramelessWindowHint |
                Qt.WindowType.Tool
            )
            self._ghost.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
            self._ghost.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
            self._ghost.setStyleSheet("background: transparent;")
            
            from types import MethodType
            def ghost_paint(ghost_self, event):
                p = QPainter(ghost_self)
                p.setRenderHint(QPainter.RenderHint.Antialiasing)
                fill_path = QPainterPath()
                margin = self.margin_y_top
                fill_path.addRoundedRect(QRectF(0, margin, ghost_self.width(), ghost_self.height() - margin), 8, 8)
                p.fillPath(fill_path, QColor(255, 255, 255, 40))
                pen = QPen(QColor(255, 255, 255, 200), 3.0, Qt.PenStyle.DashLine)
                p.setPen(pen)
                p.drawPath(fill_path)
                
                cols = getattr(ghost_self, '_cols', 1)
                rows = getattr(ghost_self, '_rows', 1)
                from PyQt6.QtGui import QFont
                font = QFont("Segoe UI", 11, QFont.Weight.Bold)
                p.setFont(font)
                p.setPen(QColor(255, 255, 255, 180))
                p.drawText(QRectF(0, 0, ghost_self.width(), ghost_self.height()),
                           Qt.AlignmentFlag.AlignCenter, f"{cols} × {rows}")
            
            self._ghost.paintEvent = MethodType(ghost_paint, self._ghost)
        
        self._ghost.setGeometry(self.geometry())
        self._ghost._cols = self.grid_cols
        self._ghost._rows = self.grid_rows
        self._ghost.show()
        self._ghost.setWindowOpacity(1.0)

    def _update_resize_ghost(self, new_cols, new_rows, target_x=None, target_y=None):
        """Smoothly animate the ghost to the new target size."""
        if not hasattr(self, '_ghost') or self._ghost is None:
            return
            
        if getattr(self._ghost, '_cols', None) == new_cols and getattr(self._ghost, '_rows', None) == new_rows:
            if target_x is None or (target_x == self._ghost.pos().x() and target_y == self._ghost.pos().y()):
                return # already targeting this size and pos
            
        self._ghost._cols = new_cols
        self._ghost._rows = new_rows
        
        gs = self.cfg.get('general_settings', {}).get('grid_size', 110)
        pad = 8
        ghost_w = new_cols * gs - pad * 2
        ghost_h = new_rows * gs - pad * 2
        
        tx = target_x if target_x is not None else self.pos().x()
        ty = target_y if target_y is not None else self.pos().y()
        target_rect = QRect(tx, ty, int(ghost_w), int(ghost_h))
        
        self._ghost_anim = QPropertyAnimation(self._ghost, b"geometry")
        self._ghost_anim.setDuration(150)
        self._ghost_anim.setEasingCurve(QEasingCurve.Type.OutCubic)
        self._ghost_anim.setEndValue(target_rect)
        self._ghost_anim.valueChanged.connect(self._ghost.update)
        self._ghost_anim.start()

    def _hide_resize_ghost(self):
        """Fade out and destroy the ghost overlay."""
        if self.dashboard and hasattr(self.dashboard, 'grid_overlay'):
            self.dashboard.grid_overlay.set_drag_state(False)
            
        if hasattr(self, '_ghost') and self._ghost is not None:
            ghost = self._ghost
            self._ghost = None
            self._ghost_fade = QPropertyAnimation(ghost, b"windowOpacity")
            self._ghost_fade.setDuration(150)
            self._ghost_fade.setStartValue(1.0)
            self._ghost_fade.setEndValue(0.0)
            self._ghost_fade.finished.connect(ghost.deleteLater)
            self._ghost_fade.start()

    def change_page(self, direction):
        apps = self.data.get('apps', [])
        page_size = self._get_page_size()
        
        if len(apps) <= page_size: return
        
        max_pages = max(1, (len(apps) + page_size - 1) // page_size)
        new_page = self.page_idx + direction
        
        # Loop scroll
        if new_page < 0: 
            new_page = max_pages - 1
        elif new_page >= max_pages: 
            new_page = 0
        
        if new_page != self.page_idx:
            self.page_idx = new_page
            
            dx, dy = 0, 0
            if self.grid_rows > self.grid_cols:
                dy = direction * self.height()
            else:
                dx = direction * self.width()
                
            self.refresh(animate=True, scroll_dx=dx, scroll_dy=dy)

    def _on_drag_scroll_timeout(self):
        if self._drag_scroll_dir != 0:
            self.change_page(self._drag_scroll_dir)
            self._drag_scroll_timer.stop()
            self._glow_anim.stop()
            self._drag_cooldown = True
            QTimer.singleShot(350, self._end_drag_cooldown)
            
    def _end_drag_cooldown(self):
        self._drag_cooldown = False
        if getattr(self, '_drag_scroll_dir', 0) != 0:
            self._drag_scroll_timer.start(800)
            self._glow_anim.start()

    def wheelEvent(self, e):
        # Ignore wheel events during drag operations
        if getattr(self, 'active_drag_app', None) is not None:
            return
            
        apps = self.data.get('apps', [])
        
        page_size = self._get_page_size()
        
        if len(apps) <= page_size: return
        
        current_time = time.time()
        last_time = getattr(self, '_last_scroll_time', 0)
        
        if current_time - last_time < 0.25:
            # Drop events that are too close together
            return
            
        delta = e.angleDelta().y()
        self._scroll_accum = getattr(self, '_scroll_accum', 0) + delta
        
        # Accumulate deltas for trackpads, low threshold for responsiveness
        if abs(self._scroll_accum) < 30: 
            return
            
        direction = 1 if self._scroll_accum < 0 else -1
        
        # Reset accumulator and update throttle timer
        self._scroll_accum = 0
        self._last_scroll_time = current_time
        
        self.change_page(direction)

    def _is_invalid_nested_drop(self, e):
        """Enforces a maximum nesting depth of 1: prevents dropping a folder into a nested folder."""
        if not self.data.get('is_nested'):
            return False
            
        if e.mimeData().hasFormat("application/x-pandora-app"):
            try:
                import json
                text = e.mimeData().text()
                if text:
                    apps = json.loads(text)
                    if isinstance(apps, dict):
                        apps = [apps]
                    for app in apps:
                        if app.get('path', '').startswith('pandora://folder/'):
                            return True
            except:
                pass
                
        return False

    def dragEnterEvent(self, e):
        if self._is_invalid_nested_drop(e):
            e.ignore()
            return
        if e.mimeData().hasUrls() or e.mimeData().hasFormat("application/x-pandora-app"):
            e.setDropAction(Qt.DropAction.MoveAction)
            e.accept()

    def dragMoveEvent(self, e):
        if self._is_invalid_nested_drop(e):
            e.ignore()
            return
        e.setDropAction(Qt.DropAction.MoveAction)
        e.accept()
        
        # Handle Edge Auto-Pagination
        # Handle Edge Auto-Pagination based on orientation
        is_vertical = self.grid_rows > self.grid_cols
        margin = 40
        pos = e.position().toPoint()
        
        new_scroll_dir = 0
        if is_vertical:
            if pos.y() < self.margin_y_top + margin:
                new_scroll_dir = -1
            elif pos.y() > self.height() - margin:
                new_scroll_dir = 1
        else:
            if pos.x() < margin:
                new_scroll_dir = -1
            elif pos.x() > self.width() - margin:
                new_scroll_dir = 1
                
        if new_scroll_dir != 0:
            self._drag_scroll_dir = new_scroll_dir
            if getattr(self, '_last_drag_scroll_dir', None) != self._drag_scroll_dir:
                self._last_drag_scroll_dir = self._drag_scroll_dir
                if not getattr(self, '_drag_cooldown', False):
                    self._glow_anim.start()
                
            self.update()
                
            if not getattr(self, '_drag_cooldown', False):
                if not self._drag_scroll_timer.isActive():
                    self._drag_scroll_timer.start(800)
        else:
            self._drag_scroll_timer.stop()
            self._drag_scroll_dir = 0
            
            if getattr(self, '_last_drag_scroll_dir', None) != self._drag_scroll_dir:
                self._last_drag_scroll_dir = self._drag_scroll_dir
                self._glow_anim.stop()
                self.update()
        
        # Only do live reorder preview for internal Pandora app drags
        if not e.mimeData().hasFormat("application/x-pandora-app"):
            return
            
        sid = e.mimeData().data("application/x-pandora-app").data().decode().strip()
        if sid != self.data.get('id', ''):
            # Cross-folder drag — no live preview needed
            return
        
        target_idx = self._pos_to_grid_idx(e.position().toPoint())
        
        # If target hasn't changed, don't re-layout
        if getattr(self, '_drag_preview_idx', -1) == target_idx:
            return
        self._drag_preview_idx = target_idx
        
        # Build a temporary reordered apps list for preview
        drag_app = getattr(self, 'active_drag_app', None)
        if drag_app is None:
            return
            
        apps = self.data.get('apps', [])
        page_size = self._get_page_size()
        start_idx = self.page_idx * page_size
        
        # Build page apps without the dragged app
        page_apps = [a for a in apps[start_idx:start_idx + page_size] if a.get('path') != drag_app.get('path')]
        
        # Clamp insertion index
        insert_idx = max(0, min(target_idx, len(page_apps)))
        
        # Insert a placeholder at the target position to shift others
        page_apps.insert(insert_idx, None)  # None = gap for dragged icon
        
        # Re-assign grid positions to visible icons based on this preview order
        icon_cols = max(1, self.grid_cols)
        existing_icons = [c for c in self.findChildren(AppIcon) if not getattr(c, '_is_outgoing', False)]
        
        for slot_i, app_data in enumerate(page_apps):
            if app_data is None:
                continue  # Skip the gap
                
            # If item is pushed off the current page's valid slots, push it off-screen
            if slot_i >= page_size:
                r = self.grid_rows
                c = 0
            else:
                r = slot_i // icon_cols
                c = slot_i % icon_cols
                
            # print(f"[DRAG] slot={slot_i}, path={app_data.get('path')}, r={r}, c={c}")
            
            for icon in existing_icons:
                if icon.app_data.get('path') == app_data.get('path') and icon.isVisible():
                    icon.set_grid_position(r, c)
                    break
        
        self._layout_icons(animate=True)

    def dragLeaveEvent(self, e):
        self._drag_scroll_timer.stop()
        if hasattr(self, '_glow_anim_timer'):
            self._glow_anim_timer.stop()
        self._drag_scroll_dir = 0
        self._last_drag_scroll_dir = 0
        self.update()
        
        # Reset preview state when drag leaves the folder
        if hasattr(self, '_drag_preview_idx'):
            del self._drag_preview_idx
        # Restore original layout
        drag_app = getattr(self, 'active_drag_app', None)
        if drag_app:
            self.refresh()

    def _pos_to_grid_idx(self, pos):
        """Convert a widget-local position to a linear grid index on the current page."""
        gs = self.cfg.get('general_settings', {}).get('grid_size', 110)
        pad = 8
        
        col = int((pos.x() + pad) / gs)
        row = int((pos.y() + pad) / gs)
        
        col = max(0, min(col, self.grid_cols - 1))
        row = max(0, min(row, self.grid_rows - 1))
        
        return row * self.grid_cols + col

    def dropEvent(self, e):
        self._drag_scroll_timer.stop()
        if hasattr(self, '_glow_anim_timer'):
            self._glow_anim_timer.stop()
        self._drag_scroll_dir = 0
        self._last_drag_scroll_dir = 0
        self.update()
        
        # Allow apps to be dropped in
        if e.mimeData().hasFormat("application/x-pandora-app"):
            # Calculate drop index from cursor position
            target_idx = self._pos_to_grid_idx(e.position().toPoint())
            
            # Adjust for page offset
            page_offset = self.page_idx * self._get_page_size()
            absolute_idx = page_offset + target_idx
            
            sid = e.mimeData().data("application/x-pandora-app").data().decode().strip()
            is_same_folder = (sid == self.data.get('id', ''))
            
            success, _ = handle_app_drop(self.cfg, self.data, e.mimeData(), e.source(), absolute_idx, self.dashboard)
            if success:
                # Clean up preview state
                if hasattr(self, '_drag_preview_idx'):
                    del self._drag_preview_idx
                self.dashboard.save_and_broadcast()
                self.refresh()
                e.setDropAction(Qt.DropAction.MoveAction)
                e.accept()
            return

        new_apps = []
        target_storage = os.path.join(STORAGE_PATH, self.data['id'])
        if not os.path.exists(target_storage): os.makedirs(target_storage)
        
        for url in e.mimeData().urls():
            s = url.toLocalFile()
            if os.path.exists(s):
                bn = os.path.basename(s)
                d = os.path.join(target_storage, bn)
                
                if os.path.exists(d):
                    name_part, ext_part = os.path.splitext(bn)
                    counter = 1
                    while os.path.exists(os.path.join(target_storage, f"{name_part} ({counter}){ext_part}")):
                        counter += 1
                    d = os.path.join(target_storage, f"{name_part} ({counter}){ext_part}")

                try:
                    shutil.move(s, d)
                    fi = QFileInfo(d)
                    name = fi.completeBaseName() if fi.isFile() else os.path.basename(d)
                    if not name: name = os.path.basename(d)
                    new_apps.append({"name": name, "path": d})
                except Exception as ex:
                    logger.error(f"FolderPanel drop error: {ex}")
        
        if new_apps:
            self.data['apps'].extend(new_apps)
            seen = set(); unique = []
            for a in self.data['apps']:
                if a['path'] not in seen:
                    unique.append(a); seen.add(a['path'])
            self.data['apps'] = unique
            self.dashboard.save_and_broadcast()
            self.refresh()

    def show_context_menu(self, pos):
        from PyQt6.QtGui import QAction
        if not hasattr(self, '_context_menu'):
            self._context_menu = AnimatedMenu(self)
        m = self._context_menu
        m.clear()
        
        if self.data.get('is_nested'):
            b = QAction("Go Back", self); b.triggered.connect(self.go_back); m.addAction(b)
            m.addSeparator()
            
        if not self.data.get('is_nested'):
            n = QAction("Create Nested Folder", self); n.triggered.connect(self.create_nested_folder); m.addAction(n)
        
        s = QAction("Toggle Snap to Grid", self); s.triggered.connect(self.toggle_snap_to_grid); m.addAction(s)
        rn = QAction("Rename Folder", self); rn.triggered.connect(self.rename_folder); m.addAction(rn)
        r = QAction("Remove Folder", self); r.triggered.connect(self.remove_self); m.addAction(r)
        
        m.exec(pos)
        # After menu closes, check if mouse left the folder
        from PyQt6.QtGui import QCursor
        if not self.rect().contains(self.mapFromGlobal(QCursor.pos())):
            self._hide_hover_ui()

    def rename_folder(self):
        from ui.ui_common import IslandRenameDialog
        if hasattr(self, '_rename_dialog') and self._rename_dialog:
            try:
                self._rename_dialog.close()
                self._rename_dialog.deleteLater()
            except:
                pass
            self._rename_dialog = None
            
        old_name = self.data.get('name', 'Folder')
        
        def save_name(new_name):
            if new_name and new_name.strip() != old_name:
                self.data['name'] = new_name.strip()
                self.dashboard.save_and_broadcast()
                self.refresh()
                
        self._rename_dialog = IslandRenameDialog(initial_text=old_name, on_save=save_name, parent=None)
        self._rename_dialog.show()

    def toggle_snap_to_grid(self):

        current_snap = self.data.get('grid_snap', self.cfg.get('general_settings', {}).get('snap_to_grid', True))
        
        if not current_snap:
            gs = self.cfg.get('general_settings', {}).get('grid_size', 110)
            screen = self.screen()
            scr_geom = screen.availableGeometry()
            scr_cx = scr_geom.center().x()
            scr_cy = scr_geom.center().y()
            margin_y_top = self.margin_y_top
            pad = 8
            
            col = round((self.pos().x() - pad - scr_cx) / gs)
            row = round((self.pos().y() - pad - scr_cy) / gs)
            
            col, row = self._get_free_snap_pos(col, row, self.grid_cols, self.grid_rows, gs, scr_geom, scr_cx, scr_cy, margin_y_top, pad)
            
            if col is None:
                from ui.ui_common import ToastNotification
                toast = ToastNotification("Cannot enable Snap-to-Grid. No space left on the grid.")
                toast.show()
                return
            
            self.data['grid_snap'] = True
            px = col * gs + scr_cx + pad
            py = row * gs + scr_cy + pad - margin_y_top
            
            self.anim = QPropertyAnimation(self, b"pos")
            self.anim.setDuration(300)
            self.anim.setEasingCurve(QEasingCurve.Type.OutBack)
            self.anim.setEndValue(QPoint(int(px), int(py)))
            self.anim.start()
            self.data['pos'] = [px, py]
        else:
            self.data['grid_snap'] = False
            
        self.dashboard.save_and_broadcast()

    def create_nested_folder(self):
        import uuid
        new_id = f"folder_{uuid.uuid4().hex[:8]}"
        
        greek_names = ["Alpha", "Beta", "Gamma", "Delta", "Epsilon", "Zeta", "Eta", "Theta", 
                       "Iota", "Kappa", "Lambda", "Mu", "Nu", "Xi", "Omicron", "Pi", 
                       "Rho", "Sigma", "Tau", "Upsilon", "Phi", "Chi", "Psi", "Omega"]
        existing_names = {f.get('name', '') for f in self.cfg.get('folders', [])}
        folder_name = next((n for n in greek_names if n not in existing_names), "New Folder")
        
        # Create folder entry in config
        new_folder = {
            "id": new_id,
            "name": folder_name,
            "pos": self.data.get('pos', [200, 200]),
            "apps": [],
            "color": "#ffffff",
            "template_type": "grid",
            "template_name": "Default",
            "show_title": True,
            "grid_cols": 2,
            "grid_rows": 2,
            "is_nested": True
        }
        self.cfg['folders'].append(new_folder)
        
        # Add entry to current folder
        self.data['apps'].append({
            "name": folder_name,
            "path": f"pandora://folder/{new_id}"
        })
        
        # Create physical directory and desktop.ini immediately
        target_storage = os.path.join(STORAGE_PATH, new_id)
        if not os.path.exists(target_storage):
            try:
                os.makedirs(target_storage)
            except:
                pass
        self._sync_desktop_ini(folder_data=new_folder)
        
        self.dashboard.save_and_broadcast()
        self.refresh()

    def remove_self(self):
        regular_apps = [app for app in self.data.get('apps', []) if not app['path'].startswith('pandora://folder/')]
        if regular_apps:
            from ui.ui_common import IslandConfirmDialog
            def handle_choice(choice):
                if choice == "Cancel":
                    return
                elif choice == "Spill out":
                    self.execute_remove(spill_regular=True)
                elif choice == "Delete them":
                    self.execute_remove(spill_regular=False)
                    
            self._confirm_dialog = IslandConfirmDialog(
                message=f"This folder contains {len(regular_apps)} items.",
                options=[
                    ("Cancel", "rgba(100, 100, 100, 150)"),
                    ("Spill out", "rgba(38, 192, 211, 150)"),
                    ("Delete them", "rgba(220, 50, 50, 150)")
                ],
                on_choice=handle_choice,
                parent=None
            )
            self._confirm_dialog.show()
        else:
            self.execute_remove(spill_regular=False)

    def execute_remove(self, spill_regular=False):
        regular_apps = [app for app in self.data.get('apps', []) if not app['path'].startswith('pandora://folder/')]
        # Immediately hide to avoid Z-order or DWM composition conflicts (only if we're deleting the root panel itself)
        if self.data == self.root_data:
            self.hide()
        # Un-nest any nested folders inside this folder
        for app in self.data.get('apps', []):
            if app['path'].startswith('pandora://folder/'):
                fid = app['path'].replace('pandora://folder/', '')
                target_folder = next((f for f in self.cfg['folders'] if f['id'] == fid), None)
                if target_folder:
                    target_folder['is_nested'] = False
                    target_folder['pos'] = [self.pos().x(), self.pos().y()]
                    if hasattr(self, 'dashboard') and self.dashboard:
                        panel = self.__class__(target_folder, self.cfg, self.dashboard)
                        self.dashboard.app_instances.append(panel)
                        snap = target_folder.get('grid_snap', self.cfg.get('general_settings', {}).get('snap_to_grid', True))
                        if snap:
                            gs = self.cfg.get('general_settings', {}).get('grid_size', 110)
                            screen = self.screen()  # Use self's screen since self is currently visible
                            scr_geom = screen.availableGeometry()
                            scr_cx = scr_geom.center().x()
                            scr_cy = scr_geom.center().y()
                            margin_y_top = panel.margin_y_top
                            pad = 8
                            col = round((panel.pos().x() - pad - scr_cx) / gs)
                            row = round((panel.pos().y() - pad - scr_cy) / gs)
                            col, row = panel._get_free_snap_pos(col, row, panel.grid_cols, panel.grid_rows, gs, scr_geom, scr_cx, scr_cy, margin_y_top, pad)
                            if col is None:
                                from ui.ui_common import ToastNotification
                                toast = ToastNotification("No space left on grid. Snap-to-grid has been disabled.")
                                toast.show()
                                target_folder['grid_snap'] = False
                            else:
                                px = int(col * gs + scr_cx + pad)
                                py = int(row * gs + scr_cy + pad - margin_y_top)
                                target_folder['pos'] = [px, py]
                                panel.move(px, py)
                                
                        panel.show()
        
        if spill_regular and regular_apps:
            self.move_to_desktop(regular_apps)
            
        from config import STORAGE_PATH
        import os
        import shutil
        import logging
        logger = logging.getLogger(__name__)
        target_storage = os.path.join(STORAGE_PATH, self.data['id'])
        if os.path.exists(target_storage):
            try:
                if not spill_regular:
                    import send2trash
                    send2trash.send2trash(target_storage)
                else:
                    shutil.rmtree(target_storage)
            except Exception as e:
                logger.error(f"Failed to remove folder storage {target_storage}: {e}")
                try:
                    shutil.rmtree(target_storage)
                except: pass
            
        self.cfg['folders'] = [f for f in self.cfg['folders'] if f['id'] != self.data['id']]
        
        # Remove self from parent folder's apps if nested
        parent_f = next((f for f in self.cfg.get('folders', []) for app in f.get('apps', []) if app.get('path') == f"pandora://folder/{self.data['id']}"), None)
        if parent_f:
            parent_f['apps'] = [app for app in parent_f.get('apps', []) if app.get('path') != f"pandora://folder/{self.data['id']}"]
            
        if self.data != self.root_data:
            self.dashboard.save_and_broadcast()
            self.go_back()
        else:
            if hasattr(self, 'dashboard') and self in getattr(self.dashboard, 'app_instances', []):
                self.dashboard.app_instances.remove(self)
            self._is_closing = True
            self.dashboard.save_and_broadcast()
            self.deleteLater()
    def move_to_desktop(self, ad_or_list):
        if not isinstance(ad_or_list, list):
            ad_or_list = [ad_or_list]
            
        from PyQt6.QtGui import QCursor
        cursor_pos = QCursor.pos()
            
        for ad in ad_or_list:
            if ad['path'].startswith('pandora://folder/'):
                fid = ad['path'].replace('pandora://folder/', '')
                target_folder = next((f for f in self.cfg['folders'] if f['id'] == fid), None)
                if target_folder:
                    target_folder['is_nested'] = False
                    target_folder['pos'] = [cursor_pos.x() - 50, cursor_pos.y() - 50]
                    if hasattr(self, 'dashboard') and self.dashboard:
                        from PyQt6.QtCore import QTimer
                        initial_px = cursor_pos.x() - 50
                        initial_py = cursor_pos.y() - 50
                        
                        def spawn_new_panel(tgt=target_folder, cfg=self.cfg, dash=self.dashboard, px=initial_px, py=initial_py):
                            panel = self.__class__(tgt, cfg, dash)
                            dash.app_instances.append(panel)
                            
                            snap = tgt.get('grid_snap', cfg.get('general_settings', {}).get('snap_to_grid', True))
                            if snap:
                                gs = cfg.get('general_settings', {}).get('grid_size', 110)
                                screen = self.screen()
                                scr_geom = screen.availableGeometry()
                                scr_cx = scr_geom.center().x()
                                scr_cy = scr_geom.center().y()
                                margin_y_top = panel.margin_y_top
                                pad = 8
                                col = round((panel.pos().x() - pad - scr_cx) / gs)
                                row = round((panel.pos().y() - pad - scr_cy) / gs)
                                col, row = panel._get_free_snap_pos(col, row, panel.grid_cols, panel.grid_rows, gs, scr_geom, scr_cx, scr_cy, margin_y_top, pad)
                                if col is None:
                                    from ui.ui_common import ToastNotification
                                    toast = ToastNotification("No space left on grid. Snap-to-grid has been disabled.")
                                    toast.show()
                                    tgt['grid_snap'] = False
                                else:
                                    final_px = int(col * gs + scr_cx + pad)
                                    final_py = int(row * gs + scr_cy + pad - margin_y_top)
                                    tgt['pos'] = [final_px, final_py]
                                    panel.move(final_px, final_py)
                            else:
                                panel.move(px, py)
                                    
                            panel.show()
                            panel.raise_()
                            panel.activateWindow()
                            panel.refresh()
                            panel.repaint()
                            self.dashboard.save_and_broadcast()
                            
                            # Removed extra resize poke here, handled natively in showEvent
                            
                        QTimer.singleShot(10, spawn_new_panel)
            else:
                try:
                    bn = os.path.basename(ad['path'])
                    dest = os.path.join(DESKTOP_PATH, bn)
                    if os.path.exists(ad['path']):
                        dest_norm = os.path.normcase(os.path.abspath(dest))
                        src_norm = os.path.normcase(os.path.abspath(ad['path']))
                        if os.path.exists(dest) and dest_norm != src_norm:
                            # Auto-rename if collision occurs on desktop
                            name_part, ext_part = os.path.splitext(bn)
                            counter = 1
                            while os.path.exists(os.path.join(DESKTOP_PATH, f"{name_part} ({counter}){ext_part}")):
                                counter += 1
                            dest = os.path.join(DESKTOP_PATH, f"{name_part} ({counter}){ext_part}")
                        
                        if os.path.normcase(os.path.abspath(dest)) != src_norm:
                            shutil.move(ad['path'], dest)
                except Exception as ex:
                    logger.error(f"Error moving file to desktop: {ex}")
            self.data['apps'] = [a for a in self.data['apps'] if a['path'] != ad['path']]
            
        self.selected_apps.clear()
        
        dummy_desk = os.path.join(DESKTOP_PATH, 'Pandora_Nested_Folder.tmp')
        if os.path.exists(dummy_desk):
            try:
                os.remove(dummy_desk)
            except: pass
            
        self.dashboard.save_and_broadcast()
        self.refresh()

    def _get_occupied_grid_rects(self, gs, scr_cx, scr_cy, margin_y_top, pad):
        rects = []
        if not self.dashboard: return rects
        for other in getattr(self.dashboard, 'app_instances', []):
            if other == self: continue
            snap = other.data.get('grid_snap', self.cfg.get('general_settings', {}).get('snap_to_grid', True))
            if snap:
                try:
                    ox = other.pos().x() - pad
                    oy = other.pos().y() - pad + margin_y_top
                    c = round((ox - scr_cx) / gs)
                    r = round((oy - scr_cy) / gs)
                    rects.append((c, r, other.grid_cols, other.grid_rows))
                except RuntimeError:
                    continue
        return rects

    def _is_grid_rect_free(self, c, r, target_cols, target_rows, gs, scr_geom, scr_cx, scr_cy, margin_y_top, pad, strict_bounds=False):
        occupied = self._get_occupied_grid_rects(gs, scr_cx, scr_cy, margin_y_top, pad)
        px = c * gs + scr_cx + pad
        py = r * gs + scr_cy + pad - margin_y_top
        
        target_w = target_cols * gs - 16
        target_h = target_rows * gs - 16
        
        m_t, m_b, m_l, m_r = 0, 0, 0, 0
        if strict_bounds:
            gen = self.cfg.get('general_settings', {})
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

    def _get_free_snap_pos(self, original_col, original_row, target_cols, target_rows, gs, scr_geom, scr_cx, scr_cy, margin_y_top, pad, strict_bounds=False):
        def is_free(c, r):
            return self._is_grid_rect_free(c, r, target_cols, target_rows, gs, scr_geom, scr_cx, scr_cy, margin_y_top, pad, strict_bounds)

        if is_free(original_col, original_row):
            return original_col, original_row
            
        for radius in range(1, 20):
            points = []
            for dc in range(-radius, radius + 1):
                for dr in range(-radius, radius + 1):
                    if max(abs(dc), abs(dr)) == radius:
                        points.append((original_col + dc, original_row + dr))
            
            points.sort(key=lambda p: (p[0] - original_col)**2 + (p[1] - original_row)**2)
            
            for pc, pr in points:
                if is_free(pc, pr):
                    return pc, pr
                    
        return None, None