import ctypes
import ctypes.wintypes
import time
import pyautogui

user32 = ctypes.windll.user32

# Find the Electron window
found = []
def enum_cb(hwnd, lParam):
    length = user32.GetWindowTextLengthW(hwnd)
    if length > 0:
        buf = ctypes.create_unicode_buffer(length + 1)
        user32.GetWindowTextW(hwnd, buf, length + 1)
        title = buf.value
        if 'pandora' in title.lower() and 'dashboard' in title.lower() and 'chrome' not in title.lower():
            found.append((hwnd, title))
    return True

EnumWindowsProc = ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.wintypes.HWND, ctypes.wintypes.LPARAM)
user32.EnumWindows(EnumWindowsProc(enum_cb), 0)

if not found:
    print("No Pandora Dashboard window found")
    exit(1)

hwnd, title = found[0]
print(f"Found: {title} (HWND: {hwnd})")

# Get window rect
rect = ctypes.wintypes.RECT()
user32.GetWindowRect(hwnd, ctypes.byref(rect))
print(f"Window rect: left={rect.left}, top={rect.top}, right={rect.right}, bottom={rect.bottom}")

# Focus and restore
user32.ShowWindow(hwnd, 9)  # SW_RESTORE
time.sleep(0.3)
user32.SetWindowPos(hwnd, -1, 0, 0, 0, 0, 3) # HWND_TOPMOST, SWP_NOMOVE | SWP_NOSIZE
time.sleep(0.5)

# Click on the Halo tab (5th icon in sidebar, roughly)
# The sidebar icons are at x ~= rect.left + 310 (the sidebar icons column)
# Looking at the screenshot, sidebar icons are around x=310
# The halo icon (4th from top after general) should be around y = rect.top + 350
sidebar_x = rect.left + 312
halo_y = rect.top + 353  # the target/circles icon

print(f"Clicking halo tab at ({sidebar_x}, {halo_y})")
pyautogui.click(sidebar_x, halo_y)
time.sleep(1)

# Take screenshot
width = rect.right - rect.left
height = rect.bottom - rect.top
pyautogui.screenshot('c:/Users/Base/Desktop/Seb/Pandora/scratch/halo_tab.png', region=(rect.left, rect.top, width, height))
print("Screenshot saved")
