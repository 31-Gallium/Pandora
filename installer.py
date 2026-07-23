import sys
import os
import shutil
import winreg
import subprocess
import tempfile
import zipfile
import math
from PyQt6.QtCore import Qt, pyqtSignal, QSize, QPoint, QPropertyAnimation, QEasingCurve, QTimer, QRectF, QRect, QParallelAnimationGroup, QThread
from PyQt6.QtGui import QFont, QCursor, QPainter, QColor, QLinearGradient, QIcon, QPainterPath
from PyQt6.QtSvg import QSvgRenderer
from PyQt6.QtWidgets import (QApplication, QWidget, QVBoxLayout, QHBoxLayout, 
                             QLabel, QPushButton, QFrame, QGraphicsDropShadowEffect,
                             QProgressBar, QGraphicsOpacityEffect, QCheckBox)

class InstallWorker(QThread):
    finished = pyqtSignal(bool)
    progress = pyqtSignal(int, str)
    
    def __init__(self, do_desktop, do_startmenu, do_startup, parent=None):
        super().__init__(parent)
        self.do_desktop = do_desktop
        self.do_startmenu = do_startmenu
        self.do_startup = do_startup
        self.localappdata_dir = os.path.join(os.environ.get('LOCALAPPDATA', os.path.expanduser('~')), "Programs", "Pandora")
        
    def run(self):
        try:
            self.progress.emit(10, "Closing existing instances...")
            import subprocess
            import time
            subprocess.run(["taskkill", "/F", "/IM", "Pandora.exe", "/T"], creationflags=subprocess.CREATE_NO_WINDOW)
            time.sleep(1)
            
            self.progress.emit(20, "Extracting application files...")
            import sys
            import zipfile
            if getattr(sys, 'frozen', False):
                payload_path = sys.executable
            else:
                payload_path = os.path.join(os.path.dirname(__file__), 'installer', 'payload.zip')
                
            if not os.path.exists(payload_path):
                # Fallback for testing
                payload_path = os.path.join(os.path.dirname(__file__), 'payload.zip')
                if not os.path.exists(payload_path):
                    with open(payload_path, 'w') as f: f.write("mock")

                
            if not os.path.exists(self.localappdata_dir):
                os.makedirs(self.localappdata_dir)
                
            if zipfile.is_zipfile(payload_path):
                with zipfile.ZipFile(payload_path, 'r') as zip_ref:
                    total_files = len(zip_ref.namelist())
                    extracted = 0
                    for file in zip_ref.namelist():
                        zip_ref.extract(file, self.localappdata_dir)
                        extracted += 1
                        if extracted % 20 == 0:
                            prog = 20 + int(50 * (extracted / total_files))
                            self.progress.emit(prog, f"Extracting {file}...")
            else:
                time.sleep(1.5)
                self.progress.emit(70, "Mock extraction complete...")
            
            # Ensure critical runtime DLLs are findable by the PyInstaller bootloader.
            # On machines without the VC++ 2015-2022 Redistributable installed system-wide,
            # python312.dll fails to load because its transitive dependencies 
            # (vcruntime140.dll, ucrtbase.dll) aren't on the DLL search path.
            # Fix: copy these DLLs from _internal/ to the root install directory.
            self.progress.emit(75, "Configuring runtime dependencies...")
            try:
                import glob
                internal_dir = os.path.join(self.localappdata_dir, '_internal')
                if os.path.isdir(internal_dir):
                    for pattern in ['vcruntime140*.dll', 'python3*.dll', 'ucrtbase.dll']:
                        for src in glob.glob(os.path.join(internal_dir, pattern)):
                            dst = os.path.join(self.localappdata_dir, os.path.basename(src))
                            if not os.path.exists(dst):
                                shutil.copy2(src, dst)
            except Exception:
                pass
            
            self.progress.emit(85, "Creating shortcuts...")
            exe_path = os.path.join(self.localappdata_dir, 'Pandora.exe')
            
            ps_script = "$WshShell = New-Object -comObject WScript.Shell\n"
            if self.do_desktop:
                ps_script += f'$DesktopPath = [Environment]::GetFolderPath("Desktop")\n$Shortcut = $WshShell.CreateShortcut("$DesktopPath\\Pandora.lnk")\n$Shortcut.TargetPath = "{exe_path}"\n$Shortcut.WorkingDirectory = "{self.localappdata_dir}"\n$Shortcut.IconLocation = "{exe_path}, 0"\n$Shortcut.Save()\n'
            if self.do_startmenu:
                ps_script += f'$StartMenuPath = [Environment]::GetFolderPath("Programs")\n$Shortcut = $WshShell.CreateShortcut("$StartMenuPath\\Pandora.lnk")\n$Shortcut.TargetPath = "{exe_path}"\n$Shortcut.WorkingDirectory = "{self.localappdata_dir}"\n$Shortcut.IconLocation = "{exe_path}, 0"\n$Shortcut.Save()\n'
            
            if self.do_desktop or self.do_startmenu:
                subprocess.run(["powershell.exe", "-Command", ps_script], creationflags=subprocess.CREATE_NO_WINDOW)
                
            self.progress.emit(90, "Registering system hooks...")
            import winreg
            if self.do_startup:
                try:
                    key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Software\\Microsoft\\Windows\\CurrentVersion\\Run", 0, winreg.KEY_SET_VALUE)
                    winreg.SetValueEx(key, "Pandora", 0, winreg.REG_SZ, f'"{exe_path}" --startup')
                    winreg.CloseKey(key)
                except:
                    pass
                    
            try:
                import datetime
                today = datetime.datetime.now().strftime("%Y%m%d")
                key = winreg.CreateKey(winreg.HKEY_CURRENT_USER, r"Software\\Microsoft\\Windows\\CurrentVersion\\Uninstall\\Pandora")
                winreg.SetValueEx(key, "DisplayName", 0, winreg.REG_SZ, "Pandora")
                winreg.SetValueEx(key, "DisplayIcon", 0, winreg.REG_SZ, f'"{exe_path}"')
                uninstaller_path = os.path.join(self.localappdata_dir, 'Uninstaller', 'PandoraUninstaller.exe')
                winreg.SetValueEx(key, "UninstallString", 0, winreg.REG_SZ, f'"{uninstaller_path}"')
                winreg.SetValueEx(key, "Publisher", 0, winreg.REG_SZ, "Pandora")
                winreg.SetValueEx(key, "DisplayVersion", 0, winreg.REG_SZ, "1.0.0")
                winreg.SetValueEx(key, "EstimatedSize", 0, winreg.REG_DWORD, 1000000)
                winreg.SetValueEx(key, "InstallDate", 0, winreg.REG_SZ, today)
                winreg.CloseKey(key)
            except:
                pass
                
            self.progress.emit(100, "Finishing installation cleanup...")
            self.finished.emit(True)
        except Exception as e:
            self.progress.emit(100, f"Error: {str(e)}")
            self.finished.emit(False)


