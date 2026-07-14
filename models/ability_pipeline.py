from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any, Literal, TYPE_CHECKING, Union

from models.effects.base import Resolver
from models.events_all import StateBasedEvent, CastResolvedEvent, AbilityActivatedEvent
from models.zone import Zone

if TYPE_CHECKING:
    from game_state import GameState
    from models.effects.base import EffSpec
    from models.game_card.game_card import GameCard

@dataclass
class AbilityPipeline:
    p_id: int
    gs: GameState
    source: GameCard
    eff_spec: EffSpec

    # values gathered while progressing
    x_value: int | None = None
    chosen_mode: int | None = None
    targets: list[Any] = field(default_factory=list)

    # information produced by paying costs
    cost_result: Union["CostResult", None] = None

    @property
    def origin(self) -> Literal["spell", "activated", "triggered", "static"] | None:
        return self.eff_spec.activation_type

    def can_begin(self) -> bool:
        min_x, max_x = self.get_x_range()
        if max_x < min_x:
            return False

        target_spec = self.eff_spec.target_spec
        if target_spec:
            targets = target_spec.get_targets(self.gs, self.source)
            if len(targets) < target_spec.min_cnt:
                return False

        mana_cost = self.source.casting_cost[:] if self.origin == 'spell' else self.eff_spec.cost
        if not self.gs.mana_pools[self.p_id].can_pay(mana_cost):
            return False

        for extra_cost in (self.eff_spec.extra_costs or []):
            if not extra_cost.can_pay(self.gs, self.source):
                return False

        return True

    def advance(self):
        """Advance the pipeline to the next unresolved step.
            Each branch either:
                1. Creates a pending ChoiceAction and returns, or
                2. Continues automatically if no user input is required."""

        # unique to auras who use the pipeline to find a target & attach but only have listeners & no resolver
        if self.eff_spec.effect is None:
            self.finish()
            return

        if self.needs_x:
            from models.choice_actions_all import XChoice2
            self.gs.pending_choice = XChoice2(self)
        elif self.needs_mode:
            from models.choice_actions_all import ModeChoice2
            self.gs.pending_choice = ModeChoice2(self)
        elif self.needs_targets:
            from models.choice_actions_all import TargetChoice2
            self.gs.pending_choice = TargetChoice2(self)
        elif self.needs_extra_cost_choices:
            pass
            # from models.choice_actions_all import ExtraCostChoice2
            # self.gs.pending_choice = ExtraCostChoice2(self)
        else:
            self.finish()

    def target_argument(self):
        if not self.targets:
            return None
        return self.targets[0] if len(self.targets) == 1 else self.targets

    def finish(self):
        """Pay costs; create the AbilityAction & push it onto the stack"""
        from models.actions.ability_pipeline import AbilityAction
        if self.origin == 'activated' and 'T' in self.eff_spec.cost:
            self.source.tap()
        mana_cost = self.source.casting_cost[:] if self.origin == 'spell' else self.eff_spec.cost
        mana_cost = mana_cost.replace('X', str(self.x_value)) if self.x_value else mana_cost
        if mana_cost:
            self.gs.mana_pools[self.p_id].pay(mana_cost)
        for extra_cost in (self.eff_spec.extra_costs or []):
            extra_cost.pay(self.gs, self.source)

        action = AbilityAction(self.p_id, self.gs, self)
        if 'Land' in self.source.card_types:
            self.gs.turn_mgr.has_played_land = True
            action.play()
        else:
            self.gs.action_stack.push(action, self.gs)
        self.gs.event_mgr.emit(StateBasedEvent(), self.gs)

    def resolve_ability(self):

        if isinstance(self.eff_spec.effect, Resolver):
            self.eff_spec.effect.resolve(self.gs, self.source, self.target_argument())

        if self.origin == 'activated':
            print(f"Successfully activated ability for {self.source.props.name}")
            aa = next(aa for aa in self.source.activated_abilities if aa.eff_spec is self.eff_spec)
            aa.activations_this_turn += 1
            self.gs.event_mgr.emit(AbilityActivatedEvent(self.p_id, aa), self.gs)

        if self.source.zone != Zone.HAND:
            print(f"Successfully executed ability for {self.source.props.name}")

        if self.source.zone == Zone.HAND:
            print(f"Successfully cast {self.source.props.name}")
            if self.source.props.is_permanent:
                self.gs.pile_mgr.move_card(self.source, Zone.BATTLEFIELD, cause='cast')

            self.gs.event_mgr.emit(CastResolvedEvent(self.source, self.source.orig_owner_id, None), self.gs)

            if 'Aura' in self.source.card_sub_types:
                host = self.targets[0]
                self.source.host = host
                host.auras.append(self.source)

            from models.effects.base import Listener
            for eff_spec in self.source.abilities:
                if isinstance(eff_spec.effect, Listener):
                    self.gs.event_mgr.register(eff_spec.effect, self.source)
                    print(f"Registered listener for {self.source.props.name}: {eff_spec.effect.__class__.__name__}")

            if not self.source.props.is_permanent:
                self.gs.pile_mgr.move_card(self.source, Zone.GRAVEYARD, cause='cast')

        self.gs.event_mgr.emit(StateBasedEvent(), self.gs)

    @property
    def needs_x(self) -> bool:
        # if you have selected an x_value, you no longer need to be in this flow
        if self.x_value is not None:
            return False
        if self.origin == 'spell' and 'X' in self.source.casting_cost:
            return True
        if self.origin == 'activated' and 'X' in self.eff_spec.cost:
            return True
        return False

    @property
    def needs_mode(self) -> bool:
        return False
        # TODO: implement "modes"

    @property
    def needs_targets(self) -> bool:
        if self.eff_spec.target_spec is None:
            return False
        return len(self.targets) < self.eff_spec.target_spec.min_cnt

    @property
    def needs_extra_cost_choices(self) -> bool:
        if not self.eff_spec.extra_costs:
            return False
        return any(cost.requires_choice for cost in self.eff_spec.extra_costs)

    def get_x_range(self) -> tuple[int, int]:
        # TODO: the below line is a placeholder, using a random large number of "10", just to get through some tests
        max_x = 10 if not self.eff_spec.max_x_func else self.eff_spec.max_x_func(self.gs, self.source)
        return self.eff_spec.min_x_func(self.gs, self.source), max_x
