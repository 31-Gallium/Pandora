import os
import json
from PyQt6.QtWidgets import QWidget, QApplication
from PyQt6.QtCore import QTimer, Qt, QPropertyAnimation, QPoint, QMimeData, QUrl, QRect, QRectF, pyqtProperty, QEasingCurve
from PyQt6.QtGui import QPainter, QColor, QCursor, QDrag, QAction, QPixmap, QPen, QPainterPath

from utils import IconExtractor, VectorIcon
from ui.ui_common import AnimatedMenu

def elide_text_two_lines(text, max_width, fm):
    # If the whole text fits in one line, return [text]
    if fm.horizontalAdvance(text) <= max_width:
        return [text]
    
    # Try splitting by words first
    words = text.split(' ')
    line1 = ""
    line2 = ""
    
    i = 0
    # Add words to line 1 as long as they fit
    while i < len(words):
        test_line = (line1 + " " + words[i]).strip()
        if fm.horizontalAdvance(test_line) <= max_width:
            line1 = test_line
            i += 1
        else:
            break
            
    # If line 1 is empty (e.g. the first word itself is too long), 
    # we have to split the first word character-by-character
    if not line1:
        first_word = words[0]
        # Find how many characters of the first word fit in line 1
        for char_idx in range(len(first_word), 0, -1):
            test_line = first_word[:char_idx]
            if fm.horizontalAdvance(test_line) <= max_width:
                line1 = test_line
                remaining_text = first_word[char_idx:] + (" " + " ".join(words[1:]) if len(words) > 1 else "")
                line2 = fm.elidedText(remaining_text.strip(), Qt.TextElideMode.ElideRight, max_width)
                return [line1, line2]
    
    # If we have remaining words, put them in line 2 and elide line 2
    if i < len(words):
        remaining_text = " ".join(words[i:])
        line2 = fm.elidedText(remaining_text, Qt.TextElideMode.ElideRight, max_width)
        return [line1, line2]
    
    return [line1]