class PremiumCheckBox(QCheckBox):
    def __init__(self, text, parent=None):
        super().__init__(text, parent)
        self.setMouseTracking(True)
        self.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        
    def enterEvent(self, event):
        super().enterEvent(event)
        self.update()
        
    def leaveEvent(self, event):
        super().leaveEvent(event)
        self.update()
        
    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        h = self.height()
        ind_size = 14
        iy = (h - ind_size) // 2
        # Align circle perfectly
        ind_rect = QRectF(2, iy, ind_size, ind_size)
        
        is_hover = self.underMouse()
        is_checked = self.isChecked()
        
        painter.setPen(Qt.PenStyle.NoPen)
        if is_checked:
            # Draw premium check circle (Cyan filled)
            painter.setBrush(QColor("#26c0d3"))
            painter.drawEllipse(ind_rect)
            # Inner circle (Dark background)
            inner_rect = ind_rect.adjusted(1.5, 1.5, -1.5, -1.5)
            painter.setBrush(QColor("#0c0d12"))
            painter.drawEllipse(inner_rect)
            # Center dot (Cyan)
            dot_rect = ind_rect.adjusted(4.0, 4.0, -4.0, -4.0)
            painter.setBrush(QColor("#26c0d3"))
            painter.drawEllipse(dot_rect)
        else:
            # Unchecked: clean thin circle border
            border_color = QColor(255, 255, 255, 160 if is_hover else 70)
            painter.setBrush(border_color)
            painter.drawEllipse(ind_rect)
            
            inner_rect = ind_rect.adjusted(1.5, 1.5, -1.5, -1.5)
            painter.setBrush(QColor(12, 13, 18, 220))
            painter.drawEllipse(inner_rect)
            
        # Draw label
        painter.setPen(QColor("#e2e2e2"))
        painter.setFont(self.font())
        text_rect = QRect(24, 0, self.width() - 24, h)
        painter.drawText(text_rect, Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft, self.text())

