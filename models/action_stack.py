from __future__ import annotations
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, TypeVar, Union

if TYPE_CHECKING:
    from game_state import GameState

from models.actions.ability_pipeline_support import AbilityAction
from models.actions.cast import CastPermanentAction
from models.choice_actions_all import ChoiceAction
from models.actions.base import Action
from models.utils import flip

T = TypeVar('T', bound=Action)
StackItemType = Union[AbilityAction | CastPermanentAction | ChoiceAction]


@dataclass
class ActionStack:
    _actions: list[StackItemType] = field(default_factory=list)

    def __len__(self) -> int:
        return len(self._actions)

    @property
    def actions(self) -> list[StackItemType]:
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
    def last_action(self) -> StackItemType:
        return self._actions[-1]

    @property
    def spells(self) -> list[AbilityAction | CastPermanentAction | None]:
        spells = []
        for a in self.actions:
            if isinstance(a, AbilityAction) and a.pipeline.eff_spec and not a.pipeline.eff_spec.is_spell:
                continue
            spells.append(a)
        return spells
        # return [a for a in self.actions if isinstance(a, AbilityPipeline) and a.eff_spec.is_spell]

    def push(self, action: StackItemType, gs: GameState, flip_action_on_opponent: bool = True) -> None:
        if not isinstance(action, StackItemType):
            raise TypeError(f"Action Stack expects an action, received {action}, type {type(action)}")
        self._actions.append(action)
        if flip_action_on_opponent:
            gs.action_on_idx = flip(gs.action_on_idx)

    def pop(self):
        self._actions.pop()

    def remove(self, action: StackItemType):
        if action not in self.actions:
            print('Warning: Action not found on stack')
            return
        self._actions.remove(action)

    def clear_(self) -> None:
        self._actions.clear()
