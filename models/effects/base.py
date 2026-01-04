from __future__ import annotations
from typing import TYPE_CHECKING, Optional

from ..damage import DamageEvent

if TYPE_CHECKING:
    from ..game_card import GameCard
    from game_state import GameState

class Effect:
    """
    Base class for all card effects.
    Subclasses must set `event` to one of:
      - 'cast'   : when a card is successfully cast (resolve time)
      - 'upkeep' : at upkeep (permanent's upkeep)
      - 'tap'    : when a card becomes tapped
      - 'untap'  : when a card becomes untapped
      - 'leave'  : when the card leaves the battlefield (sent to graveyard/exile)
    And implement resolve(gs, source, target)
    """
    event: str = 'generic'

    def resolve(self, gs, source: GameCard, target: Optional[GameCard] = None):
        raise NotImplementedError()

    def on_damage(self, gs: GameState, event: DamageEvent):
        return

    def on_query(self, gs, event: str, card: GameCard, **kwargs):
        return None  # default: no opinion

