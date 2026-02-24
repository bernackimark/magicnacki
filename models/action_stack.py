from __future__ import annotations
from typing import TYPE_CHECKING

from models.choice_actions_all import ChoiceAction

if TYPE_CHECKING:
    from game_state import GameState
    from models.actions.base import Action

from dataclasses import dataclass, field

from models.utils import flip


@dataclass
class ActionStack:
    _actions: list[Action | ChoiceAction] = field(default_factory=list)

    def __len__(self) -> int:
        return len(self._actions)

    @property
    def actions(self) -> list[Action | ChoiceAction]:
        return self._actions

    @property
    def first_actor_idx(self) -> int:
        return self._actions[0].player_idx

    @property
    def last_actor_idx(self) -> int:
        return self._actions[-1].player_idx

    @property
    def action_on_idx(self) -> int:
        return flip(self.last_actor_idx)

    @property
    def last_action(self) -> Action | ChoiceAction:
        return self._actions[-1]

    def push(self, action: Action, gs: GameState, flip_action_on_opponent: bool = True) -> None:
        self._actions.append(action)
        if flip_action_on_opponent:
            gs.action_on_idx = flip(gs.action_on_idx)

    def pop(self):
        self._actions.pop()

    def clear_(self) -> None:
        self._actions.clear()
