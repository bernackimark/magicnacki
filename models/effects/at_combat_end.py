from __future__ import annotations
from typing import TYPE_CHECKING, Optional

from ..counter_tokens import CARRION, CORPSE, PLUS_ONE_ZERO

if TYPE_CHECKING:
    from ..game_card import GameCard
    from game_state import GameState

from models.effects.base import Effect
from card_filter import CardFilter
from utils import flip

def clockwork_avian_and_beast_at_combat_end():
    """... At end of combat, if this creature attacked or blocked this combat, remove a +1/+0 counter from it ..."""
    class E(Effect):
        event = 'combat_end'

        def resolve(self, gs: GameState, source: GameCard, target: Optional[GameCard] = None):
            if source in gs.card_filter.combatants().result():
                source.counters.remove_counter(PLUS_ONE_ZERO)
    return E()

