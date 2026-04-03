from dataclasses import dataclass

from models.actions.base import Action
from models.choice_actions_all import ChoiceAction
from models.utils import flip
from phase_fsm import Phase


class GameOverChoice(ChoiceAction):
    def __init__(self, p_id, gs):
        super().__init__(p_id, gs, source=None)
        ...

    def get_actions(self) -> list[Action]:
        return [KeepDeck(self.player_idx, self.gs), Sideboard(self.player_idx, self.gs)]

@dataclass
class Sideboard(Action):
    def __repr__(self):
        return f"Sideboard"

    def play(self) -> None:
        self.gs.phase_mgr.phase = Phase.SIDEBOARDING
        if self.gs.action_stack.actions:
            self.gs.action_stack.pop()
        exit()  # TODO: Sideboarding phase; use same approach for console, which PG can render

@dataclass
class KeepDeck(Action):
    def __repr__(self):
        return f"Keep Deck"

    def play(self) -> None:
        self.gs.phase_mgr.phase = Phase.NEW_GAME
        if self.gs.action_stack.actions:
            self.gs.action_stack.pop()

@dataclass
class Concede(Action):
    def __repr__(self):
        return "Concede Game"

    def play(self) -> None:
        self.gs.winner = flip(self.player_idx)
        self.gs.is_game_over = True
        print(f'Player #{self.player_idx} concedes; Player #{self.gs.winner} wins the game')
