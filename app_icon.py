import os
import json
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QLabel
from PyQt6.QtCore import Qt, QPropertyAnimation, QPoint, QMimeData, QUrl, QRect
from PyQt6.QtGui import QPainter, QColor, QCursor, QDrag, QAction

from utils import IconExtractor, VectorIcon
from ui_common import AnimatedMenu

class AppIcon(QWidget):
    def __init__(self, data, parent_view, pop_in=False, font_size=10, icon_size=48):
        super().__init__(parent_view.grid_widget)
        self.app_data = data
        self.parent_view = parent_view

        self.setFixedSize(max(icon_size + 40, 100), icon_size + font_size * 2 + 40)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setMouseTracking(True)
        self._hover = False
        self.is_internal = False

        l = QVBoxLayout(self)
        l.setContentsMargins(10, 10, 10, 10)
        l.setSpacing(8)
        l.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.il = QLabel()
        self.il.setFixedSize(icon_size, icon_size)
        self.il.setScaledContents(True)

        pix = IconExtractor.get_icon_pixmap(data.get('path', ''), icon_size)
        if not pix.isNull():
            self.il.setPixmap(pix.scaled(icon_size, icon_size, Qt.AspectRatioMode.IgnoreAspectRatio, Qt.TransformationMode.SmoothTransformation))

        from PyQt6.QtGui import QFont
        font = QFont("Segoe UI", font_size)
        font.setStyleStrategy(QFont.StyleStrategy.PreferAntialias)

        self.nl = QLabel(data.get('name', ''))
        self.nl.setFont(font)
        self.nl.setStyleSheet(f"color: white; font-size: {font_size}px;")
        self.nl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.nl.setWordWrap(True)

        l.addWidget(self.il, 0, Qt.AlignmentFlag.AlignCenter)
        l.addWidget(self.nl, 0, Qt.AlignmentFlag.AlignCenter)
        self.setCursor(Qt.CursorShape.PointingHandCursor)

        # Removed QGraphicsOpacityEffect for stability on translucent backgrounds.
        if pop_in:
            pass

    def enterEvent(self, e):
        self._hover = True
        self.update()

    def leaveEvent(self, e):
        self._hover = False
        self.update()

    def paintEvent(self, e):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)

        is_selected = hasattr(self, 'parent_view') and self.app_data['path'] in getattr(self.parent_view, 'selected_apps', set())

        if is_selected:
            p.translate(self.width() / 2, self.height() / 2)
            p.scale(1.05, 1.05)
            p.translate(-self.width() / 2, -self.height() / 2)

        if self._hover:
            p.setBrush(QColor(255, 255, 255, 20))
            p.setPen(Qt.PenStyle.NoPen)
            p.drawRoundedRect(self.rect().adjusted(2, 2, -2, -2), 16, 16)
        if is_selected:
            p.setBrush(QColor(80, 250, 123, 100))
            p.setPen(Qt.PenStyle.NoPen)
            p.drawRoundedRect(self.rect().adjusted(2, 2, -2, -2), 16, 16)
        if self.app_data.get('pinned'):
            pin_pix = VectorIcon.icon("pin", "#ffdd57").pixmap(14, 14)
            p.drawPixmap(self.width() - 25, 12, pin_pix)

    def mouseDoubleClickEvent(self, e):
        if getattr(self.parent_view, 'is_sandbox', False): return
        if os.path.exists(self.app_data['path']):
            os.startfile(self.app_data['path'])
            self.parent_view.hide_morph()

    def mousePressEvent(self, e):
        self.sp = e.pos()
        path = self.app_data['path']
        pv = self.parent_view

        if e.modifiers() & Qt.KeyboardModifier.ControlModifier:
            if path in pv.selected_apps:
                pv.selected_apps.remove(path)
            else:
                pv.selected_apps.add(path)
            pv.last_selected_path = path
        elif e.modifiers() & Qt.KeyboardModifier.ShiftModifier:
            if hasattr(pv, 'last_selected_path') and pv.last_selected_path in pv.current_vis_paths:
                start_idx = pv.current_vis_paths.index(pv.last_selected_path)
                end_idx = pv.current_vis_paths.index(path)
                step = 1 if start_idx <= end_idx else -1
                for i in range(start_idx, end_idx + step, step):
                    pv.selected_apps.add(pv.current_vis_paths[i])
            else:
                pv.selected_apps.add(path)
                pv.last_selected_path = path
        else:
            if path not in pv.selected_apps:
                pv.selected_apps.clear()
                pv.selected_apps.add(path)
            pv.last_selected_path = path

        for w in pv.app_widgets.values():
            w.update()

        if e.button() == Qt.MouseButton.RightButton and not getattr(self.parent_view, 'is_sandbox', False):
            self.show_menu(e.globalPosition().toPoint())

    def mouseReleaseEvent(self, e):
        if e.button() == Qt.MouseButton.LeftButton:
            if not (e.modifiers() & (Qt.KeyboardModifier.ControlModifier | Qt.KeyboardModifier.ShiftModifier)):
                pv = self.parent_view
                if len(pv.selected_apps) > 1 and self.app_data['path'] in pv.selected_apps:
                    pv.selected_apps.clear()
                    pv.selected_apps.add(self.app_data['path'])
                    for w in pv.app_widgets.values():
                        w.update()
        super().mouseReleaseEvent(e)

    def mouseMoveEvent(self, e):
        if not (e.buttons() & Qt.MouseButton.LeftButton) or (e.pos() - self.sp).manhattanLength() < 10:   
            return
        if self.app_data['path'] not in self.parent_view.selected_apps:
            self.parent_view.selected_apps.clear()
            self.parent_view.selected_apps.add(self.app_data['path'])
            for w in self.parent_view.app_widgets.values():
                w.update()

        self.is_internal = False
        self.parent_view.is_dragging = True
        try:
            drag = QDrag(self)
            mime = QMimeData()
            selected_apps_data = [a for a in self.parent_view.folder_data.get('apps', []) if a['path'] in self.parent_view.selected_apps]
            mime.setText(json.dumps(selected_apps_data))
            mime.setData("application/x-cusfolder-app", self.parent_view.folder_data.get('id', '').encode())

            urls = []
            for app_data in selected_apps_data:
                if os.path.exists(app_data['path']):
                    urls.append(QUrl.fromLocalFile(app_data['path']))
            if urls:
                mime.setUrls(urls)

            drag.setMimeData(mime)
            if self.il.pixmap():
                drag.setPixmap(self.il.pixmap().scaled(53, 53))
            drag.setHotSpot(QPoint(26, 26))

            for p in self.parent_view.selected_apps:
                if p in self.parent_view.app_widgets:
                    self.parent_view.app_widgets[p].hide()

            self.parent_view.active_drag_app = self.app_data
            self.parent_view.refresh()
            
            # If sandbox, restrict drag to internal move only
            if getattr(self.parent_view, 'is_sandbox', False):
                res = drag.exec(Qt.DropAction.MoveAction)
            else:
                res = drag.exec(Qt.DropAction.MoveAction | Qt.DropAction.CopyAction)

            if getattr(self.parent_view, 'is_sandbox', False):
                # Never move to desktop in sandbox
                pass
            elif not self.is_internal and res in (Qt.DropAction.MoveAction, Qt.DropAction.CopyAction, Qt.DropAction.TargetMoveAction) and not self.parent_view.geometry().contains(QCursor.pos()):
                self.parent_view.move_to_desktop(selected_apps_data)

        finally:
            self.parent_view.is_dragging = False
            self.parent_view.active_drag_app = None
            self.parent_view.selected_apps.clear()
            self.parent_view.refresh()
            self.parent_view.parent_icon.update()

    def show_menu(self, pt):
        m = AnimatedMenu(self)

        is_multi = hasattr(self, 'parent_view') and len(self.parent_view.selected_apps) > 1 and self.app_data['path'] in self.parent_view.selected_apps

        if is_multi:
            l = QAction("Launch All", self)
            l.triggered.connect(self.launch_multi)
            m.addAction(l)

            selected_apps_data = [a for a in self.parent_view.folder_data.get('apps', []) if a['path'] in self.parent_view.selected_apps]
            all_pinned = all(a.get('pinned') for a in selected_apps_data)

            p = QAction("Unpin All" if all_pinned else "Pin All to Top", self)
            p.triggered.connect(lambda: self.toggle_pin_multi(all_pinned))
            m.addAction(p)

            r = QAction("Remove All", self)
            r.triggered.connect(self.remove_multi)
            m.addAction(r)
        else:
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

    def launch_multi(self):
        selected_apps_data = [a for a in self.parent_view.folder_data.get('apps', []) if a['path'] in self.parent_view.selected_apps]
        for app in selected_apps_data:
            if os.path.exists(app['path']):
                os.startfile(app['path'])
        self.parent_view.hide_morph()

    def toggle_pin_multi(self, currently_all_pinned):
        selected_apps_data = [a for a in self.parent_view.folder_data.get('apps', []) if a['path'] in self.parent_view.selected_apps]
        for app in selected_apps_data:
            app['pinned'] = not currently_all_pinned
        self.parent_view.apply_sort()

    def remove_multi(self):
        selected_apps_data = [a for a in self.parent_view.folder_data.get('apps', []) if a['path'] in self.parent_view.selected_apps]
        self.parent_view.move_to_desktop(selected_apps_data)

    def rename(self):
        self.parent_view.start_rename()

    def toggle_pin(self):
        self.app_data['pinned'] = not self.app_data.get('pinned')
        self.parent_view.apply_sort()
