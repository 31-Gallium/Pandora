import os
import time
from PIL import ImageGrab
import sys

def take_screenshot():
    # Capture the entire screen
    screenshot = ImageGrab.grab()
    
    # Define a path to save the screenshot in the artifact directory
    artifact_dir = r"C:\Users\Base\.gemini\antigravity-ide\brain\e7c63557-e028-47bf-831c-b6bafb66141a\scratch"
    os.makedirs(artifact_dir, exist_ok=True)
    save_path = os.path.join(artifact_dir, "current_screen_merged.png")
    
    # Save the screenshot
    screenshot.save(save_path)
    print(f"Screenshot saved to {save_path}")

if __name__ == "__main__":
    take_screenshot()
