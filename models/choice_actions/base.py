from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from constants import Target
    from game_state import GameState
    from models.actions.base import Action
    from models.game_card import GameCard


@dataclass
class ChoiceAction(ABC):
    p_id: int
    gs: GameState
    source: GameCard
    target: Optional[Target] = None

    @abstractmethod
    def get_actions(self) -> list[Action]:
        ...
