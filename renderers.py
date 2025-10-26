from abc import ABC, abstractmethod
from dataclasses import dataclass

from game_state import GameState
from players import Player


@dataclass
class Renderer(ABC):
    @staticmethod
    @abstractmethod
    def render(gs, players):
        raise NotImplementedError


@dataclass
class ConsoleRenderer(Renderer):
    @staticmethod
    def render(gs: GameState, players: list[Player]):
        p_idx = gs.player_turn_idx
        action_idx = gs.action_on_idx
        opp_idx = 1 if gs.action_on_idx == 0 else 0
        print()
        print(f"{players[p_idx].name}'s turn; {players[action_idx].name}'s action; current phase: {gs.phase}")
        print(f"Combats: {gs.combats}")
        print(f"Their board: {gs.boards[opp_idx].cards}")
        print(f"Board: {gs.boards[action_idx].cards}")
        print(f"Hand: {gs.hands[action_idx].cards}")
        print()
