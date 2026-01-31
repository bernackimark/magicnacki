from __future__ import annotations
from typing import Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from game_state import GameState
    from models.game_card import GameCard

from models.counter_tokens import VITALITY, PLUS_ONE
from models.damage import DamageEvent
from models.effects.base import Effect
from utils import flip

def creature_bond_on_leave():
    class E(Effect):
        event = 'leave'
        # need this instance that uses the leave event, because it DOES something on leave, not just the removal of a
        # continuous effect

        def resolve(self, gs, source: GameCard, target: Optional[GameCard] = None):
            # TODO: i think this is wrong; i think it's only if creature goes to graveyard
            # creature leaving: for every attached aura that is creature-bond, do life loss to creature's owner
            for aura in target.modifiers.auras:
                if aura.props.slug == 'creature-bond':
                    gs.decrement_life(target.orig_owner_id, target.props.toughness, aura)
                    # TODO: use apply_damage instead of directly calling decrement_life; make decrement_life private?
    return E()

def martyrs_of_korlis_on_damage():
    """As long as this creature is untapped,
    all damage that would be dealt to you by artifacts is dealt to this creature instead"""
    class E(Effect):
        event = 'on_damage'

        def resolve(self, gs: GameState, event: DamageEvent, this_card: GameCard = None):
            if this_card.is_tapped:
                return
            if event.target != this_card.orig_owner_id:
                return
            if 'Artifact' not in event.source.props.card_types:
                return
            event.target = this_card
    return E()

def living_artifact_on_damage():
    """Enchant artifact Whenever you're dealt damage, put that many vitality counters on this Aura ... """
    class E(Effect):
        event = 'on_damage'

        def resolve(self, gs: GameState, event: DamageEvent, this_card: GameCard = None):
            if event.target == this_card.orig_owner_id:
                this_card.counters.add_counter(VITALITY)
    return E()

def fungusaur_on_damage():
    """Whenever this creature is dealt damage, put a +1/+1 counter on it"""
    class E(Effect):
        event = 'on_damage'

        def resolve(self, gs: GameState, event: DamageEvent, this_card: GameCard = None):
            if event.target == this_card:
                this_card.counters.add_counter(PLUS_ONE)
    return E()

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

def all_damage_prevented_to_target_card(c: GameCard):
    class E(Effect):
        def on_damage(self, gs: GameState, event: DamageEvent):
            if event.target == c:
                event.prevented += event.remaining
    return E()

def scarecrow_func():
    class E(Effect):
        def on_damage(self, gs: GameState, event: DamageEvent):
            if event.target == flip(gs.player_turn_idx):
                if event.source in gs.card_filter.in_play().creatures().has('Flying').result():
                    event.prevented += event.remaining
    return E()

def all_combat_damage_prevented():
    class E(Effect):
        def on_damage(self, gs: GameState, event: DamageEvent):
            if event.is_combat:
                event.prevented += event.remaining
    return E()
