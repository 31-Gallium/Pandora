import ctypes
import ctypes.wintypes
import sys
from PyQt6.QtWidgets import QApplication
from PyQt6.QtGui import QScreen

user32 = ctypes.windll.user32

found = []
def enum_cb(hwnd, lParam):
    length = user32.GetWindowTextLengthW(hwnd)
    if length > 0:
        buf = ctypes.create_unicode_buffer(length + 1)
        user32.GetWindowTextW(hwnd, buf, length + 1)
        title = buf.value
        if 'pandora' in title.lower() and 'dashboard' in title.lower() and 'chrome' not in title.lower():
            found.append(hwnd)
    return True

EnumWindowsProc = ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.wintypes.HWND, ctypes.wintypes.LPARAM)
user32.EnumWindows(EnumWindowsProc(enum_cb), 0)

if not found:
    print("No Pandora window found")
    sys.exit(1)

hwnd = found[0]

app = QApplication(sys.argv)
screen = QApplication.primaryScreen()

# Simulate click using win32api
import win32api, win32con
import time

def click(x, y):
    win32api.SetCursorPos((x,y))
    win32api.mouse_event(win32con.MOUSEEVENTF_LEFTDOWN,x,y,0,0)
    win32api.mouse_event(win32con.MOUSEEVENTF_LEFTUP,x,y,0,0)

rect = ctypes.wintypes.RECT()
user32.GetWindowRect(hwnd, ctypes.byref(rect))

# Ensure window is visible
user32.ShowWindow(hwnd, 9)
user32.SetWindowPos(hwnd, -1, 0, 0, 0, 0, 3) # Topmost

# Wait for paint
time.sleep(1)

# Click Halo tab (sidebar left, a bit down)
click(rect.left + 312, rect.top + 353)
time.sleep(1)

pixmap = screen.grabWindow(hwnd)
pixmap.save("c:/Users/Base/Desktop/Seb/Pandora/scratch/real_screenshot.png", "PNG")
print("Saved real_screenshot.png")
