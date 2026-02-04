from __future__ import annotations
from typing import TYPE_CHECKING, Iterable

if TYPE_CHECKING:
    from models.game_card import GameCard

from models.actions.base import Action


class Exile(Action):
    def __init__(self, p_id, gs, source: GameCard, w_damage_amt: int = 0):
        super().__init__(p_id, gs)
        self.source = source
        self.w_damage_amt = w_damage_amt

    def __repr__(self):
        return f'Exile {self.source.props.name}'

    def play(self):
        if self.w_damage_amt:
            self.gs.apply_damage(self.source, self.w_damage_amt, self.source.orig_owner_id)
        self.gs.exile(self.source)
        self.gs.action_stack.pop()  # remove choice


class Sac(Action):
    def __init__(self, p_id, gs, source: GameCard, w_damage_amt: int = 0):
        super().__init__(p_id, gs)
        self.source = source
        self.w_damage_amt = w_damage_amt

    def __repr__(self):
        return f'Sacrifice {self.source.props.name}'

    def play(self):
        if self.w_damage_amt:
            self.gs.apply_damage(self.source, self.w_damage_amt, self.source.orig_owner_id)
        self.gs.destroy(self.source)
        self.gs.action_stack.pop()  # remove choice
