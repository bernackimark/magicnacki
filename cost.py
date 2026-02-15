from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from models.game_card import GameCard
    from game_state import GameState
    from models.counter_tokens import CounterType

class Cost(ABC):
    @abstractmethod
    def can_pay(self, gs: GameState, source: GameCard) -> bool:
        ...

    @abstractmethod
    def pay(self, gs: GameState, source: GameCard) -> None:
        ...

class DiscardAtRandomCost(Cost):
    def can_pay(self, gs: GameState, source: GameCard):
        return len(gs.hands[source.owner_id].cards) > 0

    def pay(self, gs: GameState, source: GameCard):
        cards = gs.hands[source.owner_id].cards
        if not cards:
            return
        if len(cards) == 1:
            gs.discard(cards[0])
            return
        random_card: GameCard = gs.randomize_event(source.owner_id, cards)
        gs.discard(random_card)

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
        return len([i for i in gs.card_filter.on_player_board(source.orig_owner_id).islands().result()]) >= 2

    def pay(self, gs, source):
        your_islands = gs.card_filter.on_player_board(source.orig_owner_id).islands().result()
        for island in your_islands[:2]:
            gs.destroy(island)

class ExileSelfCost(Cost):
    def can_pay(self, gs, source):
        return source in gs.card_filter.in_play().result()

    def pay(self, gs, source):
        gs.exile(source)

class RemoveCounterCost(Cost):
    def __init__(self, counter_type: CounterType, cnt: int = 1):
        self.counter_type = counter_type
        self.cnt = cnt

    def can_pay(self, gs: GameState, source: GameCard) -> bool:
        return source.counters.get_count(self.counter_type) >= self.cnt

    def pay(self, gs: GameState, source: GameCard):
        source.counters.remove_counter(self.counter_type, self.cnt)
