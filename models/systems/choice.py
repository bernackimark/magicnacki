from __future__ import annotations
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from game_state import GameState
    from models.choice_actions_all import ChoiceAction
    from models.choice_options import CO

class ChoiceManager:
    def __init__(self, gs: GameState, starting_choice: ChoiceAction | None = None):
        self._gs = gs
        self._current: ChoiceAction | None = starting_choice
        self._pending: list[ChoiceAction] = []

    @property
    def current(self) -> ChoiceAction | None:
        return self._current

    def choose(self, option: CO) -> None:
        # The current choice is being consumed.
        self._current = None

        # Execute the actual game operation.
        option.play()

        # If the callback didn't create another current choice, promote the next queued choice.
        if self.current is None and self._pending:
            self._current = self._pending.pop(0)

    def queue(self, choice: ChoiceAction) -> None:
        if self.current is None:
            self._current = choice
        else:
            self._pending.append(choice)

    def complete(self) -> None:
        """The current choice has been completed."""
        self._current = self._pending.pop(0) if self._pending else None

    def clear(self) -> None:
        self._current = None
        self._pending.clear()

    def clear_current(self) -> None:
        self._current = None

    def get_actions(self) -> list[CO]:
        if self.current is None:
            return []
        return self.current.get_actions()
