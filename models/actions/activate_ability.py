from dataclasses import dataclass

from models.actions.base import Action
from models.activated_ability import ActivatedAbility
from models.board import casting_weight
from models.game_card import GameCard


@dataclass
class ActivateAbility(Action):
    ability: ActivatedAbility
    target: GameCard | None = None

    def __repr__(self) -> str:
        target_text = ''
        if isinstance(self.target, list) and self.target and isinstance(self.target[0], GameCard):
            target_text = f", targeting {', '.join([_ for _ in self.target])}"
        elif isinstance(self.target, GameCard):
            target_text = ', targeting ' + self.target.props.name
        elif (isinstance(self.target, list) or isinstance(self.target, tuple)) and self.target and isinstance(self.target[0], int):
            target_text = ', targeting Player #' + '& '.join([_ for _ in self.target])
        elif isinstance(self.target, int):
            target_text = f', targeting Player #{self.target}'
        return f"Activate Ability: {self.ability.card}{target_text}"

    def play(self) -> None:
        # Pay tap cost
        if self.ability.cost_tap:
            self.ability.card.tap(self.gs)

        # Pay mana cost
        if self.ability.cost_mana:
            self.gs.boards[self.ability.card.orig_owner_id].pay_casting_weight(casting_weight(self.ability.cost_mana), self.gs)

        # Execute effect
        # TODO: for the sake of testing, perms are being auto-cast, instead of being added to the stack
        self.ability.effect(self.gs, self.ability.card, self.target)
