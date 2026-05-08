import sys
from PyQt6.QtWidgets import QApplication, QSystemTrayIcon, QMenu
from PyQt6.QtCore import QTimer
from config import ConfigManager
from folder_icon import FolderIcon
from utils import VectorIcon, IconExtractor, DesktopMonitor
from dashboard import DashboardUI
from grid_overlay import GridOverlay

def warm_up():
    for f in cfg.get('folders', []):
        for app_data in f.get('apps', []):
            IconExtractor.get_icon_pixmap(app_data.get('path', ''), 48)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)
    cfg = ConfigManager.load()
    
    QTimer.singleShot(500, warm_up)
    
    dashboard = DashboardUI(cfg, [])
    dashboard.prewarm()
    
    grid_overlay = GridOverlay(cfg)
    dashboard.grid_overlay = grid_overlay
    
    wins = []
    for f in cfg['folders']:
        w = FolderIcon(f, cfg, dashboard)
        wins.append(w)
        w.show()
        
    dashboard.app_instances = wins
    
    tray = QSystemTrayIcon(VectorIcon.icon("settings"))
    tray.show()
    tray.activated.connect(lambda reason: dashboard.show() if reason == QSystemTrayIcon.ActivationReason.Trigger else None)
    
    m = QMenu()
    
    def toggle_grid():
        is_visible = grid_overlay.toggle()
        grid_action.setText("Hide Grid" if is_visible else "Show Grid")
    
    grid_action = m.addAction("Show Grid")
    grid_action.triggered.connect(toggle_grid)
    m.addSeparator()
    def add_folder():
        # Generate a truly unique ID by finding the max existing ID or using timestamp
        existing_ids = [int(f['id'].split('_')[1]) for f in cfg['folders'] if f['id'].startswith('folder_') and f['id'].split('_')[1].isdigit()]
        new_id_num = max(existing_ids) + 1 if existing_ids else len(cfg['folders']) + 1
        new_id = f"folder_{new_id_num}"
        
        new_f = {"id": new_id, "name": "New", "pos": [100,100], "apps": [], "color": "#ffffff"}
        cfg['folders'].append(new_f)
        ConfigManager.save(cfg)
        w = FolderIcon(new_f, cfg, dashboard)
        dashboard.app_instances.append(w)
        w.show()
        
    m.addAction("Add Folder", add_folder)
    m.addAction("Quit", app.quit)
    tray.setContextMenu(m)
    
    sys.exit(app.exec())
