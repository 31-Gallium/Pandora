import sys
import os
from PyQt6.QtWidgets import QApplication
from PyQt6.QtGui import QPixmap
from PyQt6.QtCore import QFileInfo

# Add parent dir to path to import utils
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from utils import IconExtractor

app = QApplication(sys.argv)

print("Testing UWP Icon Extraction...")
spotify_uwp = "SpotifyAB.SpotifyMusic_zpdnekdrzrea0!Spotify"
pix = IconExtractor.get_icon_pixmap(f"shell:AppsFolder\\{spotify_uwp}", 256)
if pix and not pix.isNull():
    print(f"-> SUCCESS: Extracted Spotify UWP icon (Size: {pix.width()}x{pix.height()})")
else:
    print("-> FAILED: Could not extract Spotify UWP icon")

print("\nTesting Win32 Process Scan...")
import psutil
chrome_path = None
for p in psutil.process_iter(['name', 'exe']):
    try:
        if p.info['name'] and p.info['name'].lower() == 'chrome.exe':
            chrome_path = p.info['exe']
            break
    except:
        pass

print(f"Chrome Path: {chrome_path}")
if chrome_path:
    pix_chrome = IconExtractor.get_icon_pixmap(chrome_path, 256)
    if pix_chrome and not pix_chrome.isNull():
        print(f"-> SUCCESS: Extracted Chrome icon (Size: {pix_chrome.width()}x{pix_chrome.height()})")
    else:
        print("-> FAILED: Could not extract Chrome icon")
else:
    print("-> Chrome process not running, skipping Chrome test")
