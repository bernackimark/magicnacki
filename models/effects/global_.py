from typing import Optional

from card_filter import CardFilter

class GlobalEffect:
    """A continuous non-target-specific effect that can modify card properties (ex Castle, Crusade)"""
    def applies_to(self, card, gs: "GameState") -> bool:
        return False

    def pt_offset(self, card=None, power=None, toughness=None):
        # Returns the delta to power/toughness
        return 0, 0


class CastleEffect(GlobalEffect):
    def __init__(self, owner_id: int):
        self.owner_id = owner_id

    def applies_to(self, card, gs: "GameState") -> bool:
        # White creatures, untapped, owned by castle owner
        return card in CardFilter(gs).creatures().on_player_board(self.owner_id).tapped(False).white().result()

    def pt_offset(self, card=None, power=None, toughness=None):
        return 0, 2


class CrusadeEffect(GlobalEffect):
    def __init__(self, owner_id: Optional[int] = None):
        self.owner_id = owner_id  # Optional, can affect all players

    def applies_to(self, card, gs: "GameState") -> bool:
        # All untapped creatures on any board (or specific player if owner_id set)
        return card in CardFilter(gs).in_play().creatures().white().result()

    def pt_offset(self, card=None, power=None, toughness=None):
        return 1, 1
