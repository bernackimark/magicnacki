from dataclasses import dataclass


@dataclass
class Turn:
    in_turn_player_idx: int
    out_turn_player_idx: int
    has_played_land: bool = False
