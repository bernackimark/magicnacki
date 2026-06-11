from dataclasses import dataclass

from models.actions.base import Action
from models.combat import Combat
from models.game_card.game_card import GameCard
from models.utils import flip
from models.phase_manager import Phase

@dataclass
class CreatureAttack(Action):
    card: GameCard

    def __repr__(self) -> str:
        return f"Add {self.card.__repr__()} to attack"

    def play(self) -> None:
        if 'Vigilance' not in self.card.keyword_abilities:
            self.card.tap()
        self.gs.combat_mgr.combats.append(Combat(self.gs, self.card))

@dataclass
class BeginCombat(Action):

    def __repr__(self) -> str:
        return "Begin Combat"

    def play(self) -> None:
        self.gs.phase_mgr.set_phase(Phase.DECLARE_ATTACKERS, self.gs)

@dataclass
class FinishDeclaringAttackers(Action):

    def __repr__(self) -> str:
        return "Done Declaring Attackers"

    def play(self) -> None:
        self.gs.phase_mgr.set_phase(Phase.DECLARE_BLOCKERS, self.gs)
        self.gs.action_on_idx = flip(self.gs.action_on_idx)

@dataclass
class AssignBlocker(Action):
    blocker: GameCard
    attacker: GameCard

    def __repr__(self) -> str:
        return f"Block {self.attacker} with {self.blocker}"

    def play(self) -> None:
        for com in self.gs.combat_mgr.combats:
            if com.attacker == self.attacker:
                com.blockers.append(self.blocker)

@dataclass
class FinishBlocking(Action):

    def __repr__(self) -> str:
        return f"Finish Blocks"

    def play(self) -> None:
        self.gs.phase_mgr.set_phase(Phase.PRE_COMBAT_DAMAGE, self.gs)

@dataclass
class AssignCombatDamage(Action):
    def __repr__(self):
        return "Assign Combat Damage"

    def play(self) -> None:
        self.gs.phase_mgr.set_phase(Phase.ASSIGN_COMBAT_DAMAGE, self.gs)
