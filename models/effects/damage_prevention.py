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
            if (not hasattr(event.source.props, 'slug') or not hasattr(event.target.props, 'slug') or
                    event.target.props.slug != 'argothian-pixies'):
                return

            if 'Artifact' in event.source.props.card_types and 'Creature' in event.source.props.card_types:
                event.prevented += event.remaining
    return E()

def argothian_treefolk_damage_prevention():
    """Prevent all damage that would be dealt to this creature by artifact sources"""
    class E(Effect):
        def on_damage(self, gs: GameState, event: DamageEvent):
            if (not hasattr(event.source.props, 'slug') or not hasattr(event.target.props, 'slug') or
                    event.target.props.slug != 'argothian-treefolk'):
                return

            # Source must be an artifact creature
            if 'Artifact' in event.source.props.card_types:
                event.prevented += event.remaining
    return E()
