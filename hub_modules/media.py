import time
import math
import random
from collections import deque
from PyQt6.QtCore import QRectF, Qt, QPointF, QTimer
from PyQt6.QtGui import (QPainter, QFont, QColor, QPen, QBrush, QPainterPath,
                          QRadialGradient, QConicalGradient, QPixmap, QImage)
from PyQt6.QtWidgets import QApplication, QGraphicsScene, QGraphicsPixmapItem, QGraphicsBlurEffect
from .base import BaseHubModule
from .physics import (Spring, ExponentialDecay, SIZE_PULSING_PROFILES,
                      VOXEL_PROFILES, RING_EQ_PROFILES)
from utils import VectorIcon, MediaSessionManager, IconExtractor

# Exposure of constants for visualizer tuning
VOXEL_PRIMARY_KICK_SCALE = 0.15
VOXEL_SECONDARY_KICK_SCALE = 0.08
VOXEL_PAN_BIAS_SCALE = 1200.0
SIZE_PULSE_SECONDARY_SCALE = 0.3
IDLE_AUDIO_THRESHOLD = 0.005
IDLE_FRAME_LIMIT = 120

# Wave Coupling Physics
WAVE_COUPLING = 120.0  # Rate of wave propagation across visual columns

# Size Pulsing drive weights
PULSE_SUB_BASS_WEIGHT = 0.55
PULSE_BASS_WEIGHT = 0.30
PULSE_RMS_WEIGHT = 0.15

# Precomputed trigonometric values for shape vertex generation in 60FPS render loop
_CIRCLE_TRIG = [(math.cos(i * 2 * math.pi / 16) / 2.0, math.sin(i * 2 * math.pi / 16) / 2.0) for i in range(16)]
_HEX_TRIG = [(math.cos(math.radians(i * 60 + 30)) * 1.15 / 2.0, math.sin(math.radians(i * 60 + 30)) * 1.15 / 2.0) for i in range(6)]

_ROUNDED_TRIG = []
for i in range(4):
    a = math.radians(270 + i * 30)
    _ROUNDED_TRIG.append((math.cos(a), math.sin(a), 0.5, -0.5))
for i in range(4):
    a = math.radians(0 + i * 30)
    _ROUNDED_TRIG.append((math.cos(a), math.sin(a), 0.5, 0.5))
for i in range(4):
    a = math.radians(90 + i * 30)
    _ROUNDED_TRIG.append((math.cos(a), math.sin(a), -0.5, 0.5))
for i in range(4):
    a = math.radians(180 + i * 30)
    _ROUNDED_TRIG.append((math.cos(a), math.sin(a), -0.5, -0.5))

_DIAMOND_TRIG = [(math.cos(math.radians(i * 90)) / 2.0, math.sin(math.radians(i * 90)) / 2.0) for i in range(4)]

def _catmull_rom(p0, p1, p2, p3, t):
    t2 = t * t
    t3 = t2 * t
    return 0.5 * ((2.0 * p1) + (-p0 + p2) * t + (2.0 * p0 - 5.0 * p1 + 4.0 * p2 - p3) * t2 + (-p0 + 3.0 * p1 - 3.0 * p2 + p3) * t3)

def get_shape_vertices(cx, cy, w, h, shape, gy, block_size):
    if shape == "Circles":
        return [QPointF(cx + ux * w, cy + uy * h) for ux, uy in _CIRCLE_TRIG]
    elif shape == "Hexagons":
        offset_x = (block_size / 2.0) if gy % 2 == 1 else 0.0
        cx_eff = cx + offset_x
        return [QPointF(cx_eff + ux * w, cy + uy * h) for ux, uy in _HEX_TRIG]
    elif shape == "Rounded":
        r = 4.0
        half_w_minus_r = w / 2.0 - r
        half_h_minus_r = h / 2.0 - r
        return [
            QPointF(cx + sx * half_w_minus_r + ca * r, cy + sy * half_h_minus_r + sa * r)
            for ca, sa, sx, sy in _ROUNDED_TRIG
        ]
    elif shape == "Diamonds":
        return [QPointF(cx + ux * w, cy + uy * h) for ux, uy in _DIAMOND_TRIG]
    else: # "Square"
        return [
            QPointF(cx - w / 2.0, cy - h / 2.0),
            QPointF(cx + w / 2.0, cy - h / 2.0),
            QPointF(cx + w / 2.0, cy + h / 2.0),
            QPointF(cx - w / 2.0, cy + h / 2.0)
        ]


class MusicInterpreter:
    def __init__(self):
        self._avg_energy = 0.15
        self._smoothed_warmth = 0.0
        self._smoothed_rhythm = 0.0
        
    def process(self, features, dt: float) -> dict:
        if not features:
            return {"impact": 0.0, "warmth": 0.0, "sparkle": 0.0, "rhythm": 0.0, "energy": 0.0, "bands": [], "raw_peak": 0.0, "pan": 0.0}
            
        raw_peak = features.peak
        
        # Energy: AGC normalized peak
        if raw_peak > 0.005:
            # Slower decay for overall energy
            self._avg_energy += (raw_peak - self._avg_energy) * 0.5 * dt
            self._avg_energy = max(0.05, min(1.0, self._avg_energy))
        
        energy = max(0.0, min(1.0, raw_peak / self._avg_energy))
        
        # Warmth: heavily low-passed bass (slow)
        self._smoothed_warmth += (features.bass - self._smoothed_warmth) * 2.0 * dt
        warmth = max(0.0, min(1.0, self._smoothed_warmth))
        
        # Rhythm: slightly faster low-passed sub_bass
        self._smoothed_rhythm += (features.sub_bass - self._smoothed_rhythm) * 5.0 * dt
        rhythm = max(0.0, min(1.0, self._smoothed_rhythm))
        
        # Impact: fast transients (just use beat_strength for now, already transient-detected by engine)
        impact = features.beat_strength
        
        # Sparkle: high-frequency transients
        sparkle = features.treble
        
        bands = [
            features.sub_bass, features.bass, features.low_mid,
            features.mid, features.upper_mid, features.presence,
            features.treble, features.air
        ]
        
        return {
            "impact": impact,
            "warmth": warmth,
            "sparkle": sparkle,
            "rhythm": rhythm,
            "energy": energy,
            "bands": bands,
            "raw_peak": raw_peak
        }


# Band name labels for dominant_region (indexed 0-7)
_BAND_NAMES = ["Sub Bass", "Bass", "Low Mid", "Mid", "Upper Mid", "Presence", "Treble", "Air"]


