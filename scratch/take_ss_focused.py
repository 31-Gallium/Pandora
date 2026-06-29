import ctypes
import time
from PIL import ImageGrab
import sys

def main():
    user32 = ctypes.windll.user32
    hwnd_electron = user32.FindWindowW(None, "Pandora Dashboard — UI Prototype")
    
    if hwnd_electron:
        print(f"Found Electron (HWND: {hwnd_electron})")
        # Find active foreground window
        hwnd_fg = user32.GetForegroundWindow()
        if hwnd_fg and hwnd_fg != hwnd_electron:
            print(f"Minimizing foreground window (HWND: {hwnd_fg}) to reveal Electron...")
            user32.ShowWindow(hwnd_fg, 6) # SW_MINIMIZE
            time.sleep(0.3)
        
        # Now focus Electron
        user32.ShowWindow(hwnd_electron, 9) # SW_RESTORE
        user32.SetForegroundWindow(hwnd_electron)
        time.sleep(0.5)
        
        img = ImageGrab.grab()
        img.save(sys.argv[1])
        print("Success.")
    else:
        print("Electron window not found.")

if __name__ == "__main__":
    main()
