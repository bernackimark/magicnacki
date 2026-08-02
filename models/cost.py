from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Callable

from models.actions.destroy_sac_regen import Sac, Exile
from models.choice_actions_all import ChoiceAction

if TYPE_CHECKING:
    from models.game_card.game_card import GameCard
    from game_state import GameState
    from models.counter_tokens import CounterType

class Cost(ABC):
    requires_choice: bool = False

    @abstractmethod
    def can_pay(self, gs: GameState, source: GameCard) -> bool:
        ...

    @abstractmethod
    def pay(self, gs: GameState, source: GameCard) -> None:
        ...

class DiscardAtRandomCost(Cost):
    def can_pay(self, gs: GameState, source: GameCard):
        return len(gs.pile_mgr.hands[source.owner_id]) > 0

    def pay(self, gs: GameState, source: GameCard):
        cards = gs.pile_mgr.hands[source.owner_id]
        if not cards:
            return
        if len(cards) == 1:
            gs.pile_mgr.discard(cards[0])
            return
        random_card: GameCard = gs.randomize_event(source.owner_id, cards)
        gs.pile_mgr.discard(random_card)

class DiscardLastCardDrawnThisTurn(Cost):
    def can_pay(self, gs: GameState, source: GameCard) -> bool:
        from models.events_all import DrawCardEvent
        last_drawn = next((e.card for e in gs.event_mgr.get_events(gs.turn_mgr.turn_number, DrawCardEvent)[::-1]
                           if e.player_id == source.owner_id), None)
        if last_drawn and last_drawn in gs.pile_mgr.hands[source.owner_id]:
            return True
        return False

    def pay(self, gs: GameState, source: GameCard) -> None:
        from models.events_all import DrawCardEvent
        last_drawn = next((e.card for e in gs.event_mgr.get_events(gs.turn_mgr.turn_number, DrawCardEvent)[::-1]
                           if e.player_id == source.owner_id), None)
        if not last_drawn:
            return
        gs.pile_mgr.discard(last_drawn, source)

class ExileCreatureFromYourGraveyardCost(Cost):
    requires_choice = True

    def __init__(self, target_func: Callable[[GameState, GameCard], list[GameCard]]):
        self.target_func = target_func

    def can_pay(self, gs: GameState, source: GameCard) -> bool:
        return len(gs.card_filter.in_player_graveyard(source.owner_id).creatures().result()) > 0

    def pay(self, gs: GameState, source: GameCard) -> None:
        sac_options = self.target_func(gs, source)
        # because this is a cost, it must be paid before its action goes on the stack
        # within gs.get_available_actions(), it first seeks out gs.pending_choice, presents user w the action options,
        # executes and then pushes the effect onto the stack
        options = [Exile(gs.action_on_idx, gs, c) for c in sac_options]
        gs.queue_choice(ChoiceAction(options))

class ExileSelfCost(Cost):
    def can_pay(self, gs, source):
        return source in gs.card_filter.in_play().result()

    def pay(self, gs, source):
        gs.pile_mgr.exile(source)

class ManaCost(Cost):
    def __init__(self, cost: str):
        self.cost = cost

    def can_pay(self, gs, source):
        return gs.mana_pools[source.owner_id].can_pay(self.cost)

    def pay(self, gs, source):
        gs.mana_pools[source.owner_id].pay(self.cost)

class PayLifeCost(Cost):
    def __init__(self, amt: int = 1):
        self.amt = amt

    def can_pay(self, gs, source):
        return True

    def pay(self, gs, source):
        gs.apply_damage(source, self.amt, source.owner_id)

class RemoveCounterCost(Cost):
    def __init__(self, counter_type: CounterType, cnt: int = 1):
        self.counter_type = counter_type
        self.cnt = cnt

    def can_pay(self, gs: GameState, source: GameCard) -> bool:
        return source.counters.get_count(self.counter_type) >= self.cnt

    def pay(self, gs: GameState, source: GameCard):
        source.counters.remove_counter(self.counter_type, self.cnt)

class SacCardCost(Cost):
    requires_choice = True

    def __init__(self, target_func: Callable[[GameState, GameCard], list[GameCard]]):
        self.target_func = target_func

    def can_pay(self, gs: GameState, source: GameCard) -> bool:
        return len(self.target_func(gs, source)) >= 1

    def pay(self, gs: GameState, source: GameCard):
        sac_options = self.target_func(gs, source)
        # because this is a cost, it must be paid before its action goes on the stack
        # within gs.get_available_actions(), it first seeks out gs.pending_choice, presents user w the action options,
        # executes and then pushes the effect onto the stack
        options = [Sac(gs.action_on_idx, gs, c) for c in sac_options]
        gs.queue_choice(ChoiceAction(options))

class SacSelfCost(Cost):
    def can_pay(self, gs, source):
        return source in gs.card_filter.in_play().result()

    def pay(self, gs, source):
        gs.pile_mgr.destroy(source)

class SacTwoIslandsCost(Cost):
    def can_pay(self, gs: GameState, source: GameCard):
        return len([i for i in gs.card_filter.on_player_board(source.owner_id).islands().result()]) >= 2

    def pay(self, gs, source):
        your_islands = gs.card_filter.on_player_board(source.owner_id).islands().result()
        for island in your_islands[:2]:
            gs.pile_mgr.destroy(island)

class TapCost(Cost):
    def can_pay(self, gs, source):
        return not source.is_tapped

    def pay(self, gs, source):
        source.tap()

