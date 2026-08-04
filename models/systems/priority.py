from __future__ import annotations
from typing import TYPE_CHECKING

from models.utils import flip

if TYPE_CHECKING:
    from game_state import GameState

class PriorityManager:
    def __init__(self, gs: GameState):
        self._gs = gs
        self.players_passed: set[int] = set()

    def pass_priority(self, player_idx: int):
        self.players_passed.add(player_idx)

        # Give priority to the opponent
        self._gs.action_on_idx = flip(player_idx)

        # Opponent hasn't passed yet
        if len(self.players_passed) < 2:
            return

        # Everyone passed
        self.players_passed.clear()

        if self._gs.action_stack.actions:
            self.resolve_top_of_stack()
        # else:
        #     self._gs.phase_mgr.advance()  # commenting this suggestion for now. may already get handled elsewhere

    def new_stack_item_added(self):
        """Called whenever something is pushed onto the stack."""
        self.players_passed.clear()
        self._gs.action_on_idx = flip(self._gs.action_on_idx)

    def resolve_top_of_stack(self):
        while self._gs.action_stack.actions:
            action = self._gs.action_stack.last_action
            self._gs.action_stack.pop()
            action.play()

            # If somebody added something to the stack while resolving,
            # stop and restart the priority cycle.
            if self.players_passed:
                return

        self._gs.action_on_idx = self._gs.player_turn_idx
