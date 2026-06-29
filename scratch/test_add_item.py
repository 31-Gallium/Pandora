import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from PyQt6.QtWidgets import QApplication
from dashboard import DashboardUI
from config import ConfigManager

if __name__ == "__main__":
    app = QApplication(sys.argv)
    
    cfg = ConfigManager.load()
    print("Config loaded.")
    
    dashboard = DashboardUI(cfg, [])
    print("DashboardUI created.")
    
    # Find the launcher widget layer ID in config
    lid = None
    hub_cfg = cfg.get("hub_config", {})
    layers = hub_cfg.get("layers", [])
    for l in layers:
        if l and l.get('type') == 'launcher':
            lid = l['id']
            break
            
    if not lid:
        print("No launcher module found in configuration!")
        sys.exit(1)
        
    print(f"Testing _add_launcher_item for layer: {lid}")
    
    # This simulates the button click and the full UI refresh loop
    try:
        dashboard.show()
        QApplication.processEvents()
        print("Dashboard shown.")
        
        dashboard._add_launcher_item(lid)
        print("Launcher item added.")
        
        # Process events several times to force layout calculations
        for _ in range(10):
            QApplication.processEvents()
            import time
            time.sleep(0.05)
            
        print("Success! Launcher item added successfully.")
    except Exception as e:
        import traceback
        print("ERROR/CRASH detected:")
        traceback.print_exc()
