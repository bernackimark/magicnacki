from __future__ import annotations
from typing import Optional, TYPE_CHECKING

from phase_fsm import Phase
from utils import flip

if TYPE_CHECKING:
    from game_state import GameState
    from models.game_card import GameCard

from models.effects.base import Effect
from card_filter import CardFilter
from models.choice_actions.choice_actions_all import UntapChoice, UntapWithManaChoice
from ..actions.tap_untap import LeaveTapped
from ..counter_tokens import PUPA, SLEEP


# --- GENERICS ---
class TapCardEffect(Effect):
    def resolve(self, gs: GameState, source: GameCard, target: GameCard = None):
        target.tap(gs)

class HostStaysTapped(Effect):
    def resolve(self, gs: GameState, source: GameCard, _: GameCard = None):
        if not source.attached_to:
            raise RuntimeError(f"{source.props.name} needs a host at untap phase")
        if gs.player_turn_idx != source.attached_to.orig_owner_id:
            return
        gs.action_stack.push(LeaveTapped(source.orig_owner_id, gs, source.attached_to), gs, False)

class StaysTapped(Effect):
    def resolve(self, gs: GameState, source: GameCard, _: GameCard = None):
        gs.action_stack.push(LeaveTapped(source.orig_owner_id, gs, source), gs, False)

class OptionalUntap(Effect):
    def resolve(self, gs: GameState, source: GameCard, _: GameCard = None):
        gs.action_stack.push(UntapChoice(gs.player_turn_idx, gs, source), gs, False)

class UntapForManaEffect(Effect):
    def __init__(self, mana_cost: str):
        self.mana_cost = mana_cost

    def resolve(self, gs: GameState, source: GameCard, _: GameCard = None):
        gs.action_stack.push(UntapWithManaChoice(source.orig_owner_id, gs, source, self.mana_cost))


# --- CARD-SPECIFIC ---
class CocoonHostStaysTapped(Effect):
    """Enchanted creature doesn't untap during your untap step if this Aura has a pupa counter on it"""
    def resolve(self, gs: GameState, source: GameCard, _: GameCard = None):
        if source.attached_to.counters.get_count(PUPA):
            gs.action_stack.push(LeaveTapped(source.orig_owner_id, gs, source.attached_to), gs, False)

class GiantTortoiseTap(Effect):
    def resolve(self, gs, source: GameCard, _: GameCard = None):
        if source.props.slug == "giant-tortoise":
            source.modifiers.remove_aura(source)

class ManaShort(Effect):
    def resolve(self, gs: GameState, source: GameCard, target: Optional[int] = None):
        """target = player_id whose lands should be tapped"""
        if target is None:
            return
        player_lands = (CardFilter(gs).on_player_board(target).lands().result())
        for land in player_lands:
            land.tap(gs)
        print(f"Mana Short taps {len(player_lands)} lands belonging to player {target}.")

class Riptide(Effect):
    """Tap all blue creatures"""
    def resolve(self, gs: GameState, _: GameCard, t: Optional[GameCard] = None):
        for c in gs.card_filter.in_play().creatures().untapped().blue().result():
            c.tap(gs)

class Twiddle(Effect):
    def resolve(self, gs, source: GameCard, target: Optional[GameCard] = None):
        if target:
            # toggle tapped state
            target.untap(gs) if target.is_tapped else target.tap(gs)

class VenarianGoldHostStaysTapped(Effect):
    """Enchanted creature doesn't untap during its controller's untap step if it has a sleep counter on it."""
    def resolve(self, gs: GameState, source: GameCard, _: GameCard = None):
        if source.attached_to.counters.get_count(SLEEP):
            gs.action_stack.push(LeaveTapped(source.orig_owner_id, gs, source.attached_to), gs, False)


class Reset(Effect):
    """Cast this spell only during an opponent's turn after their upkeep step. Untap all lands you control"""
    def resolve(self, gs: GameState, source: GameCard, target: Optional[GameCard] = None):
        if gs.phase == Phase.UPKEEP or gs.player_turn_idx == source.orig_owner_id:
            raise ValueError("Reset must be played on opponent's turn after their upkeep phase")
        for land in gs.card_filter.on_player_board(source.orig_owner_id).lands().untapped().result():
            land.untap(gs)


class ForestTap(Effect):
    """lifetap: Enchantment UU [] Whenever a Forest an opponent controls becomes tapped, you gain 1 life."""
    def resolve(self, gs, s: "GameCard", target: Optional["GameCard"] = None):
        for _ in gs.card_filter.on_player_board(flip(s.orig_owner_id)).by_slug('lifetap').result():
            gs.increment_life(flip(s.orig_owner_id), 1)


class MountainTap(Effect):
    """"lifeblood": Enchantment 2WW [] Whenever a Mountain an opponent controls becomes tapped, you gain 1 life."""
    def resolve(self, gs: "GameState", s: "GameCard", target: Optional["GameCard"] = None):
        for _ in gs.card_filter.on_player_board(flip(s.orig_owner_id)).by_slug('lifeblood').result():
            gs.increment_life(flip(s.orig_owner_id), 1)
