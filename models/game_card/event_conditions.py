from __future__ import annotations
from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from game_state import GameState
    from models.events_all import Event, AttackEvent
    from models.game_card.game_card import GameCard

class EventCondition(ABC):
    @abstractmethod
    def matches(self, gs: GameState, source: GameCard, event: Event) -> bool: ...

class SelfIsAttacking(EventCondition):
    def matches(self, gs: GameState, source: GameCard, event: AttackEvent) -> bool:
        return event.attacker is source
