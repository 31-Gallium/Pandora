import pythoncom
from pycaw.pycaw import AudioUtilities, IAudioMeterInformation
from comtypes import CLSCTX_ALL

def test_all():
    pythoncom.CoInitialize()
    
    print("Enumerating all active render devices...")
    try:
        device_enumerator = AudioUtilities.GetDeviceEnumerator()
        devices = device_enumerator.EnumAudioEndpoints(0, 1) # active render devices
        count = devices.GetCount()
        print(f"Found {count} active rendering devices:")
        
        for i in range(count):
            device = devices.Item(i)
            print(f"\n--- Device {i} ---")
            try:
                interface = device.Activate(IAudioMeterInformation._iid_, CLSCTX_ALL, None)
                meter = interface.QueryInterface(IAudioMeterInformation)
                val = meter.GetPeakValue()
                print(f"Activated meter successfully. Current peak: {val:.6f}")
            except Exception as e:
                print(f"Failed to activate/query meter: {e}")
                
    except Exception as e:
        print(f"Error enumerating: {e}")

if __name__ == "__main__":
    test_all()
