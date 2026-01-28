from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from models.game_card import GameCard

from models.events.base import Event

@dataclass(frozen=True)
class CastResolvedEvent(Event):
    card: GameCard
    owner_id: int
    target: GameCard | None = None

@dataclass(frozen=True)
class CombatEndEvent(Event):
    active_player: int

@dataclass(frozen=True)
class EndStepEvent(Event):
    active_player: int

@dataclass(frozen=True)
class TapCardEvent(Event):
    card: GameCard

@dataclass(frozen=True)
class UpkeepEvent(Event):
    active_player: int

@dataclass(frozen=True)
class UntapCardEvent(Event):
    card: GameCard

@dataclass
class DamageEvent(Event):
    """..."""
    # TODO: i'm pretty sure that damage.py's DamageEvent is what can be placed here
