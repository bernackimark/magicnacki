from typing import Optional

from models.effects.base import Effect
from card_filter import CardFilter

# Convenience factory functions for common simple effects used previously
def send_to_graveyard_all_lands():
    class E(Effect):
        event = 'cast'

        def resolve(self, gs, source: "GameCard", target: Optional["GameCard"] = None):
            for land in CardFilter(gs).in_play().by_type('Land').result():
                gs.send_to_graveyard(land)
    return E()
