from __future__ import annotations
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Iterable, Any

if TYPE_CHECKING:
    from models.actions.ability_pipeline_support import AbilityAction
    from models.actions.cast import CastPermanentAction
    from models.effects.base import ActivatedAbility
    from models.constants import Target
    from models.game_card.game_card import GameCard
    from models.modifiers import ModType
    from models.zone import Zone

"""
Events are dataclasses that can be emitted and Listener effects can respond.
They are commonly frozen.
However, some objects can be passed around and mutated, such as:
    -   DamageProposedEvent, which is mutated until finalization, when it becomes a frozen DamageResolvedEvent
    -   Can[x]QueryEvent, containing a .permission attribute, which Listeners can set to False
"""

class Event:
    pass


@dataclass(frozen=True)
class AbilityActivatedEvent(Event):
    activator: int
    aa: ActivatedAbility

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
    p_id: int
    permission: bool | None = None

@dataclass
class CanDamageQueryEvent(Event):
    source: GameCard
    target: GameCard
    permission: bool | None = None

@dataclass
class CanEnterUntapPhaseQueryEvent(Event):
    active_player: int
    permission: bool | None = None

@dataclass
class CanRegenerateQueryEvent(Event):
    card: GameCard
    permission: bool | None = None

@dataclass
class CanTargetQueryEvent(Event):
    source: GameCard
    target: GameCard | int
    permission: bool | None = None

@dataclass
class CanUntapQueryEvent(Event):
    """Should be used to determine if the card can ever untap"""
    card: GameCard
    permission: bool | None = None

@dataclass
class CanUntapAtUntapPhaseQueryEvent(Event):
    """Should be used to determine if the card can untap specifically at the owner's untap phase"""
    active_player: int
    card: GameCard
    permission: bool | None = None

@dataclass(frozen=True)
class CastResolvedEvent(Event):
    card: GameCard
    owner_id: int
    target: GameCard | None = None

@dataclass
class CombatBeginEvent(Event):
    active_player: int

@dataclass
class CombatDamageEvent(Event):
    is_first_strike: bool = False

@dataclass(frozen=True)
class CombatEndEvent(Event):
    active_player: int

@dataclass
class CostQueryEvent(Event):
    """Query is either 'cast' or 'activate';
    cost (a string ex '2U') will be mutated by listeners before GameState presents the costs to the user"""
    player_id: int
    query: str
    card: GameCard
    cost: str

@dataclass
class DamageProposedEvent(Event):
    """This event is mutable, as damage preventers/limiters/replacers may modify it"""
    source: GameCard
    target: GameCard | int
    amt: int
    remaining: int
    prevented: int = 0
    is_combat: bool = False

    def __post_init__(self):
        self.remaining = self.amt


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
    card: GameCard

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

@dataclass(frozen=True)
class MainPhaseEvent(Event):
    active_p_id: int

@dataclass
class QueryEvent(Event):
    query: str
    card: GameCard

@dataclass
class ModQueryEvent(QueryEvent):
    """Mutable structure because various effects will append to mods"""
    mods: list[ModType] = field(default_factory=list)

@dataclass
class PassTheTurnEvent(Event):
    active_player: int

@dataclass
class RandomEvent(Event):
    player_id: int
    iterable: Iterable
    result: Any = None

@dataclass(frozen=True)
class StackAdditionEvent(Event):
    player_id: int
    action: AbilityAction | CastPermanentAction

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

