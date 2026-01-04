from __future__ import annotations
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from game_state import GameState
    from models.actions.base import Action

from dataclasses import dataclass, field

from utils import flip


@dataclass
class ActionStack:
    _actions: list[Action] = field(default_factory=list)

    def __len__(self) -> int:
        return len(self._actions)

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
    def last_action(self) -> Action:
        return self._actions[-1]

    def add_(self, action: Action, gs: GameState) -> None:
        self._actions.append(action)
        gs.action_on_idx = flip(gs.action_on_idx)

    def clear(self) -> None:
        self._actions.clear()
