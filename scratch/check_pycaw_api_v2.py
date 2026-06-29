import sys
import os
sys.path.append(os.getcwd())
try:
    import pythoncom
    pythoncom.CoInitialize()
    from pycaw.pycaw import AudioUtilities
    devices = AudioUtilities.GetSpeakers()
    print(f"EndpointVolume type: {type(devices.EndpointVolume)}")
    print(f"Mute status: {devices.EndpointVolume.GetMute()}")
except Exception as e:
    print(f"Error: {e}")
