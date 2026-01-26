from __future__ import annotations
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from models.game_card import GameCard

from models.actions.base import Action

class DealDamage(Action):
    def __init__(self, p_id, gs, source: GameCard, damage_amt: int):
        super().__init__(p_id, gs)
        self.source = source
        self.damage_amt = damage_amt

    def __repr__(self):
        return f'{self.source.props.name} deals {self.damage_amt} damage to you'

    def play(self):
        self.gs.apply_damage(self.source, self.damage_amt, self.source.orig_owner_id)
        self.gs.action_stack.pop()  # remove choice


class PayLife(Action):
    def __init__(self, p_id, gs, source: GameCard, amt: int):
        super().__init__(p_id, gs)
        self.source = source
        self.amt = amt

    def __repr__(self):
        return f'Pay {self.amt} life for {self.source.props.name}'

    def play(self):
        self.gs.apply_damage(self.source, self.amt, self.source.attached_to.orig_owner_id)
        self.gs.action_stack.pop()
