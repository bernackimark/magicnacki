from abc import ABC, abstractmethod
from dataclasses import dataclass

from game_state import GameState
from models.presentation_request import PresentationRequest
from players import Player


@dataclass
class Renderer(ABC):
    @staticmethod
    @abstractmethod
    def render(gs, players):
        raise NotImplementedError

    @staticmethod
    @abstractmethod
    def render_presentation_request(request: PresentationRequest):
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
        print(f"Their hand: {['*' if not c.is_face_up else c for c in gs.pile_mgr.hands[opp_idx]]}")
        print(f"Their board: {[c for c in gs.pile_mgr.boards[opp_idx] if not c.props.is_aura]}")
        print(f"Combats: {gs.combat_mgr.combats}")
        print(f"Board: {[c for c in gs.pile_mgr.boards[action_idx] if not c.props.is_aura]}")
        reprs = []
        for c in gs.pile_mgr.hands[action_idx]:
            if c.props.is_creature:
                repr_ = f"{c.props.name} ({c.casting_cost}) ({c.base_pt[0]}/{c.base_pt[1]})"
            elif c.casting_cost:
                repr_ = f"{c.props.name} ({c.casting_cost})"
            else:
                repr_ = c.props.name
            reprs.append(repr_)
        print(f"Hand: {reprs}")
        print()

    @staticmethod
    def render_presentation_request(req: PresentationRequest):
        if req.type_ == 'view_card':
            print("Viewing card:")
            for c in req.payload['cards']:
                print(c)
        if req.type_ == 'view_library':
            print("Viewing library:")
            for c in req.payload['cards']:
                print(c)
        if req.type_ == 'search_library':
            print("Choose a card:")
            for i, c in enumerate(req.payload['cards']):
                print(i, c)
        if req.type_ == 'declare':
            print("Declaration:")
            print(req.payload['declaration'])
