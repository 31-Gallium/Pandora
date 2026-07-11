import struct
import time
import win32file
from dataclasses import dataclass, field
from enum import Enum, auto
from PyQt6.QtCore import QThread, pyqtSignal

class EngineState(Enum):
    DISCONNECTED = auto()
    STARTING = auto()
    CONNECTING = auto()
    CONNECTED = auto()
    ERROR = auto()
    STOPPING = auto()

@dataclass(frozen=True)
class AudioFeatures:
    sequence_number: int
    timestamp_ms: int
    peak: float
    rms: float
    pan: float
    beat_strength: float
    
    # Processed Frequency Bands
    sub_bass: float
    bass: float
    low_mid: float
    mid: float
    upper_mid: float
    presence: float
    treble: float
    air: float
    
    dominant_frequency: float
    
    # Metadata
    sample_rate: int
    channels: int
    fft_size: int
    output_mode: int
    num_bins: int
    
    # Raw FFT Bins
    raw_bins: tuple[float, ...] = field(default_factory=tuple)

class AudioEngineClient(QThread):
    features_updated = pyqtSignal(AudioFeatures)
    state_changed = pyqtSignal(EngineState)

    def __init__(self, engine_pid: int):
        super().__init__()
        self.engine_pid = engine_pid
        self.running = False
        self.handle = None
        self.state = EngineState.DISCONNECTED
        
        self._target_output_mode = 2 # Bins128 by default
        self._target_smoothing = 0.8
        self._needs_config_update = False

    def set_state(self, new_state: EngineState):
        if self.state != new_state:
            self.state = new_state
            self.state_changed.emit(self.state)

    def request_config(self, output_mode: int, smoothing: float):
        self._target_output_mode = output_mode
        self._target_smoothing = smoothing
        self._needs_config_update = True

    def run(self):
        self.running = True
        self.set_state(EngineState.CONNECTING)
        
        pipe_name = fr'\\.\pipe\PandoraAudioEngine_{self.engine_pid}'
        
        # Try to connect
        for _ in range(50):
            if not self.running:
                break
            try:
                self.handle = win32file.CreateFile(
                    pipe_name,
                    win32file.GENERIC_READ | win32file.GENERIC_WRITE,
                    0, None,
                    win32file.OPEN_EXISTING,
                    0, None
                )
                break
            except Exception:
                time.sleep(0.1)
                
        if not self.handle:
            self.set_state(EngineState.ERROR)
            return
            
        self.set_state(EngineState.CONNECTED)
        
        self.request_config(self._target_output_mode, self._target_smoothing)
        
        # Main Read Loop
        fmt_audio = '< Q Q f f f 8f f f I H H B H'
        fmt_audio_size = struct.calcsize(fmt_audio)
        
        while self.running:
            if self._needs_config_update:
                self._send_config(self._target_output_mode, self._target_smoothing)
                self._needs_config_update = False
                
            try:
                # Read 12-byte header
                hr, header_data = win32file.ReadFile(self.handle, 12)
                if hr != 0 or len(header_data) != 12:
                    continue
                    
                magic, version, ptype, size = struct.unpack('<I H H I', header_data)
                
                if magic != 0x444E4150: # 'PAND'
                    continue
                    
                if size > 0:
                    hr, payload = win32file.ReadFile(self.handle, size)
                    if ptype == 1: # AudioFrame
                        if len(payload) >= fmt_audio_size:
                            base_data = struct.unpack(fmt_audio, payload[:fmt_audio_size])
                            num_bins = base_data[19]
                            
                            raw_bins_tup = ()
                            if num_bins > 0 and len(payload) >= fmt_audio_size + (num_bins * 4):
                                raw_bins = struct.unpack(f'<{num_bins}f', payload[fmt_audio_size:fmt_audio_size + (num_bins * 4)])
                                raw_bins_tup = tuple(raw_bins)
                                
                            features = AudioFeatures(
                                sequence_number=base_data[0],
                                timestamp_ms=base_data[1],
                                peak=base_data[2],
                                rms=base_data[3],
                                pan=base_data[4],
                                sub_bass=base_data[5],
                                bass=base_data[6],
                                low_mid=base_data[7],
                                mid=base_data[8],
                                upper_mid=base_data[9],
                                presence=base_data[10],
                                treble=base_data[11],
                                air=base_data[12],
                                dominant_frequency=base_data[13],
                                beat_strength=base_data[14],
                                sample_rate=base_data[15],
                                channels=base_data[16],
                                fft_size=base_data[17],
                                output_mode=base_data[18],
                                num_bins=base_data[19],
                                raw_bins=raw_bins_tup
                            )
                            self.features_updated.emit(features)
                    
            except Exception as e:
                # Disconnected or broken pipe
                if self.running:
                    self.set_state(EngineState.ERROR)
                break
                
        # Send Graceful Shutdown if we initiated the stop
        if self.handle:
            try:
                shutdown_header = struct.pack('<I H H I', 0x444E4150, 1, 4, 0)
                win32file.WriteFile(self.handle, shutdown_header)
                win32file.CloseHandle(self.handle)
            except Exception:
                pass
                
        self.set_state(EngineState.DISCONNECTED)

    def _send_config(self, mode: int, smoothing: float):
        if not self.handle: return
        try:
            # bool updateOutputMode, bool updateSmoothing, bool updateTargetPID, uint8_t newOutputMode, float newSmoothingFactor, uint32_t newTargetPID
            payload = struct.pack('<???BfI', True, True, False, mode, smoothing, 0)
            header = struct.pack('<I H H I', 0x444E4150, 1, 2, len(payload))
            win32file.WriteFile(self.handle, header + payload)
        except Exception:
            pass

    def stop(self):
        self.running = False
        self.set_state(EngineState.STOPPING)
        self.wait()
