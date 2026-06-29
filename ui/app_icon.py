import os
import json
from PyQt6.QtWidgets import QWidget, QApplication
from PyQt6.QtCore import Qt, QPropertyAnimation, QPoint, QMimeData, QUrl, QRect, QRectF, pyqtProperty, QEasingCurve
from PyQt6.QtGui import QPainter, QColor, QCursor, QDrag, QAction, QPixmap, QPen

from utils import IconExtractor, VectorIcon
from ui.ui_common import AnimatedMenu

class AppIcon(QWidget):
    def __init__(self, data, parent_view, pop_in=False, font_size=10, icon_size=48):
        super().__init__(parent_view)
        self.app_data = data
        self.parent_view = parent_view

        gs = 110
        if hasattr(parent_view, 'cfg'):
            gs = parent_view.cfg.get('general_settings', {}).get('grid_size', 110)
            
        scale = gs / 110.0
        icon_size = max(24, int(32 * scale))
        font_size = max(9, int(11 * scale))
        
        show_app_names = getattr(self.parent_view, 'data', getattr(self.parent_view, 'folder_data', {})).get('show_app_names', False)
        
        widget_w = icon_size + int(16 * scale)
        if show_app_names:
            widget_h = icon_size + font_size + int(24 * scale)
        else:
            widget_h = icon_size + int(8 * scale)
            
        logical_w = max(widget_w, int(54 * scale))
        logical_h = widget_h
        
        # Expand physical widget bounds by 40% to allow hover scaling without clipping
        self.setFixedSize(int(logical_w * 1.4), int(logical_h * 1.4))
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setMouseTracking(True)
        self._hover = False
        self.is_internal = False
        self._hover_scale = 1.0
        self._text_opacity = 1.0
        self._icon_size = icon_size

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
        elif data.get('is_back_btn'):
            icon_path = os.path.join(os.path.dirname(__file__), '..', 'assets', 'back.svg')
            if os.path.exists(icon_path):
                self._icon_pixmap = VectorIcon.pixmap(icon_path, "#ffffff", icon_size)
            else:
                self._icon_pixmap = QPixmap()
        else:
            high_res = int(icon_size * 1.5)
            pix = IconExtractor.get_icon_pixmap(data.get('path', ''), high_res)
            if not pix.isNull():
                self._icon_pixmap = pix
            else:
                self._icon_pixmap = QPixmap()

        from PyQt6.QtGui import QFont, QFontMetrics
        font = QFont("Segoe UI")
        font.setPixelSize(font_size)
        font.setStyleStrategy(QFont.StyleStrategy.PreferAntialias)

        name_text = data.get('name', '')
        fm = QFontMetrics(font)
        self._elided_name = fm.elidedText(name_text, Qt.TextElideMode.ElideRight, max(10, widget_w - 8))
        self._font = font
        self._font_size = font_size

        self.setCursor(Qt.CursorShape.PointingHandCursor)

        # Removed QGraphicsOpacityEffect for stability on translucent backgrounds.
        if pop_in:
            pass

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
            p.translate(self.width() / 2, self.height() / 2)
            p.scale(base_scale, base_scale)
            p.translate(-self.width() / 2, -self.height() / 2)


        show_app_names = getattr(self.parent_view, 'data', getattr(self.parent_view, 'folder_data', {})).get('show_app_names', False)
        
        content_h = self._icon_size + (self._font_size + 8 if show_app_names else 0)
        start_y = (self.height() - content_h) / 2.0

        if hasattr(self, '_icon_pixmap') and not self._icon_pixmap.isNull():
            ix = int((self.width() - self._icon_size) / 2)
            p.drawPixmap(QRectF(ix, start_y, self._icon_size, self._icon_size), self._icon_pixmap, QRectF(0, 0, self._icon_pixmap.width(), self._icon_pixmap.height()))
        
        if self.app_data.get('pinned'):
            pin_pix = VectorIcon.icon("pin", "#ffdd57").pixmap(14, 14)
            p.drawPixmap(self.width() - int(25 + self.width() * 0.15), int(12 + self.height() * 0.15), pin_pix)
            
        if show_app_names:
            p.setOpacity(self.text_opacity)
            p.setFont(self._font)
            text_rect = QRectF(0, start_y + self._icon_size + 8, self.width(), self._font_size + 4)
            
            p.setPen(QColor(0, 0, 0, 150))
            p.drawText(text_rect.translated(0, 1), Qt.AlignmentFlag.AlignCenter, self._elided_name)
            
            p.setPen(Qt.GlobalColor.white)
            p.drawText(text_rect, Qt.AlignmentFlag.AlignCenter, self._elided_name)
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
        m = AnimatedMenu(self)

        a = QAction("Rename", self)
        a.triggered.connect(self.rename)
        m.addAction(a)
        
        p = QAction("Unpin" if self.app_data.get('pinned') else "Pin to Top", self)
        p.triggered.connect(self.toggle_pin)
        m.addAction(p)
        
        r = QAction("Remove", self)
        r.triggered.connect(lambda: self.parent_view.move_to_desktop([self.app_data]))
        m.addAction(r)

        m.exec(pt)

    def rename(self):
        from ui.ui_common import IslandRenameDialog
        if hasattr(self, '_rename_dialog') and self._rename_dialog and self._rename_dialog.isVisible():
            return
            
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
                ConfigManager.save(self.parent_view.cfg)
                
        self._rename_dialog = IslandRenameDialog(initial_text=old_name, on_save=save_name, parent=None)
        self._rename_dialog.show()

    def toggle_pin(self):
        self.app_data['pinned'] = not self.app_data.get('pinned')
        from config import ConfigManager
        ConfigManager.save(self.parent_view.cfg)
        self.parent_view.refresh()

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
                
                from PyQt6.QtCore import QMimeData
                import json
                mime = QMimeData()
                mime.setText(json.dumps(self.drag_data))
                data_obj = getattr(self.parent_view, 'data', getattr(self.parent_view, 'folder_data', {}))
                mime.setData("application/x-pandora-app", data_obj.get('id', '').encode())
                
                from ui.logic import handle_app_drop
                from config import ConfigManager
                success, _ = handle_app_drop(target_panel.cfg, target_panel.data, mime, self, False, absolute_idx, target_panel.dashboard)
                if success:
                    ConfigManager.save(target_panel.cfg)
                    target_panel.refresh()
            
        self.parent_view.is_dragging = False
        self.parent_view.active_drag_app = None
        self.parent_view.selected_apps.clear()
        self.parent_view.refresh()
        parent_icon = getattr(self.parent_view, 'parent_icon', None)
        if parent_icon:
            parent_icon.update()
            
        self.deleteLater()
