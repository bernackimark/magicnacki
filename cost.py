from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from models.game_card import GameCard
    from game_state import GameState

class Cost(ABC):
    @abstractmethod
    def can_pay(self, gs: GameState, source: GameCard) -> bool:
        ...

    @abstractmethod
    def pay(self, gs: GameState, source: GameCard) -> None:
        ...

class ManaCost(Cost):
    def __init__(self, cost: str):
        self.cost = cost

    def can_pay(self, gs, source):
        return gs.mana_pools[source.orig_owner_id].can_pay(self.cost)

    def pay(self, gs, source):
        gs.mana_pools[source.orig_owner_id].pay(self.cost)

class TapCost(Cost):
    def can_pay(self, gs, source):
        return not source.is_tapped

    def pay(self, gs, source):
        source.tap(gs)

class SacSelfCost(Cost):
    def can_pay(self, gs, source):
        return source in gs.card_filter.in_play().result()

    def pay(self, gs, source):
        gs.send_to_graveyard_from_play(source)

class ExileSelfCost(Cost):
    def can_pay(self, gs, source):
        return source in gs.card_filter.in_play().result()

    def pay(self, gs, source):
        gs.send_to_exile_from_play(source)
