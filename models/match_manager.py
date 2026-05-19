from __future__ import annotations
from collections import Counter
import random
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from models.game_card.card import Card

from models.deck import Deck
from models.game_card import GameCard
from game_state import GameState
from models.utils import flip


class MatchManager:
    """Accepts Decks (list of Cards), rules, tokens, etc.; converts Cards to GameCards; creates GameState object;
    stores game winners and determines if there is a match winner;
    could be extended for more rules; first to act can be provided else will assign randomly"""
    def __init__(self, player_cnt: int, rules: dict, decks: list[Deck], tokens: dict[str: Card],
                 first_to_act: int | None = None):
        self.player_cnt = player_cnt
        self.rules = rules
        self.decks = decks
        self.deck_game_cards: list[list[GameCard]] = self._create_game_cards()
        self.tokens = tokens
        self.is_match_over: bool = False
        self._best_of = self.rules['best_of']
        self._winners: list[int] = []  # -1 for a draw, 0 for player 0, 1 for player 1
        self._match_winner: int | None = None
        self.first_to_act = first_to_act if first_to_act is not None else self.set_first_to_act()

        if not self._best_of % 2:
            raise ValueError('Best Of must be an odd number')

    @property
    def match_winner(self) -> int | None:
        return self._match_winner

    @property
    def _wins_needed(self):
        return self._best_of // 2 + 1

    def set_first_to_act(self) -> None:
        """If this is the first game, return random 0 or 1; if last game was a draw, return the previous first_to_act;
        if last game was won/lost, return the loser"""
        if self.first_to_act is None:
            self.first_to_act = random.randint(0, 1)
        elif len(self._winners) and self._winners[-1] in (0, 1):
            self.first_to_act = flip(self._winners[-1])

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
            if wins >= self._wins_needed:
                self._match_winner = idx
                self.is_match_over = True
                print(f'Player #{idx} wins the match')
                return idx

        return None

    def create_game_state(self) -> GameState:
        self.set_first_to_act()
        return GameState(self.player_cnt, self.first_to_act, self.rules, self.deck_game_cards, self.tokens)

    def _create_game_cards(self) -> list[list[GameCard]]:
        return [[GameCard(c, i) for c in deck.main] for i, deck in enumerate(self.decks)]
