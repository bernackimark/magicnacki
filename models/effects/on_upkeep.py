from __future__ import annotations
from typing import TYPE_CHECKING, Optional

from ..actions.choices import SunkenCityUpkeepChoice

if TYPE_CHECKING:
    from ..game_card import GameCard
    from game_state import GameState

from models.effects.base import Effect
from card_filter import CardFilter
from utils import flip


def copper_tablet_on_upkeep():
    """At the beginning of each player's upkeep, this artifact deals 1 damage to that player"""
    class E(Effect):
        event = 'upkeep'

        def resolve(self, gs: GameState, source: GameCard, target: Optional[GameCard] = None):
            gs.apply_damage(source, 1, gs.player_turn_idx)
    return E()


def cursed_land_on_upkeep():
    """Cursed Land does 1 damage to target land's controller during each upkeep"""
    class E(Effect):
        event = 'upkeep'

        def resolve(self, gs: GameState, source: GameCard, target: Optional[GameCard] = None):
            gs.apply_damage(source, 1, target.orig_owner_id)
    return E()

def feedback_on_upkeep():
    """At the beginning of the upkeep of enchanted enchantment's controller, this Aura deals 1 damage to that player"""
    class E(Effect):
        event = 'upkeep'
        
        def resolve(self, gs: GameState, source: GameCard, target: Optional[GameCard] = None):
            gs.apply_damage(source, 1, target.orig_owner_id)
    return E()

def ivory_tower_on_upkeep():
    class E(Effect):
        event = 'upkeep'

        def resolve(self, gs: GameState, source: GameCard, target: Optional[GameCard] = None):
            # At the beginning of your upkeep, you gain X life, where X is the number of cards in your hand minus 4
            p_id = source.orig_owner_id
            if (hand_size := len(gs.hands[p_id].cards)) > 4:
                gs.increment_life(p_id, hand_size - 4)
    return E()

def karma_on_upkeep():
    class E(Effect):
        event = 'upkeep'
        
        def resolve(self, gs: GameState, source: GameCard, target: Optional[GameCard] = None):
            """At the beginning of each player's upkeep,
            this enchantment deals damage to that player equal to the number of Swamps they control."""
            p_id = gs.player_turn_idx
            swamp_cnt = len(CardFilter(gs).on_player_board(p_id).by_slug('swamp').result())
            if swamp_cnt:
                gs.apply_damage(source, swamp_cnt, source.orig_owner_id)
    return E()

def juzam_djinn_on_upkeep():
    class E(Effect):
        event = 'upkeep'

        def resolve(self, gs: GameState, source: GameCard, target: Optional[GameCard] = None):
            gs.apply_damage(source, 1, source.orig_owner_id)
    return E()

def power_surge_on_upkeep():
    """At the beginning of each player's upkeep, this enchantment deals X damage to that player,
    where X is the number of untapped lands they controlled at the beginning of this turn"""
    class E(Effect):
        event = 'upkeep'

        def resolve(self, gs: GameState, source: GameCard, target: Optional[GameCard] = None):
            untapped_lands = gs.card_filter.in_play().untapped().lands().result()
            gs.apply_damage(source, len(untapped_lands), gs.player_turn_idx)
    return E()

def serendib_efreet_on_upkeep():
    class E(Effect):
        event = 'upkeep'
        
        def resolve(self, gs: GameState, source: GameCard, target: Optional[GameCard] = None):
            gs.apply_damage(source, 1, source.orig_owner_id)
    return E()

def spiritual_sanctuary_on_upkeep():
    """At the beginning of each player's upkeep, if that player controls a Plains, they gain 1 life"""
    class E(Effect):
        event = 'upkeep'

        def resolve(self, gs: GameState, source: GameCard, target: Optional[GameCard] = None):
            if 'plains' in gs.card_filter.on_player_board(gs.player_turn_idx).by_slug('plains').result():
                gs.increment_life(gs.player_turn_idx, 1)
    return E()

def storm_world_on_upkeep():
    """At the beginning of each player's upkeep, this enchantment deals X damage to that player,
    where X is 4 minus the number of cards in their hand"""

    class E(Effect):
        event = 'upkeep'

        def resolve(self, gs: GameState, source: GameCard, target: Optional[GameCard] = None):
            card_cnt = len(gs.hands[gs.player_turn_idx].cards)
            if card_cnt > 4:
                gs.apply_damage(source, card_cnt - 4, gs.player_turn_idx)
    return E()

def sunken_city_on_upkeep():
    """At the beginning of your upkeep, sacrifice this enchantment unless you pay {UU}. """
    class E(Effect):
        event = 'upkeep'

        def resolve(self, gs: GameState, source: GameCard, target=None):
            # Pause the game and force a choice
            gs.action_stack.push(SunkenCityUpkeepChoice(source.orig_owner_id, gs, source), gs, False)
    return E()
