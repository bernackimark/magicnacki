from dataclasses import dataclass

from models.actions.base import Action
from phase_fsm import Phase
from models.utils import flip


@dataclass
class MoveToEndStep(Action):

    def __repr__(self) -> str:
        return "Move to End Step"

    def play(self) -> None:
        self.gs.phase_mgr.set_phase(Phase.END_STEP, self.gs)


@dataclass
class PassTheTurn(Action):
    pass_turn_to_opp: bool = True

    def __repr__(self) -> str:
        return "Pass the Turn"

    def play(self) -> None:
        self.gs.cards_that_died_this_turn.clear()
        self.gs.turn_mgr.create_new_turn(self.gs, self.pass_turn_to_opp)
