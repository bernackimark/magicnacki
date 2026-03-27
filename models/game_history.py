from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

from models.actions.base import Action

if TYPE_CHECKING:
    from game_state import GameState

@dataclass
class HistoryRecord:
    action: Action
    game_state: GameState

@dataclass
class GameHistory:
    items: list[HistoryRecord] = field(default_factory=list)

    def append(self, item: HistoryRecord) -> None:
        """Need to store a copy of game_state, not just a reference"""
        gs_copy = deepcopy(item.game_state)
        record = HistoryRecord(item.action, gs_copy)
        self.items.append(record)

    @property
    def last_action(self) -> HistoryRecord | None:
        if not self.items:
            return None
        return self.items[-1]

    def get_last_n(self, n: int) -> list[HistoryRecord]:
        return self.items[-n:]

