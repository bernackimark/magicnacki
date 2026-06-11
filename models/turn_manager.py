from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from models.game_card.game_card import GameCard
    from game_state import GameState

from models.utils import flip
from models.phase_manager import Phase

@dataclass(frozen=True)
class Turn:
    turn_number: int
    in_turn_player_id: int

class TurnManager:
    def __init__(self, player_cnt: int, starting_player_idx: int):
        self._player_cnt = player_cnt
        self.player_turn_idx = starting_player_idx
        self.most_recent_turn_started: dict[int, int] = {p_idx: 1 if p_idx == self.player_turn_idx else 0
                                                         for p_idx in range(self._player_cnt)}
        self._turn_number: int = 1
        self.turns: list[Turn] = [Turn(1, starting_player_idx)]
        self.has_played_land: bool = False
        self.cards_that_died: list[GameCard] = []
        self.untap_decisions_made: set[str] = set()

    @property
    def turn_number(self) -> int:
        return self._turn_number

    def create_new_turn(self, gs: GameState, does_turn_pass_to_opp: bool = True) -> None:
        """Increment turn_number; if the turn passes to the opponent (True ex time-walk, etc.);
        updates p_idx_most_recent_turn_started, which is critical for summoning sickness"""
        self._turn_number += 1
        if does_turn_pass_to_opp:
            self.player_turn_idx = flip(self.player_turn_idx)
        self.turns.append(Turn(self.turn_number, self.player_turn_idx))
        gs.action_on_idx = self.player_turn_idx
        self.most_recent_turn_started[self.player_turn_idx] = self._turn_number
        self.has_played_land = False
        self.cards_that_died.clear()
        self.untap_decisions_made.clear()
        gs.phase_mgr.set_phase(Phase.UNTAP, gs)

    def get_players_last_turn_num(self, player_id: int) -> int | None:
        for turn_num, p_idx in self.turns[::-1]:
            if turn_num == self.turn_number:
                continue
            if p_idx == player_id:
                return turn_num
