from __future__ import annotations
from typing import TYPE_CHECKING, Optional

if TYPE_CHECKING:
    from ..game_card import GameCard
    from game_state import GameState

from models.effects.base import Effect
from card_filter import CardFilter

# Convenience factory functions for common simple effects used previously
def send_to_graveyard_all_lands():
    class E(Effect):
        event = 'cast'

        def resolve(self, gs: GameState, source: "GameCard", target: Optional["GameCard"] = None):
            for land in CardFilter(gs).in_play().by_type('Land').result():
                gs.send_to_graveyard_from_play(land)
    return E()
