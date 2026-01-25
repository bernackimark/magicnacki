from __future__ import annotations
from typing import TYPE_CHECKING

from .base import Effect
from ..counter_tokens import PLUS_ONE, VITALITY
from ..damage import DamageEvent

if TYPE_CHECKING:
    from ..game_card import GameCard
    from game_state import GameState

def fungusaur_on_damage():
    """Whenever this creature is dealt damage, put a +1/+1 counter on it"""
    class E(Effect):
        event = 'on_damage'

        def on_damage(self, gs: GameState, event: DamageEvent, this_card: GameCard = None):
            if event.target == this_card:
                this_card.counters.add_counter(PLUS_ONE)
    return E()

def living_artifact_on_damage():
    """Enchant artifact Whenever you're dealt damage, put that many vitality counters on this Aura ... """
    class E(Effect):
        event = 'on_damage'

        def on_damage(self, gs: GameState, event: DamageEvent, this_card: GameCard = None):
            if event.target == this_card.orig_owner_id:
                this_card.counters.add_counter(VITALITY)
    return E()

def martyrs_of_korlis_on_damage():
    """As long as this creature is untapped,
    all damage that would be dealt to you by artifacts is dealt to this creature instead"""
    class E(Effect):
        event = 'on_damage'

        def on_damage(self, gs: GameState, event: DamageEvent, this_card: GameCard = None):
            if this_card.is_tapped:
                return
            if event.target != this_card.orig_owner_id:
                return
            if 'Artifact' not in event.source.props.card_types:
                return
            event.target = this_card
    return E()

def spirit_link_on_damage():
    """Enchant creature  Whenever enchanted creature deals damage, you gain that much life"""
    class E(Effect):
        event = 'on_damage'

        def on_damage(self, gs: GameState, event: DamageEvent, this_card: GameCard = None):
            if event.source == this_card.attached_to:
                gs.increment_life(this_card.attached_to.orig_owner_id, event.remaining)
    return E()
