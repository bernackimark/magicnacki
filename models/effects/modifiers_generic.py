from __future__ import annotations
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from game_state import GameState
    from models.game_card.game_card import GameCard
    from models.events_all import DamageProposedEvent, Event

from models.effects.base import Modifier

class PreventDamage(Modifier):
    def modify(self, gs: GameState, source: GameCard, event: DamageProposedEvent) -> None:
        event.prevented += event.remaining
        event.remaining = 0

class RedirectToSource(Modifier):
    def modify(self, gs: GameState, source: GameCard, event: DamageProposedEvent) -> None:
        event.target = source
