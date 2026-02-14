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
            if not gs.card_filter.on_player_board(creature.orig_owner_id).islands().result():
                gs.destroy(creature)
                changed = True

        return changed

class ZeroToughnessSBR(StateBasedRule):
    @staticmethod
    def apply(gs: GameState) -> bool:
        changed = False

        for creature in gs.card_filter.in_play().creatures().result():
            if creature.damage_received_this_turn >= creature.toughness:
                gs.destroy(creature)
                changed = True

        return changed


STATE_BASED_RULES = [IslandhomeSBR, ZeroToughnessSBR]
