from __future__ import annotations
from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from models.game_card.game_card import GameCard
    from models.effects.base import EffSpec, ActivatedAbility

from models.actions.base import Action
from models.events_all import StateBasedEvent


@dataclass
class ActivateAbility(Action):
    """Action for acitvating an activated ability"""
    # candidate for a re-name
    aa: ActivatedAbility
    target: GameCard | list[GameCard] | tuple[int] | int | None = None
    x_value: int | None = None

    def __repr__(self) -> str:
        from models.target import create_target_text
        target_text = create_target_text(self.target)
        if self.x_value is not None:
            target_text += f", X={self.x_value}"
        return (f"{self.card}: {{{self.x_value or ''}{self.spec.cost}}}: "
                f"{self.spec.text}{target_text}")

    @property
    def card(self) -> GameCard:
        return self.aa.source

    @property
    def spec(self) -> EffSpec:
        return self.aa.eff_spec

    def play(self) -> None:
        if self.x_value is not None:
            x_cost = self.spec.cost[:].replace('X', str(self.x_value))
            self.gs.mana_pools[self.player_idx].pay(x_cost)
            self.card.extras['x'] = self.x_value
        else:
            self.gs.mana_pools[self.player_idx].pay(self.spec.cost)
            if self.spec.extra_costs:
                for extra_cost in self.spec.extra_costs:
                    extra_cost.pay(self.gs, self.card)
        if 'T' in self.spec.cost:
            self.card.tap()
        self.aa.activations_this_turn += 1
        self.gs.action_stack.push(self, self.gs)
        self.gs.event_mgr.emit(StateBasedEvent(), self.gs)

@dataclass
class BeginAbilityActivationAction(Action):
    """Handles pre-activation choices: X-values and target selection."""
    aa: ActivatedAbility

    def __repr__(self):
        return f'{self.spec.cost}: {self.spec.effect}'

    @property
    def card(self) -> GameCard:
        return self.aa.source

    @property
    def spec(self) -> EffSpec:
        return self.aa.eff_spec

    def play(self):
        if self.gs.action_stack.actions:
            self.gs.action_stack.pop()

        if self.spec.max_x_func:
            from models.choice_actions_all import XValueChoice

            # TODO: Feed XValueChoice options for X based on casting cost & available mana
            #  this would handle banshee & candelabra-of-tawnos

            self.gs.pending_choice = XValueChoice(self.card.owner_id, self.gs, self.card, self.spec, self.aa)
            return

        from models.choice_actions_all import MultiTargetChoice
        self.gs.pending_choice = MultiTargetChoice(self.card.owner_id, self.gs, self.card, self.spec)

        # # --- No X or targets → simple activation
        # self.gs.action_stack.append(ActivateAbility(self.player_idx, self.gs, self.ability))
