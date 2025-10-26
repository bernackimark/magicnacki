from abc import ABC, abstractmethod
from contextlib import suppress
from dataclasses import dataclass

from game_state import Action, GameState


@dataclass
class Player(ABC):
    idx: int
    name: str
    is_bot: bool = False

    @abstractmethod
    def make_move(self, gs: GameState):
        ...


@dataclass
class ConsolePlayer(Player):
    def make_move(self, gs: GameState) -> Action | None:
        avail_actions = gs.get_available_actions(self.idx)
        if not avail_actions:
            return None
        for i, avail_action in enumerate(avail_actions):
            print(f"{i}: {avail_action}")
        with suppress(KeyboardInterrupt):
            sel_action: int = int(input("Please select an action "))
            return avail_actions[sel_action]
