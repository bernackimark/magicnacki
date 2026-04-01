from __future__ import annotations
from abc import ABC, abstractmethod
from collections import defaultdict, Counter
from typing import TYPE_CHECKING

from models.utils import flip

if TYPE_CHECKING:
    from game_state import GameState

class StateBasedRule(ABC):
    @staticmethod
    @abstractmethod
    def apply(gs: GameState) -> bool:
        """Return True if the game state changed"""

def _is_match_over(gs: GameState):
    best_of = gs.rules.get('best_of')
    if not best_of:
        return False
    c = Counter(gs.winners)
    winner = 0 if c[0] > c[1] else 1 if c[1] > c[0] else None
    if winner:
        gs.winner = winner
        print(f'Player #{winner} wins the match')

class GameOverSBR(StateBasedRule):
    """Check for game_over (player life <= 0 & poison counters >= 10)"""
    @staticmethod
    def apply(gs: GameState) -> bool:
        if gs.is_game_over:  # there could be another win condition that sets is_game_over to True elsewhere
            return True

        zero_life = [idx for idx, life in enumerate(gs.life) if life <= 0]
        ten_poison = [idx for idx, poison in enumerate(gs.poison_counters) if poison >= 10]

        if not zero_life or ten_poison:
            return False

        gs.is_game_over = True
        losers = tuple(set(zero_life + ten_poison))
        if len(losers) > 1:
            gs.winners.append(-1)
            print('The game ends in a draw')
        else:
            winner = flip(losers[0])
            gs.winners.append(winner)
            print(f'Player #{winner} wins the game')
            print(f'Player #0 has {gs.winners.count(0)} win(s); Player #1 has {gs.winners.count(1)} win(s)')

        _is_match_over(gs)

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
