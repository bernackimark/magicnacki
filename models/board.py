from dataclasses import dataclass, field
import re

from models.game_card import GameCard
from constants import COLOR_LETTERS, BASIC_LANDS


@dataclass
class Board:
    player_idx: int
    _cards: list[GameCard] = field(default_factory=list)

    @property
    def cards(self) -> list[GameCard]:
        return self._cards

    @property
    def available_blockers(self) -> list[GameCard]:
        return [c for c in self.cards if c.can_block and not c.is_tapped]

    def play_to_board(self, c: GameCard):
        self._cards.append(c)
        self._cards.sort(key=lambda card: (card.props.is_land, card.props.is_creature))

    def remove_from_board(self, c: GameCard):
        self._cards.remove(c)
        self._cards.sort(key=lambda c: (c.props.is_land, c.props.is_creature))
