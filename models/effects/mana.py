from __future__ import annotations
from typing import TYPE_CHECKING, Optional

if TYPE_CHECKING:
    from ..game_card import GameCard
    from game_state import GameState

from constants import COLOR_LETTERS_W_COLORLESS
from utils import flip
from .base import Effect

class AddMana(Effect):
    def __init__(self, color: str, cnt: int = 1):
        self.color = color
        self.cnt = cnt

        if color not in COLOR_LETTERS_W_COLORLESS:
            raise ValueError(f"Color must be one of: {COLOR_LETTERS_W_COLORLESS}")

    def resolve(self, gs: GameState, source: GameCard, target: GameCard = None):
        gs.mana_pools[source.orig_owner_id].add_floating(self.color, self.cnt)

class DrainPower(Effect):
    def resolve(self, gs: GameState, source: GameCard, target: Optional[int] = None):
        """target = player_id whose available mana will be targeted & given to the other player"""
        if target is None:
            return
        land_giver_mana = gs.mana_pools[target].available_mana.copy()
        land_taker_id = flip(target)
        for color, amt in land_giver_mana.items():
            gs.mana_pools[land_taker_id].add_floating(color, amt)
        print(f"{source} steals all of Player #{target}'s unused mana.")

class EnergyTap(Effect):
    def resolve(self, gs: GameState, source: GameCard, target: Optional[GameCard] = None):
        """target = GameCard to be tapped"""
        if target is None:
            return
        target.tap(gs)
        mana_value = source.props.casting_weight
        gs.mana_pools[source.orig_owner_id].add_floating('C', mana_value)
        print(f"{source} taps to add {mana_value} colorless to your mana pool.")

class ExchangeLifeTotals(Effect):
    def resolve(self, gs: GameState, s: GameCard, _: Optional[GameCard] = None):
        your_life = gs.life[s.orig_owner_id]
        opp_life = gs.life[flip(s.orig_owner_id)]
        gs.life[s.orig_owner_id], gs.life[flip(s.orig_owner_id)] = opp_life, your_life
