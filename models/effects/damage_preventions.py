from __future__ import annotations
from typing import TYPE_CHECKING, Optional

from models.effects.base import Effect
from utils import flip

if TYPE_CHECKING:
    from game_state import GameState
    from models.game_card import GameCard

from models.damage import DamageEvent
from models.effects.specifications import Static


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
        if event.target is not card.attached_to:
            return False
        return 'Artifact' in event.source.props.card_types

class EnchantedBeingPrevention(DamagePreventionEffect):
    """Prevent all combat damage that would be dealt to this creature by enchanted creatures"""
    def applies(self, gs: GameState, event: DamageEvent, card: Optional[GameCard] = None):
        if event.target is not card.attached_to:
            return False
        if not event.is_combat:
            return False
        if not event.source:
            return False

        return any(aura.props for aura in event.source.modifiers.auras if hasattr(aura, 'props'))

class MarblePriestPrevention(DamagePreventionEffect):
    """Prevent all combat damage that would be dealt to this creature by Walls"""
    def applies(self, gs: GameState, event: DamageEvent, card: Optional[GameCard] = None):
        return event.target is card and event.is_combat and event.source and 'Wall' in event.source.props.card_sub_types

class ScarecrowPrevention(DamagePreventionEffect):
    def applies(self, gs: GameState, event: DamageEvent, card: Optional[GameCard] = None) -> bool:
        return (event.target == flip(gs.player_turn_idx) and
                event.source in gs.card_filter.in_play().creatures().has('Flying').result())
