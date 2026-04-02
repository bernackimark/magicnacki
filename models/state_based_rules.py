from __future__ import annotations
from abc import ABC, abstractmethod
from collections import defaultdict, Counter
from typing import TYPE_CHECKING


if TYPE_CHECKING:
    from game_state import GameState

class StateBasedRule(ABC):
    @staticmethod
    @abstractmethod
    def apply(gs: GameState) -> bool:
        """Return True if the game state changed"""


class GameOverSBR(StateBasedRule):
    """Check for game_over (player life <= 0 & poison counters >= 10)"""
    @staticmethod
    def apply(gs: GameState) -> bool:
        if gs.match_manager.is_game_over:  # there could be another win condition that sets is_game_over to True elsewhere
            return True

        game_winner = gs.match_manager.determine_game_winner()
        if game_winner is not None:
            gs.match_manager.determine_match_winner()
            return True

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


STATE_BASED_RULES = (GameOverSBR, IslandhomeSBR, ZeroToughnessSBR)
