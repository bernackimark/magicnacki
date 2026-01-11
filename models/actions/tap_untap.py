from dataclasses import dataclass

from models.actions.base import Action
from models.game_card import GameCard

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
        return f"Tap {self.card.__repr__()}"

    def play(self) -> None:
        self.card.untap(self.gs)
