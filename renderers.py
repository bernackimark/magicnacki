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
        print(f"{players[p_idx].name}'s turn; {players[action_idx].name}'s action; current phase: {gs.phase_mgr.phase.name}; current life: {gs.life}")
        print(f"Their board: {[c for c in gs.boards[opp_idx] if not c.props.is_aura]}")
        print(f"Combats: {gs.combats}")
        print(f"Board: {[c for c in gs.boards[action_idx] if not c.props.is_aura]}")
        reprs = []
        for c in gs.hands[action_idx].cards:
            if c.props.is_creature:
                repr_ = f"{c.props.name} ({c.casting_cost}) ({c.base_pt[0]}/{c.base_pt[1]})"
            elif c.casting_cost:
                repr_ = f"{c.props.name} ({c.casting_cost})"
            else:
                repr_ = c.props.name
            reprs.append(repr_)
        print(f"Hand: {reprs}")
        print()
