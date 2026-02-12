from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from constants import Target
from models.zone import Zone

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
class DamageResolvedEvent(Event):
    source: GameCard
    amt: int
    target: Target
    is_combat: bool

@dataclass(frozen=True)
class DrawCardEvent(Event):
    player_id: int

@dataclass(frozen=True)
class DrawStepEvent(Event):
    active_player: int

@dataclass(frozen=True)
class DiesEvent(Event):
    """MTG specifically considers 'dies' as moving from board to graveyard only"""
    card: GameCard

@dataclass(frozen=True)
class EndStepEvent(Event):
    active_player: int

@dataclass(frozen=True)
class StateBasedEvent(Event):
    """Emitted whenever a relevant board state change happens (play to board, remove from board, control changes)"""
    pass

@dataclass(frozen=True)
class TapCardEvent(Event):
    card: GameCard

@dataclass(frozen=True)
class UpkeepEvent(Event):
    active_player: int

@dataclass(frozen=True)
class UntapCardEvent(Event):
    card: GameCard

@dataclass(frozen=True)
class UntapPhaseEvent(Event):
    active_player: int

@dataclass(frozen=True)
class ZoneChangeEvent(Event):
    card: GameCard
    from_zone: Zone
    to_zone: Zone
    cause: str | None = None

# Note: Damage is special since it is not fire-and-forget; it must be stateful to apply a chain of modifications
# It can be found in the dedicated damage module
