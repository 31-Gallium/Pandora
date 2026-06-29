import ctypes
import ctypes.wintypes
import time
import pyautogui

user32 = ctypes.windll.user32

found = []
def enum_cb(hwnd, lParam):
    length = user32.GetWindowTextLengthW(hwnd)
    if length > 0:
        buf = ctypes.create_unicode_buffer(length + 1)
        user32.GetWindowTextW(hwnd, buf, length + 1)
        title = buf.value
        if 'pandora dashboard' in title.lower():
            found.append((hwnd, title))
    return True

EnumWindowsProc = ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.wintypes.HWND, ctypes.wintypes.LPARAM)
user32.EnumWindows(EnumWindowsProc(enum_cb), 0)

if not found:
    print("No Pandora Dashboard window found")
    exit(1)

hwnd, title = found[0]

# Focus and restore
user32.ShowWindow(hwnd, 9)
time.sleep(0.3)
user32.SetForegroundWindow(hwnd)
time.sleep(0.5)

# Assuming the window rect
rect = ctypes.wintypes.RECT()
user32.GetWindowRect(hwnd, ctypes.byref(rect))

# The radial menu is in the center of the main panel.
# Main panel is right of sidebar.
# Let's click the top slice. Center of radial is ~ cx=250, cy=250 inside the SVG.
# We'll just click at x = rect.left + 500, y = rect.top + 300 to hit the top slice.
# We can also take a screenshot before clicking.

pyautogui.click(rect.left + 500, rect.top + 200) # top slice
time.sleep(0.5)

# Click somewhere else in the SVG just in case
pyautogui.click(rect.left + 600, rect.top + 300)
time.sleep(0.5)

pyautogui.screenshot('c:/Users/Base/Desktop/Seb/Pandora/scratch/click_slice.png')
print("Screenshot saved")
