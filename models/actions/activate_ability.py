from dataclasses import dataclass

from models.actions.base import Action
from models.activated_ability import ActivatedAbility
from models.game_card import GameCard


@dataclass
class ActivateAbility(Action):
    ability: ActivatedAbility
    target: GameCard | list[GameCard] | tuple[int] | int | None = None

    def __repr__(self) -> str:
        if self.ability.text:
            target_text = f' {self.ability.text}'
        elif isinstance(self.target, list) and self.target and isinstance(self.target[0], GameCard):
            target_text = f", targeting {', '.join([_ for _ in self.target])}"
        elif isinstance(self.target, GameCard):
            target_text = ', targeting ' + self.target.props.name
        elif (isinstance(self.target, list) or isinstance(self.target, tuple)) and self.target and isinstance(self.target[0], int):
            target_text = ', targeting Player #' + '& '.join([_ for _ in self.target])
        elif isinstance(self.target, int):
            target_text = f', targeting Player #{self.target}'
        else:
            target_text = ''
        return f"Activate Ability: {self.ability.card}{target_text}"

    def play(self) -> None:
        self.ability.pay_costs(self.gs)

        # Execute effect
        # TODO: for the sake of testing, perms are being auto-cast, instead of being added to the stack
        self.ability.effect(self.gs, self.ability.card, self.target)
