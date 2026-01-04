from __future__ import annotations
from typing import TYPE_CHECKING, Optional

if TYPE_CHECKING:
    from ..game_card import GameCard
    from game_state import GameState

from models.effects.base import Effect
from card_filter import CardFilter
from utils import flip


def copper_tablet_on_upkeep():
    class E(Effect):
        event = 'upkeep'

        def resolve(self, gs: GameState, source: GameCard, target: Optional[GameCard] = None):
            gs.decrement_life(gs.player_turn_idx, 1, source)
    return E()


def cursed_land_on_upkeep():
    class E(Effect):
        event = 'upkeep'

        def resolve(self, gs: GameState, source: GameCard, target: Optional[GameCard] = None):
            gs.decrement_life(target.orig_owner_id, 1, source)

    return E()

def feedback_on_upkeep():
    class E(Effect):
        event = 'upkeep'
        
        def resolve(self, gs: GameState, source: GameCard, target: Optional[GameCard] = None):
            gs.decrement_life(gs.player_turn_idx, 1, source)
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
            opponent = flip(gs.player_turn_idx)
            swamp_list = CardFilter(gs).on_player_board(opponent).by_slug('swamp').result()
            swamp_cnt = len(swamp_list)
            if swamp_cnt:
                gs.decrement_life(opponent, swamp_cnt, source)
    return E()

def serendib_efreet_on_upkeep():
    class E(Effect):
        event = 'upkeep'
        
        def resolve(self, gs: GameState, source: GameCard, target: Optional[GameCard] = None):
            gs.decrement_life(gs.player_turn_idx, 1, source)
    return E()
