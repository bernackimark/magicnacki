import pygame as pg

def int_to_dice_values(total: int, max_total: int = 36) -> list[int]:
    """Ex: 20 -> [5, 5, 5, 5]; 22 -> [6, 6, 5, 5]; 7 -> [5, 2]; anything above max_total is displayed as max_total"""
    total = min(total, max_total)
    max_face = 5 if total <= 20 else 6
    dice = []
    while total > 0:
        value = min(max_face, total)
        dice.append(value)
        total -= value
    return dice

def make_pg_dice(width: int, height: int, value: int) -> pg.Surface:
    """Return a surface with die pips"""
    surf = pg.Surface((width, height), pg.SRCALPHA)
    pg.draw.rect(surf, (240, 240, 240), surf.get_rect(), 0, 2)
    # pg.draw.rect(surf, (0, 0, 0), surf.get_rect(), 2, 2)

    grid_size = surf.get_size()[0] // 3
    pip_radius = surf.get_size()[0] // 10
    pos = {1: ((1, 1),), 2: ((0, 2), (2, 0)), 3: ((0, 2), (1, 1), (2, 0)), 4: ((0, 0), (0, 2), (2, 0), (2, 2)),
           5: ((0, 0), (0, 2), (2, 0), (2, 2), (1, 1)), 6: ((0, 0), (1, 0), (2, 0), (0, 2), (1, 2), (2, 2))}
    for row, col in pos[value]:
        pg.draw.aacircle(surf, (0, 0, 0), (row * grid_size + (grid_size / 2), col * grid_size + (grid_size / 2)),
                         pip_radius)
    return surf