class MusicalIntelligence:
    """Transforms raw normalized FFT bands into artistic control signals.
    
    Maintains slowly-varying musical context descriptors that evolve over
    seconds, and uses them to discover which parts of the music deserve
    emphasis. Does not invent new information — only decides what deserves
    visual clarity.
    """
    
    def __init__(self):
        # Slowly-varying context descriptors
        self._brightness = 0.0       # High-freq energy ratio (~2s)
        self._warmth = 0.0           # Low-freq energy ratio (~2s)
        self._spectral_spread = 0.0  # Energy distribution width (~2s)
        self._harmonic_density = 0.0 # Count of simultaneously active bands (~2s)
        self._transient_density = 0.0 # Transient events per second (~3s)
        self._complexity = 0.0       # Composite descriptor (~3s)
        self._confidence = 0.0       # How strongly spectrum favors one region (~1.5s)
        self._stability = 0.0        # How slowly the spectrum is evolving (~2s)
        
        # Dominant Region with temporal persistence
        self._dominant_region_idx = 3  # Current exposed dominant region (default: Mid)
        self._candidate_dominant_idx = 3  # Instantaneous candidate
        self._dominant_hold_timer = 0.0   # Time remaining on current dominant lock
        _DOMINANT_HOLD_MIN = 0.3          # Minimum hold time (seconds)
        _DOMINANT_HOLD_MAX = 0.7          # Maximum hold time (seconds)
        self._dominant_hold_min = _DOMINANT_HOLD_MIN
        self._dominant_hold_max = _DOMINANT_HOLD_MAX
        
        # Per-band temporal memory for sustained vs. transient classification
        self._band_memory = [0.0] * 8
        
        # Spectral stability: rolling history of band snapshots
        self._stability_prev = [0.0] * 8
        
        # Transient event counter (rolling window)
        self._transient_events = deque(maxlen=180)  # ~3 seconds at 60fps
        
        # Previous bands for transient detection
        self._prev_bands = [0.0] * 8
        
        # Future: spectral_momentum (energy moving toward lower or higher freqs)
        # self._spectral_momentum = 0.0
    
    def process(self, norm_bands, rms, impact_primary, dt):
        """Process raw normalized bands into artistic control signals.
        
        Args:
            norm_bands: 8-element list of globally-normalized FFT band values.
            rms: Current RMS loudness (0.0-1.0).
            impact_primary: Current beat/transient strength (0.0-1.0).
            dt: Delta time in seconds.
            
        Returns:
            dict with 'art_bands' (8 floats) and 'context' (dict of descriptors).
        """
        if not norm_bands or len(norm_bands) < 8:
            return {
                "art_bands": [0.0] * 8,
                "context": {
                    "brightness": 0.0, "warmth": 0.0, "complexity": 0.0,
                    "transient_density": 0.0, "spread": 0.0,
                    "confidence": 0.0, "stability": 0.5,
                    "dominant_region": "Mid", "dominant_region_idx": 3,
                }
            }
        
        # --- 1. Update Slowly-Varying Context Descriptors ---
        
        total_energy = max(0.001, sum(norm_bands))
        
        # Brightness: ratio of high-frequency energy (Treble + Air + Presence)
        high_energy = (norm_bands[5] + norm_bands[6] + norm_bands[7]) / total_energy
        self._brightness += (high_energy - self._brightness) * 0.8 * dt  # ~2s tau
        
        # Warmth: ratio of low-frequency energy (Sub + Bass + Low Mid)
        low_energy = (norm_bands[0] + norm_bands[1] + norm_bands[2]) / total_energy
        self._warmth += (low_energy - self._warmth) * 0.8 * dt
        
        # Spectral Spread: standard deviation of band magnitudes
        avg_band = total_energy / 8.0
        variance = sum((b - avg_band) ** 2 for b in norm_bands) / 8.0
        instant_spread = math.sqrt(variance) / max(0.001, avg_band)  # Coefficient of variation
        instant_spread = min(1.0, instant_spread)
        self._spectral_spread += (instant_spread - self._spectral_spread) * 0.8 * dt
        
        # Harmonic Density: count of bands simultaneously above 30% of the max
        band_max = max(norm_bands)
        threshold = band_max * 0.3 if band_max > 0.01 else 0.01
        active_count = sum(1 for b in norm_bands if b > threshold)
        instant_density = active_count / 8.0
        self._harmonic_density += (instant_density - self._harmonic_density) * 0.8 * dt
        
        # Transient Density: rolling rate of transient events
        frame_has_transient = 0
        for i in range(8):
            delta = norm_bands[i] - self._prev_bands[i]
            if delta > 0.15:  # Significant per-band jump
                frame_has_transient = 1
                break
        self._transient_events.append(frame_has_transient)
        self._prev_bands = list(norm_bands)
        
        # Approximate events-per-second (normalized to 0-1 range)
        event_count = sum(self._transient_events)
        instant_td = min(1.0, event_count / max(1, len(self._transient_events)) * 3.0)
        self._transient_density += (instant_td - self._transient_density) * 0.5 * dt  # ~3s tau
        
        # Complexity: composite of spread, harmonic density, and transient density
        instant_complexity = (self._spectral_spread * 0.35 + 
                              self._harmonic_density * 0.35 + 
                              self._transient_density * 0.30)
        self._complexity += (instant_complexity - self._complexity) * 0.5 * dt
        
        # Stability: how slowly the spectrum is evolving over time
        # Measures the average frame-to-frame change across all bands
        frame_change = 0.0
        for i in range(8):
            frame_change += abs(norm_bands[i] - self._stability_prev[i])
        self._stability_prev = list(norm_bands)
        frame_change /= 8.0  # Average per-band change
        # Invert: high change = low stability, low change = high stability
        instant_stability = max(0.0, 1.0 - frame_change * 8.0)
        self._stability += (instant_stability - self._stability) * 0.8 * dt  # ~2s tau
        
        # Confidence: how strongly the spectrum favors one or more regions
        # High when one band clearly dominates, low when energy is evenly distributed
        if band_max > 0.01:
            # Ratio of strongest band to average (1.0 = perfectly flat, higher = more focused)
            focus_ratio = band_max / avg_band
            # Normalize: ratio of 1.0 → confidence 0.0, ratio of 4.0+ → confidence 1.0
            instant_confidence = min(1.0, max(0.0, (focus_ratio - 1.0) / 3.0))
        else:
            instant_confidence = 0.0
        self._confidence += (instant_confidence - self._confidence) * 1.0 * dt  # ~1.5s tau
        
        # --- Dominant Region with Temporal Stability (300-700ms hold) ---
        # Find instantaneous candidate from band_memory (temporally smoothed)
        candidate_idx = 0
        candidate_val = -1.0
        for i in range(8):
            if self._band_memory[i] > candidate_val:
                candidate_val = self._band_memory[i]
                candidate_idx = i
        
        # Tick down the hold timer
        self._dominant_hold_timer -= dt
        
        if candidate_idx != self._dominant_region_idx:
            # A different region wants to become dominant
            if self._dominant_hold_timer <= 0.0:
                # Hold expired — allow the transition
                self._dominant_region_idx = candidate_idx
                # Set new hold duration, scaled by stability
                # Stable music → longer hold (closer to 700ms)
                # Volatile music → shorter hold (closer to 300ms)
                hold_duration = self._dominant_hold_min + self._stability * (self._dominant_hold_max - self._dominant_hold_min)
                self._dominant_hold_timer = hold_duration
        else:
            # Same region is still dominant — keep refreshing the hold
            if self._dominant_hold_timer < 0.0:
                self._dominant_hold_timer = 0.0
        
        # --- 2. Per-Band Artistic Processing ---
        
        art_bands = [0.0] * 8
        
        # Adaptive compression exponent driven primarily by CONFIDENCE
        # High confidence → aggressive compression (exponent ~2.5)
        # Low confidence → gentle compression (exponent ~1.2)
        # Complex music can still have clear dominance — confidence captures this directly
        compression = 1.2 + (self._confidence * 1.3)
        compression = max(1.2, min(2.5, compression))
        
        for i in range(8):
            # Temporal memory: sustained presence builds slowly, decays slowly
            if norm_bands[i] > self._band_memory[i]:
                self._band_memory[i] += (norm_bands[i] - self._band_memory[i]) * 3.0 * dt
            else:
                self._band_memory[i] += (norm_bands[i] - self._band_memory[i]) * 1.5 * dt
            
            # Spectral Importance: how far above average this band is
            importance = max(0.0, norm_bands[i] - avg_band * 0.5)
            
            # Sustained presence bonus: bands that have been consistently strong
            # get a gentle lift from their temporal memory
            sustained_bonus = self._band_memory[i] * 0.3
            
            # Combined raw importance
            raw_art = importance + sustained_bonus
            
            # Dynamic Spectral Compression: exaggerate the strong, suppress the weak
            # Scale with confidence — only compress when the spectrum has clear focus
            if raw_art > 0.001:
                compressed = math.pow(raw_art, compression)
                # Blend compression strength with confidence
                # Low confidence → less compression (closer to raw)
                # High confidence → full compression
                blend = 0.3 + self._confidence * 0.7
                art_bands[i] = raw_art * (1.0 - blend) + compressed * blend
            else:
                art_bands[i] = 0.0
        
        # Normalize art_bands so the maximum reaches ~1.0
        # but do NOT equalize — preserve the asymmetry
        art_max = max(art_bands) if art_bands else 0.001
        if art_max > 0.001:
            for i in range(8):
                art_bands[i] /= art_max
        
        context = {
            "brightness": max(0.0, min(1.0, self._brightness)),
            "warmth": max(0.0, min(1.0, self._warmth)),
            "complexity": max(0.0, min(1.0, self._complexity)),
            "transient_density": max(0.0, min(1.0, self._transient_density)),
            "spread": max(0.0, min(1.0, self._spectral_spread)),
            "confidence": max(0.0, min(1.0, self._confidence)),
            "stability": max(0.0, min(1.0, self._stability)),
            "dominant_region": _BAND_NAMES[self._dominant_region_idx],
            "dominant_region_idx": self._dominant_region_idx,
        }
        
        return {"art_bands": art_bands, "context": context}


