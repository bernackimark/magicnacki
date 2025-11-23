LAND_MANA_DICT = {'island': 'U', 'forest': 'G', 'swamp': 'B', 'mountain': 'R', 'plains': 'W'}

def flip(idx: int) -> int:
    return int(not idx)

def str_to_int(string_: str) -> int:
    try:
        number = int(string_)
        return number
    except ValueError:
        return 0
