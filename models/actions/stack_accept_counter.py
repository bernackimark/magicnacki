from __future__ import annotations
from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from models.ability_pipeline import AbilityPipeline
    from models.actions.cast import CastPermanentAction

from models.actions.base import Action


@dataclass
class AcceptAction(Action):
    def __repr__(self) -> str:
        return f"Accept {self.gs.action_stack.last_action}"

    def play(self) -> None:
        last_action: CastPermanentAction | AbilityPipeline = self.gs.action_stack.last_action
        if last_action is None:
            raise RuntimeError("Nothing on the stack.")

        last_action.play()

        # --- reset action stack and current actor ---
        self.gs.action_on_idx = self.gs.action_stack.first_actor_idx  # action returns to the first actor
        self.gs.action_stack.clear_()
