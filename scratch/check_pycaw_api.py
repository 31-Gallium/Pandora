import sys
import os
sys.path.append(os.getcwd())
try:
    import pythoncom
    pythoncom.CoInitialize()
    from pycaw.pycaw import AudioUtilities
    devices = AudioUtilities.GetSpeakers()
    print(f"Type of devices: {type(devices)}")
    print(f"Attributes: {dir(devices)}")
except Exception as e:
    print(f"Error: {e}")
