from __future__ import annotations

import functools
from abc import abstractmethod, ABC
from dataclasses import dataclass, field
from enum import StrEnum, auto, Enum
from typing import TYPE_CHECKING, Union, Callable, Any, TypeAlias

from models.cost import Cost, CostResult
from models.events_all import Event
from ..target import TargetSpec

if TYPE_CHECKING:
    from ..action_stack import StackItemType
    from ..game_card.game_card import GameCard
    from ..game_card.effect_spec_templates import On
    from game_state import GameState
    from models.systems.phase import Phase

RTarget: TypeAlias = "GameCard | int | StackItemType | list[GameCard] | None"


@dataclass
class ResContext:
    """Resolution Context passes information from Ability Pipeline to the Resolver"""
    cost_result: CostResult | None = None
    x_value: int | None = None
    chosen_mode: int | None = None
    event: Event | None = None

class Resolver(ABC):
    def __repr__(self):
        return self.__class__.__name__

    @abstractmethod
    def resolve(self, gs: GameState, source: GameCard, t: RTarget = None, context: ResContext = None) -> None:
        ...

    def can_cast(self, gs: GameState, source: GameCard) -> bool:
        return True

    def can_activate(self, gs: GameState, source: GameCard) -> bool:
        return True

    @staticmethod
    def target_required(fn):
        """wrapper for .resolve() that replaces 100s of methods starting with:
        if t is None:
            raise ValueError(f"{source.props.name} needs a target")"""
        @functools.wraps(fn)
        def wrapper(self, gs, source, t=None, context=None):
            if t is None:
                raise ValueError(f"{source.props.name} needs a target")
            return fn(self, gs, source, t, context)
        return wrapper

class Listener:
    listens_to: type[Event] | None = None  # used by event listeners
    expires: str | None = None
    is_expired: bool = False

    def __repr__(self):
        return self.__class__.__name__

    def initialize(self, gs: GameState, source: GameCard, target: Any):
        """Used when registering a Listener with a target; the selected targets are stored in self.target(s)"""
        pass

    def on_event(self, gs: GameState, source: GameCard, event: Event) -> None:
        """React to something that just happened (ex: sacrifice if no lands, gain life based el-hajjaj damaging)"""
        raise NotImplementedError()


class ESType(StrEnum):
    """EffSpec types"""
    ACTIVATED = auto()
    SPELL = auto()
    STATIC = auto()
    TRIGGERED = auto()


@dataclass(frozen=True)
class EffSpec:
    """Effect Specification; mapping slugs to Effects uses EffSpec"""
    spec_type: ESType
    cost: str
    effect: Resolver | Listener
    target_spec: Union[Enum, TargetSpec, None] = None
    extra_costs: list[Cost | None] = field(default_factory=list)
    allowed_phases: list[Phase | None] = field(default_factory=list)
    allowed_p_turn_func: Callable[[GameState, GameCard], int] = None
    allowed_activators: Callable[[GameState, GameCard], tuple[int] | None] = None
    max_activations_per_turn: int = 999
    text: str = ''
    min_x_func: Callable = lambda gs, s: 1
    max_x_func: Union[Callable[..., int], None] = None
    is_mana_ability: bool = False

    def __post_init__(self):
        """Some slug-eff_spec mappings provide a callable (assume exactly 1 target will be chosen);
        to support multi-card targets, TargetSpec was created and tuple[filter_func, min_cnt, max_cnt] is acceptable;
        either way, we convert that to a TargetSpec via _normalize_target_spec"""
        object.__setattr__(self, "target_spec", self._normalize_target_spec(self.target_spec))

    @property
    def is_aa(self) -> bool:
        return self.spec_type == ESType.ACTIVATED

    @property
    def is_spell(self) -> bool:
        return self.spec_type == ESType.SPELL

    @staticmethod
    def _normalize_target_spec(target_spec: Callable | TargetSpec | None) -> TargetSpec | None:
        if target_spec is None:
            return None
        if isinstance(target_spec, TargetSpec):
            return target_spec
        if callable(target_spec):
            return TargetSpec(target_spec, 1, 1)
        raise TypeError(f"Invalid target type: {target_spec}")


@dataclass
class ActivatedAbility:
    source: GameCard
    eff_spec: EffSpec
    activations_this_turn: int = 0


def Activated(cost: str,
              effect: Resolver | Listener,
              target_spec: Union[Callable, TargetSpec, None] = None,
              *,
              extra_costs: list[Cost | None] = None,
              allowed_phases: list[Phase | None] = None,
              allowed_p_turn_func: Callable[[GameState, GameCard], int] = None,
              allowed_activators: Callable[[GameState, GameCard], tuple[int] | None] = None,
              max_activations_per_turn: int = 999,
              text: str = '',
              min_x_func: Callable = lambda gs, s: 1,
              max_x_func: Union[Callable[..., int], None] = None,
              is_mana_ability: bool = False) -> EffSpec:

    return EffSpec(spec_type=ESType.ACTIVATED, cost=cost, effect=effect, target_spec=target_spec,
                   extra_costs=extra_costs or [], allowed_phases=allowed_phases or [],
                   allowed_p_turn_func=allowed_p_turn_func, allowed_activators=allowed_activators,
                   max_activations_per_turn=max_activations_per_turn, text=text,
                   min_x_func=min_x_func, max_x_func=max_x_func, is_mana_ability=is_mana_ability)

def GenTrig(on: On) -> EffSpec:
    return EffSpec(spec_type=ESType.TRIGGERED, cost='', effect=on.build())

def Spell(effect: Resolver | Listener,
          target_spec: Union[Callable, TargetSpec, None] = None,
          *,
          extra_costs: list[Cost | None] | None = None,
          allowed_phases: list[Phase | None] = None,
          allowed_p_turn_func: Callable[[GameState, GameCard], int] = None,
          text: str = '',
          min_x_func: Callable = lambda gs, s: 1,
          max_x_func: Callable[..., int] | None = None) -> EffSpec:
    return EffSpec(spec_type=ESType.SPELL, cost='', effect=effect, target_spec=target_spec,
                   extra_costs=extra_costs or [], allowed_phases=allowed_phases or [],
                   allowed_p_turn_func=allowed_p_turn_func, text=text, min_x_func=min_x_func, max_x_func=max_x_func)

def Static(effect: Listener,
           target_spec: Union[Callable, TargetSpec, None] = None,
           *,
           text: str = '') -> EffSpec:

    return EffSpec(spec_type=ESType.STATIC, cost='', effect=effect, target_spec=target_spec, text=text)

def Triggered(effect: Listener,
              target_spec: Union[Callable, TargetSpec, None] = None,
              *,
              allowed_phases: list[Phase | None] | None = None,
              allowed_p_turn_func: Callable[[GameState, GameCard], int] | None = None,
              allowed_activators: Callable[[GameState, GameCard], tuple[int] | None] | None = None,
              text: str = '') -> EffSpec:

    return EffSpec(spec_type=ESType.TRIGGERED, cost='', effect=effect, target_spec=target_spec,
                   allowed_phases=allowed_phases or [], allowed_p_turn_func=allowed_p_turn_func,
                   allowed_activators=allowed_activators, text=text)


"""
Activated is when the player opts to activate an ability (aladdins-ring)
Spell is rarely more than one per card; it is for casting (lightning-bolt)
Static is always on & can answer questions without causing actions (crusade)
Triggered are abilities that respond to 'when/whenever' (hypnotic-specter)
"""

