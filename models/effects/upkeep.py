from typing import Optional

from models.effects.base import Effect
from card_filter import CardFilter
from utils import flip


def copper_tablet_on_upkeep():
    class E(Effect):
        event = 'upkeep'

        def resolve(self, gs, source: "GameCard", target: Optional["GameCard"] = None):
            gs.decrement_life(gs.player_turn_idx, 1, source)
    return E()


def cursed_land_on_upkeep():
    class E(Effect):
        event = 'upkeep'

        def resolve(self, gs, source: "GameCard", target: Optional["GameCard"] = None):
            gs.decrement_life(target.orig_owner_id, 1, source)

    return E()

def feedback_on_upkeep():
    class E(Effect):
        event = 'upkeep'
        
        def resolve(self, gs, source: "GameCard", target: Optional["GameCard"] = None):
            gs.decrement_life(gs.player_turn_idx, 1, source)
    return E()

def karma_on_upkeep():
    class E(Effect):
        event = 'upkeep'
        
        def resolve(self, gs, source: "GameCard", target: Optional["GameCard"] = None):
            opponent = flip(gs.player_turn_idx)
            swamp_list = CardFilter(gs).on_player_board(opponent).by_slug('swamp').result()
            swamp_cnt = len(swamp_list)
            if swamp_cnt:
                gs.decrement_life(opponent, swamp_cnt, source)
    return E()

def serendib_efreet_on_upkeep():
    class E(Effect):
        event = 'upkeep'
        
        def resolve(self, gs, source: "GameCard", target: Optional["GameCard"] = None):
            gs.decrement_life(gs.player_turn_idx, 1, source)
    return E()
