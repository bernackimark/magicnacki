from __future__ import annotations
from typing import TYPE_CHECKING, Callable

from models.actions.tap_untap import LeaveTapped
from models.choice_actions_all import UntapChoice
from models.effects.base import Listener
from models.events_all import UntapPhaseEvent

if TYPE_CHECKING:
    from game_state import GameState
    from models.game_card.game_card import GameCard


class CardsDontUntapAtUntapPhase(Listener):
    """Cards [from card_filter_func] don't untap during their controllers' untap steps"""
    listens_to = UntapPhaseEvent

    def __init__(self, card_filter_func: Callable[[GameState, GameCard], list[GameCard | None]]):
        self.card_filter_func = card_filter_func

    def on_event(self, gs: GameState, s: GameCard, event: UntapPhaseEvent):
        for c in self.card_filter_func(gs, s):
            gs.action_stack.push(LeaveTapped(event.active_player, gs, c), gs, False)


class OptionalUntap(Listener):
    listens_to = UntapPhaseEvent

    def on_event(self, gs: GameState, source: GameCard, event: UntapPhaseEvent):
        if source.owner_id != event.active_player or not source.is_tapped:
            return
        gs.action_stack.push(UntapChoice(gs.turn_mgr.player_turn_idx, gs, source), gs, False)


class MagneticMountainOnUntapStep(Listener):
    """Blue creatures don't untap during their controllers' untap steps"""
    listens_to = UntapPhaseEvent

    def on_event(self, gs: GameState, s: GameCard, event: UntapPhaseEvent):
        if event.active_player != s.owner_id:
            return
        if s in gs.card_filter.on_player_board(event.active_player).blue().creatures().result():
            gs.action_stack.push(LeaveTapped(s.owner_id, gs, s), gs, False)
