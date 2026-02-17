from __future__ import annotations
from dataclasses import dataclass
from typing import TYPE_CHECKING

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
        if len(self.gs.action_stack):
            self.gs.action_stack.pop()


@dataclass
class DiscardCard(Action):
    cards: GameCard | list[GameCard]

    def __repr__(self) -> str:
        if not isinstance(self.cards, list):
            return f"Discard {self.cards} to graveyard"
        else:
            return f"Discard {', '.join([c.__repr__() for c in self.cards])} to graveyard"

    def play(self) -> None:
        if not isinstance(self.cards, list):
            self.cards = [self.cards]
        for c in self.cards:
            print(f"Discarding {c} from player {self.player_idx}'s hand")
            self.gs.discard(c)
        if self.gs.pending_choice:
            self.gs.pending_choice = None
        elif len(self.gs.action_stack):
            self.gs.action_stack.pop()

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
