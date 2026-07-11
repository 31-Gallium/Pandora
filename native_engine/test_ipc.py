import win32file
import win32pipe
import struct
import time
import sys

def test_ipc(pid):
    pipe_name = fr'\\.\pipe\PandoraAudioEngine_{pid}'
    print(f"Connecting to {pipe_name}...")
    
    handle = None
    for _ in range(50):
        try:
            handle = win32file.CreateFile(
                pipe_name,
                win32file.GENERIC_READ | win32file.GENERIC_WRITE,
                0, None,
                win32file.OPEN_EXISTING,
                0, None
            )
            break
        except Exception as e:
            time.sleep(0.1)
            
    if not handle:
        print("Failed to connect.")
        return
        
    print("Connected!")
    
    # Send a config command to change output mode to Bins128 (2)
    # struct ConfigCommandPayload: bool, bool, bool, uint8_t, float, uint32_t
    cmd_payload = struct.pack('<???BfI', True, False, False, 2, 0.0, 0)
    
    cmd_header = struct.pack('<IHHcI', 0x444E4150, 1, 0x02, b'\x00', len(cmd_payload)) # Wait, packetType is uint16_t, so H not c
    cmd_header = struct.pack('<I H H I', 0x444E4150, 1, 2, len(cmd_payload))
    
    print("Sending ConfigCommand to change output mode to Bins128...")
    win32file.WriteFile(handle, cmd_header + cmd_payload)
    
    frames_received = 0
    while frames_received < 10:
        try:
            # Read Header
            hr, data = win32file.ReadFile(handle, 12)
            if hr != 0 or len(data) != 12:
                continue
                
            magic, version, ptype, size = struct.unpack('<I H H I', data)
            
            if magic != 0x444E4150:
                print(f"Bad magic: {magic:x}")
                continue
                
            # Read Payload
            hr, payload = win32file.ReadFile(handle, size)
            if ptype == 0: # Handshake
                ver, caps, engine_pid = struct.unpack('<I I I', payload)
                print(f"[Handshake] Version: {ver}, PID: {engine_pid}")
            elif ptype == 1: # AudioFrame
                # struct AudioFramePayload (fields up to numBins)
                # uint64, uint64, float(peak), float(rms), 8*float(bands), float(domFreq), float(beat), uint32(sampleRate), uint16(channels), uint16(fftSize), uint8(outputMode), uint16(numBins)
                # Wait, outputMode is enum class (uint8_t), but because of struct alignment, is it packed?
                # C++ used #pragma pack(push, 1) so there is NO padding!
                fmt = '< Q Q f f 8f f f I H H B H'
                fmt_size = struct.calcsize(fmt)
                
                if len(payload) >= fmt_size:
                    unpacked = struct.unpack(fmt, payload[:fmt_size])
                    seq = unpacked[0]
                    mode = unpacked[16]
                    num_bins = unpacked[17]
                    
                    print(f"[AudioFrame] Seq: {seq}, OutputMode: {mode}, Bins: {num_bins}")
                    
                    if num_bins > 0:
                        raw_bins = struct.unpack(f'<{num_bins}f', payload[fmt_size:])
                        print(f"  First bin: {raw_bins[0]:.4f}")
                        
                    frames_received += 1
                    
        except Exception as e:
            print(f"Error reading: {e}")
            break

    # Send GracefulShutdown
    shutdown_header = struct.pack('<I H H I', 0x444E4150, 1, 4, 0)
    win32file.WriteFile(handle, shutdown_header)
    print("Sent GracefulShutdown.")
    
    win32file.CloseHandle(handle)

if __name__ == '__main__':
    if len(sys.argv) > 1:
        test_ipc(sys.argv[1])
