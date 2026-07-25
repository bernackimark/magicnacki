from __future__ import annotations
from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from models.game_card.game_card import GameCard

from models.actions.base import Action
from models.systems.phase import Phase
from models.utils import flip

@dataclass
class CreatureAttack(Action):
    card: GameCard

    def __repr__(self) -> str:
        return f"Add {self.card.__repr__()} to attack"

    def play(self) -> None:
        if 'Vigilance' not in self.card.keyword_abilities:
            self.card.tap()
        self.gs.combat_mgr.create_combat(self.card)

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
class AssignBlocker(Action):
    blocker: GameCard
    attacker: GameCard

    def __repr__(self) -> str:
        return f"Block {self.attacker} with {self.blocker}"

    def play(self) -> None:
        com = self.gs.combat_mgr.get_combat(self.attacker)
        com.blockers.append(self.blocker)

@dataclass
class FinishBlocking(Action):

    def __repr__(self) -> str:
        return f"Finish Blocks"

    def play(self) -> None:
        self.gs.phase_mgr.set_phase(Phase.PRE_COMBAT_DAMAGE)
