from __future__ import annotations
from dataclasses import dataclass
from typing import TYPE_CHECKING

from models.constants import Target

if TYPE_CHECKING:
    from models.choice_actions_all import MultiTargetChoice

from models.actions.base import Action

@dataclass
class AddTargetAction(Action):
    choice: MultiTargetChoice
    target: Target

    def __repr__(self):
        return f'{self.choice.source}: add target: {self.target}'

    def play(self):
        self.choice.selected_targets.append(self.target)

        target_spec = self.choice.eff_spec.target_spec
        selected = len(self.choice.selected_targets)

        # If we've reached max targets, auto-finish
        if target_spec.max_cnt is not None and selected >= target_spec.max_cnt:
            finish = FinishTargetsAction(self.player_idx, self.gs, self.choice)
            finish.play()
            return

@dataclass
class FinishTargetsAction(Action):
    choice: MultiTargetChoice

    def __repr__(self):
        return 'Finish Adding Targets'

    def play(self):
        gs = self.choice.gs
        source = self.choice.source
        targets = list(self.choice.selected_targets)

        if gs.pending_choice:
            gs.pending_choice = None
        if gs.action_stack.actions:
            gs.action_stack.pop()

        # Send spell back into normal casting pipeline
        from models.actions.cast import CastToTargetAddToStack
        if not targets:
            target = None
        elif len(targets) == 1:
            target = targets[0]
        else:
            target = targets

        CastToTargetAddToStack(self.player_idx, gs, source, target, self.choice.eff_spec).play()
