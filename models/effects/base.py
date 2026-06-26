from __future__ import annotations
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum, auto
from functools import partial
from typing import TYPE_CHECKING, Optional, Literal, Union, Callable

from models.cost import Cost, TapCost, ManaCost
from models.utils import flip

from models.events_all import Event

if TYPE_CHECKING:
    from ..game_card.game_card import GameCard
    from game_state import GameState
    from models.phase_manager import Phase
    from ..modifiers import ModType

@dataclass
class TargetSpec:
    filter_func: Callable
    min_cnt: int = 1
    max_cnt: int | None = 1
    allow_duplicate_targets: bool = False  # used in pyrotechnics/fireball where we always add 1 damage at a time

    def get_targets(self, gs: GameState, source: GameCard) -> list[GameCard | int | None]:
        """Execute the effect's filter func
        If target is an int, let it through; if target is a GameCard, check can_target();
        If there are enough targets, return all targets, else return []"""
        candidates = self.filter_func(gs, source)
        legal_targets = [c for c in candidates if isinstance(c, int) or gs.perm_querier.can_target(c, source)]
        return legal_targets if len(legal_targets) >= self.min_cnt else []

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

class Querier(Effect):
    query: str | tuple[str] | None = None  # used by queriers

    @abstractmethod
    def on_query(self, gs: GameState, card: GameCard, **kwargs) -> bool | None:
        """Answer a rules question (ex: can this attack?)"""
        return None  # default: no opinion

class ModRetriever(Effect):
    modifies: str | tuple[str] | None = None  # used by Modifier queries

    @abstractmethod
    def get_mods(self, gs: GameState, query: str, card: GameCard, source: GameCard, **kwargs) -> (
            ModType | list[ModType] | None):
        """A GameCard asks for any global mods (ex: Crusade would return a PTMOd to a white creature)"""
        return None

@dataclass
class EffSpec:
    """Effect Specification; mapping slugs to Effects uses EffSpec"""
    activation_type: Literal['activated', 'spell', 'static', 'triggered']
    cost: str
    effect: Effect
    target_spec: Union[tuple[Callable, int, int | None], Callable, TargetSpec, None] = None
    trigger_event: type[Event] | None = None
    extra_costs: list[Cost | None] = None
    allowed_phases: list[Phase | None] = field(default_factory=list)
    allowed_p_id_turn: int | None = None
    activated_cnt_this_turn: int = 0
    max_activations_per_turn: int = 999
    text: str = ''
    max_x_func: Union[Callable[..., int], None] = None
    min_x: int = 1

    def __post_init__(self):
        """Some slug-eff_spec mappings provide a callable (assume exactly 1 target will be chosen);
        to support multi-card targets, TargetSpec was created and tuple[filter_func, min_cnt, max_cnt] is acceptable;
        either way, we convert that to a TargetSpec via _normalize_target_spec"""
        self.target_spec: TargetSpec | None = self._normalize_target_spec(self.target_spec)

    @staticmethod
    def _normalize_target_spec(target_spec: tuple[Callable, int, int] | None | Callable | TargetSpec | None) -> (
            TargetSpec | None):
        if target_spec is None:
            return None

        if isinstance(target_spec, TargetSpec):
            return target_spec

        if isinstance(target_spec, tuple):
            filter_func, min_cnt, max_cnt = target_spec
            return TargetSpec(filter_func, min_cnt, max_cnt)

        # Legacy support: assume single-target filter
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
class StaticEffSpec(EffSpec):
    ...


@dataclass
class ActivatedAbility:
    source: GameCard
    eff_spec: EffSpec

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
        if self.eff_spec.activated_cnt_this_turn >= self.eff_spec.max_activations_per_turn:
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
Spell is one per card max; it is for casting (lightning-bolt)
Static is always on & can answer questions without causing actions (crusade)
Triggered are abilities that respond to 'when/whenever' (hypnotic-specter)
"""

Activated = partial(EffSpec, 'activated')
Spell = partial(EffSpec, 'spell', '')
Static = partial(EffSpec, 'static', '')
Triggered = partial(EffSpec, 'triggered', '')
