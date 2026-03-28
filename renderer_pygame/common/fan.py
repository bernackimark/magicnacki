import math

def get_fan_positions(n_cards, center_x, center_y, radius, angle_spread_deg):
    """Fan images around an invisible semicircle (like someone holding a hand of playing cards)"""
    if n_cards == 1:
        return [(center_x, center_y - radius, 0)]

    positions = []

    start_angle = -angle_spread_deg / 2
    angle_step = angle_spread_deg / (n_cards - 1)

    for i in range(n_cards):
        angle_deg = start_angle + i * angle_step
        angle_rad = math.radians(angle_deg)

        x = center_x + radius * math.sin(angle_rad)
        y = center_y - radius * math.cos(angle_rad)

        positions.append((x, y, angle_deg))

    return positions
