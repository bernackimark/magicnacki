import random
from typing import Callable, Any

class Animation:
    """Generic animation for any property."""
    def __init__(self, update_fn: Callable[[float], None], duration: float, effect_fn: Callable[[float], Any] = None):
        """duration: Total duration in seconds
           update_fn: Callable receiving eased progress [0..1], updates the target
           effect_fn: Optional easing / effect function applied to progress"""
        self.duration = duration
        self.update_fn = update_fn
        self.effect_fn = effect_fn or (lambda p: p)
        self.timer = duration
        self.finished = False

    def update(self, dt: float):
        if self.finished:
            return

        self.timer -= dt
        progress = max(0.0, min(1.0, 1 - self.timer / self.duration))
        eased_progress = self.effect_fn(progress)
        self.update_fn(eased_progress)

        if self.timer <= 0:
            self.finished = True


# Effect functions
def jiggle(progress: float, magnitude: float = 6.0, slows_over_time: bool = False):
    """Return x, y offsets for jiggle; fades out over time."""
    scale = 1 - progress if slows_over_time else 1
    return random.uniform(-magnitude, magnitude) * scale, random.uniform(-magnitude, magnitude) * scale

