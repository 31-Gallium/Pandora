import ctypes
import time

def main():
    hwnd = ctypes.windll.user32.FindWindowW(None, "Pandora Dashboard — UI Prototype")
    if hwnd:
        print(f"Found Electron window (HWND: {hwnd}). Bringing to front...")
        # Force window to show and restore
        ctypes.windll.user32.ShowWindow(hwnd, 9) # SW_RESTORE
        ctypes.windll.user32.SetForegroundWindow(hwnd)
        print("Done.")
    else:
        print("Electron window not found by title 'Pandora Dashboard — UI Prototype'.")

if __name__ == "__main__":
    main()
