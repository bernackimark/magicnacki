from __future__ import annotations
from typing import TYPE_CHECKING


if TYPE_CHECKING:
    from models.game_card.game_card import GameCard
    from game_state import GameState

from models.utils import flip
from models.phase_manager import Phase

class TurnManager:
    def __init__(self, player_cnt: int, starting_player_idx: int):
        self._player_cnt = player_cnt
        self.player_turn_idx = starting_player_idx
        self.most_recent_turn_started: dict[int, int] = {p_idx: 1 if p_idx == self.player_turn_idx else 0
                                                         for p_idx in range(self._player_cnt)}
        self._turn_number: int = 1
        self.has_played_land: bool = False
        self.cards_that_died: list[GameCard] = []

    @property
    def turn_number(self) -> int:
        return self._turn_number

    def create_new_turn(self, gs: GameState, does_turn_pass_to_opp: bool = True) -> None:
        """Increment turn_number; if the turn passes to the opponent (True ex time-walk, etc.);
        updates p_idx_most_recent_turn_started, which is critical for summoning sickness"""
        self._turn_number += 1
        if does_turn_pass_to_opp:
            self.player_turn_idx = flip(self.player_turn_idx)
        gs.action_on_idx = self.player_turn_idx
        self.most_recent_turn_started[self.player_turn_idx] = self._turn_number
        self.has_played_land = False
        self.cards_that_died.clear()
        gs.phase_mgr.set_phase(Phase.UNTAP, gs)

