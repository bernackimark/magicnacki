from __future__ import annotations
from typing import Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from game_state import GameState
    from models.game_card import GameCard

from models.effects.base import Effect
from card_filter import CardFilter
from phase_fsm import Phase
from utils import flip
from ..actions.choices import LeaveTapped, UntapChoice
from ..counter_tokens import PUPA, SLEEP


def forest_on_tap():
    """lifetap: Enchantment UU [] Whenever a Forest an opponent controls becomes tapped, you gain 1 life."""
    class E(Effect):
        event = 'tap'

        def resolve(self, gs, s: "GameCard", target: Optional["GameCard"] = None):
            for _ in gs.card_filter.on_player_board(flip(s.orig_owner_id)).by_slug('lifetap').result():
                gs.increment_life(flip(s.orig_owner_id), 1)
    return E()

def giant_tortoise_on_tap():
    class E(Effect):
        event = 'tap'
        
        def resolve(self, gs, source: "GameCard", target: Optional["GameCard"] = None):
            if source.props.slug == "giant-tortoise":
                source.modifiers.remove_aura(source)
    return E()

def mountain_on_tap():
    """"lifeblood": Enchantment 2WW [] Whenever a Mountain an opponent controls becomes tapped, you gain 1 life."""
    class E(Effect):
        event = 'tap'

        def resolve(self, gs: "GameState", s: "GameCard", target: Optional["GameCard"] = None):
            for _ in gs.card_filter.on_player_board(flip(s.orig_owner_id)).by_slug('lifeblood').result():
                gs.increment_life(flip(s.orig_owner_id), 1)
    return E()

def psychic_venom_on_tap():
    class E(Effect):
        event = 'tap'
        
        def resolve(self, gs, source: "GameCard", target: Optional["GameCard"] = None):
            if any(a.props.slug == "psychic-venom" for a in source.modifiers.auras):
                gs.decrement_life(source.orig_owner_id, 2, source)
    return E()


def host_stays_tapped_at_untap_phase():
    """This card doesn't untap during its controller's next untap step"""
    class E(Effect):
        event = 'on_untap_phase'

        def resolve(self, gs: GameState, source: GameCard, _: GameCard = None):
            if not source.attached_to:
                raise RuntimeError(f"{source.props.name} needs a host at untap phase")
            gs.action_stack.push(LeaveTapped(source.orig_owner_id, gs, source.attached_to), gs, False)
    return E()


def stays_tapped_at_untap_phase():
    """This card doesn't untap during its controller's next untap step"""
    class E(Effect):
        event = 'on_untap_phase'

        def resolve(self, gs: GameState, source: GameCard, _: GameCard = None):
            gs.action_stack.push(LeaveTapped(source.orig_owner_id, gs, source), gs, False)
    return E()


def untap_option_at_untap_phase():
    class E(Effect):
        event = 'on_untap_phase'

        def resolve(self, gs: GameState, source: GameCard, _: GameCard = None):
            gs.action_stack.push(UntapChoice(gs.player_turn_idx, gs, source), gs, False)
    return E()


def cocoon_at_untap_phase():
    """Enchanted creature doesn't untap during your untap step if this Aura has a pupa counter on it"""
    class E(Effect):
        event = 'on_untap_phase'

        def resolve(self, gs: GameState, source: GameCard, _: GameCard = None):
            if source.attached_to.counters.get_count(PUPA):
                gs.action_stack.push(LeaveTapped(source.orig_owner_id, gs, source.attached_to), gs, False)
    return E()


def venarian_gold_at_untap_phase():
    """Enchanted creature doesn't untap during its controller's untap step if it has a sleep counter on it."""
    class E(Effect):
        event = 'on_untap_phase'

        def resolve(self, gs: GameState, source: GameCard, _: GameCard = None):
            if source.attached_to.counters.get_count(SLEEP):
                gs.action_stack.push(LeaveTapped(source.orig_owner_id, gs, source.attached_to), gs, False)
    return E()


class TapCardEffect(Effect):
    def resolve(self, gs: GameState, source: GameCard, target: GameCard = None):
        target.tap(gs)


def leviathan_on_cast():
    class E(Effect):
        event = 'cast'

        def resolve(self, gs, source: GameCard, _: Optional[GameCard] = None):
            source.tap(gs)
    return E()


def mana_short_on_cast():
    class E(Effect):
        event = 'cast'

        def resolve(self, gs: GameState, source: GameCard, target: Optional[int] = None):
            """target = player_id whose lands should be tapped"""
            if target is None:
                return
            player_lands = (CardFilter(gs).on_player_board(target).lands().result())
            for land in player_lands:
                land.tap(gs)
            print(f"Mana Short taps {len(player_lands)} lands belonging to player {target}.")
    return E()


def nevinyrrals_disk_on_cast():
    """This artifact enters tapped"""
    class E(Effect):
        event = 'cast'

        def resolve(self, gs: GameState, source: GameCard, target: Optional[GameCard] = None):
            source.tap(gs)  # what is the correct way to handle tapping a card: gs.apply_tap_effects() or c.tap()?
            gs.apply_tap_effects(source)
    return E()


def paralyze_on_cast():
    """When this Aura enters, tap enchanted creature..."""
    class E(Effect):
        event = 'cast'

        def resolve(self, gs: GameState, source: GameCard, target=None):
            if not target:
                raise RuntimeError(f"{source.props.name} needs a target")
            target.tap(gs)
    return E()


def reset_on_cast():
    """Cast this spell only during an opponent's turn after their upkeep step. Untap all lands you control"""
    class E(Effect):
        event = 'cast'

        def resolve(self, gs: GameState, source: GameCard, target: Optional[GameCard] = None):
            if gs.phase == Phase.UPKEEP or gs.player_turn_idx == source.orig_owner_id:
                raise ValueError("Reset must be played on opponent's turn after their upkeep phase")
            for land in gs.card_filter.on_player_board(source.orig_owner_id).lands().untapped().result():
                land.untap(gs)
    return E()


def riptide_on_cast():
    """Tap all blue creatures"""

    class E(Effect):
        event = 'cast'

        def resolve(self, gs: GameState, _: GameCard, t: Optional[GameCard] = None):
            for c in gs.card_filter.in_play().creatures().untapped().blue().result():
                c.tap(gs)
    return E()


def time_vault_on_cast():
    """This artifact enters tapped..."""
    class E(Effect):
        event = 'cast'

        def resolve(self, gs: GameState, source: GameCard, target=None):
            source.tap(gs)
    return E()


def twiddle_on_cast():
    class E(Effect):
        event = 'cast'

        def resolve(self, gs, source: GameCard, target: Optional[GameCard] = None):
            if target:
                # toggle tapped state
                target.untap(gs) if target.is_tapped else target.tap(gs)
    return E()
