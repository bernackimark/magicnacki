from __future__ import annotations
from dataclasses import dataclass
from typing import Callable, TYPE_CHECKING, Optional

from models.events_all import DamageProposedEvent

if TYPE_CHECKING:
    from game_card.game_card import GameCard
    from game_state import GameState


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
    combat_only: bool = False

    def __post_init__(self):
        print(self)

    def apply(self, event: DamageProposedEvent) -> None:
        """Returns amt of damage prevented or 0"""
        if self.remaining and self.remaining <= 0:
            return

        if self.source_filter and event.source and not self.source_filter(event.source):
            return

        if self.target_player is not None:
            if not isinstance(event.target, int) or event.target != self.target_player:
                return

        if self.target_card:
            if event.target is not self.target_card:
                return

        if self.target_filter and not self.target_filter(event.target):
            return

        if self.combat_only and not event.is_combat:
            return

        # uncapped prevention
        if self.remaining is None:
            return

        event.prevented = min(self.remaining, event.remaining)
        self.remaining -= event.prevented

        if self.on_prevent:
            self.on_prevent(event.prevented)
