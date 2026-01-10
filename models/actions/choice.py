from __future__ import annotations
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional, Union, TYPE_CHECKING

if TYPE_CHECKING:
    from models.actions.base import Action
    from models.game_card import GameCard
    from game_state import GameState

Target = Union["GameCard", list["GameCard"], int, tuple[int, int], None]

@dataclass
class ChoiceAction(ABC):
    p_id: int
    gs: GameState
    source: GameCard
    target: Optional[Target] = None

    @abstractmethod
    def get_actions(self) -> list[Action]:
        ...

    def play(self):
        raise RuntimeError("ChoiceAction cannot be played directly")
