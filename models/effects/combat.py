from __future__ import annotations
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from game_state import GameState
    from models.game_card import GameCard

from models.effects.base import Effect

class WalkRuleRemoved(Effect):
    """Creatures with a landwalk can be blocked as though they didn't have that landwalk."""
    event = 'query'

    def __init__(self, walk_type: str):
        self.walk_type = walk_type

    def on_query(self, gs: GameState, event: str, card: GameCard, **kwargs):
        if event != 'can_block':
            return None
        attacker = kwargs.get('attacker')
        if not attacker:
            return None
        if self.walk_type not in attacker.keyword_abilities:
            return None
        return True  # a hard-confirm that the block is allowed

