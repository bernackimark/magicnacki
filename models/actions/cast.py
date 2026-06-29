from __future__ import annotations
from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from models.game_card.game_card import GameCard

from models.actions.base import Action
from models.effects.base import EffSpec
from models.events_all import StateBasedEvent, CastResolvedEvent
from models.zone import Zone


@dataclass
class CastToBoard(Action):
    """Lands are special; their cast bypasses the stack"""
    card: GameCard
    x_values_for_variable_cast: int | None = None

    def __repr__(self) -> str:
        variable_cast_text = '' if not self.x_values_for_variable_cast else f', X={self.x_values_for_variable_cast}'
        return f"Cast {self.card.props.name}{variable_cast_text}"

    def play(self) -> None:
        if self.x_values_for_variable_cast is not None:
            cast_cost = self.card.casting_cost[:]
            cast_cost = cast_cost.replace('X', str(self.x_values_for_variable_cast))
            self.gs.mana_pools[self.player_idx].pay(cast_cost)
            self.card.extras['x'] = self.x_values_for_variable_cast
        else:
            self.gs.mana_pools[self.player_idx].pay(self.card.casting_cost)
        if self.card.props.is_land:
            self.gs.turn_mgr.has_played_land = True

        # --- AUTO-ACCEPTING CAST TO BOARD FOR SPEED OF TESTING ---
        print(f"Successfully cast {self.card.props.name}")
        self.gs.pile_mgr.move_card(self.card, Zone.BATTLEFIELD, cause='cast')

        # --- new event/phase-aware registration
        from models.game_card.slug_effect_map import INVOCATIONS
        from models.effects.base import Listener
        if self.card.props.slug in INVOCATIONS:
            for eff_spec in INVOCATIONS[self.card.props.slug]:
                # I need this because I'm allowing card to go straight to the board w/o hitting the stack
                # NOTE: for a card like Jihad with a Spell() & a listener ... the listener must be listed 1st
                # in the slug-effects list, else it won't be reached because Jihad's ETB never cedes control back here
                if isinstance(eff_spec.effect, Listener):
                    self.gs.event_mgr.register(eff_spec.effect, self.card)
                if eff_spec.activation_type != 'triggered':
                    continue

                if eff_spec.activation_type == 'spell':
                    target_spec = eff_spec.target_spec

                    if target_spec is None:
                        eff_spec.effect.resolve(self.gs, self.card, None)
                        return

                    candidates = target_spec.filter_func(self.gs, self.card)

                    # --- exactly 1 target (legacy behavior) ---
                    if target_spec.min_cnt == 1 and target_spec.max_cnt == 1:
                        if candidates is None:
                            return  # fizzles silently
                        target = candidates[0] if isinstance(candidates, list) else candidates
                        eff_spec.effect.resolve(self.gs, self.card, target)
                        return

                    # --- multi-target or open-ended
                    from models.choice_actions_all import MultiTargetChoice
                    self.gs.pending_choice = MultiTargetChoice(self.card.owner_id, self.gs, self.card, eff_spec)
                    print(f"Activated the ability on cast for {self.card.props.name}")

        self.gs.event_mgr.emit(StateBasedEvent(), self.gs)
        self.gs.event_mgr.emit(CastResolvedEvent(self.card, self.card.orig_owner_id, None), self.gs)


@dataclass
class CastToTargetAddToStack(Action):
    card: GameCard
    target: GameCard | list[GameCard] | None
    eff_spec: EffSpec | None = None
    text: str = ''

    # TODO: right now, activated abilities are following this path.  Need to determine if that's correct ...
    #  if so, the repr shouldn't say "Cast", the class name shouldn't include "Cast", etc.

    def __repr__(self) -> str:
        from models.target import create_target_text
        variable_cast_text = ''
        if self.card.extras.get('x') is not None:
            variable_cast_text = f", X={self.card.extras.get('x')}"
        if not self.target:
            return f"Cast {self.card.props.name} {self.text}{variable_cast_text}"
        target_text = create_target_text(self.target)
        return f"Cast {self.card.props.name} {self.text}{target_text}{variable_cast_text}"

    def play(self) -> None:
        if self.card.extras.get('x'):
            cast_cost = self.card.casting_cost[:]
            cast_cost = cast_cost.replace('X', str(self.card.extras.get('x')))
            self.gs.mana_pools[self.player_idx].pay(cast_cost)
        else:
            self.gs.mana_pools[self.player_idx].pay(self.card.casting_cost)
        self.gs.action_stack.push(self, self.gs)
        self.gs.event_mgr.emit(StateBasedEvent(), self.gs)


@dataclass
class CastCounter(Action):
    card: GameCard
    target: Action

    def __repr__(self):
        return f"Cast {self.card.props.name} to counter {self.target}"

    def play(self) -> None:
        self.gs.mana_pools[self.player_idx].pay(self.card.casting_cost)
        hand = self.gs.pile_mgr.hands[self.player_idx]
        hand.cards.remove(self.card)
        self.gs.action_stack.push(self, self.gs)

        # --- new event emission approach
        for eff_spec in self.card.abilities:
            self.gs.event_mgr.register(eff_spec.effect, self.card)

@dataclass
class BeginSpellCastAction(Action):
    card: GameCard
    eff_spec: EffSpec | None

    def __repr__(self):
        return f'Cast {self.card.props.name}'

    def play(self) -> None:
        """Determines which pipeline to enter"""
        # --- X selection first (if needed)
        if self.eff_spec and 'X' in self.card.casting_cost:
            from models.choice_actions_all import XValueChoice

            min_x = self.eff_spec.min_x_func(self.gs, self.card)
            max_x = self.eff_spec.max_x_func(self.gs, self.card) // self.card.casting_cost.count('X')  # for double X
            x_options = [i for i in range(min_x, max_x + 1)]

            self.gs.pending_choice = XValueChoice(self.player_idx, self.gs, self.card, x_options, self.eff_spec)
            return

        # --- Targeting ---
        if self.eff_spec and self.eff_spec.target_spec:
            from models.choice_actions_all import MultiTargetChoice
            self.gs.pending_choice = MultiTargetChoice(self.player_idx, self.gs, self.card, self.eff_spec)
            return

        # --- No targeting → cast immediately ---
        self.gs.action_stack.push(CastToTargetAddToStack(self.player_idx, self.gs, self.card,
                                                         target=None, eff_spec=self.eff_spec), self.gs)
