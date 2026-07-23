import sys
import os
import ctypes

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

try:
    import hub_modules.vis_engine_bridge as vis
    
    success = vis.init_vis_engine(512, 512, 0)
    print(f"Init Success: {success}")
    
    if success:
        pts = 120
        radii = [200.0] * (pts + 1)
        fluids = [1.0] * pts
        
        img = vis.render_vis_frame(radii, fluids, 400.0, 10.0, 1.0, 0.0, 0.0, 1.0, 1.0, 1.0, 1.0)
        print(f"Render Success: {img is not None}")
        
        vis.destroy_vis_engine()
        print("Destroyed successfully")
except Exception as e:
    print(f"Error: {e}")
