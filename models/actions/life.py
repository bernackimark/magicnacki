from __future__ import annotations
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from models.game_card import GameCard

from models.actions.base import Action

class GainLifeAction(Action):
    def __init__(self, p_id, gs, gain_life_p_id: int, amt: int = 1):
        super().__init__(p_id, gs)
        self.gain_life_p_id = gain_life_p_id
        self.amt = amt

    def __repr__(self):
        return f'Add {self.amt} life'

    def play(self):
        self.gs.increment_life(self.gain_life_p_id, self.amt)
