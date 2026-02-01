from __future__ import annotations
from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from game_state import GameState

class StateBasedRule(ABC):
    @staticmethod
    @abstractmethod
    def apply(gs: GameState) -> bool:
        """Return True if the game state changed"""

class IslandhomeSBR(StateBasedRule):
    @staticmethod
    def apply(gs: GameState) -> bool:
        changed = False

        for creature in gs.card_filter.in_play().has('Islandhome').result():
            if not gs.card_filter.on_player_board(creature.orig_owner_id).by_slug('island').result():
                gs.send_to_graveyard_from_play(creature)
                changed = True

        return changed
