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
        choice = self._current
        self._current = None

        # Execute the actual game operation.
        option.play()

        # If the callback created another choice, that choice takes precedence.
        if self._current is not None:
            return

        # This choice is complete
        if choice.on_complete:
            choice.complete()

        # Promote a queued choice, if one exists.
        if self._pending:
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