class AppIcon(QWidget):
    _icon_load_queue = []
    _icon_load_timer = None
    
    @classmethod
    def _process_icon_queue(cls):
        if not cls._icon_load_queue:
            cls._icon_load_timer = None
            return
            
        instance, fetch_func = cls._icon_load_queue.pop(0)
        try:
            fetch_func()
        except RuntimeError:
            pass
        except Exception as e:
            print("Icon load error:", e)
            
        if cls._icon_load_queue:
            QTimer.singleShot(10, cls._process_icon_queue)
        else:
            cls._icon_load_timer = None

    @classmethod
    def queue_icon_load(cls, instance, fetch_func):
        cls._icon_load_queue.append((instance, fetch_func))
        if cls._icon_load_timer is None:
            cls._icon_load_timer = True
            QTimer.singleShot(10, cls._process_icon_queue)
    def __init__(self, data, parent_view, pop_in=False, font_size=10, icon_size=48):
        super().__init__(parent_view)
        self.app_data = data
        self.parent_view = parent_view

        gs = 110
        if hasattr(parent_view, 'cfg'):
            gs = parent_view.cfg.get('general_settings', {}).get('grid_size', 110)
            
        scale = gs / 110.0
        icon_size = max(24, int(28 * scale))
        font_size = max(9, int(9.5 * scale))
        
        show_app_names = getattr(self.parent_view, 'data', getattr(self.parent_view, 'folder_data', {})).get('show_app_names', False)
        
        box_size = icon_size + int(12 * scale)
        widget_w = box_size
        
        start_y = int(0.2 * box_size)
        self._box_center_y = start_y + box_size / 2.0
        
        line_height = int(font_size * 1.25)
        if show_app_names:
            widget_h = int(box_size * 1.4) + (2 * line_height) + int(4 * scale)
        else:
            widget_h = int(box_size * 1.4)
            
        logical_w = max(widget_w, int(54 * scale))
        
        # Expand physical widget bounds to allow hover scaling without clipping
        self.setFixedSize(int(logical_w * 1.4), widget_h)
        self.setMouseTracking(True)
        self._hover = False
        self.is_internal = False
        self._hover_scale = 1.0
        self._text_opacity = 1.0
        self._icon_size = icon_size
        self._scale = scale
        self._box_size = box_size

        if data.get('is_placeholder'):
            pix = QPixmap(icon_size, icon_size)
            pix.fill(Qt.GlobalColor.transparent)
            pp = QPainter(pix)
            pp.setRenderHint(QPainter.RenderHint.Antialiasing)
            pp.setBrush(QColor(data.get('color', "#ffffff")))
            pp.setPen(Qt.PenStyle.NoPen)
            pp.drawRoundedRect(QRectF(0, 0, icon_size, icon_size), 8, 8)
            pp.end()
            self._icon_pixmap = pix
        elif data.get('path', '').startswith('pandora://folder/'):
            self._icon_pixmap = QPixmap()
            def load_folder_icon():
                folder_id = data['path'].replace('pandora://folder/', '')
                target_folder = next((f for f in getattr(self.parent_view, 'cfg', {}).get('folders', []) if f['id'] == folder_id), None)
                
                pix = QPixmap(icon_size, icon_size)
                pix.fill(Qt.GlobalColor.transparent)
                pp = QPainter(pix)
                pp.setRenderHint(QPainter.RenderHint.Antialiasing)
                
                # Draw rounded background
                pp.setBrush(QColor(0, 0, 0, 100))
                pp.setPen(QPen(QColor(255, 255, 255, 30), 1))
                pp.drawRoundedRect(QRectF(0, 0, icon_size, icon_size), max(6, icon_size//6), max(6, icon_size//6))
                
                # Draw up to 4 mini icons
                if target_folder:
                    apps = target_folder.get('apps', [])
                    mini_size = int(icon_size * 0.35)
                    padding = int((icon_size - (mini_size * 2)) / 3)
                    
                    for i in range(min(4, len(apps))):
                        app = apps[i]
                        r, c = divmod(i, 2)
                        x = padding + c * (mini_size + padding)
                        y = padding + r * (mini_size + padding)
                        
                        if not app.get('path', '').startswith('pandora://folder/'):
                            mini_pix = IconExtractor.get_icon_pixmap(app.get('path', ''), int(mini_size * 1.5))
                            if mini_pix and not mini_pix.isNull():
                                pp.drawPixmap(QRect(x, y, mini_size, mini_size), mini_pix, mini_pix.rect())
                pp.end()
                self._icon_pixmap = pix
                self.update()
            AppIcon.queue_icon_load(self, load_folder_icon)
        elif data.get('is_back_btn'):
            icon_path = os.path.join(os.path.dirname(__file__), '..', 'assets', 'back.svg')
            if os.path.exists(icon_path):
                self._icon_pixmap = VectorIcon.pixmap(icon_path, "#ffffff", icon_size)
            else:
                self._icon_pixmap = QPixmap()
        else:
            self._icon_pixmap = QPixmap()
            def load_regular_icon():
                high_res = int(icon_size * 1.5)
                pix = IconExtractor.get_icon_pixmap(data.get('path', ''), high_res)
                if not pix.isNull():
                    self._icon_pixmap = pix
                self.update()
            AppIcon.queue_icon_load(self, load_regular_icon)

        from PyQt6.QtGui import QFont, QFontMetrics
        font = QFont("Segoe UI")
        font.setPointSizeF(max(8.0, 9.5 * scale))
        font.setWeight(QFont.Weight.Medium)
        font.setStyleStrategy(QFont.StyleStrategy.PreferAntialias | QFont.StyleStrategy.PreferQuality)

        self._name_text = data.get('name', '')
        self._font = font
        self._font_size = font.pointSizeF()
        self._logical_w = logical_w
        self._grid_r = -1
        self._grid_c = -1
        self.update_elided_text()

        self.setCursor(Qt.CursorShape.PointingHandCursor)

        # Removed QGraphicsOpacityEffect for stability on translucent backgrounds.
        if pop_in:
            pass

    def set_grid_position(self, r, c):
        self._grid_r = r
        self._grid_c = c
        self.update_elided_text()

    def update_elided_text(self):
        show_app_names = getattr(self.parent_view, 'data', getattr(self.parent_view, 'folder_data', {})).get('show_app_names', False)
        if not show_app_names:
            return
            
        from PyQt6.QtGui import QFontMetrics
        fm = QFontMetrics(self._font)
        max_text_w = int(self._logical_w * 1.4) - 8
        
        # Check if we are on the bottom row
        is_bottom_row = False
        if hasattr(self.parent_view, 'grid_rows') and hasattr(self, '_grid_r'):
            if self._grid_r == self.parent_view.grid_rows - 1:
                is_bottom_row = True
                
        if is_bottom_row:
            # Only allow 1 line for the bottom row to prevent clipping at the folder boundary
            self._elided_lines = [fm.elidedText(self._name_text, Qt.TextElideMode.ElideRight, max_text_w)]
        else:
            self._elided_lines = elide_text_two_lines(self._name_text, max_text_w, fm)

    @pyqtProperty(float)
    def hover_scale(self):
        return self._hover_scale
        
    @hover_scale.setter
    def hover_scale(self, v):
        self._hover_scale = v
        self.update()

    @pyqtProperty(float)
    def text_opacity(self):
        return getattr(self, '_text_opacity', 1.0)
        
    @text_opacity.setter
    def text_opacity(self, value):
        self._text_opacity = value
        self.update()


    def enterEvent(self, e):
        self._hover = True
        self.anim = QPropertyAnimation(self, b"hover_scale")
        self.anim.setDuration(500)
        self.anim.setEasingCurve(QEasingCurve.Type.OutElastic)
        self.anim.setEndValue(1.25)
        self.anim.start()
        
        self.anim_op = QPropertyAnimation(self, b"text_opacity")
        self.anim_op.setDuration(200)
        self.anim_op.setEndValue(0.0)
        self.anim_op.start()

    def leaveEvent(self, e):
        self._hover = False
        self.anim = QPropertyAnimation(self, b"hover_scale")
        self.anim.setDuration(300)
        self.anim.setEasingCurve(QEasingCurve.Type.OutBack)
        self.anim.setEndValue(1.0)
        self.anim.start()
        
        self.anim_op = QPropertyAnimation(self, b"text_opacity")
        self.anim_op.setDuration(200)
        self.anim_op.setEndValue(1.0)
        self.anim_op.start()

    def box_center_y(self):
        return getattr(self, '_box_center_y', self.height() / 2.0)

    def paintEvent(self, e):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.setRenderHint(QPainter.RenderHint.TextAntialiasing)
        p.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)

        morph_scale = getattr(self.parent_view, 'anim_progress', 1.0)
        # Scale factor ranges from 0.5 to 1.0 based on morph progress
        base_scale = 0.5 + (0.5 * morph_scale)
        base_scale *= self._hover_scale

        if base_scale != 1.0:
            cx = self.width() / 2.0
            cy = self.box_center_y()
            p.translate(cx, cy)
            p.scale(base_scale, base_scale)
            p.translate(-cx, -cy)

        show_app_names = getattr(self.parent_view, 'data', getattr(self.parent_view, 'folder_data', {})).get('show_app_names', False)
        
        box_size = self._box_size
        scale = self._scale
        
        start_y = int(0.2 * box_size)

        # 1. Draw glassmorphic boundary box container for the icon
        bx = (self.width() - box_size) / 2.0
        box_rect = QRectF(bx, start_y, box_size, box_size)
        box_path = QPainterPath()
        box_radius = max(6, int(10 * scale))
        box_path.addRoundedRect(box_rect, box_radius, box_radius)
        
        # Get parent folder's color and alpha tint dynamically
        folder_color, folder_alpha = self.parent_view.get_folder_color()
        icon_alpha = int(folder_alpha * 0.5)
        
        is_light = getattr(self.parent_view, 'is_light', False)
        
        if self._hover:
            fill_color = QColor(folder_color.red(), folder_color.green(), folder_color.blue(), min(255, int(icon_alpha * 1.5)))
            border_color = QColor(255, 255, 255, 120) if not is_light else QColor(0, 0, 0, 60)
        else:
            fill_color = QColor(folder_color.red(), folder_color.green(), folder_color.blue(), icon_alpha)
            border_color = QColor(255, 255, 255, 45) if not is_light else QColor(0, 0, 0, 20)
            
        p.fillPath(box_path, fill_color)
        p.strokePath(box_path, QPen(border_color, 1))

        # 2. Draw the icon centered inside the box
        if hasattr(self, '_icon_pixmap') and not self._icon_pixmap.isNull():
            ix = bx + (box_size - self._icon_size) / 2.0
            iy = start_y + (box_size - self._icon_size) / 2.0
            
            icon_pm = self._icon_pixmap
            if is_light and self.app_data.get('is_placeholder'):
                pm2 = QPixmap(icon_pm.size())
                pm2.fill(Qt.GlobalColor.transparent)
                tp = QPainter(pm2)
                tp.drawPixmap(0, 0, icon_pm)
                tp.setCompositionMode(QPainter.CompositionMode.CompositionMode_SourceIn)
                tp.fillRect(pm2.rect(), QColor(36, 41, 47))
                tp.end()
                icon_pm = pm2
                
            p.drawPixmap(QRectF(ix, iy, self._icon_size, self._icon_size), icon_pm, QRectF(0, 0, icon_pm.width(), icon_pm.height()))
        
        if show_app_names and hasattr(self, '_elided_lines'):
            p.setOpacity(self.text_opacity)
            p.setFont(self._font)
            line_height = int(self._font_size * 1.25)
            y_start = start_y + box_size + int(4 * scale)
            
            for idx, line in enumerate(self._elided_lines):
                text_rect = QRectF(2, y_start + idx * line_height, self.width() - 4, line_height + 2)
                
                if not is_light:
                    p.setPen(QColor(0, 0, 0, 160))
                    p.drawText(text_rect.translated(0, 1), Qt.AlignmentFlag.AlignCenter, line)
                    p.setPen(Qt.GlobalColor.white)
                else:
                    p.setPen(QColor(36, 41, 47))
                p.drawText(text_rect, Qt.AlignmentFlag.AlignCenter, line)
            p.setOpacity(1.0)

    def mousePressEvent(self, e):
        self.sp = e.pos()
        path = self.app_data['path']
        pv = self.parent_view

        pv.selected_apps.clear()
        pv.selected_apps.add(path)
        pv.last_selected_path = path

        if e.button() == Qt.MouseButton.RightButton and not getattr(self.parent_view, 'is_sandbox', False):
            self.show_menu(e.globalPosition().toPoint())

    def mouseReleaseEvent(self, e):
        if e.button() == Qt.MouseButton.LeftButton:
            if hasattr(self, 'sp') and (e.pos() - self.sp).manhattanLength() < 10:
                if not getattr(self.parent_view, 'is_sandbox', False):
                    if self.app_data['path'].startswith('pandora://folder/'):
                        folder_id = self.app_data['path'].replace('pandora://folder/', '')
                        self.parent_view.open_nested_folder(folder_id)
                    elif self.app_data['path'] == 'pandora://system/back':
                        if hasattr(self.parent_view, 'go_back'):
                            self.parent_view.go_back()
                    elif os.path.exists(self.app_data['path']):
                        try:
                            os.startfile(self.app_data['path'])
                            if hasattr(self.parent_view, 'hide_morph'):
                                self.parent_view.hide_morph()
                        except OSError as e:
                            print(f"Failed to start file: {e}")
                        except Exception as e:
                            print(f"Unexpected error starting file: {e}")
        super().mouseReleaseEvent(e)

    def mouseMoveEvent(self, e):
        if self.app_data.get('is_back_btn'):
            return
        if not (e.buttons() & Qt.MouseButton.LeftButton) or (e.pos() - self.sp).manhattanLength() < 10:   
            return
        if self.app_data['path'] not in self.parent_view.selected_apps:
            self.parent_view.selected_apps.clear()
            self.parent_view.selected_apps.add(self.app_data['path'])
            from ui.app_icon import AppIcon
            for w in self.parent_view.findChildren(AppIcon):
                w.update()

        self.is_internal = False
        self.parent_view.is_dragging = True
        try:
            drag = QDrag(self)
            mime = QMimeData()
            data_obj = getattr(self.parent_view, 'data', getattr(self.parent_view, 'folder_data', {}))
            selected_apps_data = [a for a in data_obj.get('apps', []) if a['path'] in self.parent_view.selected_apps]
            mime.setText(json.dumps(selected_apps_data))
            mime.setData("application/x-pandora-app", data_obj.get('id', '').encode())

            urls = []
            has_nested = False
            for app_data in selected_apps_data:
                if os.path.exists(app_data['path']):
                    urls.append(QUrl.fromLocalFile(app_data['path']))
                elif app_data['path'].startswith('pandora://folder/'):
                    has_nested = True
                    
            if not urls and has_nested:
                from ui.app_icon import GhostWidget
                self.parent_view.is_dragging = True
                self.parent_view.active_drag_app = self.app_data
                scaled_pix = None
                if hasattr(self, '_icon_pixmap') and not self._icon_pixmap.isNull():
                    scaled_pix = self._icon_pixmap.scaled(53, 53, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
                self.ghost = GhostWidget(scaled_pix, selected_apps_data, self.parent_view)
                return

            if urls:
                mime.setUrls(urls)

            drag.setMimeData(mime)
            if hasattr(self, '_icon_pixmap') and not self._icon_pixmap.isNull():
                drag.setPixmap(self._icon_pixmap.scaled(53, 53, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation))
            drag.setHotSpot(QPoint(26, 26))

            from ui.app_icon import AppIcon
            for p in self.parent_view.selected_apps:
                for w in self.parent_view.findChildren(AppIcon):
                    if w.app_data.get('path') == p:
                        w.hide()

            self.parent_view.active_drag_app = self.app_data
            self.parent_view.refresh()
            
            # If sandbox, restrict drag to internal move only
            parent_icon = getattr(self.parent_view, 'parent_icon', None)
            if parent_icon and hasattr(parent_icon, 'dashboard') and hasattr(parent_icon.dashboard, '_setup_drag_hook'):
                parent_icon.dashboard._setup_drag_hook()

            if getattr(self.parent_view, 'is_sandbox', False):
                res = drag.exec(Qt.DropAction.MoveAction)
            else:
                # Force MoveAction to signify that the file will be relocated, not duplicated.
                res = drag.exec(Qt.DropAction.MoveAction)

            if not self.is_internal and res in (Qt.DropAction.MoveAction, Qt.DropAction.CopyAction, Qt.DropAction.TargetMoveAction, Qt.DropAction.IgnoreAction):
                if not getattr(self.parent_view, 'is_sandbox', False):
                    # Check if cursor is over ANY Pandora folder panel, not just source
                    cursor_pos = QCursor.pos()
                    dropped_on_folder = False
                    if self.parent_view.geometry().contains(cursor_pos):
                        dropped_on_folder = True
                    elif hasattr(self.parent_view, 'dashboard') and self.parent_view.dashboard:
                        for panel in getattr(self.parent_view.dashboard, 'app_instances', []):
                            try:
                                if panel.geometry().contains(cursor_pos):
                                    dropped_on_folder = True
                                    break
                            except RuntimeError:
                                pass
                    if not dropped_on_folder:
                        self.parent_view.move_to_desktop(selected_apps_data)

        finally:
            if hasattr(self, 'parent_view') and hasattr(self.parent_view, '_start_hide_timer'):
                self.parent_view._start_hide_timer()
            parent_icon = getattr(self.parent_view, 'parent_icon', None)
            if parent_icon and hasattr(parent_icon, 'dashboard') and hasattr(parent_icon.dashboard, '_remove_drag_hook'):
                parent_icon.dashboard._remove_drag_hook()
            self.parent_view.is_dragging = False
            self.parent_view.active_drag_app = None
            self.parent_view.selected_apps.clear()
            self.parent_view.refresh()
            parent_icon = getattr(self.parent_view, 'parent_icon', None)
            if parent_icon:
                parent_icon.update()

    def show_menu(self, pt):
        if self.app_data.get('is_back_btn'):
            return
        
        if not hasattr(self, '_context_menu'):
            self._context_menu = AnimatedMenu(self)
        m = self._context_menu
        m.clear()

        a = QAction("Rename", self)
        a.triggered.connect(self.rename)
        m.addAction(a)
        r = QAction("Remove", self)
        r.triggered.connect(lambda: self.parent_view.move_to_desktop([self.app_data]))
        m.addAction(r)

        m.exec(pt)
        
        # After the context menu closes, the mouse might have left the folder panel 
        # bounds without triggering a proper leaveEvent (due to focus grab). 
        # Manually trigger a hide check.
        if hasattr(self, 'parent_view') and hasattr(self.parent_view, '_start_hide_timer'):
            self.parent_view._start_hide_timer()

    def rename(self):
        from ui.ui_common import IslandRenameDialog
        if hasattr(self, '_rename_dialog') and self._rename_dialog:
            try:
                self._rename_dialog.close()
                self._rename_dialog.deleteLater()
            except:
                pass
            self._rename_dialog = None
            
        old_name = self.app_data.get('name', '')
        
        def save_name(new_name):
            new_name = new_name.strip()
            if new_name and new_name != old_name:
                self.app_data['name'] = new_name
                from PyQt6.QtGui import QFontMetrics
                fm = QFontMetrics(self._font)
                self._elided_name = fm.elidedText(new_name, Qt.TextElideMode.ElideRight, max(10, self.width() - 8))
                self.update()
                from config import ConfigManager
                self.parent_view.dashboard.save_and_broadcast()
                
        self._rename_dialog = IslandRenameDialog(initial_text=old_name, on_save=save_name, parent=None)
        self._rename_dialog.show()

class GhostWidget(QWidget):
    def __init__(self, pixmap, drag_data, parent_view):
        super().__init__(None)
        self.setWindowFlags(Qt.WindowType.ToolTip | Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnTopHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.pixmap = pixmap
        self.drag_data = drag_data
        self.parent_view = parent_view
        
        if pixmap:
            self.resize(pixmap.size())
        else:
            self.resize(53, 53)
            
        self.move(QCursor.pos() - QPoint(26, 26))
        self.show()
        self.grabMouse()
        
    def paintEvent(self, e):
        if self.pixmap:
            from PyQt6.QtGui import QPainter
            p = QPainter(self)
            p.drawPixmap(0, 0, self.pixmap)
            
    def mouseMoveEvent(self, e):
        self.move(e.globalPosition().toPoint() - QPoint(26, 26))
        
    def mouseReleaseEvent(self, e):
        self.releaseMouse()
        self.hide()
        
        cursor_pos = e.globalPosition().toPoint()
        dropped_on_folder = False
        
        if self.parent_view.geometry().contains(cursor_pos):
            dropped_on_folder = True
        elif hasattr(self.parent_view, 'dashboard') and self.parent_view.dashboard:
            for panel in getattr(self.parent_view.dashboard, 'app_instances', []):
                try:
                    if panel.geometry().contains(cursor_pos):
                        dropped_on_folder = True
                        break
                except RuntimeError:
                    pass
                    
        if not dropped_on_folder:
            self.parent_view.move_to_desktop(self.drag_data)
        else:
            target_panel = None
            if self.parent_view.geometry().contains(cursor_pos):
                target_panel = self.parent_view
            elif hasattr(self.parent_view, 'dashboard') and self.parent_view.dashboard:
                for panel in getattr(self.parent_view.dashboard, 'app_instances', []):
                    try:
                        if panel.geometry().contains(cursor_pos):
                            target_panel = panel
                            break
                    except RuntimeError: pass
            
            if target_panel:
                local_pos = target_panel.mapFromGlobal(cursor_pos)
                target_idx = target_panel._pos_to_grid_idx(local_pos)
                page_offset = target_panel.page_idx * target_panel._get_page_size()
                absolute_idx = page_offset + target_idx
                
                from PyQt6.QtCore import QTimer, QMimeData
                import json
                mime = QMimeData()
                mime.setText(json.dumps(self.drag_data))
                data_obj = getattr(self.parent_view, 'data', getattr(self.parent_view, 'folder_data', {}))
                mime.setData("application/x-pandora-app", data_obj.get('id', '').encode())
                
                from ui.logic import handle_app_drop
                from config import ConfigManager
                success, _ = handle_app_drop(target_panel.cfg, target_panel.data, mime, self, absolute_idx, target_panel.dashboard)
                if success:
                    target_panel.dashboard.save_and_broadcast()
                    target_panel.refresh()
            
        self.parent_view.is_dragging = False
        self.parent_view.active_drag_app = None
        self.parent_view.selected_apps.clear()
        self.parent_view.refresh()
        parent_icon = getattr(self.parent_view, 'parent_icon', None)
        if parent_icon:
            parent_icon.update()
            
        self.deleteLater()
