import ctypes
import time
from PIL import ImageGrab
import sys

# Windows API Constants
GW_HWNDNEXT = 2
SW_MINIMIZE = 6
SW_RESTORE = 9

def get_window_title(hwnd):
    length = ctypes.windll.user32.GetWindowTextLengthW(hwnd)
    buff = ctypes.create_unicode_buffer(length + 1)
    ctypes.windll.user32.GetWindowTextW(hwnd, buff, length + 1)
    return buff.value

def is_window_visible(hwnd):
    return ctypes.windll.user32.IsWindowVisible(hwnd)

def main():
    user32 = ctypes.windll.user32
    hwnd_electron = user32.FindWindowW(None, "Pandora Dashboard — UI Prototype")
    
    if not hwnd_electron:
        print("Electron window not found.")
        return

    # Find the top-most window
    hwnd = user32.GetTopWindow(None)
    while hwnd:
        if is_window_visible(hwnd) and hwnd != hwnd_electron:
            title = get_window_title(hwnd)
            # Minimize any visible window that is not our Electron app or VS Code
            if title and "Visual Studio Code" not in title and "Pandora" not in title and "Task Manager" not in title:
                print(f"Minimizing: {title} (HWND: {hwnd})")
                user32.ShowWindow(hwnd, SW_MINIMIZE)
        hwnd = user32.GetWindow(hwnd, GW_HWNDNEXT)
        
    time.sleep(0.5)
    # Restore and focus Electron
    user32.ShowWindow(hwnd_electron, SW_RESTORE)
    user32.SetForegroundWindow(hwnd_electron)
    time.sleep(0.5)
    
    img = ImageGrab.grab()
    img.save(sys.argv[1])
    print("Success.")

if __name__ == "__main__":
    main()
