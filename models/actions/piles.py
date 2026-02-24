from __future__ import annotations
from typing import TYPE_CHECKING

from models.utils import flip
from models.zone import Zone

if TYPE_CHECKING:
    from models.game_card import GameCard

from models.actions.base import Action

# --- GENERICS ---
class HandToBattlefield(Action):
    def __init__(self, p_id, gs, target: GameCard):
        super().__init__(p_id, gs)
        self.target = target

    def __repr__(self):
        return f'Move {self.target.props.name} from hand to battlefiend'

    def play(self):
        self.gs.move_card(self.target, Zone.BATTLEFIELD, cause='hand_to_battlefield')
        self.gs.action_stack.pop()  # remove choice
