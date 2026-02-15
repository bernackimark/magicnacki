from dataclasses import dataclass

from models.actions.activate_ability import ActivateAbility
from models.actions.base import Action
from models.actions.cast import CastToTargetAddToStack
from models.effects.base import ActivatedAbility
from models.card_attributes.card_effect_specs import INVOCATIONS
from models.events.events_all import CastResolvedEvent, EnterBattlefieldEvent
from models.zone import Zone
from utils import flip


@dataclass
class AcceptAction(Action):
    def __repr__(self) -> str:
        return f"Accept {self.gs.action_stack.last_action}"

    def play(self) -> None:
        last_action: CastToTargetAddToStack | ActivateAbility = self.gs.action_stack.last_action
        target = last_action.target if hasattr(last_action, 'target') else None

        if isinstance(last_action, ActivateAbility):
            if last_action.x_value is not None:
                last_action.ability.eff_spec.effect.resolve(self.gs, last_action.ability.source, target, last_action.x_value)
            else:
                last_action.ability.eff_spec.effect.resolve(self.gs, last_action.ability.source, target)
            self.gs.action_on_idx = self.gs.action_stack.first_actor_idx  # action returns to the first actor
            self.gs.action_stack.clear_()
            return

        card = last_action.card
        if card.props.is_aura:
            card.attached_to = target
            target.modifiers.auras.append(card)

        # --- new system: resolve the card's own effect(s) ---
        for eff_spec in INVOCATIONS.get(card.props.slug, []):
            if eff_spec.activation_type in ('activated', 'triggered'):
                # resolve immediately if it's a 'cast' effect
                if eff_spec.trigger_event is CastResolvedEvent and eff_spec.effect:
                    eff_spec.effect.resolve(self.gs, card, target)

        # --- Emit event so other effects can respond ---
        print(f"Successfully cast {card.props.name}")
        self.gs.emit(CastResolvedEvent(card=card, owner_id=card.orig_owner_id, target=target))

        # --- register triggered effects ---
        if card.props.slug in INVOCATIONS:
            for eff_spec in INVOCATIONS[card.props.slug]:
                # Only register triggered effects
                if eff_spec.activation_type == 'triggered' and eff_spec.trigger_event:
                    self.gs.register_effect(eff_spec.effect, card)
                    print(f"Registered triggered effect for {card.props.name} on {eff_spec.trigger_event}")

        # --- register activated abilities ---
        for eff_spec in INVOCATIONS.get(card.props.slug, []):
            if eff_spec.activation_type == 'activated':
                ability = ActivatedAbility(card, eff_spec)
                card.activated_abilities.append(ability)

        # --- if permanent, add card to board, else graveyard ---
        if card.props.is_permanent:
            self.gs.move_card(card, Zone.BATTLEFIELD, cause='cast')
        else:
            self.gs.move_card(card, Zone.GRAVEYARD, cause='cast')

        # --- reset action stack and current actor ---
        self.gs.action_on_idx = self.gs.action_stack.first_actor_idx  # action returns to the first actor
        self.gs.action_stack.clear_()


@dataclass
class CounterAction(Action):
    action: Action

    def __repr__(self) -> str:
        return f"In response to {self.gs.action_stack.last_action}: {self.action}"

    def play(self) -> None:
        self.gs.action_stack.push(self.action, self.gs)
        self.gs.action_on_idx = flip(self.gs.action_on_idx)
