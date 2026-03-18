from random import randint

def jiggle_and_slow(x: int, y: int, intensity: int, pct_thru_animation: float) -> tuple[int, int]:
    intensity = int(intensity * pct_thru_animation)
    return randint(x - intensity, x + intensity), randint(y - intensity, y + intensity)
