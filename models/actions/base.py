from __future__ import annotations
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from models.choice_actions_all import ChoiceAction
    from game_state import GameState

import abc
from abc import ABC
from dataclasses import dataclass


@dataclass
class Action(ABC):
    player_idx: int
    gs: GameState

    @abc.abstractmethod
    def play(self) -> None:
        ...

    def finish(self, next_choice: ChoiceAction | None = None) -> None:
        """This is default behavior chosen by most Actions;
        those with successive ChoiceActions would implement their own logic"""
        if next_choice:
            self.gs.pending_choice = next_choice
        elif self.gs.pending_choice:
            self.gs.pending_choice = None
            if self.gs.choice_queue:
                self.gs.pending_choice = self.gs.choice_queue.pop(0)
        elif self.gs.action_stack.actions:
            self.gs.action_stack.pop()
