from __future__ import annotations
from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

from models.utils import flip

if TYPE_CHECKING:
    from game_state import GameState

class StateBasedRule(ABC):
    @staticmethod
    @abstractmethod
    def apply(gs: GameState) -> bool:
        """Return True if the game state changed"""


class GameOverSBR(StateBasedRule):
    """Check for game_over (player life <= 0 & poison counters >= 10); sets gs.winner as -1 draw or 0/1 for win"""
    @staticmethod
    def apply(gs: GameState) -> bool:
        if gs.is_game_over:  # there could be a win condition that sets is_game_over to True elsewhere
            return True

        """Returns None if game is not over;
        else -1 if a draw, 0 for player #0, 1 for player #1, updates gs.is_game_over"""
        zero_life = [idx for idx, life in enumerate(gs.life) if life <= 0]
        ten_poison = [idx for idx, poison in enumerate(gs.poison_counters) if poison >= 10]

        losers = tuple(set(zero_life + ten_poison))
        if not losers:
            return False
        if len(losers) > 1:
            gs.winner = -1
            gs.is_game_over = True
            print('The game ends in a draw')
            return True
        else:
            gs.winner = flip(losers[0])
            gs.is_game_over = True
            print(f'Player #{gs.winner} wins the game')
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
