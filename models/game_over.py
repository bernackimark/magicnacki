from dataclasses import dataclass

from models.actions.base import Action
from models.choice_actions_all import ChoiceAction
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
        self.gs.phase = Phase.SIDEBOARDING
        if self.gs.action_stack.actions:
            self.gs.action_stack.pop()
        exit()  # TODO: Sideboarding phase; use same approach for console, which PG can render

@dataclass
class KeepDeck(Action):
    def __repr__(self):
        return f"Keep Deck"

    def play(self) -> None:
        self.gs.phase = Phase.NEW_GAME
        if self.gs.action_stack.actions:
            self.gs.action_stack.pop()
