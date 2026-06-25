from __future__ import annotations
from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from models.game_card.game_card import GameCard
    from models.effects.base import EffSpec

from models.actions.base import Action
from models.events_all import StateBasedEvent


@dataclass
class ActivateAbility(Action):
    card: GameCard
    eff_spec: EffSpec
    target: GameCard | list[GameCard] | tuple[int] | int | None = None
    x_value: int | None = None

    def __repr__(self) -> str:
        from models.target import create_target_text
        target_text = create_target_text(self.target)
        if self.x_value is not None:
            target_text += f", X={self.x_value}"
        return (f"{self.card}: {{{self.x_value or ''}{self.eff_spec.cost}}}: "
                f"{self.eff_spec.text}{target_text}")

    def play(self) -> None:
        if self.x_value is not None:
            x_cost = self.eff_spec.cost[:].replace('X', str(self.x_value))
            self.gs.mana_pools[self.player_idx].pay(x_cost)
            self.card.extras['x'] = self.x_value
        else:
            self.gs.mana_pools[self.player_idx].pay(self.eff_spec.cost)
            if self.eff_spec.extra_costs:
                for extra_cost in self.eff_spec.extra_costs:
                    extra_cost.pay(self.gs, self.card)
        if 'T' in self.eff_spec.cost:
            self.card.tap()
        self.gs.action_stack.push(self, self.gs)
        self.gs.event_mgr.emit(StateBasedEvent(), self.gs)

@dataclass
class BeginAbilityActivationAction(Action):
    """Handles pre-activation choices: X-values and target selection."""
    card: GameCard
    eff_spec: EffSpec

    def __repr__(self):
        return f'{self.eff_spec.cost}: {self.eff_spec.effect}'

    def play(self):
        if self.gs.action_stack.actions:
            self.gs.action_stack.pop()

        spec = self.eff_spec
        if spec.max_x_func:
            from models.choice_actions_all import XValueChoice
            self.gs.pending_choice = XValueChoice(self.card.owner_id, self.gs, self.card, spec, a)
            return

        from models.choice_actions_all import MultiTargetChoice
        self.gs.pending_choice = MultiTargetChoice(self.card.owner_id, self.gs, self.card, spec)

        # # --- No X or targets → simple activation
        # self.gs.action_stack.append(ActivateAbility(self.player_idx, self.gs, self.ability))
