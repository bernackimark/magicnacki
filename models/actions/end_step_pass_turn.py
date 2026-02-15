from dataclasses import dataclass

from models.actions.base import Action
from models.turn import Turn
from phase_fsm import Phase
from models.utils import flip


@dataclass
class MoveToEndStep(Action):

    def __repr__(self) -> str:
        return "Move to End Step"

    def play(self) -> None:
        self.gs.phase = Phase.END_STEP


@dataclass
class PassTheTurn(Action):

    def __repr__(self) -> str:
        return "Pass the Turn"

    def play(self) -> None:
        self.gs.cards_that_died_this_turn.clear()
        self.gs.player_turn_idx = flip(self.gs.player_turn_idx)
        self.gs.action_on_idx = self.gs.player_turn_idx
        self.gs.turn = Turn(self.gs.player_turn_idx, flip(self.gs.player_turn_idx))
        self.gs.turn_number += 1
        self.gs.phase = Phase.UNTAP
