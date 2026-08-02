from __future__ import annotations
from dataclasses import dataclass
from typing import TYPE_CHECKING

from models.zone import Zone

if TYPE_CHECKING:
    from models.actions.ability_pipeline import AbilityPipeline
    from models.actions.ability_pipeline_support import AbilityAction
    from models.actions.cast import CastPermanentAction
    from game_state import GameState

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
        self.gs.action_stack.remove(last_action)

@dataclass
class CounterSpellAction(Action):
    def __init__(self, p_id: int, gs: GameState, target_spell: AbilityAction | CastPermanentAction):
        super().__init__(p_id, gs)
        self.target_spell = target_spell

    def __repr__(self):
        return f"Counter {self.target_spell}"

    def play(self) -> None:
        from models.actions.cast import CastPermanentAction
        self.gs.action_stack.remove(self.target_spell)
        if self.gs.pending_choice:
            self.gs.pending_choice = None
        source = self.target_spell.source if isinstance(self.target_spell, CastPermanentAction) else self.target_spell.pipeline.source
        self.gs.pile_mgr.move_card(source, Zone.GRAVEYARD, cause='fizzled', emit_zone_event=False)
