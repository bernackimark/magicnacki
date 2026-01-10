from __future__ import annotations
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from game_state import GameState
    from models.game_card import GameCard

from models.actions.base import Action
from models.actions.choice import ChoiceAction


class PaySunkenCity(Action):
    def __init__(self, p_id, gs, source):
        super().__init__(p_id, gs)
        self.source = source

    def __repr__(self):
        return 'Pay {UU} for Sunken City'

    def play(self):
        self.gs.mana_pools[self.player_idx].pay("UU")
        self.gs.action_stack.pop()  # remove choice

class SacSunkenCity(Action):
    def __init__(self, p_id, gs, source):
        super().__init__(p_id, gs)
        self.source = source

    def __repr__(self):
        return 'Sacrifice Sunken City'

    def play(self):
        self.gs.send_to_graveyard_from_play(self.source)
        self.gs.action_stack.pop()  # remove choice

class SunkenCityUpkeepChoice(ChoiceAction):
    def __init__(self, p_id: int, gs: GameState, source: GameCard):
        super().__init__(p_id, gs, source)

    def get_actions(self) -> list[Action]:
        actions: list[Action] = []
        if self.gs.mana_pools[self.p_id].can_pay("UU"):
            actions.append(PaySunkenCity(self.p_id, self.gs, self.source))
        actions.append(SacSunkenCity(self.p_id, self.gs, self.source))
        return actions


