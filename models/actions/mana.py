from __future__ import annotations
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from models.game_card.game_card import GameCard

from models.actions.base import Action


class AddMana(Action):
    def __init__(self, p_id, gs, source: GameCard, color: str, amt: int = 1):
        super().__init__(p_id, gs)
        self.source = source
        self.color = color
        self.amt = amt

    def __repr__(self):
        return f'Add {self.amt} {self.color} to your mana pool'

    def play(self):
        self.gs.mana_pools[self.player_idx].add_floating(self.color, self.amt)


class PayMana(Action):
    def __init__(self, p_id, gs, source: GameCard, cost: str):
        super().__init__(p_id, gs)
        self.source = source
        self.cost = cost

    def __repr__(self):
        return f'Pay {self.cost} for {self.source.props.name}'

    def play(self):
        self.gs.mana_pools[self.player_idx].pay(self.cost)
        if self.gs.pending_choice:
            self.gs.pending_choice = None
        elif self.gs.action_stack:
            self.gs.action_stack.pop()
