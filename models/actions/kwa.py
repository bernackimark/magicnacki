from __future__ import annotations
from typing import TYPE_CHECKING, Iterable

if TYPE_CHECKING:
    from game_state import GameState
    from models.game_card import GameCard

from models.actions.base import Action
from models.modifiers import KWATemp, KWAModifier


class AddKWA(Action):
    def __init__(self, p_id: int, gs: GameState, s: GameCard, target: GameCard, ability: str, until_eot: bool = True):
        super().__init__(p_id, gs)
        self.source = s
        self.target = target
        self.ability = ability
        self.until_eot = until_eot

    def play(self):
        if self.until_eot:
            self.target.modifiers.temps.append(KWATemp('add', self.ability))
        else:
            self.target.modifiers.auras.append(KWAModifier(self.source, 'add', self.ability))
