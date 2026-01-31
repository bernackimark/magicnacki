from __future__ import annotations
from typing import TYPE_CHECKING, Optional

from ..damage import DamageEvent
from ..events.base import Event

if TYPE_CHECKING:
    from ..game_card import GameCard
    from game_state import GameState

class Effect:
    """Base class for all card effects."""
    event: str = 'generic'  # old system
    listens_to: type[Event] | None = None  # new system

    def resolve(self, gs, source: GameCard, target: Optional[GameCard] = None):
        raise NotImplementedError()

    def on_damage(self, gs: GameState, event: DamageEvent):
        return

    def on_query(self, gs, event: str, card: GameCard, **kwargs):
        return None  # default: no opinion

