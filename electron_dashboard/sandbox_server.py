import sys
import os
import json
import threading
sys.stdout = open("C:/Users/Base/Desktop/Seb/Pandora/scratch/sandbox_stdout.txt", "w")
sys.stderr = open("C:/Users/Base/Desktop/Seb/Pandora/scratch/sandbox_stderr.txt", "w")
from PyQt6.QtWidgets import QApplication, QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QComboBox, QLabel
from PyQt6.QtGui import QPainter, QColor, QConicalGradient, QLinearGradient, QPen, QBrush
from PyQt6.QtCore import Qt, pyqtSignal, QObject, QTimer, QPropertyAnimation, QEasingCurve

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from ui_dashboard_common import SandboxFolderIcon, SandboxFolderView
from config import ConfigManager

class StdinReader(QObject):
    data_received = pyqtSignal(dict)
    def run(self):
        for line in sys.stdin:
            line = line.strip()
            if not line: continue
            try:
                data = json.loads(line)
                self.data_received.emit(data)
            except: pass

class SandboxWindow(QWidget):
    def __init__(self, cfg):
        super().__init__()
        self.cfg = cfg
        # Frameless + Tool + AlwaysOnTop. We handle z-layer manually by hiding on blur in Electron.
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.Tool | Qt.WindowType.WindowStaysOnTopHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating)
        
        self.fade_anim = QPropertyAnimation(self, b"windowOpacity")
        self.fade_anim.setDuration(300)
        self.fade_anim.setEasingCurve(QEasingCurve.Type.OutCubic)
        
        self._init_ui()

            
    def _init_ui(self):
        self.angle = 0
        self.bg_color = "transparent"
        self.anim_timer = QTimer(self)
        self.anim_timer.timeout.connect(self.update_angle)
        self.anim_timer.start(16)
        
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(16, 16, 16, 16)
        
        # TOP UI
        top_layout = QHBoxLayout()
        top_layout.setAlignment(Qt.AlignmentFlag.AlignHCenter)
        self.btn_col = QPushButton("Collapsed")
        self.btn_exp = QPushButton("Expanded")
        btn_style = """
            QPushButton {
                background: transparent;
                color: #888;
                border: none;
                padding: 6px 16px;
                font-weight: 500;
                font-size: 13px;
                border-radius: 4px;
            }
            QPushButton:hover {
                color: #bbb;
                background: rgba(255,255,255,0.05);
            }
            QPushButton:checked {
                color: #eee;
                background: rgba(255,255,255,0.08);
                font-weight: bold;
            }
        """
        self.btn_col.setStyleSheet(btn_style)
        self.btn_col.setCheckable(True)
        self.btn_col.setChecked(True)
        self.btn_exp.setStyleSheet(btn_style)
        self.btn_exp.setCheckable(True)
        top_layout.addWidget(self.btn_col)
        top_layout.addWidget(self.btn_exp)
        self.layout.addLayout(top_layout)
        
        self.btn_col.clicked.connect(lambda checked: self.set_mode("collapsed"))
        self.btn_exp.clicked.connect(lambda checked: self.set_mode("expanded"))
        
        # CONTENT
        self.content_layout = QVBoxLayout()
        self.content_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.layout.addLayout(self.content_layout)
        
        # BOT UI
        bot_layout = QHBoxLayout()
        bot_layout.setAlignment(Qt.AlignmentFlag.AlignRight)
        bot_lbl = QLabel("BACKGROUND")
        bot_lbl.setStyleSheet("color: #8a8a93; font-size: 10px; font-weight: bold;")
        self.combo_bg = QComboBox()
        self.combo_bg.addItems(["Transparent", "Black", "White"])
        self.combo_bg.setStyleSheet("""
            QComboBox {
                background: rgba(255,255,255,0.05);
                color: #eee;
                border: 1px solid rgba(255,255,255,0.1);
                padding: 4px 12px;
                border-radius: 6px;
                font-size: 11px;
                font-weight: bold;
                min-width: 80px;
            }
            QComboBox:hover {
                background: rgba(255,255,255,0.1);
                border: 1px solid rgba(255,255,255,0.2);
            }
            QComboBox::drop-down {
                border: none;
                width: 24px;
            }
            QComboBox::down-arrow {
                image: none;
                border-left: 4px solid transparent;
                border-right: 4px solid transparent;
                border-top: 5px solid rgba(255,255,255,0.6);
                margin-right: 8px;
            }
            QComboBox QAbstractItemView {
                background: #1a1a1f;
                color: #eee;
                border: 1px solid rgba(255,255,255,0.1);
                border-radius: 6px;
                selection-background-color: rgba(255,255,255,0.1);
                selection-color: #fff;
                outline: none;
            }
        """)
        bot_layout.addWidget(bot_lbl)
        bot_layout.addWidget(self.combo_bg)
        self.layout.addLayout(bot_layout)
        
        self.combo_bg.currentTextChanged.connect(self.ui_set_bg)
        
        # Real UI
        self.mode = "collapsed"
        self.sandbox_icon = SandboxFolderIcon(self.cfg)
        self.sandbox_view = SandboxFolderView(self.sandbox_icon.data, self.sandbox_icon, parent=self)
        self.sandbox_view.anim_progress = 1.0
        
        self.content_layout.addWidget(self.sandbox_icon)
        self.content_layout.addWidget(self.sandbox_view)
        
        self.sandbox_icon.show()
        self.sandbox_view.hide()
        self.current_content = self.sandbox_icon

        self.target_x = 0
        self.target_y = 0
        self.target_w = 400
        self.target_h = 700
        
        self.move_timer = QTimer(self)
        self.move_timer.setSingleShot(True)
        self.move_timer.timeout.connect(self.do_fade_in)
        
        self.layout.setStretch(1, 1)
        # Start hidden but force initial buffer creation to prevent first-time jank
        self.setWindowOpacity(0.0)
        self.show()
        self.hide()
        
    def ui_set_bg(self, bg):
        self.bg_color = bg.lower()
        self.update()
        
    def update_angle(self):
        self.angle = (self.angle - 2) % 360
        self.update()
        
    def changeEvent(self, event):
        from PyQt6.QtCore import QEvent
        if event.type() == QEvent.Type.ActivationChange:
            import json
            import sys
            state = "focus" if self.isActiveWindow() else "blur"
            sys.__stdout__.write(json.dumps({"event": state}) + "\n")
            sys.__stdout__.flush()
        super().changeEvent(event)
        
    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        rect = self.rect().adjusted(2, 2, -2, -2)
        
        if self.bg_color == "black":
            painter.setBrush(QColor("#0a0a0c"))
        elif self.bg_color == "white":
            painter.setBrush(QColor("#ffffff"))
        else:
            painter.setBrush(QColor(0, 0, 0, 1))
            
        painter.setPen(Qt.PenStyle.NoPen)
        # Convert rect to QRectF for precision if needed, but ints are fine.
        painter.drawRoundedRect(rect, 20.0, 20.0)
            
        # Ensure rect center is valid for gradient
        center = rect.center()
        
        grad = QConicalGradient(float(center.x()), float(center.y()), float(self.angle))
        if self.bg_color == "white":
            grad.setColorAt(0.0, QColor(0, 0, 0, 100))
            grad.setColorAt(0.5, QColor(0, 0, 0, 10))
            grad.setColorAt(1.0, QColor(0, 0, 0, 100))
        else:
            grad.setColorAt(0.0, QColor(255, 255, 255, 100))
            grad.setColorAt(0.5, QColor(255, 255, 255, 0))
            grad.setColorAt(1.0, QColor(255, 255, 255, 100))
            
        pen = QPen(QBrush(grad), 2)
        painter.setPen(pen)
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawRoundedRect(rect, 20.0, 20.0)
            
    def set_mode(self, mode):
        if mode == self.mode:
            self.btn_col.setChecked(self.mode == "collapsed")
            self.btn_exp.setChecked(self.mode == "expanded")
            return
        self.mode = mode
        
        self.btn_col.setChecked(mode == "collapsed")
        self.btn_exp.setChecked(mode == "expanded")
        
        if mode == "collapsed":
            self.sandbox_view.hide()
            self.sandbox_icon.show()
            self.current_content = self.sandbox_icon
        else:
            self.sandbox_icon.hide()
            self.sandbox_view.folder_data = self.sandbox_icon.data
            self.sandbox_view.refresh()
            self.sandbox_view.show()
            self.current_content = self.sandbox_view
            
    def handle_command(self, cmd):
        action = cmd.get("action")
        with open("C:/Users/Base/Desktop/Seb/Pandora/scratch/sandbox_debug.txt", "a") as f:
            f.write(f"CMD received: {cmd}\n")
            
        if action == "set_mode":
            self.set_mode(cmd.get("mode", "collapsed"))
        elif action == "set_bg":
            bg = cmd.get("bg", "transparent").lower()
            idx = self.combo_bg.findText(bg.capitalize())
            if idx >= 0: self.combo_bg.setCurrentIndex(idx)
        elif action == "update_config":
            data = cmd.get("data", {})
            t_type = data.get("template_type", "grid")
            t_name = data.get("template_name", "Default")
            settings = data.get("settings", {})
            
            self.sandbox_icon.data['template_type'] = t_type
            self.sandbox_icon.data['template_name'] = t_name
            self.sandbox_icon.data['show_cover'] = settings.get('show_cover', False)
            self.sandbox_icon.data['show_title'] = settings.get('show_title', True)
            self.sandbox_icon.local_settings = settings
            self.sandbox_icon.update()
            
            if self.mode == "expanded":
                self.sandbox_view.folder_data = self.sandbox_icon.data
                self.sandbox_view.refresh()
                
        elif action == "hide":
            self.move_timer.stop()
            self.do_fade_out()
        elif action == "show":
            ex, ey, ew, eh = cmd.get("x", 0), cmd.get("y", 0), cmd.get("width", 0), cmd.get("height", 0)
            self.target_x = ex
            self.target_y = ey
            self.target_w = ew
            self.target_h = eh
            self.move_timer.start(150)

    def do_fade_in(self):
        if hasattr(self, "target_w") and hasattr(self, "target_h"):
            self.setFixedSize(int(self.target_w), int(self.target_h))
            
        self.move(int(self.target_x), int(self.target_y))
        
        self.fade_anim.stop()
        current = self.windowOpacity()
        if current < 0.01:
            self.setWindowOpacity(0.0)
        self.show()
        self.raise_()  # Bring to front alongside Electron
        self.fade_anim.setStartValue(self.windowOpacity())
        self.fade_anim.setEndValue(1.0)
        self.fade_anim.start()
        


    def do_fade_out(self):
        if self.isHidden():
            return
        self.fade_anim.stop()
        self.fade_anim.setStartValue(self.windowOpacity())
        self.fade_anim.setEndValue(0.0)
        try:
            self.fade_anim.finished.disconnect(self._on_fade_out_done)
        except Exception:
            pass
        self.fade_anim.finished.connect(self._on_fade_out_done)
        self.fade_anim.start()

    def _on_fade_out_done(self):
        if self.windowOpacity() <= 0.01:
            self.hide()
        try:
            self.fade_anim.finished.disconnect(self._on_fade_out_done)
        except Exception:
            pass

def main():
    import traceback
    try:
        app = QApplication(sys.argv)
        cfg = ConfigManager.load()
        win = SandboxWindow(cfg)
        reader = StdinReader()
        reader.data_received.connect(win.handle_command)
        thread = threading.Thread(target=reader.run, daemon=True)
        thread.start()
        sys.exit(app.exec())
    except Exception as e:
        with open("C:/Users/Base/Desktop/Seb/Pandora/scratch/sandbox_debug.txt", "w") as f:
            f.write(str(e) + "\n" + traceback.format_exc())

if __name__ == "__main__":
    main()
