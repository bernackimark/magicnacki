from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from game_state import GameState
    from models.game_card import GameCard

from models.effects.base import Effect
from utils import flip

# --- GENERICS ---
class SetColor(Effect):
    def __init__(self, color: str):
        self.color = color

    def resolve(self, gs: GameState, source: GameCard, target: GameCard = None):
        if target is None:
            raise ValueError(f'{source.props.name} needs a target')
        target.colors = self.color