class MediaHub(BaseHubModule):
    def __init__(self, manager):
        super().__init__(manager)
        self.media_mgr = MediaSessionManager.instance()
        
        self._smoothed_peak = 0.0
        self._average_peak = 0.15
        self._voxel_physics = {}
        
        self.interpreter = MusicInterpreter()
        self.musical_intelligence = MusicalIntelligence()
        self._last_frame_time = time.time()
        
        # Physics Primitives
        self.pulse_spring = Spring()
        self.pulse_mid_spring = Spring(tension=150.0, damping=15.0)
        
        # Voxel Wiggle State (16 Coupled Nodes Wave Simulation)
        self.node_values = [0.0] * 16
        self.node_velocities = [0.0] * 16
        self.voxel_spring = Spring()
        self.voxel_history = [0.0] * 120
        self.voxel_history_idx = 0
        self.drift_x_spring = Spring(tension=10.0, damping=15.0) # Highly damped for slow, organic drifting
        self.drift_y_spring = Spring(tension=10.0, damping=15.0)
        
        # Derived Visual Signals State
        self._prev_sequence_number = 0
        self._prev_signals = None
        self._band_histories = [deque(maxlen=180) for _ in range(8)]
        self._sub_bass_history = deque(maxlen=180)
        self._bass_history = deque(maxlen=180)
        self._rms_history = deque(maxlen=180)
        self._idle_frame_counter = 0
        self._prev_mid_pres = 0.0
        self._idle_fade = 0.0
        
        # Edge Ring EQ State (Musical Expression)
        self.ring_phase = 0.0
        self.ring_shape = [0.0] * 8
        self.ring_thick = [0.0] * 8
        self.surface_thick = [0.0] * 120
        self.surface_flow_speed = 0.0
        self.ring_global_pulse = 0.0
        self.ring_global_breath = 0.0
        self.ring_prev_bands = [0.0] * 8
        
        # Voxel Wiggle Band States
        self.voxel_state_springs = {
            'bass': Spring(tension=35.0, damping=8.0),
            'mids': Spring(tension=35.0, damping=8.0),
            'treble': Spring(tension=35.0, damping=8.0)
        }
        self.voxel_state_springs['bass'].value = 1.0 # Default active
        self._voxel_band_histories = {
            'bass': deque(maxlen=60),
            'mids': deque(maxlen=60),
            'treble': deque(maxlen=60)
        }
        self._voxel_prev_bands = {'bass': 0.0, 'mids': 0.0, 'treble': 0.0}
        self._voxel_treble_state = 0  # 0: Down, 1: Right, 2: Up, 3: Left
        self._voxel_treble_wave_x = Spring(tension=20.0, damping=7.0)
        self._voxel_treble_wave_y = Spring(tension=20.0, damping=7.0)
        self._voxel_treble_disp_x = Spring(tension=20.0, damping=7.0)
        self._voxel_treble_disp_y = Spring(tension=20.0, damping=7.0)
        self._voxel_treble_wave_x.value = 0.0
        self._voxel_treble_wave_y.value = 1.0
        self._voxel_treble_disp_x.value = 1.0
        self._voxel_treble_disp_y.value = 0.0
        self._voxel_mids_dir_spring = Spring(tension=20.0, damping=7.0)  # Smooth direction transitions
        self._voxel_extrusion_spring = Spring(tension=50.0, damping=12.0)
        self._voxel_extrusion_spring.value = 0.0
        
        # Per-band energy springs — these provide smooth, independent intensity
        # values for each visual channel (size, brightness, displacement).
        # Lower tension + higher damping = smoother, less jittery response.
        self._voxel_bass_energy_spring = Spring(tension=25.0, damping=9.0)
        self._voxel_mids_energy_spring = Spring(tension=18.0, damping=10.0)  # Extra smooth for brightness
        self._voxel_treble_energy_spring = Spring(tension=30.0, damping=8.0)
        
        # Animation phase accumulators (accumulated at audio-driven speed)
        self._voxel_bass_phase = 0.0
        self._voxel_mids_phase = 0.0
        self._voxel_treble_phase = 0.0
        
        # High-Resolution State (32 Bins)
        self.filament_resolution = 32
        self.filament_shape = [0.0] * self.filament_resolution
        
        self._cached_thumb = None
        self._cached_round_thumb = None
        self._cached_thumb_id = ""
        self._cached_size = 0
        self._cached_strength = -1
        self._cached_art_style = ""
        self._dominant_color = QColor(189, 147, 249, 180) # Default
        
        self._prev_thumb = None
        self._prev_color_map = None
        self._thumb_anim_progress = 1.0
        self._prev_timeline_progress = 0.0
        
        # Caching for 8-Bit Mosaic Scale
        self._cached_mosaic_thumb_id = ""
        self._cached_block_size = -1
        self._cached_mosaic_color_map = None
        self._cached_mosaic_prev_thumb_id = ""
        self._cached_mosaic_prev_block_size = -1
        self._cached_mosaic_prev_color_map = None
        
        # New State for Spacebar Override
        self._holding = False
        self._space_pressed = False
        self._space_press_time = 0.0
        
        self.settings = {}
        
        self.media_tools = [
            {"id": "volume", "icon": "volume up", "label": "Volume"},
            {"id": "next", "icon": "next", "label": "Next Track"},
            {"id": "timeline", "icon": "clock", "label": "Timeline"},
            {"id": "prev", "icon": "prev", "label": "Prev Track"}
        ]

    def _clear_cache(self, track_info=None):
        # We handle this manually in _get_round_thumbnail for smoother transitions
        pass

    def load_settings(self, settings):
        self.settings = settings
        self._clear_cache()
        self._cached_thumb_id = ""
        self._cached_art_style = ""
        self._cached_mosaic_thumb_id = ""
        self._cached_block_size = -1
        self._cached_mosaic_color_map = None

    def derive_visual_signals(self, features, prof, dt):
        if not features:
            # Fallback signals if features is None
            return {
                "pulse_drive": 0.0,
                "impact_primary": 0.0,
                "impact_secondary": 0.0,
                "pan_bias": 0.0,
                "sharpness": 1.0,
                "band_array": [0.0] * 8,
                "norm_bands": [0.0] * 8,
                "filament_bands": [0.0] * self.filament_resolution,
                "is_idle": True,
                "raw_peak": 0.0,
                "rms": 0.0,
                "voxel_weights": {'bass': 1.0, 'mids': 0.0, 'treble': 0.0},
                "voxel_band_energies": {'bass': 0.0, 'mids': 0.0, 'treble': 0.0},
                "voxel_mids_dir": 1.0,
                "voxel_treble_state": 0,
                "voxel_treble_wave_x": 0.0,
                "voxel_treble_wave_y": 1.0,
                "voxel_treble_disp_x": 1.0,
                "voxel_treble_disp_y": 0.0,
                "voxel_bass_phase": 0.0,
                "voxel_mids_phase": 0.0,
                "voxel_treble_phase": 0.0,
                "voxel_extrusion": 0.0
            }

        sub_bass = getattr(features, 'sub_bass', 0.0)
        bass = getattr(features, 'bass', 0.0)
        rms = getattr(features, 'rms', 0.0)
        peak = getattr(features, 'peak', 0.0)
        pan = getattr(features, 'pan', 0.0)
        beat_strength = getattr(features, 'beat_strength', 0.0)
        dominant_frequency = getattr(features, 'dominant_frequency', 100.0)
        
        # Noise floor squelch
        if rms < 0.005: rms = 0.0
        if peak < 0.005: peak = 0.0
        if sub_bass < 0.005: sub_bass = 0.0
        if bass < 0.005: bass = 0.0
        
        band_array = [
            sub_bass,
            bass,
            getattr(features, 'low_mid', 0.0),
            getattr(features, 'mid', 0.0),
            getattr(features, 'upper_mid', 0.0),
            getattr(features, 'presence', 0.0),
            getattr(features, 'treble', 0.0),
            getattr(features, 'air', 0.0)
        ]

        # Apply noise floor squelch to all bands
        for i in range(8):
            if band_array[i] < 0.005:
                band_array[i] = 0.0

        # Update rolling max buffers
        self._sub_bass_history.append(sub_bass)
        self._bass_history.append(bass)
        self._rms_history.append(rms)

        max_sub_bass = max(0.05, max(self._sub_bass_history))
        max_bass = max(0.05, max(self._bass_history))
        max_rms = max(0.05, max(self._rms_history))

        # Normalize bands against rolling max
        norm_sub_bass = sub_bass / max_sub_bass
        norm_bass = bass / max_bass
        norm_rms = rms / max_rms

        # Compute pulse_drive
        pulse_drive = (PULSE_SUB_BASS_WEIGHT * norm_sub_bass + 
                       PULSE_BASS_WEIGHT * norm_bass + 
                       PULSE_RMS_WEIGHT * norm_rms)
        pulse_drive = max(0.0, min(1.0, pulse_drive))

        # Rolling-max normalization against a GLOBAL max across all bands
        # to preserve their natural relative volumes.
        global_max = 0.05
        for i in range(8):
            self._band_histories[i].append(band_array[i])
            global_max = max(global_max, max(self._band_histories[i]))
            
        norm_bands = []
        for i in range(8):
            norm_bands.append(band_array[i] / global_max)

        # Compute primary & secondary impacts
        impact_primary = beat_strength

        # Secondary impact: frame-to-frame rise in (upper_mid + presence) / 2
        upper_mid = band_array[4]
        presence = band_array[5]
        current_mid_pres = (upper_mid + presence) / 2.0
        delta = current_mid_pres - self._prev_mid_pres
        self._prev_mid_pres = current_mid_pres
        impact_secondary = max(0.0, delta)

        # Compute pan_bias
        pan_bias = pan

        # Compute sharpness from dominant frequency (20Hz - 10000Hz mapped to 0.5 - 2.0)
        freq = max(20.0, min(10000.0, dominant_frequency))
        log_freq = math.log10(freq)
        sharpness = 0.5 + (log_freq - 1.3) / (4.0 - 1.3) * 1.5
        sharpness = max(0.5, min(2.0, sharpness))

        # Idle state detection
        is_idle = False
        if rms < IDLE_AUDIO_THRESHOLD and peak < IDLE_AUDIO_THRESHOLD:
            self._idle_frame_counter += 1
            if self._idle_frame_counter >= IDLE_FRAME_LIMIT:
                is_idle = True
        else:
            self._idle_frame_counter = 0

        # --- High-Resolution Processing (32 Bins) ---
        raw_bins = getattr(features, 'raw_bins', ())
        self._voxel_raw_bins = raw_bins
        filament_bands = [0.0] * self.filament_resolution
        if raw_bins and len(raw_bins) >= 128:
            avg_eng = max(0.05, self.interpreter._avg_energy)
            
            for i in range(self.filament_resolution):
                x_start = i / self.filament_resolution
                x_end = (i + 1) / self.filament_resolution
                
                start_idx = int(127.0 * (x_start ** 2.0))
                end_idx = int(127.0 * (x_end ** 2.0))
                if end_idx <= start_idx:
                    end_idx = start_idx + 1
                end_idx = min(128, end_idx)
                
                group_sum = sum(raw_bins[start_idx:end_idx])
                group_count = max(1, end_idx - start_idx)
                group_avg = group_sum / group_count
                
                texture_emphasis = 1.0 + (x_start * 1.5)
                val = (group_avg / avg_eng) * texture_emphasis
                filament_bands[i] = max(0.0, min(1.0, val))

        # --- Voxel Wiggle: Simultaneous Energy-Proportional Blending ---
        # All three animations always contribute. Their weights are
        # proportional to each group's current energy, normalized against
        # its own rolling max so treble/mids aren't crushed by bass.
        raw_bass = (band_array[0] + band_array[1]) / 2.0
        raw_mids = (band_array[2] + band_array[3] + band_array[4]) / 3.0
        raw_treble = (band_array[5] + band_array[6] + band_array[7]) / 3.0
        
        self._voxel_band_histories['bass'].append(raw_bass)
        self._voxel_band_histories['mids'].append(raw_mids)
        self._voxel_band_histories['treble'].append(raw_treble)
        
        # Per-group rolling max (independent ceilings)
        max_bass = max(0.005, max(self._voxel_band_histories['bass']))
        max_mids = max(0.005, max(self._voxel_band_histories['mids']))
        max_treble = max(0.005, max(self._voxel_band_histories['treble']))
        
        # Normalize each group to [0, 1] against its own peak
        v_bass = raw_bass / max_bass
        v_mids = raw_mids / max_mids
        v_treble = raw_treble / max_treble
        # Scale by log-magnitude of raw energy so genuinely quiet groups
        # are suppressed. Without this, per-group normalization makes even
        # noise-floor groups sit at ~1.0 (since 0.01 / max(0.01) = 1.0).
        import math as _m
        total_raw = raw_bass + raw_mids + raw_treble
        if total_raw > 0.001:
            share_bass = raw_bass / total_raw
            share_mids = raw_mids / total_raw
            share_treble = raw_treble / total_raw
        else:
            share_bass = 0.33
            share_mids = 0.33
            share_treble = 0.33
        
        # Final weight = per-group-normalized level * share of total energy
        # This gives the best of both: per-group sensitivity AND
        # absolute loudness gating.
        target_bass = v_bass * (0.3 + 0.7 * share_bass)
        target_mids = v_mids * (0.3 + 0.7 * share_mids)
        target_treble = v_treble * (0.3 + 0.7 * share_treble)
        
        # Springs smooth the energy levels to avoid jittery weight changes
        self.voxel_state_springs['bass'].update(target_bass, dt)
        self.voxel_state_springs['mids'].update(target_mids, dt)
        self.voxel_state_springs['treble'].update(target_treble, dt)
        
        # Clamp to non-negative (springs can overshoot slightly)
        w_bass = max(0.0, self.voxel_state_springs['bass'].value)
        w_mids = max(0.0, self.voxel_state_springs['mids'].value)
        w_treble = max(0.0, self.voxel_state_springs['treble'].value)

        voxel_weights = {'bass': w_bass, 'mids': w_mids, 'treble': w_treble}
        
        # --- Direction Logic ---
        # Mids sweep: driven by pan bias (left = CCW, right = CW)
        mids_dir_target = 1.0 if pan_bias >= 0.0 else -1.0
        self._voxel_mids_dir_spring.update(mids_dir_target, dt)
        voxel_mids_dir = self._voxel_mids_dir_spring.value
        
        # Treble wash: flip direction on each treble transient
        # Use RAW treble delta (not per-group-normalized) for reliable
        # beat detection — normalized values can mask real spikes.
        prev_raw_treble = getattr(self, '_voxel_prev_raw_treble', 0.0)
        raw_treble_delta = raw_treble - prev_raw_treble
        self._voxel_prev_raw_treble = raw_treble
        treble_beat_threshold = 0.03  # Raw scale, much smaller than normalized
        if raw_treble_delta > treble_beat_threshold:
            self._voxel_treble_state = (self._voxel_treble_state + 1) % 4
        voxel_treble_state = self._voxel_treble_state
        
        # Determine continuous targets based on state: wave_x, wave_y, disp_x, disp_y
        # State 0: Down (Y propagation, X displacement)
        # State 1: Right (X propagation, Y displacement)
        # State 2: Up (Negative Y propagation, X displacement)
        # State 3: Left (Negative X propagation, Y displacement)
        state_targets = {
            0: (0.0, 1.0, 1.0, 0.0),
            1: (1.0, 0.0, 0.0, 1.0),
            2: (0.0, -1.0, 1.0, 0.0),
            3: (-1.0, 0.0, 0.0, 1.0)
        }
        tx, ty, dx, dy = state_targets[voxel_treble_state]
        
        self._voxel_treble_wave_x.update(tx, dt)
        self._voxel_treble_wave_y.update(ty, dt)
        self._voxel_treble_disp_x.update(dx, dt)
        self._voxel_treble_disp_y.update(dy, dt)
        
        self._voxel_prev_bands = {'bass': v_bass, 'mids': v_mids, 'treble': v_treble}
        
        # Per-band energy springs — smooth independent intensity for each effect.
        # v_bass/v_mids/v_treble are [0,1] normalized per-group values.
        self._voxel_bass_energy_spring.update(v_bass, dt)
        self._voxel_mids_energy_spring.update(v_mids, dt)
        self._voxel_treble_energy_spring.update(v_treble, dt)
        
        # Extrusion spring: only fires on strong beats when the song is loud enough.
        # This prevents constant low-level extrusion on quiet vocal tracks.
        if impact_primary > 0.4 and pulse_drive > 0.3:
            ext_target = min(1.0, impact_primary * 1.5)
        else:
            ext_target = 0.0
        self._voxel_extrusion_spring.update(ext_target, dt)
        
        voxel_band_energies = {
            'bass': max(0.0, min(1.0, self._voxel_bass_energy_spring.value)),
            'mids': max(0.0, min(1.0, self._voxel_mids_energy_spring.value)),
            'treble': max(0.0, min(1.0, self._voxel_treble_energy_spring.value))
        }
        
        # Accumulate animation phases. Base speed + dynamic speed driven by overall loudness (pulse_drive)
        # We cap the maximum speed at 100% (1.0). 
        # When silent, it drops to 30% speed. At max volume, it reaches 100% speed.
        dynamic_speed_multiplier = min(1.0, 0.3 + (pulse_drive * 0.7))
        
        self._voxel_bass_phase += dt * 15.0 * dynamic_speed_multiplier
        self._voxel_mids_phase += dt * 12.0 * dynamic_speed_multiplier * voxel_mids_dir
        self._voxel_treble_phase += dt * 20.0 * dynamic_speed_multiplier
 
        return {
            "pulse_drive": pulse_drive,
            "impact_primary": impact_primary,
            "impact_secondary": impact_secondary,
            "pan_bias": pan_bias,
            "sharpness": sharpness,
            "band_array": band_array,
            "norm_bands": norm_bands,
            "filament_bands": filament_bands,
            "is_idle": is_idle,
            "raw_peak": peak,
            "rms": rms,
            "voxel_weights": voxel_weights,
            "voxel_band_energies": voxel_band_energies,
            "voxel_mids_dir": voxel_mids_dir,
            "voxel_treble_state": voxel_treble_state,
            "voxel_treble_wave_x": self._voxel_treble_wave_x.value,
            "voxel_treble_wave_y": self._voxel_treble_wave_y.value,
            "voxel_treble_disp_x": self._voxel_treble_disp_x.value,
            "voxel_treble_disp_y": self._voxel_treble_disp_y.value,
            "voxel_bass_phase": self._voxel_bass_phase,
            "voxel_mids_phase": self._voxel_mids_phase,
            "voxel_treble_phase": self._voxel_treble_phase,
            "voxel_extrusion": max(0.0, min(1.0, self._voxel_extrusion_spring.value))
        }

    def cleanup(self):
        self._holding = False
        self._space_pressed = False
        self._space_press_time = 0.0

    def _extract_color(self, img: QImage):
        if img.isNull(): return QColor(189, 147, 249, 180)
        scaled = img.scaled(1, 1, Qt.AspectRatioMode.IgnoreAspectRatio, Qt.TransformationMode.SmoothTransformation)
        return QColor(scaled.pixel(0, 0))

    def _get_pandora_icon_image(self):
        if not hasattr(self, '_pandora_icon_img') or self._pandora_icon_img is None:
            try:
                import os
                from PyQt6.QtSvg import QSvgRenderer
                from PyQt6.QtGui import QImage, QPainter
                from PyQt6.QtCore import QRectF, Qt
                from utils import get_resource_path
                
                svg_path = "assets/Pandora.svg"
                if not os.path.exists(svg_path):
                    svg_path = get_resource_path("assets/Pandora.svg")
                
                img = QImage(256, 256, QImage.Format.Format_ARGB32)
                img.fill(Qt.GlobalColor.transparent)
                renderer = QSvgRenderer(svg_path)
                if renderer.isValid():
                    p = QPainter(img)
                    renderer.render(p, QRectF(0, 0, 256, 256))
                    p.end()
                    self._pandora_icon_img = img
                else:
                    self._pandora_icon_img = None
            except Exception as e:
                print(f"[MediaHub] Failed to load Pandora SVG: {e}")
                self._pandora_icon_img = None
        return self._pandora_icon_img

    def _get_fallback_thumbnail(self, track):
        has_media = track.get('title') and track['title'] != "No Media" and track['title'] != ""
        if not has_media:
            return self._get_pandora_icon_image(), "pandora_default_icon"
            
        thumb = self.media_mgr.thumbnail
        if thumb is not None and not thumb.isNull():
            return thumb, track.get('thumb_id', '')
            
        # Track changed grace period - removed the 1.5s hard delay
        # We rely strictly on `is_thumbnail_loading` from the daemon.
        is_loading = track.get('is_thumbnail_loading', False)
        
        # Hold onto last valid thumb for THIS session ONLY while the daemon explicitly says it's loading a new one
        session_id = track.get('session_id', '')
        if is_loading:
            last_session_thumbs = getattr(self.media_mgr, '_last_session_thumbs', {})
            if session_id and session_id in last_session_thumbs:
                return last_session_thumbs[session_id], getattr(self, '_prev_track_id', '')
            
        # Fallback to the media source app icon
        app_id = track.get('app_id', '')
        app_icon_pix = IconExtractor.get_app_icon_pixmap(app_id, 256)
        if app_icon_pix and not app_icon_pix.isNull():
            return app_icon_pix.toImage(), f"app_icon_{app_id}"
            
        return self._get_pandora_icon_image(), "pandora_fallback_icon"

    def _get_round_thumbnail(self, size, track, override_strength=None):
        thumb, thumb_id = self._get_fallback_thumbnail(track)
        has_media = track.get('title') and track['title'] != "No Media" and track['title'] != ""
        
        if thumb is None:
            if getattr(self, '_cached_thumb_id', '') != "":
                if self._cached_round_thumb and not self._cached_round_thumb.isNull():
                    self._prev_thumb = self._cached_round_thumb
                self._thumb_anim_progress = 0.0
            self._cached_thumb_id = ""
            self._cached_thumb = None
            self._cached_round_thumb = None
            return None
            
        blur_strength = override_strength if override_strength is not None else self.settings.get('effect_strength')
        if blur_strength is None: blur_strength = 25

        track_id = f"{track.get('title', '')}_{track.get('artist', '')}_{track.get('app_id', '')}"
        art_style = self.settings.get('art_style', 'Gaussian Blur')
        
        # Check cache against track_id, thumb_id, size, blur, and style
        if getattr(self, '_cached_track_id', '') == track_id and getattr(self, '_cached_thumb_id', '') == thumb_id and self._cached_round_thumb is not None and size == self._cached_size and getattr(self, '_cached_strength', -1) == blur_strength and getattr(self, '_cached_art_style', '') == art_style:
            return self._cached_round_thumb

        # Trigger animation when track_id changes OR thumb_id changes
        if getattr(self, '_cached_track_id', '') != "" and (self._cached_track_id != track_id or getattr(self, '_cached_thumb_id', '') != thumb_id):
            if self._cached_round_thumb and not self._cached_round_thumb.isNull():
                self._prev_thumb = self._cached_round_thumb
            if self._cached_thumb and not self._cached_thumb.isNull():
                self._prev_raw_thumb = self._cached_thumb
                self._prev_track_id = self._cached_track_id
            self._thumb_anim_progress = 0.0

        self._cached_track_id = track_id
        self._cached_thumb_id = thumb_id
        self._cached_thumb = thumb
        self._cached_size = size
        self._cached_strength = blur_strength
        self._cached_art_style = art_style
        self._dominant_color = self._extract_color(thumb)
        
        result = QPixmap(size, size)
        result.fill(Qt.GlobalColor.transparent)
        p = QPainter(result)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
        path = QPainterPath()
        path.addEllipse(0, 0, size, size)
        p.setClipPath(path)
        
        if art_style == "Gaussian Blur" and blur_strength > 0:
            scaled = thumb.scaled(size, size, Qt.AspectRatioMode.KeepAspectRatioByExpanding, Qt.TransformationMode.SmoothTransformation)
            x = (scaled.width() - size) // 2
            y = (scaled.height() - size) // 2
            cropped = scaled.copy(x, y, size, size)
            
            scene = QGraphicsScene()
            item = QGraphicsPixmapItem(QPixmap.fromImage(cropped))
            blur = QGraphicsBlurEffect()
            blur.setBlurRadius(blur_strength * 0.5)
            item.setGraphicsEffect(blur)
            scene.addItem(item)
            
            blurred_pixmap = QPixmap(size, size)
            blurred_pixmap.fill(Qt.GlobalColor.transparent)
            blur_painter = QPainter(blurred_pixmap)
            scene.render(blur_painter)
            blur_painter.end()
            p.drawPixmap(0, 0, blurred_pixmap)
        else:
            scaled = thumb.scaled(size, size, Qt.AspectRatioMode.KeepAspectRatioByExpanding, Qt.TransformationMode.SmoothTransformation)
            x = (scaled.width() - size) // 2
            y = (scaled.height() - size) // 2
            cropped = scaled.copy(x, y, size, size)
            p.drawImage(0, 0, cropped)

        p.end()
        self._cached_round_thumb = result
        return result

    def draw(self, p, cx, cy, inner_radius):
        track = self.media_mgr.current_track
        has_media = track.get('title') and track['title'] != "No Media" and track['title'] != ""
        
        # Retrieve animation style profiles unconditionally
        anim_style = self.settings.get('animation_style', 'Balanced')
        voxel_prof = VOXEL_PROFILES.get(anim_style, VOXEL_PROFILES["Balanced"])
        pulse_prof = SIZE_PULSING_PROFILES.get(anim_style, SIZE_PULSING_PROFILES["Balanced"])
        ring_prof = RING_EQ_PROFILES.get(anim_style, RING_EQ_PROFILES["Balanced"])
        

            
        # Smoothly interpolate dominant color on every frame for gradual color shifts
        if has_media:
            curr_raw = self.media_mgr.thumbnail
            if curr_raw is None:
                app_id = track.get('app_id', '')
                app_icon_pix = IconExtractor.get_app_icon_pixmap(app_id, 256)
                if app_icon_pix and not app_icon_pix.isNull():
                    curr_raw = app_icon_pix.toImage()
                else:
                    curr_raw = self._get_pandora_icon_image()
            if curr_raw and not curr_raw.isNull():
                if curr_raw is self.media_mgr.thumbnail:
                    session_id = track.get('session_id', '')
                    if session_id:
                        if not hasattr(self.media_mgr, '_last_session_thumbs'):
                            self.media_mgr._last_session_thumbs = {}
                        self.media_mgr._last_session_thumbs[session_id] = curr_raw
                if getattr(self, '_cached_raw_for_color', None) != curr_raw:
                    self._cached_raw_for_color = curr_raw
                    self._target_color = self._extract_color(curr_raw)
                    
                target_color = getattr(self, '_target_color', QColor(189, 147, 249, 180))
                
                if not hasattr(self, '_dominant_color') or self._dominant_color is None:
                    self._dominant_color = target_color
                else:
                    r = self._dominant_color.red() + (target_color.red() - self._dominant_color.red()) * 0.08
                    g = self._dominant_color.green() + (target_color.green() - self._dominant_color.green()) * 0.08
                    b = self._dominant_color.blue() + (target_color.blue() - self._dominant_color.blue()) * 0.08
                    self._dominant_color = QColor(int(r), int(g), int(b))
        
        sessions = track.get('available_sessions', [])
        multi_session = len(sessions) > 1
        
        visualizer = self.settings.get('visualizer', 'None')
        is_playing = track.get('status') == 'Playing'
        
        if visualizer != "None" and self.manager.halo.isVisible() and has_media:
            # Calculate Delta Time
            current_time = time.time()
            dt = min(0.1, current_time - self._last_frame_time) # Cap dt at 100ms to prevent huge jumps
            self._last_frame_time = current_time
            
            audio_features = getattr(self.media_mgr, 'audio_features', None)
            if not is_playing:
                audio_features = None
            
            # Subdivided gap detection physics loop
            current_signals = self.derive_visual_signals(audio_features, None, dt)
            if self._prev_signals is None:
                self._prev_signals = current_signals
            
            # Calculate gap based on sequence drops, and enforce dt_step <= 0.008s for CFL stability
            seq = getattr(audio_features, 'sequence_number', 0)
            seq_gap = 1
            if self._prev_sequence_number > 0 and seq > self._prev_sequence_number:
                seq_gap = min(10, seq - self._prev_sequence_number)
            self._prev_sequence_number = seq
            
            cfl_gap = int(math.ceil(dt / 0.008))
            gap = max(seq_gap, cfl_gap)
            dt_step = dt / gap
            


            for step_idx in range(1, gap + 1):
                # Interpolate signals
                blend = step_idx / gap
                step_signals = {}
                for k in current_signals:
                    if not self._prev_signals or k not in self._prev_signals:
                        step_signals[k] = current_signals[k]
                    elif isinstance(current_signals[k], list):
                        step_signals[k] = [
                            prev_val * (1.0 - blend) + curr_val * blend
                            for prev_val, curr_val in zip(self._prev_signals[k], current_signals[k])
                        ]
                    elif isinstance(current_signals[k], (int, float)):
                        step_signals[k] = self._prev_signals[k] * (1.0 - blend) + current_signals[k] * blend
                    else:
                        step_signals[k] = current_signals[k]
                
                # Unpack step signals
                pulse_drive = step_signals["pulse_drive"]
                impact_primary = step_signals["impact_primary"]
                impact_secondary = step_signals["impact_secondary"]
                pan_bias = step_signals["pan_bias"]
                sharpness = step_signals["sharpness"]
                band_array = step_signals["band_array"]
                is_idle = step_signals["is_idle"]
                
                # 1. Size Pulsing Spring Update with Idle State Cross-fading
                if is_idle:
                    self._idle_fade = min(1.0, self._idle_fade + 2.0 * dt_step)
                else:
                    self._idle_fade = max(0.0, self._idle_fade - 5.0 * dt_step)
                
                target_audio = pulse_drive * pulse_prof.sensitivity
                target_idle = 0.2 + 0.1 * math.sin(time.time() * 2.0)
                pulse_target = target_audio * (1.0 - self._idle_fade) + target_idle * self._idle_fade
                
                self.pulse_spring.tension = pulse_prof.tension
                self.pulse_spring.damping = pulse_prof.damping
                self.pulse_spring.update(pulse_target, dt_step)
                
                # Mid-range pulse secondary spring
                mid_presence = (band_array[3] + band_array[5]) / 2.0
                self.pulse_mid_spring.update(mid_presence * pulse_prof.sensitivity, dt_step)
                
                # 2. Edge Ring EQ Musical Expression Update
                
                # 0. Drop Detection (Exceptional Musical Events)
                # impact_primary represents the immediate bass transient (0.0 to ~1.0)
                is_drop = impact_primary > 0.85
                drop_multiplier = 1.0
                if is_drop and not is_idle:
                    # Exponentially scale multiplier for massive impacts (1.0x to ~3.25x)
                    drop_multiplier = 1.0 + ((impact_primary - 0.85) * 15.0)
                    
                # Derive timing from animation style sensitivity
                base_attack_speed = 15.0 * ring_prof.sensitivity
                shape_decay_speed = 5.0 * ring_prof.sensitivity
                
                # If idle, gracefully settle everything over ~300-500ms (multiplier ~ 4.0)
                idle_decay = 4.0
                
                raw_bands = step_signals["norm_bands"]
                
                # Custom Band Positioning (Skip 3 Decorrelation)
                # 0: Sub (0), 1: Mid (3), 2: Treble (6), 3: Bass (1)
                # 4: Upper Mid (4), 5: Air (7), 6: Low Mid (2), 7: Presence (5)
                band_map = [0, 3, 6, 1, 4, 7, 2, 5]
                norm_bands = [raw_bands[band_map[i]] for i in range(8)]
                
                # --- Musical Intelligence Processing ---
                mi_result = self.musical_intelligence.process(
                    norm_bands, step_signals["rms"], impact_primary, dt_step
                )
                art_bands = mi_result["art_bands"]
                mi_context = mi_result["context"]
                
                # Blend raw spectrum with artistic importance for shape
                # 70% raw (musical honesty) + 30% artistic (visual hierarchy)
                shape_bands = [0.0] * 8
                art_blend = 0.3 * mi_context["confidence"]  # Only bias when confident
                for i in range(8):
                    shape_bands[i] = norm_bands[i] * (1.0 - art_blend) + art_bands[i] * art_blend
                
                # Context-driven motion characteristics
                # Brightness → sharper responses, cleaner geometry
                brightness_mod = 1.0 + mi_context["brightness"] * 0.3
                # Warmth → softer motion, heavier material
                warmth_mod = 1.0 - mi_context["warmth"] * 0.2
                
                context_attack = base_attack_speed * brightness_mod
                context_decay = shape_decay_speed * warmth_mod
                
                # Layer 3: Breathing (Global Intensity)
                # Slow attack, slow decay based on overall energy
                breath_target = step_signals["rms"] * 0.5 if not is_idle else 0.0
                if breath_target > self.ring_global_breath:
                    self.ring_global_breath += (breath_target - self.ring_global_breath) * 3.0 * dt_step
                else:
                    self.ring_global_breath += (breath_target - self.ring_global_breath) * (1.0 if not is_idle else idle_decay) * dt_step

                # Layer 1: Shape (Blended Spectrum, context-modulated attack/decay)
                for i in range(8):
                    target_shape = shape_bands[i] if not is_idle else 0.0
                    delta = target_shape - self.ring_shape[i]
                    if delta > 0:
                        # Adaptive attack: faster for larger changes, massively accelerated by drops
                        dynamic_attack = context_attack + (delta * 60.0)
                        dynamic_attack *= drop_multiplier
                        self.ring_shape[i] += delta * dynamic_attack * dt_step
                    else:
                        self.ring_shape[i] += delta * (context_decay if not is_idle else idle_decay) * dt_step
                        
                # Layer 1.5: High-Resolution Texture (32 Bins)
                filament_bands = step_signals["filament_bands"]
                base_fil_attack = 40.0 * ring_prof.sensitivity
                base_fil_decay = 12.0 * ring_prof.sensitivity
                
                for i in range(self.filament_resolution):
                    target_fil = filament_bands[i] if not is_idle else 0.0
                    delta_fil = target_fil - self.filament_shape[i]
                    
                    if delta_fil > 0:
                        fil_attack = (base_fil_attack + (delta_fil * 80.0)) * brightness_mod
                        self.filament_shape[i] += delta_fil * fil_attack * dt_step
                    else:
                        fil_decay = (base_fil_decay * warmth_mod) if not is_idle else idle_decay
                        self.filament_shape[i] += delta_fil * fil_decay * dt_step
                        
                # Layer 2: Pulse (Momentary Global Pressure Wave)
                # Triggered primarily on exceptional drops
                pulse_target = impact_primary * ring_prof.sensitivity * 0.5 if not is_idle else 0.0
                if drop_multiplier > 1.0:
                    pulse_target *= drop_multiplier
                    
                delta_pulse = pulse_target - self.ring_global_pulse
                if delta_pulse > 0:
                    pulse_attack = 20.0 + (delta_pulse * 100.0)
                    pulse_attack *= drop_multiplier
                    self.ring_global_pulse += delta_pulse * pulse_attack * dt_step 
                else:
                    self.ring_global_pulse += delta_pulse * (6.0 if not is_idle else idle_decay) * dt_step # ~166ms smooth decay
                    
                # Multi-Factor Thickness System (Driven by art_bands for visual hierarchy)
                avg_art = sum(art_bands) / 8.0 if not is_idle else 0.0
                
                for i in range(8):
                    if is_idle:
                        self.ring_prev_bands[i] = 0.0
                        thick_target = 0.0
                    else:
                        # 1. Artistic Magnitude (Base) — from Musical Intelligence
                        mag = art_bands[i]
                        
                        # 2. Spectral Dominance (against artistic average)
                        dom = max(0.0, art_bands[i] - avg_art)
                        
                        # 3. Local Contrast (between neighboring artistic bands)
                        prev_idx = (i - 1) % 8
                        next_idx = (i + 1) % 8
                        avg_neighbor = (art_bands[prev_idx] + art_bands[next_idx]) / 2.0
                        contrast = max(0.0, art_bands[i] - avg_neighbor)
                        
                        # 4. Transient Impact (frame-to-frame delta on raw bands for immediacy)
                        transient = max(0.0, norm_bands[i] - self.ring_prev_bands[i])
                        self.ring_prev_bands[i] = norm_bands[i]
                        
                        # Combine weights (Dom: 0.5, Con: 0.3, Trans: 0.2) + baseline mag
                        raw_importance = (mag * 0.1) + (dom * 0.5) + (contrast * 0.3) + (transient * 0.2)
                        
                        # Non-linear curve to aggressively expand dominant peaks
                        curved_importance = math.pow(raw_importance, 1.5)
                        
                        # Scale with drop multiplier and loudness presence
                        target_mult = 2.8 * drop_multiplier
                        thick_target = curved_importance * target_mult * ring_prof.sensitivity * (1.0 + self.ring_global_breath * 0.5)
                        
                    # Adaptive fast attack (brightness-modulated), smooth decay (warmth-modulated)
                    delta_thick = thick_target - self.ring_thick[i]
                    if delta_thick > 0:
                        base_thick_attack = 15.0 * ring_prof.sensitivity
                        dynamic_attack = (base_thick_attack + (delta_thick * 40.0)) * brightness_mod
                        dynamic_attack *= drop_multiplier
                        self.ring_thick[i] += delta_thick * dynamic_attack * dt_step
                    else:
                        base_thick_decay = 8.0 * ring_prof.sensitivity
                        self.ring_thick[i] += delta_thick * ((base_thick_decay * warmth_mod) if not is_idle else idle_decay) * dt_step

                # ---------------------------------------------------------
                # Phase 7: Surface Flow System (Fluid Dynamics for Thickness)
                # ---------------------------------------------------------
                pts = 120
                target_thick = [0.0] * pts
                for i in range(pts):
                    hist_idx = (i / pts) * 8.0
                    idx = int(math.floor(hist_idx))
                    mu = hist_idx - idx
                    
                    t0 = self.ring_thick[(idx - 1) % 8]
                    t1 = self.ring_thick[idx % 8]
                    t2 = self.ring_thick[(idx + 1) % 8]
                    t3 = self.ring_thick[(idx + 2) % 8]
                    target_thick[i] = max(0.0, _catmull_rom(t0, t1, t2, t3, mu))
                    
                # Flow speed based on musical density (RMS)
                if not is_idle:
                    self.surface_flow_speed += (step_signals["rms"] - self.surface_flow_speed) * 2.0 * dt_step
                else:
                    self.surface_flow_speed += (0.0 - self.surface_flow_speed) * idle_decay * dt_step
                    
                # Drift represents how many indices the material shifts per frame
                # Significantly increased flow speed so it travels across the ring. Scaled by sensitivity.
                drift = (0.15 + self.surface_flow_speed * 1.5) * 60.0 * dt_step * ring_prof.sensitivity
                
                new_surface = [0.0] * pts
                for i in range(pts):
                    # 1. Drift (Read from upstream to flow clockwise)
                    src_idx = i - drift
                    idx0 = int(math.floor(src_idx)) % pts
                    idx1 = (idx0 + 1) % pts
                    mu = src_idx - math.floor(src_idx)
                    
                    # Linearly interpolate the shifted value
                    flow_val = self.surface_thick[idx0] * (1.0 - mu) + self.surface_thick[idx1] * mu
                    
                    # 2. Inject local thickness from bands (Only ADD material)
                    t_target = target_thick[i]
                    if t_target > flow_val:
                        flow_val += (t_target - flow_val) * 15.0 * dt_step # Inject fast
                        
                    # 3. Natural evaporation (Drastically reduced so material can travel far)
                    flow_val -= flow_val * (0.4 if not is_idle else idle_decay) * dt_step
                        
                    new_surface[i] = flow_val
                    
                # 4. Surface Tension (Blur / Spread)
                blur = 4.0 * dt_step # Minimal blur to maintain cohesive clumps
                for i in range(pts):
                    left = new_surface[(i - 1) % pts]
                    right = new_surface[(i + 1) % pts]
                    center = new_surface[i]
                    self.surface_thick[i] = center * (1.0 - blur) + ((left + right) / 2.0) * blur
                
                # 3. Coupled Wave Node Chain Physics Update (16 nodes)
                voxel_tension = voxel_prof.tension * sharpness
                voxel_damping = voxel_prof.damping * math.sqrt(sharpness)
                norm_bands = step_signals["norm_bands"]
                
                accels = []
                for i in range(16):
                    left_val = self.node_values[i-1] if i > 0 else 0.0
                    right_val = self.node_values[i+1] if i < 15 else 0.0
                    
                    # Neighbor coupling wave force
                    accel_coupling = WAVE_COUPLING * (left_val + right_val - 2.0 * self.node_values[i])
                    
                    # Target chasing spring force (chasing normalized band target)
                    band_idx = i // 2
                    target_val = norm_bands[band_idx] * voxel_prof.sensitivity
                    accel_target = (target_val - self.node_values[i]) * voxel_tension
                    
                    # Damping force
                    accel_damping = -voxel_damping * self.node_velocities[i]
                    
                    # Asymmetric pan bias kick
                    col_primary = impact_primary * voxel_prof.sensitivity * VOXEL_PRIMARY_KICK_SCALE
                    col_secondary = 0.0
                    if band_idx in [4, 5]:
                        col_secondary = impact_secondary * voxel_prof.sensitivity * VOXEL_SECONDARY_KICK_SCALE
                    
                    pan_factor = 1.0 + (i / 15.0 - 0.5) * 2.0 * pan_bias
                    kick_force = (col_primary + col_secondary) * pan_factor * 800.0
                    
                    total_accel = accel_coupling + accel_target + accel_damping
                    accels.append((total_accel, kick_force))
                
                # Apply updates to all nodes
                for i in range(16):
                    total_accel, kick_force = accels[i]
                    self.node_velocities[i] += (total_accel + kick_force) * dt_step
                    self.node_values[i] += self.node_velocities[i] * dt_step
                    
                    # Guard against NaN/inf propagation
                    if math.isnan(self.node_values[i]) or math.isinf(self.node_values[i]):
                        self.node_values[i] = 0.0
                        self.node_velocities[i] = 0.0
            
            self._prev_signals = current_signals
            
            # Retrieve values for drawing code (consuming from current_signals)
            pulse_drive = current_signals["pulse_drive"]
            impact_primary = current_signals["impact_primary"]
            impact_secondary = current_signals["impact_secondary"]
            pan_bias = current_signals["pan_bias"]
            sharpness = current_signals["sharpness"]
            band_array = current_signals["band_array"]
            is_idle = current_signals["is_idle"]
            voxel_weights = current_signals.get("voxel_weights", {'bass': 1.0, 'mids': 0.0, 'treble': 0.0})
            voxel_band_energies = current_signals.get("voxel_band_energies", {'bass': 0.0, 'mids': 0.0, 'treble': 0.0})
            voxel_mids_dir = current_signals.get("voxel_mids_dir", 1.0)
            voxel_treble_state = current_signals.get("voxel_treble_state", 0)
            voxel_bass_phase = current_signals.get("voxel_bass_phase", 0.0)
            voxel_mids_phase = current_signals.get("voxel_mids_phase", 0.0)
            voxel_treble_phase = current_signals.get("voxel_treble_phase", 0.0)
            
            # Map variables for backward compatibility
            raw_peak = current_signals["raw_peak"]
            impact = impact_primary
            warmth = band_array[1]
            sparkle = band_array[6]
            rhythm = band_array[0]
            energy = pulse_drive # Route standard energy fallback through pulse_drive
            bands = band_array
            
            eased_peak = energy ** 0.8
        else:
            self._last_frame_time = time.time()
            self._prev_sequence_number = 0
            self._prev_signals = None
            self._idle_frame_counter = 0
            self._idle_fade = 0.0
            self._prev_mid_pres = 0.0
            raw_peak = 0.0
            impact = 0.0
            warmth = 0.0
            sparkle = 0.0
            rhythm = 0.0
            energy = 0.0
            bands = [0.0] * 8
            eased_peak = 0.0
            is_idle = True
        active_id = None
        if self._holding:
            if hasattr(self.manager.halo, 'active_index') and self.manager.halo.active_index != -1:
                tools = self.manager.halo.current_tools
                if self.manager.halo.active_index < len(tools):
                    active_id = tools[self.manager.halo.active_index]['id']

        # 1. Base Hub (Album Art Background)
        size = int(inner_radius * 2) - 8
        art_style = self.settings.get('art_style', 'Gaussian Blur')
        effect_strength = self.settings.get('effect_strength')
        if effect_strength is None: effect_strength = 25
        
        global_op = p.opacity()

        # Edge Ring EQ (Wavy Line)
        if visualizer == "Edge Ring EQ":
            glow_c = QColor(self._dominant_color)
            
            op = max(0.15, min(1.0, (eased_peak + sum(bands)/8.0) * 1.5))
            
            # Phase 5: Glow Intensity based on Loudness (Breath)
            op = max(op, 0.15 + self.ring_global_breath * 0.2)
                
            glow_c.setAlpha(int(op * 180 * global_op))
                        
            p.setPen(Qt.PenStyle.NoPen)
            ring_r = size//2 + 10
            pts = 120
            
            # The trigger threshold dynamically adjusts based on animation sensitivity.
            # Lively (1.8): Triggers earlier at ~0.91
            # Ambient (0.4): Extremely hard to trigger at ~0.98
            # Balanced (1.0): Normal threshold at 0.95
            instability_threshold = max(0.85, min(0.99, 1.0 - (0.05 * ring_prof.sensitivity)))
            
            # Global Center Instability (Shaking the entire ring at max volume)
            max_shape = max(self.filament_shape) if self.filament_shape else 0.0
            
            # Scale dynamically based on the calculated threshold
            instability_scale = 1.0 / (1.0 - instability_threshold)
            global_instability = max(0.0, (max_shape - instability_threshold) * instability_scale)
            
            if global_instability > 0:
                maxed_bins = sum(1 for val in self.filament_shape if val > instability_threshold)
                bin_ratio = maxed_bins / self.filament_resolution
                
                # Only shake the center if more than 85% of the bins are maxing out
                # This prevents normal videos/music from triggering the violent shake
                if bin_ratio > 0.85:
                    # Map the top 15% (0.85 -> 1.0) to a 0.0 -> 1.0 intensity multiplier
                    intensity_curve = (bin_ratio - 0.85) * 6.66
                    
                    t = time.time()
                    # Speed scales from moderate to violent
                    speed_x = 10.0 + (intensity_curve * 75.0)
                    speed_y = 12.0 + (intensity_curve * 90.0)
                    
                    # Distance scales strictly based on intensity
                    shake_dist = 2.5 * intensity_curve
                    
                    cx += math.sin(t * speed_x) * global_instability * shake_dist
                    cy += math.cos(t * speed_y) * global_instability * shake_dist
            
            # 1. Pre-calculate all ring geometry and fluid thickness
            # To avoid redundant math for multiple concentric layers
            radii = [0.0] * (pts + 1)
            fluids = [0.0] * (pts + 1)
            angles = [0.0] * (pts + 1)
            
            global_expansion = self.ring_global_pulse * 2.5 + (self.ring_global_breath * 8.0 * ring_prof.sensitivity)
            base_thick = 2.0 + (self.ring_global_breath * 0.6)
            
            for i in range(pts + 1):
                idx_pts = i % pts
                angles[i] = (i / pts) * 2 * math.pi - (math.pi / 2)
                
                # Main ring geometry using 32 high-resolution bins
                hist_idx = (i / pts) * self.filament_resolution
                idx = int(math.floor(hist_idx))
                mu = hist_idx - idx
                
                r0 = self.filament_shape[(idx - 1) % self.filament_resolution]
                r1 = self.filament_shape[idx % self.filament_resolution]
                r2 = self.filament_shape[(idx + 1) % self.filament_resolution]
                r3 = self.filament_shape[(idx + 2) % self.filament_resolution]
                val_r = max(0.0, _catmull_rom(r0, r1, r2, r3, mu))
                val_r *= (0.9 + self.ring_global_breath * 0.25)
                
                # High-Volume Boundary Instability
                # As `val_r` approaches its physical maximum limit, inject a sweeping surge
                # This causes the mass of the ring to smoothly pan/rotate around the circle
                instability = max(0.0, (val_r - instability_threshold) * instability_scale)
                
                if instability > 0:
                    t = time.time()
                    # Low-frequency, fast-moving waves create a sweeping/panning mass
                    # angles[i] * 2.0 creates 2 large lobes. t * 15.0 spins them quickly.
                    surge = math.sin(angles[i] * 2.0 + t * 15.0) * 0.5 + math.cos(angles[i] * 3.0 - t * 10.0) * 0.5
                    val_r += surge * instability * 0.20 # Smooth sweeping distortion
                
                radii[i] = ring_r + val_r * 60.0 + global_expansion
                fluids[i] = self.surface_thick[idx_pts]

            # --- HARDWARE ACCELERATED RING ---
            import hub_modules.vis_engine_bridge as vis
            vis.init_ui_engine()
            vis.begin_ui_frame(0.0, 0.0, 0.0, 0.0)
            
            # Extract AARRGGBB
            rgba = glow_c.rgba() 
            
            # The DLL handles the heavy 256-point geometry calculation & rendering natively on the Dedicated GPU
            vis.draw_d2d_ring(radii, fluids, 512, base_thick, rgba, op * global_op)
            ring_img = vis.end_ui_frame()
            
            if ring_img and not ring_img.isNull():
                p.drawImage(QRectF(cx - 256, cy - 256, 512, 512), ring_img)
            # ---------------------------------

        # Draw the Thumbnail/Art
        thumb, thumb_id = self._get_fallback_thumbnail(track)
        
        if art_style == "Liquid Ferrofluid" and effect_strength > 0:
            import hub_modules.vis_engine_bridge as vis
            pref_gpu = int(self.manager.cfg.get('general_settings', {}).get('gpu_preference', 0))
            if not getattr(self, '_vis_engine_inited', False) or getattr(self, '_current_gpu_pref', -1) != pref_gpu:
                gpu_pref = pref_gpu
                if vis.init_vis_engine(512, 512, gpu_pref):
                    self._vis_engine_inited = True
                    self._current_gpu_pref = gpu_pref
            if getattr(self, '_vis_engine_inited', False):
                # Init Texture
                if getattr(self, '_cached_ferro_thumb_id', None) != thumb_id:
                    self._cached_ferro_thumb_id = thumb_id
                    vis.init_ferrofluid(thumb)
                    
                    # Extract Dominant Color from thumbnail
                    # Very basic center-ish sampling for dominant color
                    img_ptr = thumb.convertToFormat(QImage.Format.Format_RGB32)
                    r_sum, g_sum, b_sum, count = 0, 0, 0, 0
                    for y in range(0, img_ptr.height(), 10):
                        for x in range(0, img_ptr.width(), 10):
                            px = img_ptr.pixel(x, y)
                            r_sum += (px >> 16) & 0xFF
                            g_sum += (px >> 8) & 0xFF
                            b_sum += px & 0xFF
                            count += 1
                    if count > 0:
                        dom = ((r_sum//count) << 16) | ((g_sum//count) << 8) | (b_sum//count)
                        self._cached_ferro_dominant_color = dom
                    else:
                        self._cached_ferro_dominant_color = 0x888888
                
                vbe = locals().get('voxel_band_energies', {})
                bass_e = vbe.get('bass', 0.0)
                mids_e = vbe.get('mids', 0.0)
                treble_e = vbe.get('treble', 0.0)
                time_t = time.time()
                
                use_texture_setting = self.settings.get('ferrofluid_mode', 'Dominant Color')
                use_texture = 1 if use_texture_setting == 'Album Art' else 0
                dom_color = getattr(self, '_cached_ferro_dominant_color', 0x888888)
                
                ferro_img = vis.render_ferrofluid(
                    bass_e, mids_e, treble_e, time_t, 
                    use_texture, dom_color, global_op
                )
                
                if ferro_img and not ferro_img.isNull():
                    p.setOpacity(1.0)
                    
                    p.save()
                    path = QPainterPath(); path.addEllipse(int(cx - size//2), int(cy - size//2), size, size); p.setClipPath(path)
                    p.drawImage(QRectF(cx - size/2, cy - size/2, size, size), ferro_img)
                    p.restore()

        elif art_style == "8-Bit Mosaic" and effect_strength > 0:
            import hub_modules.vis_engine_bridge as vis
            pref_gpu = int(self.manager.cfg.get('general_settings', {}).get('gpu_preference', 0))
            if not getattr(self, '_vis_engine_inited', False) or getattr(self, '_current_gpu_pref', -1) != pref_gpu:
                gpu_pref = pref_gpu
                if vis.init_vis_engine(512, 512, gpu_pref):
                    self._vis_engine_inited = True
                    self._current_gpu_pref = gpu_pref
            mosaic_shape = self.settings.get('mosaic_shape', 'Square')
            if thumb:
                block_size = int(12 + (effect_strength / 100.0) * 32)
                
                # Check setting for block_size override
                setting_block_size = self.settings.get('mosaic_size', 12)
                if setting_block_size != 12:
                    block_size = setting_block_size

                grid_dim = 512 // block_size
                
                if getattr(self, '_cached_mosaic_thumb_id', '') == thumb_id and getattr(self, '_cached_block_size', -1) == block_size and self._cached_mosaic_color_map is not None:
                    color_map = self._cached_mosaic_color_map
                else:
                    self._cached_mosaic_thumb_id = thumb_id
                    self._cached_block_size = block_size
                    color_map = thumb.scaled(grid_dim, grid_dim, Qt.AspectRatioMode.IgnoreAspectRatio, Qt.TransformationMode.SmoothTransformation)
                    self._cached_mosaic_color_map = color_map
                
                if getattr(self, '_vis_engine_inited', False):
                    vis.init_mosaic(color_map, block_size, mosaic_shape)
                    
                    vbe = locals().get('voxel_band_energies', {})
                    cs = locals().get('current_signals', {})
                    
                    bass_e = vbe.get('bass', 0.0)
                    mids_e = vbe.get('mids', 0.0)
                    treble_e = vbe.get('treble', 0.0)
                    ext_factor = cs.get("voxel_extrusion", 0.0)
                    w_x = cs.get("voxel_treble_wave_x", 0.0)
                    w_y = cs.get("voxel_treble_wave_y", 1.0)
                    d_x = cs.get("voxel_treble_disp_x", 1.0)
                    d_y = cs.get("voxel_treble_disp_y", 0.0)
                    b_phase = locals().get('voxel_bass_phase', 0.0)
                    m_phase = locals().get('voxel_mids_phase', 0.0)
                    t_phase = locals().get('voxel_treble_phase', 0.0)
                    
                    ring_t = [0.0] * 8
                    if hasattr(self, 'ring_thick') and len(self.ring_thick) >= 8:
                        ring_t = self.ring_thick[:8]
                        
                    mosaic_img = vis.render_mosaic(
                        bass_e, mids_e, treble_e, ext_factor, w_x, w_y, d_x, d_y, 
                        b_phase, m_phase, t_phase, ring_t, global_op
                    )
                    
                    if mosaic_img and not mosaic_img.isNull():
                        p.setOpacity(1.0)
                        
                        # Apply circular clipping since the C++ engine doesn't clip the outer edge
                        p.save()
                        path = QPainterPath(); path.addEllipse(int(cx - size//2), int(cy - size//2), size, size); p.setClipPath(path)
                        p.drawImage(QRectF(cx - size/2, cy - size/2, size, size), mosaic_img)
                        p.restore()

        else:
            thumb = self._get_round_thumbnail(size, track, override_strength=effect_strength)
            if thumb:
                p.save()
                
                # Advance thumbnail transition animation
                anim_prog = getattr(self, '_thumb_anim_progress', 1.0)
                if anim_prog < 1.0:
                    self._thumb_anim_progress = min(1.0, anim_prog + 0.08)
                    self.manager.halo.update()
                
                # Apply scale transform for Voxel Wiggle fallback on standard art
                global_op = p.opacity()
                if visualizer == "Reactive Voxels":
                    # Combine pulse_spring and pulse_drive for combined Voxel Wiggle / Size Pulsing fallback
                    pulse_drive = locals().get('pulse_drive', 0.0)
                    scale_val = self.pulse_spring.value + pulse_drive * 0.5
                    scale = 1.0 + (scale_val * 0.10)
                        
                    p.translate(cx, cy)
                    p.scale(scale, scale)
                    
                    if anim_prog < 1.0 and hasattr(self, '_prev_thumb') and self._prev_thumb:
                        p.setOpacity(global_op * (1.0 - anim_prog))
                        p.drawPixmap(int(-size//2), int(-size//2), self._prev_thumb)
                        
                    p.setOpacity(global_op * anim_prog)
                    p.drawPixmap(int(-size//2), int(-size//2), thumb)
                else:
                    if anim_prog < 1.0 and hasattr(self, '_prev_thumb') and self._prev_thumb:
                        p.setOpacity(global_op * (1.0 - anim_prog))
                        p.drawPixmap(int(cx - size//2), int(cy - size//2), self._prev_thumb)
                        
                    p.setOpacity(global_op * anim_prog)
                    p.drawPixmap(int(cx - size//2), int(cy - size//2), thumb)
                
                p.setOpacity(global_op)
                p.restore()
            else:
                pix = VectorIcon.pixmap("music", self._dominant_color.name(), 40)
                p.drawPixmap(int(cx - 20), int(cy - 40), pix)

        # Determine local vibe based on album art luminance
        lum = 0
        if getattr(self, '_dominant_color', None):
            c = self._dominant_color
            lum = 0.299 * c.red() + 0.587 * c.green() + 0.114 * c.blue()
        is_album_light = (lum > 160)
        
        if thumb:
            grad = QRadialGradient(cx, cy, inner_radius)
            if is_album_light:
                grad.setColorAt(0.4, QColor(255, 255, 255, 40))
                grad.setColorAt(0.9, QColor(255, 255, 255, 180))
            else:
                grad.setColorAt(0.4, QColor(0, 0, 0, 40))
                grad.setColorAt(0.9, QColor(0, 0, 0, 200))
            p.setBrush(QBrush(grad)); p.setPen(Qt.PenStyle.NoPen); p.drawEllipse(QPointF(cx, cy), size//2, size//2)

        # 2. Arcs & Info
        arc_r = inner_radius - 6; arc_rect = QRectF(cx - arc_r, cy - arc_r, arc_r * 2, arc_r * 2)
        show_timeline = self.settings.get('show_timeline', True)
        if show_timeline:
            pos = track.get('position', 0); dur = track.get('duration', 0); sync_time = track.get('sync_time', 0)
            if is_playing and sync_time > 0 and dur > 0:
                pos += time.time() - sync_time
                if pos > dur: pos = dur
            progress = min(1.0, pos / dur) if dur > 0 else 0
            anim_prog = getattr(self, '_thumb_anim_progress', 1.0)
            if anim_prog < 1.0:
                e_prog = 1.0 - (1.0 - anim_prog) ** 2; prev_prog = getattr(self, '_prev_timeline_progress', 0.0)
                progress = prev_prog + (progress - prev_prog) * e_prog
            else: self._prev_timeline_progress = progress
            is_timeline_hover = (active_id == 'timeline'); arc_w = 6 if is_timeline_hover else 3
            
            is_light = is_album_light
            text_color = QColor(36, 41, 47) if is_light else QColor(255, 255, 255)
            text_sub = QColor(36, 41, 47, 160) if is_light else QColor(255, 255, 255, 160)
            track_bg = QColor(0, 0, 0, 15) if is_light else QColor(255, 255, 255, 25)
            
            p.setPen(QPen(track_bg, arc_w, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap)); p.drawArc(arc_rect, 90 * 16, -360 * 16)
            if progress > 0.001:
                tc = QColor(0, 240, 255) if is_timeline_hover else self._dominant_color
                if is_timeline_hover:
                    for i in range(2):
                        gp = QPen(QColor(0, 240, 255, 30), arc_w + (i+1)*3); p.setPen(gp); p.drawArc(arc_rect, 90 * 16, int(-360 * progress * 16))
                p.setPen(QPen(QColor(tc.red(), tc.green(), tc.blue(), 230), arc_w, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap)); p.drawArc(arc_rect, 90 * 16, int(-360 * progress * 16))

        if self.settings.get('show_title', True):
            title = track.get('title', ''); artist = track.get('artist', '')
            p.setPen(text_color); p.setFont(QFont("Segoe UI Variable Display", 9, QFont.Weight.Bold))
            p.drawText(QRectF(cx-80, cy + 5, 160, 18), Qt.AlignmentFlag.AlignCenter, title if len(title) <= 20 else title[:19] + "..")
            p.setPen(text_sub); p.setFont(QFont("Segoe UI Variable Display", 7))
            p.drawText(QRectF(cx-80, cy + 22, 160, 14), Qt.AlignmentFlag.AlignCenter, artist if len(artist) <= 25 else artist[:24] + "..")

        if self.settings.get('show_controls', True):
            action_text = ""
            if active_id in ['prev', 'next']: action_text = "SKIP NEXT" if active_id == 'next' else "SKIP PREV"
            elif active_id in ['volume', 'timeline']:
                vol = track.get('app_volume', 0.5)
                if active_id == 'volume': action_text = f"VOLUME {int(vol * 100)}%"
                else:
                    pos = track.get('position', 0); dur = track.get('duration', 0)
                    if is_playing and sync_time > 0 and dur > 0: pos += time.time() - sync_time
                    def fmt(s): m, s = int(s // 60), int(s % 60); return f"{m}:{s:02d}"
                    action_text = f"{fmt(pos)} / {fmt(dur)}"
            if action_text:
                p.setPen(QColor(0, 240, 255) if not is_light else QColor(0, 150, 255)); p.setFont(QFont("Segoe UI Variable Display", 8, QFont.Weight.Bold))
                p.drawText(QRectF(cx-80, cy - 25, 160, 15), Qt.AlignmentFlag.AlignCenter, action_text)
            elif not self._holding and has_media:
                ic = "pause" if is_playing else "play"
                icon_color = "#24292f" if is_light else "#ffffff"
                p.drawPixmap(int(cx - 8), int(cy - 20), VectorIcon.pixmap(ic, icon_color, 16))

        if multi_session and not self._holding:
            num = len(sessions)
            curr_session_id = track.get('session_id')
            idx = next((i for i,s in enumerate(sessions) if s.get('session_id') == curr_session_id), 0)
            
            arc_r = inner_radius - 15
            arc_rect = QRectF(cx - arc_r, cy - arc_r, arc_r * 2, arc_r * 2)
            span = min(60, num * 15)
            seg_span = span / num
            gap = 2.5 if num > 1 else 0
            
            p.setBrush(Qt.GlobalColor.transparent)
            for i in range(num):
                a_start = 270 - (span / 2.0) + (i * seg_span) + (gap / 2.0)
                a_len = seg_span - gap
                color = QColor(255, 255, 255) if i == idx else QColor(255, 255, 255, 60)
                p.setPen(QPen(color, 4, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
                p.drawArc(arc_rect, int(a_start * 16), int(a_len * 16))

    def on_key_press(self, event):
        try:
            if hasattr(event, 'isAutoRepeat') and event.isAutoRepeat(): return False
        except Exception as e:
            from config import APPDATA_DIR
            import os
            with open(os.path.join(APPDATA_DIR, 'crash_log.txt'), 'a') as f:
                f.write(str(e) + '\\n')
        if event.key() == Qt.Key.Key_Space:
            if not getattr(self, '_space_pressed', False):
                self._space_pressed = True; self._space_press_time = time.time()
                def check_hold():
                    if getattr(self, '_space_pressed', False):
                        self._holding = True
                        if hasattr(self.manager.halo, 'set_override_tools'):
                            self.manager.halo.set_override_tools(self.media_tools)
                        self.manager.halo.update()
                from PyQt6.QtCore import QTimer
                QTimer.singleShot(150, check_hold)
                return True
        return False

    def on_key_release(self, event):
        try:
            if hasattr(event, 'isAutoRepeat') and event.isAutoRepeat(): return False
        except Exception as e:
            pass
        if event.key() == Qt.Key.Key_Space:
            was_holding = getattr(self, '_holding', False)
            self._space_pressed = False; self._holding = False
            if was_holding:
                active_id = None
                if hasattr(self.manager.halo, 'active_index') and self.manager.halo.active_index != -1:
                    tools = self.manager.halo.current_tools
                    if self.manager.halo.active_index < len(tools): active_id = tools[self.manager.halo.active_index]['id']
                if active_id and active_id in ['prev', 'next']:
                    if active_id == 'next': self.media_mgr.next_track()
                    elif active_id == 'prev': self.media_mgr.prev_track()
                    self.manager.halo.hide()
                if hasattr(self.manager.halo, 'clear_override_tools'): self.manager.halo.clear_override_tools()
            else:
                if time.time() - getattr(self, '_space_press_time', 0) < 0.3: self.media_mgr.play_pause()
            self.manager.halo.update(); return True
        return False

    def on_mouse_press(self, pos, button):
        if button == Qt.MouseButton.MiddleButton:
            self.media_mgr.switch_session(1); self.manager.halo.update(); return
        elif button == Qt.MouseButton.RightButton:
            app_id = self.media_mgr.current_track.get('app_id', '').lower()
            if app_id:
                try:
                    import pythoncom; from pycaw.pycaw import AudioUtilities; pythoncom.CoInitialize()
                    sessions = AudioUtilities.GetAllSessions(); target = app_id.lower()
                    for session in sessions:
                        if session.Process:
                            name = session.Process.name().lower()
                            if name.replace(".exe", "") in target or target in name:
                                vol = session.SimpleAudioVolume; vol.SetMute(1 if vol.GetMute() == 0 else 0, None); break
                except: pass
            self.manager.halo.update()

    def on_mouse_move(self, pos): pass
    def on_mouse_leave(self): pass
    def on_mouse_release(self, pos, button):
        if button == Qt.MouseButton.LeftButton:
            active_id = None
            if hasattr(self.manager.halo, 'active_index') and self.manager.halo.active_index != -1:
                tools = self.manager.halo.current_tools
                if self.manager.halo.active_index < len(tools): active_id = tools[self.manager.halo.active_index]['id']
            if self._holding:
                if active_id in ['prev', 'next']:
                    if active_id == 'next': self.media_mgr.next_track()
                    else: self.media_mgr.prev_track()
                return
            else: self.media_mgr.play_pause(); return

    def on_wheel(self, delta):
        if not self._holding: return False
        active_id = None
        if hasattr(self.manager.halo, 'active_index') and self.manager.halo.active_index != -1:
            tools = self.manager.halo.current_tools
            if self.manager.halo.active_index < len(tools): active_id = tools[self.manager.halo.active_index]['id']
        if active_id == 'volume':
            vol_delta = 0.02 if delta > 0 else -0.02
            new_vol = self.media_mgr.change_app_volume(vol_delta)
            if new_vol is not None:
                self.manager.halo.vol_level = new_vol
                self.manager.halo.vol_target_opacity = 1.0; self.manager.halo.vol_opacity = 1.0
                self.manager.halo.vol_hud_val = int(new_vol * 100)
                self.manager.halo.vol_hud_dir = "up" if delta > 0 else "down"
                self.manager.halo.last_adjusted_id = "volume"
                self.manager.halo.vol_fade_timer.start(1500)
                self.manager.halo.update()
            return True
        elif active_id == 'timeline':
            time_delta = 5.0 if delta > 0 else -5.0
            self.media_mgr.scrub_timeline(time_delta)
            return True
        return False
