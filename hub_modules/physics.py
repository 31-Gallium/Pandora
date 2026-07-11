from dataclasses import dataclass

@dataclass
class MotionProfile:
    tension: float = 50.0       # Spring tension/stiffness
    damping: float = 10.0       # Spring damping (friction)
    attack: float = 10.0        # How fast decay attacks
    decay: float = 5.0          # How fast decay falls off
    sensitivity: float = 1.0    # Multiplier for the input force/scale
    smoothing: float = 0.0      # Input pre-smoothing (optional)


class Spring:
    """A critically damped, underdamped, or overdamped spring primitive."""
    def __init__(self, tension: float = 50.0, damping: float = 10.0):
        self.tension = tension
        self.damping = damping
        self.value = 0.0
        self.velocity = 0.0
        
    def update(self, target: float, dt: float) -> float:
        import math
        if math.isnan(target) or math.isinf(target):
            target = 0.0
            
        # F = -kx - cv
        force = (target - self.value) * self.tension
        force -= self.velocity * self.damping
        
        self.velocity += force * dt
        self.value += self.velocity * dt
        
        if math.isnan(self.value) or math.isinf(self.value):
            self.value = 0.0
            self.velocity = 0.0
            
        return self.value


class ExponentialDecay:
    """A primitive that snaps to peaks and decays exponentially."""
    def __init__(self, attack: float = 20.0, decay: float = 5.0):
        self.attack = attack
        self.decay = decay
        self.value = 0.0
        
    def update(self, target: float, dt: float) -> float:
        import math
        if math.isnan(target) or math.isinf(target):
            target = 0.0
            
        if target > self.value:
            # Fast attack
            self.value += (target - self.value) * self.attack * dt
        else:
            # Exponential decay
            self.value += (target - self.value) * self.decay * dt
            
        if math.isnan(self.value) or math.isinf(self.value):
            self.value = 0.0
            
        self.value = max(0.0, min(1.0, self.value))
        return self.value

# Curated Profiles

BREATHING_BLUR_PROFILES = {
    "Ambient": MotionProfile(tension=10.0, damping=8.0, sensitivity=0.4),
    "Relaxed": MotionProfile(tension=20.0, damping=10.0, sensitivity=0.6),
    "Balanced": MotionProfile(tension=40.0, damping=12.0, sensitivity=0.8),
    "Reactive": MotionProfile(tension=80.0, damping=16.0, sensitivity=1.0),
    "Lively": MotionProfile(tension=120.0, damping=18.0, sensitivity=1.2),
}

SIZE_PULSING_PROFILES = {
    "Ambient": MotionProfile(tension=20.0, damping=10.0, sensitivity=0.5),
    "Relaxed": MotionProfile(tension=40.0, damping=12.0, sensitivity=0.7),
    "Balanced": MotionProfile(tension=80.0, damping=14.0, sensitivity=1.0),
    "Reactive": MotionProfile(tension=150.0, damping=12.0, sensitivity=1.2), # Light overshoot
    "Lively": MotionProfile(tension=250.0, damping=10.0, sensitivity=1.5), # Bouncy overshoot
}

BRIGHTNESS_STROBING_PROFILES = {
    "Ambient": MotionProfile(attack=5.0, decay=2.0, sensitivity=0.3),
    "Relaxed": MotionProfile(attack=10.0, decay=4.0, sensitivity=0.6),
    "Balanced": MotionProfile(attack=30.0, decay=8.0, sensitivity=1.0),
    "Reactive": MotionProfile(attack=60.0, decay=15.0, sensitivity=1.2),
    "Lively": MotionProfile(attack=120.0, decay=25.0, sensitivity=1.5),
}

VOXEL_PROFILES = {
    "Ambient": MotionProfile(tension=15.0, damping=10.0, sensitivity=0.4),
    "Relaxed": MotionProfile(tension=30.0, damping=12.0, sensitivity=0.6),
    "Balanced": MotionProfile(tension=60.0, damping=8.0, sensitivity=1.0),
    "Reactive": MotionProfile(tension=100.0, damping=10.0, sensitivity=1.3),
    "Lively": MotionProfile(tension=200.0, damping=6.0, sensitivity=1.8),
}

RING_EQ_PROFILES = {
    "Ambient": MotionProfile(tension=10.0, damping=10.0, sensitivity=0.4, smoothing=0.08),
    "Relaxed": MotionProfile(tension=20.0, damping=15.0, sensitivity=0.7, smoothing=0.15),
    "Balanced": MotionProfile(tension=40.0, damping=20.0, sensitivity=1.0, smoothing=0.3),
    "Reactive": MotionProfile(tension=80.0, damping=25.0, sensitivity=1.4, smoothing=0.5),
    "Lively": MotionProfile(tension=150.0, damping=30.0, sensitivity=1.8, smoothing=0.8),
}
