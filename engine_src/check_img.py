import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
import hub_modules.vis_engine_bridge as vis
from PyQt6.QtWidgets import QApplication
import time

app = QApplication([])
vis.init_vis_engine(512, 512, 0)
radii = [100.0] * 121
fluids = [1.0] * 121

img = None
for i in range(10):
    img = vis.render_vis_frame(radii, fluids, 200, 2, 1,1,1, 1,1,1, 1)
    time.sleep(0.05)

if img:
    img.save("test_vis.png")
    print("Saved test_vis.png")
