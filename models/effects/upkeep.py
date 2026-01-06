from __future__ import annotations
from typing import TYPE_CHECKING, Optional

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

def serendib_efreet_on_upkeep():
    class E(Effect):
        event = 'upkeep'
        
        def resolve(self, gs: GameState, source: GameCard, target: Optional[GameCard] = None):
            gs.apply_damage(source, 1, source.orig_owner_id)
    return E()
