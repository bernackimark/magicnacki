from dataclasses import dataclass, field
from enum import Enum

from models.game_card.game_card import GameCard


@dataclass
class Hand:
    cards: list[GameCard] = field(default_factory=list)
