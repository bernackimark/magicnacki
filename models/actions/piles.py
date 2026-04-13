from __future__ import annotations
import random
from typing import TYPE_CHECKING

from models.actions.base import Action
from models.zone import Zone

if TYPE_CHECKING:
    from models.game_card import GameCard

# --- GENERICS ---
class BattlefieldToGraveyard(Action):
    def __init__(self, p_id, gs, target: GameCard):
        super().__init__(p_id, gs)
        self.target = target

    def __repr__(self):
        return f'Move {self.target} to graveyard'

    def play(self) -> None:
        self.gs.move_card(self.target, Zone.GRAVEYARD, cause='legendary_rule')
        self.gs.pending_choice = None

class HandToBattlefield(Action):
    def __init__(self, p_id, gs, target: GameCard):
        super().__init__(p_id, gs)
        self.target = target

    def __repr__(self):
        return f'Move {self.target.props.name} from hand to battlefiend'

    def play(self):
        self.gs.move_card(self.target, Zone.BATTLEFIELD, cause='hand_to_battlefield')
        self.gs.action_stack.pop()  # remove choice

class Shuffle(Action):
    def __init__(self, p_id, gs, cards: list[GameCard]):
        super().__init__(p_id, gs)
        self.cards = cards

    def __repr__(self):
        return 'Shuffle Cards'

    def play(self) -> None:
        random.shuffle(self.cards)
        if self.gs.action_stack.actions:
            self.gs.action_stack.pop()
        if self.gs.pending_choice:
            self.gs.pending_choice = None
