from __future__ import annotations
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Iterable, Any

if TYPE_CHECKING:
    from models.constants import Target
    from models.game_card.game_card import GameCard
    from models.modifiers import ModType
    from models.zone import Zone


class Event:
    pass


@dataclass(frozen=True)
class AttackEvent(Event):
    attacker: GameCard

@dataclass(frozen=True)
class BlockEvent(Event):
    attacker: GameCard
    blocker: GameCard

@dataclass
class CanAttackQueryEvent(Event):
    attacker: GameCard
    permission: bool | None = None

@dataclass
class CanBlockQueryEvent(Event):
    blocker: GameCard
    attacker: GameCard
    permission: bool | None = None

@dataclass
class CanCastQueryEvent(Event):
    card: GameCard
    permission: bool | None = None

@dataclass
class CanTargetQueryEvent(Event):
    source: GameCard
    target: GameCard
    permission: bool | None = None

@dataclass
class CanUntapQueryEvent(Event):
    card: GameCard
    permission: bool | None = None

@dataclass(frozen=True)
class CastResolvedEvent(Event):
    card: GameCard
    owner_id: int
    target: GameCard | None = None

@dataclass(frozen=True)
class CombatEndEvent(Event):
    active_player: int

@dataclass
class DamageProposedEvent(Event):
    """This event is mutable, as damage preventers/limiters/replacers may modify it"""
    source: GameCard
    target: GameCard | int
    amt: int
    remaining: int
    prevented: int = 0
    is_combat: bool = False


@dataclass(frozen=True)
class DamageResolvedEvent(Event):
    source: GameCard
    amt: int
    target: Target
    is_combat: bool

@dataclass
class DestroyAttemptEvent(Event):
    card: GameCard
    allow_regeneration: bool = True

@dataclass
class DiscardStepEvent(Event):
    active_player: int

@dataclass(frozen=True)
class DiesEvent(Event):
    """MTG specifically considers 'dies' as moving from board to graveyard only"""
    card: GameCard

@dataclass(frozen=True)
class DrawCardEvent(Event):
    player_id: int

@dataclass(frozen=True)
class DrawStepEvent(Event):
    active_player: int

@dataclass(frozen=True)
class DiscardEvent(Event):
    active_player: int
    card: GameCard
    source: GameCard | None = None

@dataclass(frozen=True)
class EndStepEvent(Event):
    active_player: int

@dataclass(frozen=True)
class EnterBattlefieldEvent(Event):
    caster: int
    card: GameCard

@dataclass(frozen=True)
class LifeGainEvent(Event):
    p_id_gaining_life: int
    amt: int
    source: GameCard

@dataclass
class LifeLossEvent(Event):
    """Is not frozen as it may be modified (ex: ali-from-cairo)"""
    p_id_taking_damage: int
    amt: int
    source: GameCard

@dataclass
class QueryEvent(Event):
    query: str
    card: GameCard

@dataclass
class ModQueryEvent(QueryEvent):
    """Mutable structure because various effects will append to mods"""
    mods: list[ModType] = field(default_factory=list)

@dataclass
class RandomEvent(Event):
    player_id: int
    iterable: Iterable
    result: Any = None

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
class UnblockedAttackerEvent(Event):
    attacker: GameCard
    defending_player_id: int

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
