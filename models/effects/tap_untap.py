from __future__ import annotations
from typing import Optional, TYPE_CHECKING

from models.phase_manager import Phase

if TYPE_CHECKING:
    from game_state import GameState
    from models.game_card.game_card import GameCard

from models.effects.base import Effect
from models.choice_actions_all import UntapWithManaChoice
from ..actions.tap_untap import LeaveTapped
from ..counter_tokens import PUPA, SLEEP


# --- GENERICS ---

class TapCardEffect(Effect):
    def resolve(self, gs: GameState, source: GameCard, target: GameCard = None):
        gs.tap_card(target)


class TapCardsEffect(Effect):
    """Accepts a list of targets and taps each"""
    def resolve(self, gs: GameState, source: GameCard, target: list[GameCard] = None):
        if not target:
            raise ValueError(f'{source.props.name} needs a list of targets')
        for t in target:
            gs.tap_card(t)

class UntapCardEffect(Effect):
    def resolve(self, gs: GameState, source: GameCard, target: GameCard = None):
        gs.untap_card(target)

class UntapCardsEffect(Effect):
    """Accepts a list of targets and untaps each"""
    def resolve(self, gs: GameState, source: GameCard, target: list[GameCard] = None):
        if not target:
            raise ValueError(f'{source.props.name} needs a list of targets')
        for t in target:
            gs.untap_card(t)

class HostStaysTapped(Effect):
    def resolve(self, gs: GameState, source: GameCard, _: GameCard = None):
        if not source.host:
            raise RuntimeError(f"{source.props.name} needs a host at untap phase")
        if gs.turn_mgr.player_turn_idx != source.host.owner_id:
            return
        gs.action_stack.push(LeaveTapped(source.owner_id, gs, source.host), gs, False)

class StaysTapped(Effect):
    def resolve(self, gs: GameState, source: GameCard, _: GameCard = None):
        gs.action_stack.push(LeaveTapped(source.owner_id, gs, source), gs, False)


class UntapForManaEffect(Effect):
    def __init__(self, mana_cost: str):
        self.mana_cost = mana_cost

    def resolve(self, gs: GameState, source: GameCard, _: GameCard = None):
        gs.action_stack.push(UntapWithManaChoice(source.owner_id, gs, source, self.mana_cost))

class UntapHostForManaEffect(Effect):
    def __init__(self, mana_cost: str):
        self.mana_cost = mana_cost

    def resolve(self, gs: GameState, source: GameCard, _: GameCard = None):
        gs.action_stack.push(UntapWithManaChoice(source.host.owner_id, gs, source, self.mana_cost))


# --- CARD-SPECIFIC ---
class ArenaOfTheAncientsCast(Effect):
    """When this artifact enters, tap all legendary creatures"""
    def resolve(self, gs: GameState, _: GameCard, t: Optional[GameCard] = None):
        for c in gs.card_filter.in_play().creatures().untapped().legendary().result():
            c.tap(gs)

class CocoonHostStaysTapped(Effect):
    """Enchanted creature doesn't untap during your untap step if this Aura has a pupa counter on it"""
    def resolve(self, gs: GameState, source: GameCard, _: GameCard = None):
        if source.host.counters.get_count(PUPA):
            gs.action_stack.push(LeaveTapped(source.owner_id, gs, source.host), gs, False)

class ManaShort(Effect):
    def resolve(self, gs: GameState, source: GameCard, target: Optional[int] = None):
        """target = player_id whose lands should be tapped"""
        if target is None:
            return
        player_lands = gs.card_filter.on_player_board(target).lands().result()
        for land in player_lands:
            land.tap(gs)
        print(f"Mana Short taps {len(player_lands)} lands belonging to player {target}.")

class Reset(Effect):
    """Cast this spell only during an opponent's turn after their upkeep step. Untap all lands you control"""
    def resolve(self, gs: GameState, source: GameCard, target: Optional[GameCard] = None):
        if gs.phase_mgr.phase == Phase.UPKEEP or gs.turn_mgr.player_turn_idx == source.owner_id:
            return
        for land in gs.card_filter.on_player_board(source.owner_id).lands().untapped().result():
            land.untap(gs)

class Riptide(Effect):
    """Tap all blue creatures"""
    def resolve(self, gs: GameState, _: GameCard, t: Optional[GameCard] = None):
        for c in gs.card_filter.in_play().creatures().untapped().blue().result():
            c.tap(gs)

class Twiddle(Effect):
    def resolve(self, gs, source: GameCard, target: Optional[GameCard] = None):
        if target:
            target.untap(gs) if target.is_tapped else target.tap(gs)

class VenarianGoldHostStaysTapped(Effect):
    """Enchanted creature doesn't untap during its controller's untap step if it has a sleep counter on it."""
    def resolve(self, gs: GameState, source: GameCard, _: GameCard = None):
        if source.host.counters.get_count(SLEEP):
            gs.action_stack.push(LeaveTapped(source.owner_id, gs, source.host), gs, False)
