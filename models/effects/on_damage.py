from __future__ import annotations
from typing import TYPE_CHECKING

from .base import Effect
from ..damage import DamageEvent

if TYPE_CHECKING:
    from ..game_card import GameCard
    from game_state import GameState

def martyrs_of_korlis_on_damage():
    """As long as this creature is untapped,
    all damage that would be dealt to you by artifacts is dealt to this creature instead"""
    class E(Effect):
        event = 'on_damage'

        def on_damage(self, gs: GameState, event: DamageEvent):
            if not isinstance(event.target, int):
                return
            if not (martyrs := gs.card_filter.on_player_board(event.target).by_slug('martyrs-of-korlis').untapped().result()):
                return
            if "Artifact" not in event.source.props.card_types:
                return

            # use the first found untapped martys-of-korlis owned by the damaged player
            event.target = martyrs[0]
    return E()

def spirit_link_on_damage():
    """Enchant creature  Whenever enchanted creature deals damage, you gain that much life"""
    class E(Effect):
        event = 'on_damage'

        def on_damage(self, gs: GameState, event: DamageEvent):
            for a in event.source.modifiers.auras:
                if a.props.slug != 'spirit-link':
                    continue
                gs.increment_life(event.source.orig_owner_id, event.remaining)
    return E()
