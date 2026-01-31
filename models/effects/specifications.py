from __future__ import annotations
from dataclasses import dataclass, field
from enum import Enum, auto
from functools import partial
from typing import Literal, Union, Callable, TYPE_CHECKING

if TYPE_CHECKING:
    from game_state import GameState
    from models.game_card import GameCard

from cost import Cost, TapCost, ManaCost
from models.effects.base import Effect
from models.events.base import Event
from phase_fsm import Phase
from utils import flip


@dataclass
class EffSpec:
    """Effect Specification"""

    class AllowedPlayerTurn(Enum):
        CASTER = auto()
        OPPONENT = auto()

    activation_type: Literal["cast", "upkeep", "activated", "untap", "static"]
    cost: str
    effect: Effect
    target_filter: Union[Callable, None] = None
    trigger_event: type[Event] | None = None
    conditions: list[Callable[[], bool], None] = field(default_factory=list)
    extra_costs: list[Cost | None] = None
    allowed_phases: list[Phase | None] = field(default_factory=list)
    allowed_player_turn: AllowedPlayerTurn | None = field(default_factory=list)
    allowed_p_id_turn: int | None = None
    activated_cnt_this_turn: int = 0
    max_activations_per_turn: int = 999
    text: str = ''

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
    def install(self, gs: GameState, source: GameCard):
        source.effects.append(self.effect)

    def uninstall(self, gs: GameState, source: GameCard):
        source.effects.remove(self.effect)


@dataclass
class ActivatedAbility:
    source: GameCard
    eff_spec: EffSpec

    def __post_init__(self):
        """from InitVars 'cost_mana', 'cost_tap', and 'extra_costs', build attribute 'costs'
        allowed_p_id_turns need knowledge of the card's owner and is assigned here;
        if allowed_player_turn is None, then the ability should be permitted on both turns"""
        if self.eff_spec.allowed_player_turn == self.eff_spec.AllowedPlayerTurn.CASTER:
            self.eff_spec.allowed_p_id_turn = self.source.orig_owner_id
        if self.eff_spec.allowed_player_turn == self.eff_spec.AllowedPlayerTurn.OPPONENT:
            self.eff_spec.allowed_p_id_turn = flip(self.source.orig_owner_id)

    def can_activate(self, gs: GameState) -> bool:
        if self.eff_spec.allowed_phases and gs.phase not in self.eff_spec.allowed_phases:
            print("C")
            return False
        if self.eff_spec.allowed_player_turn and gs.player_turn_idx != self.eff_spec.allowed_p_id_turn:
            print("F")
            return False
        if self.eff_spec.allowed_p_id_turn and self.source.orig_owner_id != self.eff_spec.allowed_p_id_turn:
            print("D")
            return False
        if self.eff_spec.activated_cnt_this_turn >= self.eff_spec.max_activations_per_turn:
            print("E")
            return False
        if self.eff_spec.conditions:
            for cond in self.eff_spec.conditions:
                if not cond(self.source):
                    print('G')
                    return False
        return all(cost.can_pay(gs, self.source) for cost in self.eff_spec.costs)

    def pay_costs(self, gs):
        for cost in self.eff_spec.costs:
            cost.pay(gs, self.source)


"""
Triggered is when something happens & fires once
Activated is when the player opts to do something
Static is always on & answers questions without causing actions
"""

Activated = partial(EffSpec, 'activated')
Static = partial(StaticEffSpec, 'static', '')
Triggered = partial(EffSpec, 'triggered', '')
