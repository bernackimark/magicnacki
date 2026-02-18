from __future__ import annotations
from typing import Optional, TYPE_CHECKING

from phase_fsm import Phase
from models.utils import flip
from models.events_all import ZoneChangeEvent, TapCardEvent
from ..zone import Zone

if TYPE_CHECKING:
    from game_state import GameState
    from models.game_card import GameCard

from models.effects.base import Effect
from models.card_filter import CardFilter
from models.choice_actions_all import UntapChoice, UntapWithManaChoice
from ..actions.tap_untap import LeaveTapped
from ..counter_tokens import PUPA, SLEEP


# --- GENERICS ---
class TapCardEffect(Effect):
    def resolve(self, gs: GameState, source: GameCard, target: GameCard = None):
        target.tap(gs)

class UntapCardEffect(Effect):
    def resolve(self, gs: GameState, source: GameCard, target: GameCard = None):
        target.untap(gs)

class HostStaysTapped(Effect):
    def resolve(self, gs: GameState, source: GameCard, _: GameCard = None):
        if not source.attached_to:
            raise RuntimeError(f"{source.props.name} needs a host at untap phase")
        if gs.player_turn_idx != source.attached_to.owner_id:
            return
        gs.action_stack.push(LeaveTapped(source.owner_id, gs, source.attached_to), gs, False)

class StaysTapped(Effect):
    def resolve(self, gs: GameState, source: GameCard, _: GameCard = None):
        gs.action_stack.push(LeaveTapped(source.owner_id, gs, source), gs, False)

class OptionalUntap(Effect):
    def resolve(self, gs: GameState, source: GameCard, _: GameCard = None):
        gs.action_stack.push(UntapChoice(gs.player_turn_idx, gs, source), gs, False)

class UntapForManaEffect(Effect):
    def __init__(self, mana_cost: str):
        self.mana_cost = mana_cost

    def resolve(self, gs: GameState, source: GameCard, _: GameCard = None):
        gs.action_stack.push(UntapWithManaChoice(source.owner_id, gs, source, self.mana_cost))

class UntapHostForManaEffect(Effect):
    def __init__(self, mana_cost: str):
        self.mana_cost = mana_cost

    def resolve(self, gs: GameState, source: GameCard, _: GameCard = None):
        gs.action_stack.push(UntapWithManaChoice(source.attached_to.owner_id, gs, source, self.mana_cost))


# --- CARD-SPECIFIC ---
class CocoonHostStaysTapped(Effect):
    """Enchanted creature doesn't untap during your untap step if this Aura has a pupa counter on it"""
    def resolve(self, gs: GameState, source: GameCard, _: GameCard = None):
        if source.attached_to.counters.get_count(PUPA):
            gs.action_stack.push(LeaveTapped(source.owner_id, gs, source.attached_to), gs, False)

class Kismet(Effect):
    """Artifacts, creatures, and lands your opponents control enter tapped"""
    listens_to = ZoneChangeEvent

    def on_event(self, gs: GameState, s: GameCard, event: ZoneChangeEvent):
        if event.card.owner_id != flip(s.owner_id) or event.to_zone != Zone.BATTLEFIELD:
            return
        artifacts = gs.card_filter.on_player_board(flip(s.owner_id)).artifacts().result()
        creatures = gs.card_filter.on_player_board(flip(s.owner_id)).creatures().result()
        lands = gs.card_filter.on_player_board(flip(s.owner_id)).lands().result()
        if event.card not in artifacts + creatures + lands:
            return
        gs.tap_card(event.card)

class Lifeblood(Effect):
    """Whenever a Mountain an opponent controls becomes tapped, you gain 1 life."""
    listens_to = TapCardEvent

    def on_event(self, gs: GameState, s: GameCard, event: TapCardEvent):
        if event.card is not s or event.card.owner_id == s.owner_id:
            return
        if 'Mountain' in event.card.card_sub_types:
            gs.increment_life(s.owner_id, 1)

class Lifetap(Effect):
    """Whenever a Forest an opponent controls becomes tapped, you gain 1 life."""
    listens_to = TapCardEvent

    def on_event(self, gs: GameState, s: GameCard, event: TapCardEvent):
        if event.card is not s or event.card.owner_id == s.owner_id:
            return
        if 'Forest' in event.card.card_sub_types:
            gs.increment_life(s.owner_id, 1)

class ManaShort(Effect):
    def resolve(self, gs: GameState, source: GameCard, target: Optional[int] = None):
        """target = player_id whose lands should be tapped"""
        if target is None:
            return
        player_lands = (CardFilter(gs).on_player_board(target).lands().result())
        for land in player_lands:
            land.tap(gs)
        print(f"Mana Short taps {len(player_lands)} lands belonging to player {target}.")

class PsychicVenom(Effect):
    """Whenever enchanted land becomes tapped, this Aura deals 2 damage to that land's controller"""
    listens_to = TapCardEvent

    def on_event(self, gs: GameState, s: GameCard, event: TapCardEvent):
        if event.card is not s.attached_to:
            return
        gs.apply_damage(s, 2, event.card.owner_id)

class Reset(Effect):
    """Cast this spell only during an opponent's turn after their upkeep step. Untap all lands you control"""
    def resolve(self, gs: GameState, source: GameCard, target: Optional[GameCard] = None):
        if gs.phase == Phase.UPKEEP or gs.player_turn_idx == source.owner_id:
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
        if source.attached_to.counters.get_count(SLEEP):
            gs.action_stack.push(LeaveTapped(source.owner_id, gs, source.attached_to), gs, False)
