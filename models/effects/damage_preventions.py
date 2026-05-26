from __future__ import annotations
from typing import TYPE_CHECKING, Optional, Callable

from models.effects.base import Effect
from models.utils import flip

if TYPE_CHECKING:
    from game_state import GameState
    from models.game_card.game_card import GameCard

from models.damage import DamageEvent, PreventNextDamage

"""
THIS FILE NEEDS WORK, AS EFFECT DOES NOT SUPPORT .apply(); needs overhaul
"""

# --- GENERICS ---
class DamagePreventionEffect:
    listens_to = DamageEvent

    def applies(self, gs: GameState, event: DamageEvent, card: Optional[GameCard] = None) -> bool:
        raise NotImplementedError

    def apply(self, gs: GameState, event: DamageEvent, card: Optional[GameCard] = None):
        if event.remaining <= 0:
            return
        event.prevented += event.remaining

class PreventAllDamage(DamagePreventionEffect):
    def applies(self, gs: GameState, event: DamageEvent, card: Optional[GameCard] = None) -> bool:
        return event.target is card

class PreventDamageBy(Effect):
    def __init__(self, amt: int = None, combat_only: bool = False):
        self.amt = amt
        self.combat_only = combat_only

    def resolve(self, gs: GameState, s: GameCard, target: GameCard = None):
        """target is the card dealing damage"""
        if not target:
            raise RuntimeError(f'{s.props.name} needs a target')
        prevention = PreventNextDamage(s, self.amt, source_card=target, combat_only=self.combat_only)
        gs.damage_preventions.append(prevention)

class PreventDamageByMultipleSources(Effect):
    def __init__(self, damage_dealer_func: Callable[[GameState, GameCard], list[GameCard]],
                 amt: int = None, combat_only: bool = False):
        self.damage_dealer_func = damage_dealer_func
        self.amt = amt
        self.combat_only = combat_only

    def resolve(self, gs: GameState, s: GameCard, target: GameCard = None):
        """target is the card dealing damage"""
        if not self.damage_dealer_func:
            raise RuntimeError(f"{s.props.name} doesn't know which cards to prevent damage from")
        for damage_dealer in self.damage_dealer_func(gs, s):
            prevention = PreventNextDamage(s, self.amt, source_card=damage_dealer, combat_only=self.combat_only)
            gs.damage_preventions.append(prevention)

class PreventNextDamageBy(Effect):
    def __init__(self, amt: int = None):
        self.amt = amt

    def resolve(self, gs: GameState, s: GameCard, target: GameCard = None):
        """target is the card dealing damage"""
        if not target:
            raise RuntimeError(f'{s.props.name} needs a target')
        prevention = PreventNextDamage(s, self.amt, source_card=target)
        gs.damage_preventions.append(prevention)

class PreventNextDamageToSourceOwner(Effect):
    def __init__(self, amt: int = None, combat_only: bool = False):
        self.amt = amt
        self.combat_only = combat_only

    def resolve(self, gs: GameState, s: GameCard, target: GameCard = None):
        prevention = PreventNextDamage(s, self.amt, target_player=s.owner_id, source_card=target,
                                       combat_only=self.combat_only)
        gs.damage_preventions.append(prevention)

# -- CARD-SPECIFIC ---
class ArgothianPixiesPrevention(DamagePreventionEffect):
    """Prevent all damage that would be dealt to this creature by artifact creatures"""
    def applies(self, gs: GameState, event: DamageEvent, card: Optional[GameCard] = None):
        return (event.target is card and event.source and 'Artifact' in event.source.props.card_types
                and 'Creature' in event.source.props.card_types)

class ArgothianTreefolkPrevention(DamagePreventionEffect):
    """Prevent all damage that would be dealt to this creature by artifact sources"""
    def applies(self, gs: GameState, event: DamageEvent, card: Optional[GameCard] = None):
        return event.target is card and event.source and 'Artifact' in event.source.props.card_types

class ArtifactWardPrevention(DamagePreventionEffect):
    """Prevent all damage that would be dealt to enchanted creature by artifact sources"""
    def applies(self, gs: GameState, event: DamageEvent, card: Optional[GameCard] = None) -> bool:
        if event.target is not card.host:
            return False
        return 'Artifact' in event.source.props.card_types

class EnchantedBeingPrevention(DamagePreventionEffect):
    """Prevent all combat damage that would be dealt to this creature by enchanted creatures"""
    def applies(self, gs: GameState, event: DamageEvent, card: Optional[GameCard] = None):
        if event.target is not card.host:
            return False
        if not event.is_combat:
            return False
        if not event.source:
            return False

        return any(aura.props for aura in event.source.auras if hasattr(aura, 'props'))

class Forcefield(Effect):
    """Next time an unblocked creature of your choice would deal combat damage to you this turn, reduce damage to 1"""
    def resolve(self, gs, s: GameCard, t: Optional[GameCard] = None):
        gs.damage_preventions.append(PreventNextDamage(s, source_card=t, target_player=s.owner_id, combat_only=True))
        gs.apply_damage(t, 1, s.owner_id, is_combat=True)

class MarblePriestPrevention(DamagePreventionEffect):
    """Prevent all combat damage that would be dealt to this creature by Walls"""
    def applies(self, gs: GameState, event: DamageEvent, card: Optional[GameCard] = None):
        return event.target is card and event.is_combat and event.source and 'Wall' in event.source.props.card_sub_types

class ScarecrowPrevention(DamagePreventionEffect):
    def applies(self, gs: GameState, event: DamageEvent, card: Optional[GameCard] = None) -> bool:
        return (event.target == flip(gs.turn_mgr.player_turn_idx) and
                event.source in gs.card_filter.in_play().creatures().has('Flying').result())

class UncleIstvanPrevention(DamagePreventionEffect):
    """Prevent all damage that would be dealt to this creature by creatures"""
    def applies(self, gs: GameState, event: DamageEvent, card: Optional[GameCard] = None) -> bool:
        return event.target is card and 'Creature' in event.source.props.card_types

class WallOfPutridFleshPrevention(DamagePreventionEffect):
    """Prevent all damage that would be dealt to this creature by enchanted creatures"""
    def applies(self, gs: GameState, event: DamageEvent, card: Optional[GameCard] = None):
        return event.target is card and event.source and event.source.is_enchanted