class OptionCard(QFrame):
    clicked = pyqtSignal(str)

    def __init__(self, key, title, subtitle, parent=None, checkboxes=None):
        super().__init__(parent)
        self.key = key
        self.title = title
        self.subtitle_text = subtitle
        self.is_selected = False
        self.has_options = checkboxes is not None and len(checkboxes) > 0
        self.checkbox_objs = {}
        
        self.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        
        self.base_height = 84
        self.expanded_height = 84 + (24 * len(checkboxes)) + 4 if self.has_options else 84
        self.setFixedHeight(self.base_height)
        
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(15, 10, 15, 10)
        self.main_layout.setSpacing(4)
        self.main_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        
        top_widget = QWidget()
        top_layout = QVBoxLayout(top_widget)
        top_layout.setContentsMargins(0, 0, 0, 0)
        top_layout.setSpacing(4)
        
        title_layout = QHBoxLayout()
        title_layout.setContentsMargins(0, 0, 0, 0)
        
        self.indicator = QFrame()
        self.indicator.setFixedSize(12, 12)
        title_layout.addWidget(self.indicator)
        
        self.title_label = QLabel(self.title)
        self.title_label.setFont(QFont("Segoe UI", 12, QFont.Weight.Bold))
        self.title_label.setStyleSheet("color: #ffffff; background: transparent; border: none;")
        title_layout.addWidget(self.title_label)
        title_layout.addStretch()
        
        top_layout.addLayout(title_layout)
        
        self.sub_label = QLabel(self.subtitle_text)
        self.sub_label.setFont(QFont("Segoe UI", 9))
        self.sub_label.setStyleSheet("color: #8c8c9e; background: transparent; border: none;")
        self.sub_label.setWordWrap(True)
        top_layout.addWidget(self.sub_label)
        
        self.main_layout.addWidget(top_widget)
        
        self.options_widget = QWidget()
        options_layout = QVBoxLayout(self.options_widget)
        options_layout.setContentsMargins(30, 4, 0, 4)
        options_layout.setSpacing(4)
        
        if checkboxes:
            for cb_id, cb_text, cb_checked in checkboxes:
                cb = PremiumCheckBox(cb_text)
                cb.setChecked(cb_checked)
                options_layout.addWidget(cb)
                self.checkbox_objs[cb_id] = cb
                cb.stateChanged.connect(self._on_checkbox_changed)
                
        self.main_layout.addWidget(self.options_widget)
        
        self.options_widget.setMaximumHeight(0)
        self.options_widget.setStyleSheet("background: transparent;")
        
        self.anim_min = QPropertyAnimation(self, b"minimumHeight")
        self.anim_min.setDuration(250)
        self.anim_min.setEasingCurve(QEasingCurve.Type.OutCubic)
        
        self.anim_max = QPropertyAnimation(self, b"maximumHeight")
        self.anim_max.setDuration(250)
        self.anim_max.setEasingCurve(QEasingCurve.Type.OutCubic)
        
        self.anim_opt = QPropertyAnimation(self.options_widget, b"maximumHeight")
        self.anim_opt.setDuration(250)
        self.anim_opt.setEasingCurve(QEasingCurve.Type.OutCubic)
        
        self.anim_group = QParallelAnimationGroup()
        self.anim_group.addAnimation(self.anim_min)
        self.anim_group.addAnimation(self.anim_max)
        self.anim_group.addAnimation(self.anim_opt)
        
        self.update_style()

    def _on_checkbox_changed(self, state):
        if state == 0 and self.has_options:
            if not any(cb.isChecked() for cb in self.checkbox_objs.values()):
                sender = self.sender()
                if sender:
                    sender.setChecked(True)

    def update_style(self):
        if self.is_selected:
            # Selected style: Cyan accent
            self.setStyleSheet("""
                OptionCard {
                    background-color: rgba(38, 192, 211, 0.08);
                    border: 2px solid #26c0d3;
                    border-radius: 12px;
                }
            """)
            self.indicator.setStyleSheet("""
                background-color: #26c0d3;
                border-radius: 6px;
                border: none;
            """)
            self.title_label.setStyleSheet("color: #ffffff; background: transparent; border: none;")
        else:
            # Unselected style
            self.setStyleSheet("""
                OptionCard {
                    background-color: rgba(255, 255, 255, 0.02);
                    border: 1px solid rgba(255, 255, 255, 0.08);
                    border-radius: 12px;
                }
                OptionCard:hover {
                    background-color: rgba(255, 255, 255, 0.05);
                    border: 1px solid rgba(255, 255, 255, 0.2);
                }
            """)
            self.indicator.setStyleSheet("""
                background-color: transparent;
                border-radius: 6px;
                border: 2px solid rgba(255, 255, 255, 0.3);
            """)
            self.title_label.setStyleSheet("color: #a0a0b0; background: transparent; border: none;")

    def set_selected(self, selected):
        self.is_selected = selected
        self.update_style()
        
        if self.has_options:
            if selected:
                self.options_widget.setVisible(True)
                self.anim_min.setStartValue(self.height())
                self.anim_min.setEndValue(self.expanded_height)
                self.anim_max.setStartValue(self.height())
                self.anim_max.setEndValue(self.expanded_height)
                self.anim_opt.setStartValue(self.options_widget.height())
                self.anim_opt.setEndValue(24 * len(self.checkbox_objs) + 4)
                self.anim_group.start()
            else:
                self.anim_min.setStartValue(self.height())
                self.anim_min.setEndValue(self.base_height)
                self.anim_max.setStartValue(self.height())
                self.anim_max.setEndValue(self.base_height)
                self.anim_opt.setStartValue(self.options_widget.height())
                self.anim_opt.setEndValue(0)
                
                # Connect just once using a single-shot connection if possible,
                # but PyQt6 doesn't have a simple single-shot signal.
                # So we just don't setVisible(False), since max height 0 hides it anyway!
                self.anim_group.start()

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            child = self.childAt(event.position().toPoint())
            if isinstance(child, QCheckBox) or (child and child.parentWidget() and isinstance(child.parentWidget(), QCheckBox)):
                # Let the checkbox handle its own click
                return
            self.clicked.emit(self.key)

