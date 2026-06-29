from PyQt6.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QLineEdit, QListWidget, QListWidgetItem, QPushButton, QLabel, QFrame
from PyQt6.QtCore import Qt, QThread, pyqtSignal, QRunnable, QThreadPool, QObject, QSize
from PyQt6.QtGui import QIcon, QPixmap, QImage
import os
import sys

class AppFetcherThread(QThread):
    finished_signal = pyqtSignal(list)
    error_signal = pyqtSignal(str)
    def run(self):
        try:
            import subprocess, json
            si = subprocess.STARTUPINFO()
            si.dwFlags |= subprocess.STARTF_USESHOWWINDOW
            result = subprocess.run(
                ["powershell", "-NoProfile", "-Command", "Get-StartApps | ConvertTo-Json"],
                capture_output=True, text=True, startupinfo=si
            )
            if result.returncode == 0:
                apps = json.loads(result.stdout)
                if isinstance(apps, dict): apps = [apps]
                valid_apps = []
                for a in apps:
                    name, appid = a.get('Name', ''), a.get('AppID', '')
                    if name and appid: valid_apps.append({'name': name, 'appid': appid})
                valid_apps.sort(key=lambda x: x['name'].lower())
                self.finished_signal.emit(valid_apps)
            else:
                self.error_signal.emit(result.stderr)
        except Exception as e:
            self.error_signal.emit(str(e))


class IconLoaderSignals(QObject):
    icon_loaded = pyqtSignal(object, object)


class IconLoaderWorker(QRunnable):
    def __init__(self, item, appid):
        super().__init__()
        self.item = item
        self.appid = appid
        self.signals = IconLoaderSignals()
        
    def run(self):
        import ctypes
        from ctypes import wintypes
        from PyQt6.QtGui import QImage
        try:
            shell32 = ctypes.windll.shell32
            ole32 = ctypes.windll.ole32

            class GUID(ctypes.Structure):
                _fields_ = [('Data1', wintypes.DWORD), ('Data2', wintypes.WORD),
                            ('Data3', wintypes.WORD), ('Data4', ctypes.c_byte * 8)]
            class SIZE(ctypes.Structure):
                _fields_ = [('cx', ctypes.c_long), ('cy', ctypes.c_long)]

            ole32.CoInitialize(None)
            path = rf"shell:AppsFolder\{self.appid}"
            iid = GUID(0xbcc18b79, 0xba16, 0x442f, (0x80, 0xc4, 0x8a, 0x59, 0xc3, 0x0c, 0x46, 0x3b))
            factory = ctypes.c_void_p()
            hr = shell32.SHCreateItemFromParsingName(ctypes.c_wchar_p(path), None, ctypes.byref(iid), ctypes.byref(factory))

            if hr == 0 and factory:
                GetImageType = ctypes.WINFUNCTYPE(ctypes.HRESULT, ctypes.c_void_p, SIZE, wintypes.DWORD, ctypes.POINTER(wintypes.HBITMAP))
                vtable = ctypes.cast(factory, ctypes.POINTER(ctypes.POINTER(ctypes.c_void_p)))
                GetImage = ctypes.cast(vtable.contents[3], GetImageType)
                hbitmap = wintypes.HBITMAP()
                hr = GetImage(factory, SIZE(32, 32), 0, ctypes.byref(hbitmap))
                if hr == 0 and hbitmap.value:
                    img = QImage.fromHBITMAP(hbitmap.value)
                    if img and not img.isNull():
                        self.signals.icon_loaded.emit(self.item, img)
            ole32.CoUninitialize()
        except Exception:
            pass


class AppSelectorDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.Dialog)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setFixedSize(450, 600)
        
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        
        self.bg_frame = QFrame()
        self.bg_frame.setStyleSheet("""
            QFrame#bg_frame {
                background-color: rgba(20, 20, 25, 240);
                border: 1px solid rgba(255, 255, 255, 15);
                border-radius: 12px;
            }
        """)
        self.bg_frame.setObjectName("bg_frame")
        main_layout.addWidget(self.bg_frame)
        
        layout = QVBoxLayout(self.bg_frame)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)
        
        from ui_dashboard_common import get_theme_colors
        colors = get_theme_colors()
        accent = colors.get('accent_color', '#00f0ff')
        
        title_layout = QHBoxLayout()
        title_lbl = QLabel("SELECT INSTALLED APP")
        title_lbl.setStyleSheet(f"color: {accent}; font-weight: 800; font-size: 14px; letter-spacing: 1px;")
        
        close_btn = QPushButton("✕")
        close_btn.setFixedSize(24, 24)
        close_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        close_btn.setStyleSheet("QPushButton { background: transparent; color: #888; font-weight: bold; border: none; } QPushButton:hover { color: #ff5555; background: rgba(255,85,85,20); border-radius: 12px; }")
        close_btn.clicked.connect(self.reject)
        
        title_layout.addWidget(title_lbl)
        title_layout.addStretch()
        title_layout.addWidget(close_btn)
        layout.addLayout(title_layout)
        
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Search applications...")
        self.search_input.setFixedHeight(36)
        self.search_input.setStyleSheet(f"""
            QLineEdit {{
                background: rgba(255, 255, 255, 5);
                border: 1px solid rgba(255, 255, 255, 15);
                border-radius: 8px;
                padding: 0 15px;
                color: white;
                font-size: 13px;
            }}
            QLineEdit:focus {{
                border: 1px solid {accent};
                background: rgba(255, 255, 255, 8);
            }}
        """)
        self.search_input.textChanged.connect(self.filter_apps)
        layout.addWidget(self.search_input)
        
        self.list_widget = QListWidget()
        self.list_widget.setStyleSheet(f"""
            QListWidget {{
                background: transparent;
                border: none;
                outline: none;
            }}
            QListWidget::item {{
                background: rgba(255, 255, 255, 3);
                border: 1px solid rgba(255, 255, 255, 5);
                border-radius: 8px;
                margin-bottom: 6px;
                padding: 12px;
                color: #ddd;
                font-size: 13px;
                font-weight: 500;
            }}
            QListWidget::item:hover {{
                background: rgba(255, 255, 255, 8);
                border: 1px solid rgba(255, 255, 255, 15);
                color: white;
            }}
            QListWidget::item:selected {{
                background: rgba(100, 100, 100, 15);
                border: 1px solid {accent};
                color: {accent};
            }}
            QScrollBar:vertical {{
                border: none;
                background: rgba(0,0,0,0);
                width: 8px;
                border-radius: 4px;
            }}
            QScrollBar::handle:vertical {{
                background: rgba(255,255,255,30);
                border-radius: 4px;
            }}
            QScrollBar::handle:vertical:hover {{
                background: rgba(255,255,255,50);
            }}
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height: 0px; }}
        """)
        self.list_widget.itemDoubleClicked.connect(self.accept)
        layout.addWidget(self.list_widget)
        
        self.status_label = QLabel("Initializing scanner...")
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.status_label.setStyleSheet("color: #888; font-style: italic; font-size: 12px; padding: 20px;")
        layout.addWidget(self.status_label)
        
        btn_layout = QHBoxLayout()
        btn_layout.setContentsMargins(0, 10, 0, 0)
        btn_layout.addStretch()
        
        self.cancel_btn = QPushButton("Cancel")
        self.cancel_btn.setFixedSize(100, 36)
        self.cancel_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.cancel_btn.setStyleSheet("""
            QPushButton {
                background: rgba(255, 255, 255, 5);
                color: #aaa;
                border: 1px solid rgba(255, 255, 255, 15);
                border-radius: 8px;
                font-weight: 600;
            }
            QPushButton:hover {
                background: rgba(255, 255, 255, 10);
                color: white;
            }
        """)
        self.cancel_btn.clicked.connect(self.reject)
        
        self.ok_btn = QPushButton("Connect App")
        self.ok_btn.setFixedSize(120, 36)
        self.ok_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.ok_btn.setStyleSheet(f"""
            QPushButton {{
                background: rgba(100, 100, 100, 15);
                color: {accent};
                border: 1px solid rgba(100, 100, 100, 40);
                border-radius: 8px;
                font-weight: bold;
            }}
            QPushButton:hover {{
                background: rgba(100, 100, 100, 30);
                border: 1px solid {accent};
            }}
            QPushButton:disabled {{
                background: rgba(255, 255, 255, 2);
                color: #555;
                border: 1px solid rgba(255, 255, 255, 5);
            }}
        """)
        self.ok_btn.clicked.connect(self.accept)
        self.ok_btn.setEnabled(False)
        
        btn_layout.addWidget(self.cancel_btn)
        btn_layout.addWidget(self.ok_btn)
        layout.addLayout(btn_layout)
        
        self.list_widget.itemSelectionChanged.connect(lambda: self.ok_btn.setEnabled(len(self.list_widget.selectedItems()) > 0))
        
        self.all_apps = []
        
        self.status_label.hide()
        for _ in range(8):
            item = QListWidgetItem()
            item.setSizeHint(QSize(0, 56))
            item.setFlags(Qt.ItemFlag.NoItemFlags)
            self.list_widget.addItem(item)
            skel = QFrame()
            skel.setStyleSheet("""
                QFrame { background: transparent; }
                QFrame#icon { background: rgba(255,255,255,5); border-radius: 6px; }
                QFrame#text { background: rgba(255,255,255,5); border-radius: 4px; }
            """)
            lay = QHBoxLayout(skel); lay.setContentsMargins(5, 5, 5, 5); lay.setSpacing(15)
            icon = QFrame(); icon.setObjectName("icon"); icon.setFixedSize(32, 32)
            txt = QFrame(); txt.setObjectName("text"); txt.setFixedSize(160, 12)
            lay.addWidget(icon); lay.addWidget(txt); lay.addStretch()
            self.list_widget.setItemWidget(item, skel)

        self.thread = AppFetcherThread(self)
        self.thread.finished_signal.connect(self.on_apps_loaded)
        self.thread.error_signal.connect(self.on_apps_error)
        self.thread.start()

    def filter_apps(self, text):
        text = text.lower()
        self.list_widget.clear()
        
        pool = QThreadPool.globalInstance()
        for app in self.all_apps:
            if text in app['name'].lower():
                item = QListWidgetItem(app['name'])
                item.setData(Qt.ItemDataRole.UserRole, app['appid'])
                self.list_widget.addItem(item)
                
                worker = IconLoaderWorker(item, app['appid'])
                worker.signals.icon_loaded.connect(self._apply_icon)
                pool.start(worker)

    def _apply_icon(self, item, img):
        try:
            if item.listWidget() is not None:
                item.setIcon(QIcon(QPixmap.fromImage(img)))
        except RuntimeError:
            pass

    def on_apps_loaded(self, apps):
        self.all_apps = apps
        self.status_label.hide()
        self.filter_apps(self.search_input.text())
        self.search_input.setFocus()

    def on_apps_error(self, err):
        self.status_label.setText("Failed to load apps.")
        self.status_label.setStyleSheet("color: #ff5555;")

    def get_selected_app(self):
        selected = self.list_widget.selectedItems()
        if selected:
            name = selected[0].text()
            appid = selected[0].data(Qt.ItemDataRole.UserRole)
            path = rf"shell:AppsFolder\{appid}"
            return name, path
        return None, None

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton and event.position().y() < 60:
            self._start_pos = event.globalPosition().toPoint()
    def mouseMoveEvent(self, event):
        if hasattr(self, '_start_pos') and self._start_pos:
            delta = event.globalPosition().toPoint() - self._start_pos
            self.move(self.pos() + delta)
            self._start_pos = event.globalPosition().toPoint()
    def mouseReleaseEvent(self, event):
        self._start_pos = None
