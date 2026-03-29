import math

# def get_fan_positions(n_cards, center_x, center_y, radius, angle_spread_deg) -> list[tuple[float, float, float]]:
#     """Fan images around an invisible semicircle (like someone holding a hand of playing cards)"""
#     if n_cards == 1:
#         return [(center_x, center_y - radius, 0)]
#
#     positions = []
#
#     start_angle = -angle_spread_deg / 2
#     angle_step = angle_spread_deg / (n_cards - 1)
#
#     for i in range(n_cards):
#         angle_deg = start_angle + i * angle_step
#         angle_rad = math.radians(angle_deg)
#
#         x = center_x + radius * math.sin(angle_rad)
#         y = center_y - radius * math.cos(angle_rad)
#
#         positions.append((x, y, angle_deg))
#
#     return positions
#
# import math

def get_fan_positions(item_cnt: int, center_x: int, center_y: int, radius: int, angle_step: int = 8):
    """Fan cards symmetrically around the center card (each item has a static angle_step number of degrees)"""
    if item_cnt == 1:
        return [(center_x, center_y - radius, 0)]

    positions = []
    angle_step = angle_step
    mid_idx = (item_cnt - 1) / 2

    for i in range(item_cnt):
        angle_deg = (i - mid_idx) * angle_step
        angle_rad = math.radians(angle_deg)
        x = center_x + radius * math.sin(angle_rad)
        y = center_y - radius * math.cos(angle_rad)
        positions.append((x, y, angle_deg))

    return positions
