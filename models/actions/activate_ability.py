from dataclasses import dataclass

from models.actions.base import Action
from models.effects.base import ActivatedAbility
from models.events_all import StateBasedEvent
from models.game_card import GameCard


@dataclass
class ActivateAbility(Action):
    ability: ActivatedAbility
    target: GameCard | list[GameCard] | tuple[int] | int | None = None
    x_value: int | None = None

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
        if self.x_value is not None:
            target_text += f", X={self.x_value}"
        return (f"{self.ability.source}: {{{self.x_value or ''}{self.ability.eff_spec.cost}}}: "
                f"{self.ability.eff_spec.text}{target_text}")

    def play(self) -> None:
        if self.x_value is not None:
            x_cost = self.ability.eff_spec.cost[:].replace('X', str(self.x_value))
            self.gs.mana_pools[self.player_idx].pay(x_cost)
            self.ability.source.variable_x = self.x_value
        else:
            self.gs.mana_pools[self.player_idx].pay(self.ability.eff_spec.cost)
            if self.ability.eff_spec.extra_costs:
                for extra_cost in self.ability.eff_spec.extra_costs:
                    extra_cost.pay(self.gs, self.ability.source)
        if 'T' in self.ability.eff_spec.cost:
            self.gs.tap_card(self.ability.source)
        self.gs.action_stack.push(self, self.gs)
        self.gs.emit(StateBasedEvent())