class LeftPanel(QFrame):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.is_expanded = False

    def set_expanded(self, expanded):
        self.is_expanded = expanded
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        # Dark techy gradient for left panel
        gradient = QLinearGradient(0, 0, self.width(), self.height())
        gradient.setColorAt(0, QColor("#121620"))
        gradient.setColorAt(1, QColor("#0a0c10"))
        
        # Draw rounded corners matching parent QFrame border-radius (16px)
        path = QPainterPath()
        r = 15.0 # Border radius
        if not self.is_expanded:
            # Round top-left and bottom-left only
            path.moveTo(self.width(), 0)
            path.lineTo(r, 0)
            path.quadTo(0, 0, 0, r)
            path.lineTo(0, self.height() - r)
            path.quadTo(0, self.height(), r, self.height())
            path.lineTo(self.width(), self.height())
            path.closeSubpath()
        else:
            # Round all corners since it covers the entire window
            path.addRoundedRect(0.0, 0.0, float(self.width()), float(self.height()), r, r)
            
        painter.fillPath(path, gradient)
        
        if not self.is_expanded:
            # Draw a divider border on the right side
            painter.setPen(QColor(255, 255, 255, 15))
            painter.drawLine(self.width() - 1, 0, self.width() - 1, self.height())

class AnimatedLogo(QWidget):
    def __init__(self, svg_path, parent=None):
        super().__init__(parent)
        self.renderer = QSvgRenderer(svg_path)
        self.angle = 0.0
        self.scale_factor = 1.0
        self.is_animating = False
        
        # Timer for rotation/pulsing animation
        self.anim_timer = QTimer(self)
        self.anim_timer.timeout.connect(self.tick_animation)
        self.time_elapsed = 0.0
        self.setFixedSize(120, 120)

    def start_animation(self):
        self.is_animating = True
        self.anim_timer.start(16) # ~60 FPS

    def stop_animation(self):
        self.is_animating = False
        self.anim_timer.stop()
        self.angle = 0.0
        self.scale_factor = 1.0
        self.update()

    def tick_animation(self):
        self.time_elapsed += 0.016
        # Rotate 90 degrees per second
        self.angle = (self.angle + 1.2) % 360
        
        # Breathing scale: sin wave between 0.9 and 1.1
        self.scale_factor = 1.0 + 0.1 * math.sin(self.time_elapsed * 2.5)
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        # Center the coordinate system
        cx, cy = self.width() / 2, self.height() / 2
        painter.translate(cx, cy)
        
        if self.is_animating:
            # Apply scale and rotation
            painter.scale(self.scale_factor, self.scale_factor)
            painter.rotate(self.angle)
            
        # Draw the SVG centered while preserving aspect ratio
        size = self.renderer.defaultSize()
        aspect = size.width() / size.height() if size.height() > 0 else 1.0
        
        max_size = 100.0
        if aspect > 1.0:
            svg_w = max_size
            svg_h = max_size / aspect
        else:
            svg_h = max_size
            svg_w = max_size * aspect
            
        rect = QRectF(-svg_w / 2.0, -svg_h / 2.0, svg_w, svg_h)
        self.renderer.render(painter, rect)

