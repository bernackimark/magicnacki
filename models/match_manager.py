from __future__ import annotations
from collections import Counter
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from game_state import GameState

from models.utils import flip


class MatchManager:
    def __init__(self, gs: GameState):
        self.gs = gs
        self.is_game_over: bool = False
        self.is_match_over: bool = False
        self._best_of = self.gs.rules['best_of']
        self._winners: list[int] = []  # -1 for a draw, 0 for player 0, 1 for player 1
        self._match_winner: int | None = None

        if not self._best_of % 2:
            raise ValueError('Best Of must be an odd number')

    @property
    def match_winner(self) -> int | None:
        return self._match_winner

    @property
    def wins_needed(self):
        return self._best_of // 2 + 1

    def determine_game_winner(self) -> int | None:
        """Returns None if game is not over;
        else -1 if a draw, 0 for player #0, 1 for player #1, updates gs.is_game_over"""
        zero_life = [idx for idx, life in enumerate(self.gs.life) if life <= 0]
        ten_poison = [idx for idx, poison in enumerate(self.gs.poison_counters) if poison >= 10]

        losers = tuple(set(zero_life + ten_poison))
        if not losers:
            return None
        if len(losers) > 1:
            self._winners.append(-1)
            self.is_game_over = True
            print('The game ends in a draw')
            return -1
        else:
            winner = flip(losers[0])
            self._winners.append(winner)
            self.is_game_over = True
            print(f'Player #{winner} wins the game')
            print(f'Player #0 has {self._winners.count(0)} win(s); Player #1 has {self._winners.count(1)} win(s)')
            return winner

    def determine_match_winner(self) -> int | None:
        """Returns None if match is not over;
        else -1 if a draw, 0 for player #0, 1 for player #1, updates gs.is_match_over"""
        c = Counter(self._winners)
        if len(self._winners) == self._best_of:
            winner = 0 if c[0] > c[1] else 1 if c[1] > c[0] else -1
            self.is_match_over = True
            print(f'The match is a draw') if winner == -1 else print(f'Player #{winner} wins the match')
            return winner

        for idx, wins in c.items():
            if wins >= self.wins_needed:
                self._match_winner = idx
                self.is_match_over = True
                print(f'Player #{idx} wins the match')
                return idx

        return None

    def concede(self, conceder_idx: int) -> int:
        """Appends winner to self._winners, sets gs.is_game_over, calls determine_match_winner(), returns game winner"""
        winner = flip(conceder_idx)
        self._winners.append(winner)
        self.is_game_over = True
        print(f'Player #{winner} wins the game')
        print(f'Player #0 has {self._winners.count(0)} win(s); Player #1 has {self._winners.count(1)} win(s)')
        self.determine_match_winner()
        return winner
