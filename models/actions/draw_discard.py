from __future__ import annotations
from dataclasses import dataclass
from typing import TYPE_CHECKING, Optional

if TYPE_CHECKING:
    from ..game_card import GameCard

from models.actions.base import Action
from phase_fsm import Phase


@dataclass
class DrawCard(Action):
    def __repr__(self) -> str:
        return 'Draw a Card'

    def play(self) -> None:
        self.gs.draw(self.player_idx)
        self.gs.phase = Phase.CAST


@dataclass
class DiscardCard(Action):
    card: GameCard

    def __repr__(self) -> str:
        return f"Discard {self.card} to graveyard"

    def play(self) -> None:
        print(f"Discarding {self.card} from player {self.player_idx}'s hand")
        self.gs.discard(self.card)

@dataclass
class MoveToDrawPhase(Action):

    def __repr__(self) -> str:
        return "Move to Draw Phase"

    def play(self) -> None:
        self.gs.phase = Phase.DRAW

@dataclass
class SkipDrawPhase(Action):

    def __repr__(self) -> str:
        return "Skip Draw Phase"

    def play(self) -> None:
        self.gs.phase = Phase.CAST
