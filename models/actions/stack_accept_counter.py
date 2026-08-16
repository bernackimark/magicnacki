from __future__ import annotations
from dataclasses import dataclass
from typing import TYPE_CHECKING

from models.constants import Zone

if TYPE_CHECKING:
    from models.action_stack import StackItemType
    from game_state import GameState

from models.actions.base import Action


@dataclass
class PassPriority(Action):
    def __repr__(self) -> str:
        return f"Pass priority: {self.gs.action_stack.last_action}"

    def play(self) -> None:
        self.gs.priority_mgr.pass_priority(self.player_idx)

@dataclass
class CounterSpellAction(Action):
    def __init__(self, p_id: int, gs: GameState, target_spell: StackItemType):
        super().__init__(p_id, gs)
        self.target_spell = target_spell

    def __repr__(self):
        return f"Counter {self.target_spell}"

    def play(self) -> None:
        self.gs.action_stack.remove(self.target_spell)
        if self.gs.pending_choice:
            self.gs.pending_choice = None
        source = self.target_spell.source
        self.gs.pile_mgr.move_card(source, Zone.GRAVEYARD, cause='fizzled', emit_zone_event=False)
