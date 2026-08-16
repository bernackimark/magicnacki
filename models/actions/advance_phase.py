from __future__ import annotations
from dataclasses import dataclass

from models.actions.base import Action
from models.systems.phase import Phase
from models.utils import flip


@dataclass
class BeginCombat(Action):

    def __repr__(self) -> str:
        return "Begin Combat"

    def play(self) -> None:
        self.gs.phase_mgr.set_phase(Phase.DECLARE_ATTACKERS)


@dataclass
class FinishDeclaringAttackers(Action):

    def __repr__(self) -> str:
        return "Done Declaring Attackers"

    def play(self) -> None:
        self.gs.phase_mgr.set_phase(Phase.DECLARE_BLOCKERS)
        self.gs.action_on_idx = flip(self.gs.action_on_idx)


@dataclass
class FinishBlocking(Action):

    def __repr__(self) -> str:
        return f"Finish Blocks"

    def play(self) -> None:
        self.gs.phase_mgr.set_phase(Phase.PRE_COMBAT_DAMAGE)


@dataclass
class MoveToDrawPhase(Action):

    def __repr__(self) -> str:
        return "Move to Draw Phase"

    def play(self) -> None:
        self.gs.phase_mgr.set_phase(Phase.DRAW)
        self.finish()


@dataclass
class MoveToEndStep(Action):

    def __repr__(self) -> str:
        return "Move to End Step"

    def play(self) -> None:
        self.gs.phase_mgr.set_phase(Phase.END_STEP)
        self.finish()


@dataclass
class PassTheTurn(Action):
    pass_turn_to_opp: bool = True

    def __repr__(self) -> str:
        return "Pass the Turn"

    def play(self) -> None:
        self.gs.turn_mgr.create_new_turn(self.gs, self.pass_turn_to_opp)
