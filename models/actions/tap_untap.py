from __future__ import annotations
from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from models.game_card import GameCard
    from game_state import GameState

from models.actions.base import Action

@dataclass
class TapCard(Action):
    card: GameCard

    def __repr__(self) -> str:
        return f"Tap {self.card.__repr__()}"

    def play(self) -> None:
        self.card.tap(self.gs)


@dataclass
class UntapCard(Action):
    card: GameCard

    def __repr__(self) -> str:
        return f"Untap {self.card.__repr__()}"

    def play(self) -> None:
        self.card.untap(self.gs)


class UntapCardStackPop(Action):
    def __init__(self, p_id: int, gs: GameState, s: GameCard):
        super().__init__(p_id, gs)
        self.source = s

    def __repr__(self):
        return f'Untap {self.source}'

    def play(self):
        # self.gs.apply_untap_effects(self.source)  # not clear why this wasn't working
        self.source.untap(self.gs)
        self.gs.action_stack.pop()


class LeaveTapped(Action):
    def __init__(self, p_id: int, gs: GameState, s: GameCard):
        super().__init__(p_id, gs)
        self.card = s

    def __repr__(self):
        return f'Leave {self.card} tapped'

    def play(self):
        self.gs.action_stack.pop()
