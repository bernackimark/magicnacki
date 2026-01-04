from __future__ import annotations
from dataclasses import dataclass
from typing import Callable, TYPE_CHECKING


if TYPE_CHECKING:
    from game_card import GameCard
    from game_state import GameState

@dataclass
class DamageEvent:
    source: GameCard | None  # card or None (for combat)
    amt: int
    target: GameCard | int  # creature or player index
    is_combat: bool = False
    prevented: int = 0

    @property
    def remaining(self) -> int:
        return max(0, self.amt - self.prevented)

@dataclass
class PreventNextDamage:
    source_filter: Callable[[GameCard], bool]
    target_player: int
    amt: int = 999

    def apply(self, event: DamageEvent):
        if event.target != self.target_player:
            return
        if not self.source_filter(event.source):
            return

        prevented = min(self.amt, event.remaining)
        event.prevented += prevented

