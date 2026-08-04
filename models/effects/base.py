from __future__ import annotations

import functools
from abc import abstractmethod, ABC
from dataclasses import dataclass, field
from functools import partial
from typing import TYPE_CHECKING, Literal, Union, Callable, Any, TypeAlias

from models.cost import Cost, CostResult
from models.events_all import Event
from ..target import TargetSpec

if TYPE_CHECKING:
    from ..action_stack import StackItemType
    from ..game_card.game_card import GameCard
    from game_state import GameState
    from models.systems.phase import Phase

RTarget: TypeAlias = "GameCard | int | StackItemType | list[GameCard] | None"


@dataclass
class ResContext:
    """Resolution Context passes information from Ability Pipeline to the Resolver"""
    cost_result: CostResult | None = None
    x_value: int | None = None
    chosen_mode: int | None = None

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


@dataclass(frozen=True)
class EffSpec:
    """Effect Specification; mapping slugs to Effects uses EffSpec"""
    activation_type: Literal['activated', 'spell', 'static', 'triggered']
    cost: str
    effect: Resolver | Listener
    target_spec: Union[Callable, TargetSpec, None] = None
    extra_costs: list[Cost | None] = field(default_factory=list)
    allowed_phases: list[Phase | None] = field(default_factory=list)
    allowed_p_turn_func: Callable[[GameState, GameCard], int] = None
    allowed_activators: Callable[[GameState, GameCard], tuple[int] | None] = None
    max_activations_per_turn: int = 999
    text: str = ''
    min_x_func: Callable = lambda gs, s: 1
    max_x_func: Union[Callable[..., int], None] = None

    def __post_init__(self):
        """Some slug-eff_spec mappings provide a callable (assume exactly 1 target will be chosen);
        to support multi-card targets, TargetSpec was created and tuple[filter_func, min_cnt, max_cnt] is acceptable;
        either way, we convert that to a TargetSpec via _normalize_target_spec"""
        object.__setattr__(self, "target_spec", self._normalize_target_spec(self.target_spec))

    @property
    def is_aa(self) -> bool:
        return self.activation_type == 'activated'

    @property
    def is_spell(self) -> bool:
        return self.activation_type == 'spell'

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

    # def __post_init__(self):
    #     if not isinstance(self.eff_spec.effect, Resolver):
    #         raise TypeError(f'{self.source.props.name} is trying to create an ActivatedAbility with an effect'
    #                         f'specification that is not a Resolver; the supplied effect spec is {self.eff_spec}')


"""
Activated is when the player opts to activate an ability (aladdins-ring)
Spell is rarely more than one per card; it is for casting (lightning-bolt)
Static is always on & can answer questions without causing actions (crusade)
Triggered are abilities that respond to 'when/whenever' (hypnotic-specter)
"""

Activated = partial(EffSpec, 'activated')
Spell = partial(EffSpec, 'spell', '')
Static = partial(EffSpec, 'static', '')
Triggered = partial(EffSpec, 'triggered', '')
