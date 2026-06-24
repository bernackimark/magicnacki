from __future__ import annotations
from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from models.game_card.game_card import GameCard

from models.actions.base import Action
from models.effects.base import ActivatedAbility
from models.events_all import StateBasedEvent


@dataclass
class ActivateAbility(Action):
    ability: ActivatedAbility
    target: GameCard | list[GameCard] | tuple[int] | int | None = None
    x_value: int | None = None

    def __repr__(self) -> str:
        target_text = self._parse_target_text()
        if self.x_value is not None:
            target_text += f", X={self.x_value}"
        return (f"{self.ability.source}: {{{self.x_value or ''}{self.ability.eff_spec.cost}}}: "
                f"{self.ability.eff_spec.text}{target_text}")

    def _parse_target_text(self) -> str:
        """0 -> ', targeting Player #0' ... [1, c1] -> ', targeting Player #1, Air Elemental'
        (0, 1) -> ', targeting Player #0, Player #1' ... [c1, c2] -> , 'targeting Air Elemental, Savannah Lions'"""
        from models.game_card.game_card import GameCard
        if isinstance(self.target, int):
            return f', targeting Player #{self.target}'
        if isinstance(self.target, GameCard):
            return ', targeting ' + self.target.props.name
        begin_text = ', targeting'
        target_texts = []
        for t in self.target:
            target_text = t.props.name if isinstance(t, GameCard) else f'Player #{t}'
            target_texts.append(target_text)
        return f"{begin_text} {', '.join(target_texts)}"

    def play(self) -> None:
        if self.x_value is not None:
            x_cost = self.ability.eff_spec.cost[:].replace('X', str(self.x_value))
            self.gs.mana_pools[self.player_idx].pay(x_cost)
            self.ability.source.extras['x'] = self.x_value
        else:
            self.gs.mana_pools[self.player_idx].pay(self.ability.eff_spec.cost)
            if self.ability.eff_spec.extra_costs:
                for extra_cost in self.ability.eff_spec.extra_costs:
                    extra_cost.pay(self.gs, self.ability.source)
        if 'T' in self.ability.eff_spec.cost:
            self.ability.source.tap()
        self.gs.action_stack.push(self, self.gs)
        self.gs.event_mgr.emit(StateBasedEvent(), self.gs)

@dataclass
class BeginAbilityActivationAction(Action):
    """Handles pre-activation choices: X-values and target selection."""
    ability: ActivatedAbility

    def __repr__(self):
        return f'{self.ability.eff_spec.cost}: {self.ability.eff_spec.effect}'

    def play(self):
        if self.gs.action_stack.actions:
            self.gs.action_stack.pop()

        a = self.ability
        if a.eff_spec.max_x_func:
            from models.choice_actions_all import XValueChoice
            self.gs.pending_choice = XValueChoice(a.source.owner_id, self.gs, a.source, a.eff_spec, a)
            return

        from models.choice_actions_all import MultiTargetChoice
        self.gs.pending_choice = MultiTargetChoice(a.source.owner_id, self.gs, a.source, a.eff_spec)

        # # --- No X or targets → simple activation
        # self.gs.action_stack.append(ActivateAbility(self.player_idx, self.gs, self.ability))
