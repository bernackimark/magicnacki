from dataclasses import dataclass

from constants import BASIC_LAND_MANA_PRODUCED
from models.actions.base import Action
from models.card_attributes.card_effect_specs import INVOCATIONS
from models.effects.base import ActivatedAbility
from models.events.events_all import StateBasedEvent, CastResolvedEvent
from models.game_card import GameCard
from models.zone import Zone


@dataclass
class CastToBoard(Action):
    card: GameCard
    x_values_for_variable_cast: int | None = None

    def __repr__(self) -> str:
        variable_cast_text = '' if not self.x_values_for_variable_cast else f', X={self.x_values_for_variable_cast}'
        return f"Cast {self.card.props.name}{variable_cast_text}"

    def play(self) -> None:
        if self.x_values_for_variable_cast is not None:
            cast_cost = self.card.props.casting_cost[:].replace('X', str(self.x_values_for_variable_cast))
            self.gs.mana_pools[self.player_idx].pay(cast_cost)
            self.card.variable_x = self.x_values_for_variable_cast
        else:
            self.gs.mana_pools[self.player_idx].pay(self.card.props.casting_cost)
        if self.card.props.is_land:
            self.gs.turn.has_played_land = True

        # --- AUTO-ACCEPTING CAST TO BOARD FOR SPEED OF TESTING ---
        print(f"Successfully cast {self.card.props.name}")
        self.gs.move_card(self.card, Zone.BATTLEFIELD, cause='cast')

        # --- new event/phase-aware registration
        if self.card.props.slug in INVOCATIONS:
            for eff_spec in INVOCATIONS[self.card.props.slug]:
                # I need this because I'm allowing card to go straight to the board w/o hitting the stack
                if eff_spec.activation_type != 'triggered':
                    continue
                if eff_spec.trigger_event == CastResolvedEvent:
                    targets = eff_spec.target_filter() if eff_spec.target_filter else None
                    eff_spec.effect.resolve(self.gs, self.card, targets)
                    print(f"Activated the ability on cast for {self.card.props.name}")
                else:
                    # Only register the triggered effects
                    self.gs.register_effect(eff_spec.effect, self.card)
                    print(f"Registered triggered effect for {self.card.props.name} on {eff_spec.trigger_event}")

        # --- if card has activated abilities, add them to the board
        for eff_spec in INVOCATIONS.get(self.card.props.slug, []):
            if eff_spec.activation_type == 'activated':
                ability = ActivatedAbility(self.card, eff_spec)
                self.card.activated_abilities.append(ability)

        # --- new event emission approach: now the effect itself is phase-agnostic
        self.gs.emit(StateBasedEvent())


@dataclass
class CastToTargetAddToStack(Action):
    card: GameCard
    target: GameCard | list[GameCard] | None
    x_values_for_variable_cast: int | None = None

    def __post_init__(self):
        self.card.variable_x = self.x_values_for_variable_cast

    def __repr__(self) -> str:
        target_text, variable_cast_text = '', ''
        if isinstance(self.target, list) and self.target:
            target_text = f", targeting {', '.join([c.props.name for c in self.target])}"
        elif isinstance(self.target, GameCard):
            target_text = ', targeting ' + self.target.props.name
        elif isinstance(self.target, int):
            target_text = f', targeting Player #{self.target}'
        if self.x_values_for_variable_cast is not None:
            variable_cast_text = f", X={self.x_values_for_variable_cast}"
        return f"Cast {self.card.props.name}{target_text}{variable_cast_text}"

    def play(self) -> None:
        if self.x_values_for_variable_cast is not None:
            cast_cost = self.card.props.casting_cost[:].replace('X', str(self.x_values_for_variable_cast))
            self.gs.mana_pools[self.player_idx].pay(cast_cost)
            self.card.variable_x = self.x_values_for_variable_cast
        else:
            self.gs.mana_pools[self.player_idx].pay(self.card.props.casting_cost)
        self.gs.action_stack.push(self, self.gs)
        self.gs.emit(StateBasedEvent())


@dataclass
class CastCounter(Action):
    card: GameCard
    target: Action

    def __repr__(self):
        return f"Cast {self.card.props.name} to counter {self.target}"

    def play(self) -> None:
        self.gs.mana_pools[self.player_idx].pay(self.card.props.casting_cost)
        hand = self.gs.hands[self.player_idx]
        hand.cards.remove(self.card)
        self.gs.action_stack.push(self, self.gs)

        # --- new event emission approach
        for eff_spec in self.card.triggered_abilities:
            self.gs.register_effect(eff_spec.effect, self.card)
