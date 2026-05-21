from __future__ import annotations
from typing import TYPE_CHECKING, Iterable

if TYPE_CHECKING:
    from game_state import GameState
    from models.game_card.game_card import GameCard

from models.actions.base import Action
from models.modifiers import KWAMod


class AddKWA(Action):
    def __init__(self, p_id: int, gs: GameState, s: GameCard, target: GameCard, ability: str, until_eot: bool = True):
        super().__init__(p_id, gs)
        self.source = s
        self.target = target
        self.ability = ability
        self.until_eot = until_eot

    def __repr__(self):
        return f'Give {self.ability} to {self.target.props.name}'

    def play(self):
        self.target.modifiers.items.append(KWAMod(s=self.source, add_or_remove='add', kwa=self.ability,
                                                  expires='EOT' if self.until_eot else None))
        if self.gs.pending_choice:
            self.gs.pending_choice = None
        else:
            self.gs.action_stack.pop()
