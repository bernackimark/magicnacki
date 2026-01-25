from __future__ import annotations
from typing import TYPE_CHECKING, Optional

from ..counter_tokens import MINUS_ZERO_TWO

if TYPE_CHECKING:
    from ..game_card import GameCard
    from game_state import GameState

from models.effects.base import Effect


def spirit_shackle_on_tap():
    """Whenever enchanted creature becomes tapped, put a -0/-2 counter on it. [the counters persist]"""
    class E(Effect):
        event = 'tap'

        def resolve(self, gs: GameState, source: GameCard, target: Optional[GameCard] = None):
            source.attached_to.counters.add_counter(MINUS_ZERO_TWO)
    return E()
