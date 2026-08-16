from __future__ import annotations
from dataclasses import dataclass
from typing import TYPE_CHECKING

from models.constants import KW

if TYPE_CHECKING:
    from models.game_card.game_card import GameCard

from models.actions.base import Action


@dataclass
class CreatureAttack(Action):
    card: GameCard

    def __repr__(self) -> str:
        return f"Add {self.card.__repr__()} to attack"

    def play(self) -> None:
        if KW.VIGILANCE not in self.card.keyword_abilities:
            self.card.tap()
        self.gs.combat_mgr.create_combat(self.card)


@dataclass
class AssignBlocker(Action):
    blocker: GameCard
    attacker: GameCard

    def __repr__(self) -> str:
        return f"Block {self.attacker} with {self.blocker}"

    def play(self) -> None:
        com = self.gs.combat_mgr.get_combat(self.attacker)
        com.blockers.append(self.blocker)

