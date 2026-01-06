from __future__ import annotations
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from game_state import GameState

from ..damage import DamageEvent
from models.effects.base import Effect

def argothian_pixies_damage_prevention():
    """Prevent all damage that would be dealt to this creature by artifact creatures"""
    class E(Effect):
        def on_damage(self, gs: GameState, event: DamageEvent):
            # don't have access to GameCard due to circular import; using hasattr() to see if source is a card
            if not hasattr(event.target, 'props') or event.target.props.slug != 'argothian-pixies':
                return
            if 'Artifact' in event.source.props.card_types and 'Creature' in event.source.props.card_types:
                event.prevented += event.remaining
    return E()

def argothian_treefolk_damage_prevention():
    """Prevent all damage that would be dealt to this creature by artifact sources"""
    class E(Effect):
        def on_damage(self, gs: GameState, event: DamageEvent):
            if not hasattr(event.target, 'props') or event.target.props.slug != 'argothian-treefolk':
                return
            if 'Artifact' in event.source.props.card_types:
                event.prevented += event.remaining
    return E()

def artifact_ward_damage_prevention():
    """Prevent all damage that would be dealt to enchanted creature by artifact sources"""
    class E(Effect):
        def on_damage(self, gs: GameState, event: DamageEvent):
            if not hasattr(event.target, 'props') or not event.target.modifiers.is_enchanted_by('artifact-ward'):
                return
            if 'Artifact' in event.source.props.card_types:
                event.prevented += event.remaining
    return E()

def enchanted_being_damage_prevention():
    """Prevent all combat damage that would be dealt to this creature by enchanted creatures"""
    class E(Effect):
        def on_damage(self, gs: GameState, event: DamageEvent):
            if not hasattr(event.target, 'props') or event.target.props.slug != 'enchanted-being':
                return
            if event.is_combat and [a for a in event.source.modifiers.auras if hasattr(a, 'props')]:
                event.prevented += event.remaining
    return E()

def marble_priest_damage_prevention():
    """Prevent all combat damage that would be dealt to this creature by Walls"""
    class E(Effect):
        def on_damage(self, gs: GameState, event: DamageEvent):
            if not hasattr(event.target, 'props') or event.target.props.slug != 'marble_priest':
                return
            if event.is_combat and 'Wall' in event.source.props.card_sub_types:
                event.prevented += event.remaining
    return E()
