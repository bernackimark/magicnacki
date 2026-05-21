from __future__ import annotations
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from models.game_card.game_card import GameCard

from models.actions.base import Action
from models.modifiers import PTMod


class VariablePTMod(Action):
    def __init__(self, p_id, gs, source: GameCard, target: GameCard, power: int = None, toughness: int = None):
        super().__init__(p_id, gs)
        self.source = source
        self.target = target
        self.power = power
        self.toughness = toughness

    def __repr__(self):
        return f"Set {self.target.props.name}'s power to {self.power} & toughness to {self.toughness}"

    def play(self):
        new_power = self.power - self.target.power
        new_toughness = self.toughness - self.target.toughness
        self.target.modifiers.items.append(PTMod(s=self.target, p_adj=new_power, t_adj=new_toughness))
        self.gs.action_stack.pop()
