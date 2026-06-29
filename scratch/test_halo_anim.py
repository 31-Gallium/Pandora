import os
import time
import ctypes
from PIL import ImageGrab

def press_tilde():
    print("Pressing tilde key (down)...")
    ctypes.windll.user32.keybd_event(0xC0, 0, 0, 0)

def release_tilde():
    print("Releasing tilde key (up)...")
    ctypes.windll.user32.keybd_event(0xC0, 0, 2, 0)

def capture(name):
    screenshot = ImageGrab.grab()
    artifact_dir = r"C:\Users\Base\.gemini\antigravity-ide\brain\e7c63557-e028-47bf-831c-b6bafb66141a\scratch"
    os.makedirs(artifact_dir, exist_ok=True)
    save_path = os.path.join(artifact_dir, f"{name}.png")
    screenshot.save(save_path)
    print(f"Captured {name} to {save_path}")

def run_test():
    print("Waiting 3 seconds for app to settle...")
    time.sleep(3)
    
    # 1. Trigger open
    press_tilde()
    
    # Capture mid-way open (0.25 seconds)
    time.sleep(0.25)
    capture("halo_mid_open")
    
    # Capture fully open (wait another 0.35s, total 0.6s)
    time.sleep(0.35)
    capture("halo_fully_open")
    
    # 2. Trigger close
    release_tilde()
    
    # Capture mid-way close (0.25 seconds)
    time.sleep(0.25)
    capture("halo_mid_close")
    
    # Capture fully closed (wait another 0.35s, total 0.6s)
    time.sleep(0.35)
    capture("halo_fully_closed")

if __name__ == "__main__":
    run_test()
