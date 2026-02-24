from __future__ import annotations
from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from models.game_card import GameCard
    from models.choice_actions_all import TargetChoiceAction, MultiTargetChoice

from models.actions.base import Action

@dataclass
class AddTargetAction(Action):
    choice: TargetChoiceAction | MultiTargetChoice
    card: GameCard

    def play(self):
        self.choice.selected_targets.append(self.card)

@dataclass
class FinishTargetsAction(Action):
    choice: TargetChoiceAction | MultiTargetChoice

    def play(self):
        gs = self.choice.gs
        eff = self.choice.eff_spec.effect
        source = self.choice.source
        targets = list(self.choice.selected_targets)

        if gs.pending_choice:
            gs.pending_choice = None
        if gs.action_stack.actions:
            gs.action_stack.pop()

        if not targets:
            eff.resolve(gs, source, None)
        elif len(targets) == 1:
            eff.resolve(gs, source, targets[0])
        else:
            for t in targets:
                eff.resolve(gs, source, t)
