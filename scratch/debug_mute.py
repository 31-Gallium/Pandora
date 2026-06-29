import sys
import os
import traceback
sys.path.append(os.getcwd())

def debug_mute():
    try:
        import pythoncom
        pythoncom.CoInitialize()
        from pycaw.pycaw import AudioUtilities, IAudioEndpointVolume
        from comtypes import CLSCTX_ALL
        
        print("Getting speakers...")
        devices = AudioUtilities.GetSpeakers()
        print(f"Devices: {devices}")
        
        print("Activating interface...")
        interface = devices.Activate(IAudioEndpointVolume._iid_, CLSCTX_ALL, None)
        print(f"Interface: {interface}")
        
        print("Querying IAudioEndpointVolume...")
        volume = interface.QueryInterface(IAudioEndpointVolume)
        print(f"Volume object: {volume}")
        
        mute = volume.GetMute()
        print(f"Mute status: {mute}")
        return mute == 1
    except Exception as e:
        print(f"FAILED with error: {e}")
        traceback.print_exc()
        return False

print(f"Final result: {debug_mute()}")
