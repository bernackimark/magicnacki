from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Callable

if TYPE_CHECKING:
    from models.game_card.game_card import GameCard
    from game_state import GameState
    from models.counter_tokens import CounterType


@dataclass
class CostResult:
    paid_cards: list[GameCard] = field(default_factory=list)
    paid_mana: str = ''
    paid_life: int = 0
    paid_counters: list[tuple[CounterType, int]] = field(default_factory=list)


class Cost(ABC):
    requires_choice: bool = False

    @abstractmethod
    def can_pay(self, gs: GameState, source: GameCard) -> bool:
        ...

    @abstractmethod
    def pay(self, gs: GameState, source: GameCard) -> CostResult:
        ...

class DiscardAtRandomCost(Cost):
    def can_pay(self, gs: GameState, source: GameCard):
        return len(gs.pile_mgr.hands[source.owner_id]) > 0

    def pay(self, gs: GameState, source: GameCard) -> CostResult:
        cards = gs.pile_mgr.hands[source.owner_id]
        random_card: GameCard = gs.randomize_event(source.owner_id, cards)
        cost_result = CostResult([random_card])
        gs.pile_mgr.discard(random_card)
        return cost_result

class DiscardLastCardDrawnThisTurn(Cost):
    def can_pay(self, gs: GameState, source: GameCard) -> bool:
        from models.events_all import DrawCardEvent
        last_drawn = next((e.card for e in gs.event_mgr.get_events(gs.turn_mgr.turn_number, DrawCardEvent)[::-1]
                           if e.player_id == source.owner_id), None)
        if last_drawn and last_drawn in gs.pile_mgr.hands[source.owner_id]:
            return True
        return False

    def pay(self, gs: GameState, source: GameCard) -> CostResult:
        from models.events_all import DrawCardEvent
        last_drawn = next((e.card for e in gs.event_mgr.get_events(gs.turn_mgr.turn_number, DrawCardEvent)[::-1]
                           if e.player_id == source.owner_id), None)
        cost_result = CostResult([last_drawn])
        gs.pile_mgr.discard(last_drawn, source)
        return cost_result

class ExileCreatureFromYourGraveyardCost(Cost):
    requires_choice = True

    def __init__(self, target_func: Callable[[GameState, GameCard], list[GameCard]] = None,
                 selected_card: GameCard | None = None):
        self.target_func = target_func
        self.selected_card = selected_card

    def can_pay(self, gs: GameState, source: GameCard) -> bool:
        return len(gs.card_filter.in_player_graveyard(source.owner_id).creatures().result()) > 0

    def pay(self, gs: GameState, source: GameCard) -> CostResult:
        gs.pile_mgr.exile(self.selected_card)
        return CostResult([self.selected_card])

class ExileSelfCost(Cost):
    def can_pay(self, gs, source):
        return source in gs.card_filter.in_play().result()

    def pay(self, gs: GameState, source: GameCard) -> CostResult:
        gs.pile_mgr.exile(source)
        return CostResult([source])

class PayLifeCost(Cost):
    def __init__(self, amt: int = 1):
        self.amt = amt

    def can_pay(self, gs, source):
        return True

    def pay(self, gs: GameState, source: GameCard) -> CostResult:
        gs.apply_damage(source, self.amt, source.owner_id)
        return CostResult(paid_life=self.amt)

class RemoveCounterCost(Cost):
    def __init__(self, counter_type: CounterType, cnt: int = 1):
        self.counter_type = counter_type
        self.cnt = cnt

    def can_pay(self, gs: GameState, source: GameCard) -> bool:
        return source.counters.get_count(self.counter_type) >= self.cnt

    def pay(self, gs: GameState, source: GameCard) -> CostResult:
        source.counters.remove_counter(self.counter_type, self.cnt)
        return CostResult(paid_counters=[(self.counter_type, self.cnt)])

class SacCardCost(Cost):
    requires_choice = True

    def __init__(self, target_func: Callable[[GameState, GameCard], list[GameCard]] = None,
                 selected_card: GameCard | None = None):
        self.target_func = target_func
        self.selected_card = selected_card

    def can_pay(self, gs: GameState, source: GameCard) -> bool:
        return len(self.target_func(gs, source)) >= 1

    def pay(self, gs: GameState, source: GameCard) -> CostResult:
        gs.pile_mgr.destroy(self.selected_card, allow_regeneration=False)
        return CostResult([self.selected_card])

class SacSelfCost(Cost):
    def can_pay(self, gs, source):
        return source in gs.card_filter.in_play().result()

    def pay(self, gs: GameState, source: GameCard) -> CostResult:
        gs.pile_mgr.destroy(source, allow_regeneration=False)
        return CostResult([source])

class SacTwoIslandsCost(Cost):
    def can_pay(self, gs: GameState, source: GameCard):
        return len([i for i in gs.card_filter.on_player_board(source.owner_id).islands().result()]) >= 2

    def pay(self, gs: GameState, source: GameCard) -> CostResult:
        your_islands = gs.card_filter.on_player_board(source.owner_id).islands().result()
        sacrificed_islands = your_islands[:2]
        for island in your_islands:
            gs.pile_mgr.destroy(island, allow_regeneration=False)
        return CostResult([sacrificed_islands])
