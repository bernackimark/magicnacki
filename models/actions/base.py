from __future__ import annotations
from typing import TYPE_CHECKING

if TYPE_CHECKING:
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


@dataclass
class DoNothing(Action):
    def play(self) -> None:
        pass
