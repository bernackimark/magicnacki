from __future__ import annotations
from abc import ABC
from dataclasses import dataclass, field
from functools import partial
from typing import TYPE_CHECKING, Optional, Literal, Union, Callable

from models.cost import Cost, TapCost, ManaCost
from models.events_all import Event
from ..target import TargetSpec

if TYPE_CHECKING:
    from ..game_card.game_card import GameCard
    from game_state import GameState
    from models.phase_manager import Phase


class Effect(ABC):
    """Base class for all card effects."""
    pass

class Resolver(Effect):
    def resolve(self, gs: GameState, source: GameCard, target: Optional[GameCard] = None) -> None:
        """Perform an explicit game action (ex: deal 3 damage)"""
        raise NotImplementedError()

    def can_cast(self, gs: GameState, source: GameCard) -> bool:
        return True

    def can_activate(self, gs: GameState, source: GameCard) -> bool:
        return True

class Listener(Effect):
    listens_to: type[Event] | None = None  # used by event listeners
    expires: str | None = None
    is_expired: bool = False

    def on_event(self, gs: GameState, source: GameCard, event: Event) -> None:
        """React to something that just happened (ex: sacrifice if no lands, gain life based el-hajjaj damaging)"""
        raise NotImplementedError()


@dataclass
class EffSpec:
    """Effect Specification; mapping slugs to Effects uses EffSpec"""
    activation_type: Literal['activated', 'spell', 'static', 'triggered']
    cost: str
    effect: Effect
    target_spec: Union[Callable, TargetSpec, None] = None
    extra_costs: list[Cost | None] = None
    allowed_phases: list[Phase | None] = field(default_factory=list)
    allowed_p_id_turn: int | None = None
    max_activations_per_turn: int = 999
    text: str = ''
    min_x_func: Callable = lambda gs, s: 1
    max_x_func: Union[Callable[..., int], None] = None

    def __post_init__(self):
        """Some slug-eff_spec mappings provide a callable (assume exactly 1 target will be chosen);
        to support multi-card targets, TargetSpec was created and tuple[filter_func, min_cnt, max_cnt] is acceptable;
        either way, we convert that to a TargetSpec via _normalize_target_spec"""
        object.__setattr__(self, "target_spec", self._normalize_target_spec(self.target_spec))

    @staticmethod
    def _normalize_target_spec(target_spec: Callable | TargetSpec | None) -> TargetSpec | None:
        if target_spec is None:
            return None
        if isinstance(target_spec, TargetSpec):
            return target_spec
        if callable(target_spec):
            return TargetSpec(target_spec, 1, 1)
        raise TypeError(f"Invalid target type: {target_spec}")

    @property
    def costs(self) -> list[Cost | None]:
        the_costs = []
        if not self.cost:
            pass
        elif 'T' in self.cost:
            the_costs.append(TapCost())
            the_costs.append(ManaCost(self.cost[:-1]))
        else:
            the_costs.append(ManaCost(self.cost))
        if self.extra_costs:
            for extra_cost in self.extra_costs:
                the_costs.append(extra_cost)
        return the_costs


@dataclass
class ActivatedAbility:
    source: GameCard
    eff_spec: EffSpec
    activations_this_turn: int = 0

    def __post_init__(self):
        if not isinstance(self.eff_spec.effect, Resolver):
            raise TypeError(f'{self.source.props.name} is trying to register an ActivatedAbility with an effect'
                            f'specification that is not a Resolver; the supplied effect spec is {self.eff_spec}')

    def can_activate(self, gs: GameState) -> bool:
        # card-specific restriction
        if hasattr(self.eff_spec, 'can_activate'):
            if not self.eff_spec.can_activate(gs, self.source):
                print("B")
                return False
        if self.eff_spec.allowed_phases and gs.phase_mgr.phase not in self.eff_spec.allowed_phases:
            print("C")
            return False
        if self.eff_spec.allowed_p_id_turn and self.source.owner_id != self.eff_spec.allowed_p_id_turn:
            print("D")
            return False
        if self.activations_this_turn >= self.eff_spec.max_activations_per_turn:
            print("E")
            return False
        if self.source.has_summoning_sickness and self.source.is_creature and 'T' in self.eff_spec.cost:
            print("F")
            return False
        if not all(cost.can_pay(gs, self.source) for cost in self.eff_spec.costs):
            print("G")
            return False
        return True


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
