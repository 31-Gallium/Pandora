import ctypes
import ctypes.wintypes
import time

user32 = ctypes.windll.user32

EnumWindows = user32.EnumWindows
EnumWindowsProc = ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.wintypes.HWND, ctypes.wintypes.LPARAM)
GetWindowTextW = user32.GetWindowTextW
IsWindowVisible = user32.IsWindowVisible
SetForegroundWindow = user32.SetForegroundWindow
ShowWindow = user32.ShowWindow

found = []

def enum_cb(hwnd, lParam):
    length = user32.GetWindowTextLengthW(hwnd)
    if length > 0:
        buf = ctypes.create_unicode_buffer(length + 1)
        GetWindowTextW(hwnd, buf, length + 1)
        title = buf.value
        if 'pandora' in title.lower() or 'electron' in title.lower():
            found.append((hwnd, title))
    return True

user32.EnumWindows(EnumWindowsProc(enum_cb), 0)

for hwnd, title in found:
    print(f"Found: HWND={hwnd}, Title={title}")

# Try to focus/restore
for hwnd, title in found:
    if 'pandora' in title.lower():
        ShowWindow(hwnd, 9)  # SW_RESTORE
        time.sleep(0.2)
        SetForegroundWindow(hwnd)
        print(f"Focused: {title}")
        break
else:
    if found:
        hwnd, title = found[0]
        ShowWindow(hwnd, 9)
        time.sleep(0.2)
        SetForegroundWindow(hwnd)
        print(f"Focused first match: {title}")
    else:
        print("No Electron/Pandora window found")
