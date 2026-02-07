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

class PayLifeCost(Cost):
    def __init__(self, amt: int = 1):
        self.amt = amt

    def can_pay(self, gs, source):
        return True

    def pay(self, gs, source):
        gs.apply_damage(source, self.amt, source.owner_id)

class TapCost(Cost):
    def can_pay(self, gs, source):
        return not source.is_tapped

    def pay(self, gs, source):
        source.tap(gs)

class SacSelfCost(Cost):
    def can_pay(self, gs, source):
        return source in gs.card_filter.in_play().result()

    def pay(self, gs, source):
        gs.destroy(source)

class SacTwoIslandsCost(Cost):
    def can_pay(self, gs: GameState, source: GameCard):
        return len([i for i in gs.card_filter.on_player_board(source.orig_owner_id).by_slug('island').result()]) >= 2

    def pay(self, gs, source):
        your_islands = gs.card_filter.on_player_board(source.orig_owner_id).by_slug('island').result()
        for island in your_islands[:2]:
            gs.destroy(island)

class ExileSelfCost(Cost):
    def can_pay(self, gs, source):
        return source in gs.card_filter.in_play().result()

    def pay(self, gs, source):
        gs.exile(source)
