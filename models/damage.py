from __future__ import annotations
from dataclasses import dataclass
from typing import Callable, TYPE_CHECKING, Optional

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
    preventer_card: GameCard
    remaining: int | None = None  # None = prevent all
    target_player: Optional[int] = None
    target_card: Optional[GameCard] = None
    source_card: Optional[GameCard] = None
    source_filter: Optional[Callable[[GameCard | None], bool]] = None
    target_filter: Callable[[GameCard | int], bool] | None = None
    on_prevent: Callable[[int], None] | None = None  # callback (ex: reverse-damage must be notified amt prevented)

    def __post_init__(self):
        print(self)

    def apply(self, event: DamageEvent) -> int:
        """Returns amt of damage prevented or 0"""
        if self.remaining and self.remaining <= 0:
            print('a')
            return 0

        if self.source_filter and event.source and not self.source_filter(event.source):
            print('b')
            return 0

        if self.target_player is not None:
            if not isinstance(event.target, int) or event.target != self.target_player:
                print('c')
                return 0

        if self.target_card:
            if event.target is not self.target_card:
                print('d')
                return 0

        if self.target_filter and not self.target_filter(event.target):
            print('e')
            return 0

        # uncapped prevention
        if self.remaining is None:
            return event.amt

        prevented = min(self.remaining, event.remaining)
        self.remaining -= prevented

        if self.on_prevent:
            self.on_prevent(prevented)

        return prevented

