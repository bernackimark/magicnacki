from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any, TYPE_CHECKING, Union

from models.actions.base import Action
from models.cost import Cost
from models.effects.base import Resolver, ActivatedAbility, Listener
from models.events_all import StateBasedEvent, CastResolvedEvent, AbilityActivatedEvent
from models.zone import Zone

if TYPE_CHECKING:
    from models.effects.base import EffSpec
    from models.game_card.game_card import GameCard

@dataclass
class AbilityPipeline(Action):
    """Class the builds & shepherds an ability from the hand or activation.
    1) can_begin() determines whether an ability can be made
    2) advance() handles the selections for: X, mode, targets, and extra costs
    3) finish() pays costs &:
            if casting a land:
                land_played = True
                creates & plays CastPermanent (move card, emit Cast, reg listeners, emits StateBased).
                You are done; do not go to step 4.
            if not casting a land:
                creates an AbilityAction, pushes to stack, raises StateBasedEvent ... go to #4
    4) resolve_ability():
            if a resolver: executes effect.resolve()
            if an activated ability: activations += 1, emit ActivatedAbility
            if card in hand: move to battlfield/gy, emit CastResolved, attach aura, reg listeners, emit StateBased
            """
    source: GameCard
    eff_spec: EffSpec

    # values gathered while progressing
    x_value: int | None = None
    chosen_mode: int | None = None
    targets: list[Any] = field(default_factory=list)
    selected_extra_costs: list[Cost] = field(default_factory=list)

    # information produced by paying costs
    cost_result: Union["CostResult", None] = None

    # def __post_init__(self):
    #     if self.eff_spec and self.eff_spec.effect and not isinstance(self.eff_spec.effect, Resolver):
    #         raise TypeError(f"Effects in AbilityPipeline must be type Resolver, was provided: {self.eff_spec.effect}")

    def __repr__(self):
        if self.eff_spec.is_spell:
            return f'Cast {self.source.props.name}'
        elif self.eff_spec.is_aa:
            return f'{{{self.eff_spec.cost}}} Activate ability for {self.source.props.name}: {self.eff_spec.text}'

    def play(self) -> None:
        self.advance()

    def can_begin(self) -> bool:
        if self.eff_spec.allowed_p_turn_func is not None:
            if self.eff_spec.allowed_p_turn_func(self.gs, self.source) != self.gs.player_turn_idx:
                return False
        if self.eff_spec.allowed_phases:
            if self.gs.phase_mgr.phase not in self.eff_spec.allowed_phases:
                return False

        if self.eff_spec.effect and isinstance(self.eff_spec.effect, Resolver):
            if not self.eff_spec.effect.can_cast(self.gs, self.source):
                return False
            if not self.eff_spec.effect.can_activate(self.gs, self.source):
                return False

        if self.eff_spec.is_aa:
            if self.aa.activations_this_turn >= self.eff_spec.max_activations_per_turn:
                return False
            if self.source.has_summoning_sickness and 'T' in self.eff_spec.cost:
                return False

        min_x, max_x = self.get_x_range()
        if max_x < min_x:
            return False

        target_spec = self.eff_spec.target_spec
        if target_spec:
            targets = target_spec.get_targets(self.gs, self.source)
            if len(targets) < target_spec.min_cnt:
                return False

        if not self.gs.mana_pools[self.player_idx].can_pay(self.ability_cost):
            return False

        for extra_cost in self.eff_spec.extra_costs:
            if not extra_cost.can_pay(self.gs, self.source):
                return False

        return True

    def advance(self):
        """Advance the pipeline to the next unresolved step.
            Each branch either:
                1. Creates a pending ChoiceAction and returns, or
                2. Continues automatically if no user input is required."""
        print('Entering .advance()')
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
            from models.choice_actions_all import ExtraCostChoice2
            self.gs.pending_choice = ExtraCostChoice2(self)
        else:
            self.finish()

    def target_argument(self):
        if not self.targets:
            return None
        return self.targets[0] if len(self.targets) == 1 else self.targets

    def finish(self):
        """Pay costs; if casting a cast, CastPermanentAction.play() else create AbilityAction & push onto stack"""
        print('Entering .finish()')
        from models.actions.ability_pipeline_support import AbilityAction
        if self.eff_spec.is_aa and 'T' in self.eff_spec.cost:
            self.source.tap()
        mana_cost = self.ability_cost[::]
        mana_cost = mana_cost.replace('X', str(self.x_value)) if self.x_value else mana_cost
        if mana_cost:
            self.gs.mana_pools[self.player_idx].pay(mana_cost)
        for extra_cost in self.selected_extra_costs:
            extra_cost.pay(self.gs, self.source)

        action = AbilityAction(self.player_idx, self.gs, self)
        self.gs.action_stack.push(action, self.gs)
        self.gs.event_mgr.emit(StateBasedEvent())

    def resolve_ability(self):
        if isinstance(self.eff_spec.effect, Resolver):
            self.eff_spec.effect.resolve(self.gs, self.source, self.target_argument())

        if self.eff_spec.is_aa:
            aa = next(aa for aa in self.source.activated_abilities if aa.eff_spec is self.eff_spec)
            aa.activations_this_turn += 1
            print(f"Successfully activated ability for {self.source.props.name}")
            self.gs.event_mgr.emit(AbilityActivatedEvent(self.player_idx, aa))

        if isinstance(self.eff_spec.effect, Listener):
            print(f"Initializing Listener for {self.source}")
            self.eff_spec.effect.initialize(self.gs, self.source, self.targets)
            self.gs.event_mgr.register(self.eff_spec.effect, self.source)

        if self.source.zone != Zone.HAND:
            print(f"Successfully executed ability for {self.source.props.name}")

        if self.source.zone == Zone.HAND:
            print(f"Successfully cast {self.source.props.name}")
            if self.source.props.is_permanent:
                self.gs.pile_mgr.move_card(self.source, Zone.BATTLEFIELD, cause='cast')

            self.gs.event_mgr.emit(CastResolvedEvent(self.source, self.source.orig_owner_id, None))

            if 'Aura' in self.source.card_sub_types:
                host = self.targets[0]
                self.source.host = host
                host.auras.append(self.source)

            for eff_spec in self.source.abilities:
                if eff_spec is self.eff_spec:
                    continue
                if eff_spec.is_aa or not isinstance(eff_spec.effect, Listener):
                    continue
                if eff_spec is self.eff_spec:
                    print(f"AbilityPipeline.resolve_ability() is initializing Listener for {self.source}")
                    eff_spec.effect.initialize(self.gs, self.source, self.targets)
                self.gs.event_mgr.register(eff_spec.effect, self.source)

            if not self.source.props.is_permanent:
                self.gs.pile_mgr.move_card(self.source, Zone.GRAVEYARD, cause='cast')

        self.gs.event_mgr.emit(StateBasedEvent())

    @property
    def ability_cost(self) -> str:
        return self.source.casting_cost if self.eff_spec.is_spell else self.eff_spec.cost

    @property
    def aa(self) -> ActivatedAbility | None:
        return next(aa for aa in self.source.activated_abilities if aa.eff_spec is self.eff_spec)

    @property
    def needs_x(self) -> bool:
        # if you have selected an x_value, you no longer need to be in this flow
        if self.x_value is not None:
            return False
        if 'X' in self.ability_cost:
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
        return len(self.selected_extra_costs) < len(self.eff_spec.extra_costs)

    def get_x_range(self) -> tuple[int, int]:
        # TODO: the below line is a placeholder, using a random large number of "10", just to get through some tests
        max_x = 10 if not self.eff_spec.max_x_func else self.eff_spec.max_x_func(self.gs, self.source)
        return self.eff_spec.min_x_func(self.gs, self.source), max_x
