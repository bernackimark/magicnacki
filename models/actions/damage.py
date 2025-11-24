from dataclasses import dataclass

from models.actions.base import Action
from models.game_card import GameCard
from models.modifiers import PTTemp


@dataclass
class DamageCreature(Action):
    card: GameCard
    target: GameCard
    amt: int

    def __repr__(self) -> str:
        return f"{self.card.props.name} deals {self.amt} to {self.target}"

    def play(self) -> None:
        self.target.modifiers.temps.append(PTTemp(0, -self.amt))
        if self.target.toughness <= 0:
            self.gs.send_to_graveyard_from_play(self.target)


@dataclass
class DamagePlayer(Action):
    card: GameCard
    target_player: int
    amt: int

    def __repr__(self) -> str:
        return f"{self.card.props.name} deals {self.amt} to player #{self.target_player}"

    def play(self) -> None:
        self.gs.decrement_life(self.target_player, self.amt, self.card)
