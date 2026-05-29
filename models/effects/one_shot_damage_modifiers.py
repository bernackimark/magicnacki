from __future__ import annotations
from typing import TYPE_CHECKING, Optional, Callable

from models.effects.base import Effect
from models.utils import flip

if TYPE_CHECKING:
    from game_state import GameState
    from models.game_card.game_card import GameCard

from models.damage import DamageEvent, PreventNextDamage, DamageReplacement

"""
ONE-SHOT DAMAGE PREVENTERS (like COP):
    -   They should be resolvers that create a OneShotDamagePrevention object
    -   OneShotDamagePrevention objs may take any attributes needed to implement .applies() -> bool & .apply() -> int
    -   OneShotDamagePrevention objects need to live somewhere, ex below: DamageSystem
    -   GameState must iterate over them

NOTE:
    -   This is for Temporary one-time shields -- not for continuous replacement/preventions effects like Argothian P
    
Argothian Pixes approach of continuous/card-native preventions/replacers are Listeners (see listeners_card_specific.py)
    
# Example OneShotDamagePrevention-type object.  Note: do not confuse these with an Effect, they are distinct
@dataclass
class COPShield:
    source: GameCard
    protected_player: int
    protected_color: str
    used: bool = False

    def applies(self, event: DamageEvent) -> bool:

        if self.used:
            return False

        if event.target != self.protected_player:
            return False

        if not event.source:
            return False

        return self.protected_color in event.source.colors
        
# Example Damage System/Manager:
class DamageSystem:

    def __init__(self):
        self.shields: list[DamageShield] = []

    def add_shield(self, shield):
        self.shields.append(shield)
        
# Example GameState iterating over shield objects:
for shield in list(self.damage_system.shields):

    if shield.applies(event):
        shield.apply(event)

    if shield.used:
        self.damage_system.shields.remove(shield)
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
    # lady-evangela is the sole implementer of this:
    # Activated Ability: "Prevent all combat damage that would be dealt by target creature this turn"
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
"""
ARGOTHIAN PIXIES IS THE NEW MODEL (it's located in listeners_card_specific.py):
    -   GameState calls for registered DamageProposedEvent listeners
    -   The Effect is a Listener implementing on_event()
    -   Checks if it applies within on_event()
    -   Modifies the Event
"""


# These may be examples of the one-shot approach described in the top doc string
class Forcefield(Effect):
    """Next time an unblocked creature of your choice would deal combat damage to you this turn, reduce damage to 1"""
    def resolve(self, gs, s: GameCard, t: Optional[GameCard] = None):
        gs.damage_preventions.append(PreventNextDamage(s, source_card=t, target_player=s.owner_id, combat_only=True))
        gs.apply_damage(t, 1, s.owner_id, is_combat=True)

class ScarecrowPrevention(DamagePreventionEffect):
    """(Activated Ability): Prevent all damage that would be dealt to you this turn by creatures with flying"""
    def applies(self, gs: GameState, event: DamageEvent, card: Optional[GameCard] = None) -> bool:
        return (event.target == flip(gs.turn_mgr.player_turn_idx) and
                event.source in gs.card_filter.in_play().creatures().has('Flying').result())


class RedirectDamageFromOwnerToCreature(DamageReplacement):
    def __init__(self, damage_source: GameCard, to_creature: GameCard):
        self.damage_source = damage_source
        self.to_creature = to_creature
        self.used = False

    def applies(self, gs: GameState, event: DamageEvent) -> bool:
        if self.used:
            return False
        return (event.source is self.damage_source and event.target is self.to_creature.owner_id
                and event.remaining > 0)

    def replace(self, gs: GameState, event: DamageEvent) -> None:
        # redirect the damage
        event.target = self.to_creature
        self.used = True


class RedirectDamageToOwner(DamageReplacement):
    def __init__(self, damage_source: GameCard, to_creature: GameCard):
        self.damage_source = damage_source
        self.to_creature = to_creature
        self.used = False

    def applies(self, gs: GameState, event: DamageEvent) -> bool:
        if self.used:
            return False
        return event.source is self.damage_source and event.target is self.to_creature and event.remaining > 0

    def replace(self, gs: GameState, event: DamageEvent) -> None:
        # redirect the damage
        event.target = self.to_creature.owner_id
        self.used = True


class JadeMonolith(Effect):
    """{1}: Redirect next damage from a chosen source to a chosen creature onto you."""
    def resolve(self, gs: GameState, source: GameCard, target: GameCard = None):
        replacement = RedirectDamageToOwner(source, target)
        gs.damage_replacements.append(replacement)


class MartyrsOfKorlisDamageReplacement:
    def apply(self, gs: GameState, source: GameCard):
        gs.damage_replacements.append(MartyrsOfKorlisReplacement(source))

    def remove(self, gs: GameState, source: GameCard):
        gs.damage_replacements = [r for r in gs.damage_replacements
                                  if not (isinstance(r, MartyrsOfKorlisReplacement) and r.card is source)]


class MartyrsOfKorlisReplacement(DamageReplacement):
    """As long as this creature is untapped,
    all damage that would be dealt to you by artifacts is dealt to this creature instead"""
    def __init__(self, card: GameCard):
        self.card = card

    def applies(self, gs: GameState, event: DamageEvent) -> bool:
        if self.card.is_tapped:
            return False
        if event.target != self.card.owner_id:
            return False
        if 'Artifact' not in event.source.props.card_types:
            return False
        return True

    def replace(self, gs: GameState, event: DamageEvent) -> None:
        event.target = self.card