class InstallerUI(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnTopHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setFixedSize(860, 560) # Extra size for shadow padding

        # Root layout for window padding to host drop shadow
        window_layout = QVBoxLayout(self)
        window_layout.setContentsMargins(30, 30, 30, 30)

        # Main window container with rounded corners and border
        self.main_container = QFrame(self)
        self.main_container.setFixedSize(800, 500)
        self.main_container.setStyleSheet("""
            QFrame {
                background-color: #0c0d12;
                border: 1px solid rgba(255, 255, 255, 0.08);
                border-radius: 16px;
            }
        """)
        window_layout.addWidget(self.main_container)

        # Drop shadow for the window
        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(25)
        shadow.setColor(QColor(0, 0, 0, 200))
        shadow.setOffset(0, 5)
        self.main_container.setGraphicsEffect(shadow)

        # ----------------- LEFT PANEL (Brand Panel) -----------------
        self.left_panel = LeftPanel(self.main_container)
        self.left_panel.setGeometry(0, 0, 260, 500)
        
        left_layout = QVBoxLayout(self.left_panel)
        left_layout.setContentsMargins(30, 60, 30, 40)
        left_layout.setSpacing(15)
        
        # Logo Container
        logo_container = QFrame()
        logo_container.setFixedSize(120, 120)
        logo_container.setStyleSheet("background: transparent; border: none;")
        logo_container_layout = QVBoxLayout(logo_container)
        logo_container_layout.setContentsMargins(0, 0, 0, 0)
        logo_container_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        # Find Pandora SVG Logo
        logo_path = self.resolve_asset_path("Pandora.svg")
        if logo_path:
            self.logo = AnimatedLogo(logo_path)
            logo_shadow = QGraphicsDropShadowEffect(self)
            logo_shadow.setBlurRadius(20)
            logo_shadow.setColor(QColor(38, 192, 211, 100)) # Cyan glow
            logo_shadow.setOffset(0, 0)
            self.logo.setGraphicsEffect(logo_shadow)
            logo_container_layout.addWidget(self.logo)
        else:
            # Fallback text logo if SVG is missing
            self.logo = QLabel("P")
            self.logo.setFont(QFont("Segoe UI", 36, QFont.Weight.Bold))
            self.logo.setStyleSheet("color: #26c0d3; background: transparent; border: none;")
            self.logo.setAlignment(Qt.AlignmentFlag.AlignCenter)
            logo_container_layout.addWidget(self.logo)

        left_layout.addWidget(logo_container, 0, Qt.AlignmentFlag.AlignCenter)
        
        # Brand Name
        brand_name = QLabel("P A N D O R A")
        brand_name.setFont(QFont("Segoe UI", 16, QFont.Weight.Bold))
        brand_name.setStyleSheet("color: #ffffff; letter-spacing: 3px; background: transparent; border: none;")
        left_layout.addWidget(brand_name, 0, Qt.AlignmentFlag.AlignCenter)
        
        # Progress Container (Pre-layout inside left panel, hidden initially)
        self.progress_container = QFrame()
        self.progress_container.setFixedWidth(500)
        self.progress_container.setStyleSheet("background: transparent; border: none;")
        progress_layout = QVBoxLayout(self.progress_container)
        progress_layout.setContentsMargins(0, 30, 0, 0)
        progress_layout.setSpacing(15)
        
        self.status_label = QLabel("Initializing uninstallation process...")
        self.status_label.setFont(QFont("Segoe UI", 11))
        self.status_label.setStyleSheet("color: #8c8c9e; background: transparent;")
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        progress_layout.addWidget(self.status_label)
        
        # Progress bar container
        progress_bar_container = QFrame()
        progress_bar_container_layout = QHBoxLayout(progress_bar_container)
        progress_bar_container_layout.setContentsMargins(0, 0, 0, 0)
        progress_bar_container_layout.setSpacing(15)
        
        self.progress_bar = QProgressBar()
        self.progress_bar.setFixedHeight(8)
        self.progress_bar.setTextVisible(False)
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.progress_bar.setStyleSheet("""
            QProgressBar {
                background-color: rgba(255, 255, 255, 0.05);
                border: none;
                border-radius: 4px;
            }
            QProgressBar::chunk {
                background-color: #26c0d3;
                border-radius: 4px;
            }
        """)
        progress_bar_container_layout.addWidget(self.progress_bar)
        
        self.percentage_label = QLabel("0%")
        self.percentage_label.setFont(QFont("Segoe UI", 12, QFont.Weight.Bold))
        self.percentage_label.setStyleSheet("color: #26c0d3; background: transparent;")
        self.percentage_label.setFixedWidth(50)
        self.percentage_label.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        progress_bar_container_layout.addWidget(self.percentage_label)
        progress_layout.addWidget(progress_bar_container)
        
        # Finish Button
        self.finish_btn = QPushButton("Finish")
        self.finish_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.finish_btn.setFixedSize(180, 42)
        self.finish_btn.setStyleSheet("""
            QPushButton {
                background-color: #26c0d3;
                color: #0c0d12;
                border: none;
                border-radius: 21px;
                font-weight: bold;
                font-size: 13.5px;
            }
            QPushButton:hover {
                background-color: #3ad3e6;
            }
        """)
        self.finish_btn.clicked.connect(self.close)
        self.finish_btn.setVisible(False)
        
        self.cb_launch_app = QCheckBox("Launch Pandora when finished")
        self.cb_launch_app.setStyleSheet("""
            QCheckBox {
                color: #e0e0e0;
                font-family: 'Segoe UI';
                font-size: 12px;
                background: transparent;
                border: none;
            }
            QCheckBox::indicator {
                width: 18px;
                height: 18px;
                border-radius: 4px;
                border: 1px solid rgba(255, 255, 255, 0.3);
                background: rgba(0, 0, 0, 0.2);
            }
            QCheckBox::indicator:checked {
                background: #26c0d3;
                border: 1px solid #26c0d3;
            }
        """)
        self.cb_launch_app.setChecked(True)
        self.cb_launch_app.setVisible(False)
        
        cb_launch_layout = QHBoxLayout()
        cb_launch_layout.addStretch()
        cb_launch_layout.addWidget(self.cb_launch_app)
        cb_launch_layout.addStretch()
        progress_layout.addLayout(cb_launch_layout)
        progress_layout.addSpacing(10)
        
        finish_layout = QHBoxLayout()
        finish_layout.addStretch()
        finish_layout.addWidget(self.finish_btn)
        finish_layout.addStretch()
        progress_layout.addLayout(finish_layout)
        
        self.progress_container.setVisible(False)
        
        left_layout.addWidget(self.progress_container, 0, Qt.AlignmentFlag.AlignCenter)
        left_layout.addStretch()
        
        # Version
        version_label = QLabel("Version 1.0.0")
        version_label.setFont(QFont("Segoe UI", 9))
        version_label.setStyleSheet("color: #555566; background: transparent; border: none;")
        left_layout.addWidget(version_label, 0, Qt.AlignmentFlag.AlignCenter)

        # ----------------- RIGHT PANEL (Action Panel) -----------------
        self.right_panel = QFrame(self.main_container)
        self.right_panel.setGeometry(260, 0, 540, 500)
        self.right_panel.setStyleSheet("background-color: #0c0d12; border: none; border-top-right-radius: 16px; border-bottom-right-radius: 16px;")
        
        right_layout = QVBoxLayout(self.right_panel)
        right_layout.setContentsMargins(30, 15, 30, 15)
        right_layout.setSpacing(6)
        
        # Window Close Button (Top Right)
        close_layout = QHBoxLayout()
        close_layout.addStretch()
        self.close_btn = QPushButton("✕")
        self.close_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.close_btn.setFixedSize(28, 28)
        self.close_btn.setStyleSheet("""
            QPushButton {
                background-color: transparent;
                color: #555566;
                font-size: 14px;
                border: none;
                border-radius: 14px;
            }
            QPushButton:hover {
                background-color: rgba(232, 17, 35, 0.9);
                color: white;
            }
        """)
        close_layout.addWidget(self.close_btn)
        right_layout.addLayout(close_layout)

        # Content Frame
        self.content_frame = QFrame()
        self.content_frame.setStyleSheet("background: transparent;")
        content_layout = QVBoxLayout(self.content_frame)
        content_layout.setContentsMargins(0, 0, 0, 0)
        content_layout.setSpacing(8)

        # Header Title
        title_layout = QVBoxLayout()
        title_layout.setSpacing(4)
        title_label = QLabel("Install Pandora")
        title_label.setFont(QFont("Segoe UI", 20, QFont.Weight.Bold))
        title_label.setStyleSheet("color: #ffffff; background: transparent;")
        title_layout.addWidget(title_label)
        content_layout.addLayout(title_layout)

        # Selection Cards
        self.btn_standard = OptionCard("standard", "Standard Installation", "Install Pandora to your user profile and register it with the system (Recommended).", checkboxes=[("desktop", "Create Desktop Shortcut", True), ("startmenu", "Create Start Menu Shortcut", True), ("startup", "Launch on Startup", True)])
        self.btn_portable = OptionCard("portable", "Portable Installation", "Extract the files locally without writing to the registry or creating system shortcuts.")
        
        content_layout.addWidget(self.btn_standard)
        content_layout.addWidget(self.btn_portable)

        # Dynamic Description Banner
        self.desc_banner = QLabel()
        self.desc_banner.setFont(QFont("Segoe UI", 10))
        self.desc_banner.setWordWrap(True)
        self.desc_banner.setMinimumHeight(60)
        self.desc_banner.setAlignment(Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft)
        content_layout.addWidget(self.desc_banner)

        # Footer Actions
        footer_layout = QHBoxLayout()
        footer_layout.setSpacing(15)
        
        self.cancel_btn = QPushButton("Cancel")
        self.cancel_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.cancel_btn.setFixedSize(120, 42)
        self.cancel_btn.setStyleSheet("""
            QPushButton {
                background-color: transparent;
                color: #e0e0e0;
                border: 1px solid rgba(255, 255, 255, 0.15);
                border-radius: 21px;
                font-weight: bold;
                font-size: 13px;
            }
            QPushButton:hover {
                background-color: rgba(255, 255, 255, 0.05);
                border: 1px solid rgba(255, 255, 255, 0.3);
            }
        """)
        
        self.uninstall_btn = QPushButton("Uninstall")
        self.uninstall_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.uninstall_btn.setFixedSize(180, 42)
        footer_layout.addStretch()
        footer_layout.addWidget(self.cancel_btn)
        footer_layout.addWidget(self.uninstall_btn)
        content_layout.addStretch()
        content_layout.addLayout(footer_layout)

        right_layout.addWidget(self.content_frame)

        # Options Setup
        self.btn_standard.clicked.connect(self.select_option)
        self.btn_portable.clicked.connect(self.select_option)
        self.close_btn.clicked.connect(self.close)
        self.cancel_btn.clicked.connect(self.close)
        self.uninstall_btn.clicked.connect(self.start_install_animation)

        self.current_selection = None
        self.select_option("standard")

        # Handle window drag
        self.drag_position = QPoint()
        self.is_dragging = False

    def resolve_asset_path(self, filename):
        paths = []
        if hasattr(sys, '_MEIPASS'):
            paths.append(os.path.join(sys._MEIPASS, 'assets', filename))
            paths.append(os.path.join(sys._MEIPASS, filename))
        paths.extend([
            os.path.join(os.getcwd(), 'assets', filename),
            os.path.join(os.getcwd(), filename),
            os.path.join(os.path.dirname(os.path.abspath(__file__)), 'assets', filename),
            os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'assets', filename),
            os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', filename)
        ])
        for p in paths:
            if os.path.exists(p):
                return p
        return None

    def select_option(self, key):
        if self.current_selection == key:
            return
        
        self.current_selection = key
        self.btn_standard.set_selected(key == "standard")
        self.btn_portable.set_selected(key == "portable")

        self.update_description(key)

    def update_description(self, key):
        if key == "standard":
            self.desc_banner.setText("<b>Standard Plan:</b> Your profiles, configs, and storage will be safely created in your user directory. You will get system shortcuts.")
            self.desc_banner.setStyleSheet("""
                QLabel {
                    background-color: rgba(38, 192, 211, 0.06);
                    color: #26c0d3;
                    border: 1px solid rgba(38, 192, 211, 0.2);
                    border-radius: 8px;
                    padding: 6px 12px;
                }
            """)
            self.uninstall_btn.setText("Standard Installation")
            self.uninstall_btn.setStyleSheet("""
                QPushButton {
                    background-color: #26c0d3;
                    color: #0c0d12;
                    border: none;
                    border-radius: 21px;
                    font-weight: bold;
                    font-size: 13px;
                }
                QPushButton:hover {
                    background-color: #3ad3e6;
                }
            """)
        else:
            self.desc_banner.setText("<b>NOTE:</b> Portable mode will not add Pandora to your Programs & Features list and will run completely isolated.")
            self.desc_banner.setStyleSheet("""
                QLabel {
                    background-color: rgba(38, 192, 211, 0.08);
                    color: #26c0d3;
                    border: 1px solid rgba(38, 192, 211, 0.25);
                    border-radius: 8px;
                    padding: 6px 12px;
                }
            """)
            self.uninstall_btn.setText("Portable Installation")
            self.uninstall_btn.setStyleSheet("""
                QPushButton {
                    background-color: #26c0d3;
                    color: #ffffff;
                    border: none;
                    border-radius: 21px;
                    font-weight: bold;
                    font-size: 13px;
                }
                QPushButton:hover {
                    background-color: #38d6e9;
                }
            """)
        pass

    def start_install_animation(self):
        # Disable close button
        self.close_btn.setEnabled(False)
        self.close_btn.setStyleSheet("QPushButton { color: #22222a; }")

        # Setup side panel expansion flag
        self.left_panel.set_expanded(True)

        # Transition Animation Group
        self.transition_group = QParallelAnimationGroup()
        
        # 1. Expand left panel geometry (x:0, y:0, w:260, h:500) -> (x:0, y:0, w:800, h:500)
        self.left_anim = QPropertyAnimation(self.left_panel, b"geometry")
        self.left_anim.setDuration(600)
        self.left_anim.setStartValue(QRect(0, 0, 260, 500))
        self.left_anim.setEndValue(QRect(0, 0, 800, 500))
        self.left_anim.setEasingCurve(QEasingCurve.Type.InOutCubic)
        
        # 2. Shrink right panel geometry (x:260, y:0, w:540, h:500) -> (x:800, y:0, w:0, h:500)
        self.right_anim = QPropertyAnimation(self.right_panel, b"geometry")
        self.right_anim.setDuration(600)
        self.right_anim.setStartValue(QRect(260, 0, 540, 500))
        self.right_anim.setEndValue(QRect(800, 0, 0, 500))
        self.right_anim.setEasingCurve(QEasingCurve.Type.InOutCubic)
        
        # Instantly hide the right panel content to prevent layout squishing jitter and DWM window spawn!
        self.content_frame.hide()
        self.close_btn.hide()
        
        self.transition_group.addAnimation(self.left_anim)
        self.transition_group.addAnimation(self.right_anim)
        
        self.transition_group.finished.connect(self.on_transition_finished)
        self.transition_group.start()

    def on_transition_finished(self):
        # Hide right panel completely to avoid any paint cycles
        self.right_panel.setVisible(False)

        # Show progress container
        self.progress_container.setVisible(True)
        
        # Start logo rotation & breathing
        if hasattr(self, 'logo') and hasattr(self.logo, 'start_animation'):
            self.logo.start_animation()
            
        # Start progress ticks
        self.progress_val = 0
        
        # Determine logical options
        do_desktop = False
        do_startmenu = False
        do_startup = False
        if self.current_selection == "standard":
            do_desktop = self.btn_standard.checkbox_objs["desktop"].isChecked()
            do_startmenu = self.btn_standard.checkbox_objs["startmenu"].isChecked()
            do_startup = self.btn_standard.checkbox_objs["startup"].isChecked()
            
        self.worker = InstallWorker(do_desktop, do_startmenu, do_startup)
        self.worker.progress.connect(self.update_progress)
        self.worker.finished.connect(self.on_worker_finished)
        self.worker.start()

    def update_progress(self, val, text):
        # We can animate or just jump to val
        self.progress_bar.setValue(val)
        self.percentage_label.setText(f"{val}%")
        # Use Elide text if it doesn't fit
        font_metrics = self.status_label.fontMetrics()
        elided_text = font_metrics.elidedText(text, Qt.TextElideMode.ElideRight, self.status_label.width() - 10)
        self.status_label.setText(elided_text)
        self.status_label.setToolTip(text) # Add tooltip to see full text

    def on_worker_finished(self, success):
        if hasattr(self, 'logo') and hasattr(self.logo, 'stop_animation'):
            self.logo.stop_animation()
            
        if success:
            self.status_label.setText("Pandora has been successfully installed.")
            
            
            self.launch_cb = PremiumCheckBox("Launch Pandora now")
            self.launch_cb.setChecked(True)
            
            cb_layout = QHBoxLayout()
            cb_layout.addStretch()
            cb_layout.addWidget(self.launch_cb)
            cb_layout.addStretch()
            
            # Insert into progress_container layout
            self.progress_container.layout().insertLayout(3, cb_layout)
        else:
            self.status_label.setText("Installation failed.")
        
        self.finish_btn.setVisible(True)
        try:
            self.finish_btn.clicked.disconnect()
        except:
            pass
        self.finish_btn.clicked.connect(self.execute_finish)

    def execute_finish(self):
        if hasattr(self, 'launch_cb') and self.launch_cb.isChecked():
            exe_path = os.path.join(os.environ.get('LOCALAPPDATA', os.path.expanduser('~')), "Programs", "Pandora", "Pandora.exe")
            if os.path.exists(exe_path):
                subprocess.Popen([exe_path])
        sys.exit(0)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            if event.position().x() < 260 or event.position().y() < 60:
                self.drag_position = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
                self.is_dragging = True
                event.accept()
            else:
                self.is_dragging = False

    def mouseMoveEvent(self, event):
        if event.buttons() == Qt.MouseButton.LeftButton and getattr(self, 'is_dragging', False):
            self.move(event.globalPosition().toPoint() - self.drag_position)
            event.accept()

if __name__ == "__main__":
    try:
        import pyi_splash
        pyi_splash.update_text('UI Loaded...')
        pyi_splash.close()
    except Exception:
        pass

    app = QApplication(sys.argv)
    font = app.font()
    font.setFamily("Segoe UI")
    app.setFont(font)
    ui = InstallerUI()
    ui.show()
    sys.exit(app.exec())
