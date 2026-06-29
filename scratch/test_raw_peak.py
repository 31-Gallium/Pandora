import time
import pythoncom
from pycaw.pycaw import AudioUtilities, IAudioMeterInformation
from comtypes import CLSCTX_ALL

def test_peak():
    print("Initializing COM...")
    pythoncom.CoInitialize()
    
    print("Getting speakers device...")
    try:
        devices = AudioUtilities.GetSpeakers()
        print(f"Speakers device: {devices}")
    except Exception as e:
        print(f"Failed to get speakers: {e}")
        return
        
    print("Activating IAudioMeterInformation...")
    try:
        interface = devices.Activate(IAudioMeterInformation._iid_, CLSCTX_ALL, None)
        print(f"Interface activated: {interface}")
        master_meter = interface.QueryInterface(IAudioMeterInformation)
        print(f"Master meter: {master_meter}")
    except Exception as e:
        print(f"Failed to activate meter interface: {e}")
        return
        
    print("Polling peak values for 3 seconds...")
    for i in range(30):
        try:
            val = master_meter.GetPeakValue()
            print(f"[{i*0.1:.1f}s] Peak: {val:.6f}")
        except Exception as e:
            print(f"Error getting peak value: {e}")
        time.sleep(0.1)

if __name__ == "__main__":
    test_peak()
