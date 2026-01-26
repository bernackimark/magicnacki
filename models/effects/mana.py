from __future__ import annotations
from typing import TYPE_CHECKING

from constants import COLOR_LETTERS_W_COLORLESS
from utils import flip
from .base import Effect
from ..counter_tokens import PLUS_ONE, VITALITY, POISON
from ..damage import DamageEvent

if TYPE_CHECKING:
    from ..game_card import GameCard
    from game_state import GameState

class AddMana(Effect):
    def __init__(self, color: str, cnt: int = 1):
        self.color = color
        self.cnt = cnt

        if color not in COLOR_LETTERS_W_COLORLESS:
            raise ValueError(f"Color must be {COLOR_LETTERS_W_COLORLESS}")

    def resolve(self, gs: GameState, source: GameCard, target: GameCard = None):
        gs.mana_pools[source.orig_owner_id].add_floating(self.color, self.cnt)

