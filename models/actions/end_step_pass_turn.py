from dataclasses import dataclass

from models.actions.base import Action
from models.systems.phase import Phase


@dataclass
class MoveToEndStep(Action):

    def __repr__(self) -> str:
        return "Move to End Step"

    def play(self) -> None:
        self.gs.phase_mgr.set_phase(Phase.END_STEP)


@dataclass
class PassTheTurn(Action):
    pass_turn_to_opp: bool = True

    def __repr__(self) -> str:
        return "Pass the Turn"

    def play(self) -> None:
        self.gs.turn_mgr.create_new_turn(self.gs, self.pass_turn_to_opp)
