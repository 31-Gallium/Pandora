import sys
import os

if sys.stdout is None:
    sys.stdout = open(os.devnull, 'w')
if sys.stderr is None:
    sys.stderr = open(os.devnull, 'w')

from PyQt6.QtWidgets import QApplication
from uninstaller import UninstallerUI

if __name__ == "__main__":
    app = QApplication(sys.argv)
    font = app.font()
    font.setFamily("Segoe UI")
    app.setFont(font)
    ui = UninstallerUI()
    ui.show()
    sys.exit(app.exec())
