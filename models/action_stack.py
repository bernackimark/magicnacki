from __future__ import annotations
from typing import TYPE_CHECKING

from models.choice_actions_all import ChoiceAction

if TYPE_CHECKING:
    from game_state import GameState
    from models.actions.ability_pipeline import AbilityPipeline
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

    @property
    def spells(self) -> list[AbilityPipeline | None]:
        return [a for a in self.actions if isinstance(a, AbilityPipeline) and a.eff_spec.is_spell]

    def push(self, action: Action, gs: GameState, flip_action_on_opponent: bool = True) -> None:
        if not isinstance(action, Action):
            raise TypeError(f"Action Stack expects an action, received {action}, type {type(action)}")
        self._actions.append(action)
        if flip_action_on_opponent:
            gs.action_on_idx = flip(gs.action_on_idx)

    def pop(self):
        self._actions.pop()

    def remove(self, action: Action | ChoiceAction):
        if action not in self.actions:
            print('Warning: Action not found on stack')
            return
        self._actions.remove(action)

    def clear_(self) -> None:
        self._actions.clear()
