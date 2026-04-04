from dataclasses import dataclass

from models.actions.activate_ability import ActivateAbility
from models.actions.base import Action
from models.actions.cast import CastToTargetAddToStack
from models.effects.base import ActivatedAbility
from models.events_all import CastResolvedEvent
from models.zone import Zone
from models.utils import flip


@dataclass
class AcceptAction(Action):
    def __repr__(self) -> str:
        return f"Accept {self.gs.action_stack.last_action}"

    def play(self) -> None:
        last_action: CastToTargetAddToStack | ActivateAbility = self.gs.action_stack.last_action
        target = last_action.target if hasattr(last_action, 'target') else None

        if isinstance(last_action, ActivateAbility):
            if isinstance(target, list):
                for t in target:
                    last_action.ability.eff_spec.effect.resolve(self.gs, last_action.ability.source, t)
            else:
                last_action.ability.eff_spec.effect.resolve(self.gs, last_action.ability.source, target)

            self.gs.action_on_idx = self.gs.action_stack.first_actor_idx  # action returns to the first actor
            self.gs.action_stack.clear_()
            return

        card = last_action.card
        if card.props.is_aura:
            card.attached_to = target
            target.modifiers.auras.append(card)

        if isinstance(last_action, CastToTargetAddToStack):
            if not last_action.eff_spec.effect:
                print('Warning:', last_action.card, 'has no effect')  # some cards do nothing on cast
            else:
                last_action.eff_spec.effect.resolve(self.gs, card, target)

        # # --- new system: resolve the card's own effect(s) ---
        # from models.card_attributes.card_effect_specs import INVOCATIONS
        # for eff_spec in INVOCATIONS.get(card.props.slug, []):
        #     if eff_spec.activation_type in ('activated', 'triggered'):
        #         # resolve immediately if it's a 'cast' effect
        #         if eff_spec.trigger_event is CastResolvedEvent and eff_spec.effect:
        #             eff_spec.effect.resolve(self.gs, card, target)

        # --- Emit event so other effects can respond ---
        print(f"Successfully cast {card.props.name}")
        self.gs.event_mgr.emit(CastResolvedEvent(card=card, owner_id=card.orig_owner_id, target=target), self.gs)

        # --- if permanent, add card to board, else graveyard ---
        zone = Zone.BATTLEFIELD if card.props.is_permanent else Zone.GRAVEYARD
        self.gs.move_card(card, zone, cause='cast')

        # --- register triggered effects --- is this the best place to do this?, where are static effect being reg'ed?
        from models.card_attributes.card_effect_specs import INVOCATIONS
        for eff_spec in INVOCATIONS.get(card.props.slug, []):
            if eff_spec.activation_type == 'triggered' and eff_spec.trigger_event:
                self.gs.event_mgr.register_effect(eff_spec.effect, card)
                print(f"Registered triggered effect for {card.props.name} on {eff_spec.trigger_event.__name__}")

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
