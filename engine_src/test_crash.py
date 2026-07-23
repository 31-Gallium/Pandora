import sys
import os
import ctypes

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
import hub_modules.vis_engine_bridge as vis

def run():
    print("Init:", vis.init_vis_engine(512, 512, 0))
    pts = 120
    radii = [200.0] * (pts + 1)
    fluids = [1.0] * (pts + 1)
    
    print("Calling render...")
    try:
        img = vis.render_vis_frame(radii, fluids, 400.0, 10.0, 1.0, 0.0, 0.0, 1.0, 1.0, 1.0, 1.0)
        print("Render result:", img is not None)
    except Exception as e:
        print("Python Exception:", e)
        
run()
