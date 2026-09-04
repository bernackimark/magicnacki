from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Callable, Any, Optional

from models.actions.ability_pipeline_support import AbilityAction
from models.actions.stack_accept_counter import CounterSpellAction
from models.effects.listeners_mod_queries import OwnershipModQuery

if TYPE_CHECKING:
    from models.effects.base import Resolver, Modifier
    from models.game_card.game_card import GameCard
    from game_state import GameState

from models.choice_actions_all import ChoiceAction
from models.choice_options import CO, pay_mana_to_prevent_counter
from models.game_card.counter_tokens import CounterType
from models.effects.base import Listener, ResContext
from models.events_all import DamageResolvedEvent, EndStepEvent, UntapCardEvent, UntapPhaseEvent, UpkeepEvent, \
    ZoneChangeEvent, DamageProposedEvent, PassTheTurnEvent, StackAdditionEvent, \
    ModQueryEvent, DiesEvent, Event
from models.game_card.modifiers import PTMod
from models.utils import flip
from models.constants import Zone


class GenericEventListener(Listener):
    def __init__(self, event_type: type[Event], conditions: list, resolver: Resolver, modifier: Modifier,
                 t_func: Callable, expires: str | None = None):
        self.listens_to = event_type  # used during listener registration
        self.conditions = conditions
        self.resolver = resolver
        self.modifier = modifier
        self.t_func = t_func
        self.expires = expires

    def on_event(self, gs, source, event: Event):
        if self.conditions and not all(condition(gs, source, event) for condition in self.conditions):
            return
        if self.resolver and self.t_func is None:
            self.resolver.resolve(gs, source, context=ResContext(event=event))
        elif self.resolver and self.t_func:
            t = self.t_func(gs, source, event)
            self.resolver.resolve(gs, source, t=t, context=ResContext(event=event))
        if self.modifier:
            self.modifier.modify(gs, source, event)


# --- DAMAGE PROPOSED EVENT ---
# All remaining listeners in this Damage Proposed Section rely on the target,
# which is fed in through the secondary initializer & not yet a good candidate for the fluent pattern
class PreventAllDamageByEOT(Listener):
    """Declare damage_dealer at initialization if known by the spec;
     if targeted, ability pipeline will append via the secondary initializer"""
    listens_to = DamageProposedEvent
    expires = 'EOT'

    def __init__(self, damage_dealer: GameCard = None, combat_only: bool = False):
        self.damage_dealer = damage_dealer
        self.combat_only = combat_only

    def initialize(self, gs: GameState, source: GameCard, target: Any):
        if not self.damage_dealer:
            self.damage_dealer = target[0]

    def on_event(self, gs: GameState, source: GameCard, event: DamageProposedEvent) -> None:
        if event.source is not self.damage_dealer or (self.combat_only and not event.is_combat):
            return
        event.prevented += event.remaining
        event.remaining = 0

class PreventAllDamageToEOT(Listener):
    listens_to = DamageProposedEvent
    expires = 'EOT'

    def __init__(self, target: GameCard | None = None, combat_only: bool = False):
        self.target = target
        self.combat_only = combat_only

    def initialize(self, gs: GameState, source: GameCard, targets: Any):
        if self.target is None:
            self.target = targets[0]

    def on_event(self, gs: GameState, source: GameCard, event: DamageProposedEvent) -> None:
        if event.target is not self.target or (self.combat_only and not event.is_combat):
            return
        event.prevented += event.remaining
        event.remaining = 0

class PreventNextDamageBy(Listener):
    """Declare damage_dealer at initialization if known by the spec;
     if targeted, ability pipeline will append via the secondary initializer"""
    listens_to = DamageProposedEvent
    expires = 'EOT'

    def __init__(self, damage_dealer: GameCard = None, combat_only: bool = False, preventable_amt: int | None = None):
        self.damage_dealer = damage_dealer
        self.combat_only = combat_only
        self.preventable_amt = preventable_amt

    def initialize(self, gs: GameState, source: GameCard, target: Any):
        if not self.damage_dealer:
            self.damage_dealer = target[0]

    def on_event(self, gs: GameState, source: GameCard, event: DamageProposedEvent) -> None:
        if event.source is not self.damage_dealer or (self.combat_only and not event.is_combat):
            return
        if self.preventable_amt is None:
            event.prevented += 999999
        else:
            event.prevented += min(self.preventable_amt, event.remaining)
        event.remaining = event.amt - event.prevented
        self.is_expired = True

class PreventNextDamageTo(Listener):
    """If the protected entity is part of the spec (COP would be the source's owner), then provide in the initializer;
    if a target is selected, then it will be known in the ability pipeline and appended via the seconary initializer."""
    listens_to = DamageProposedEvent
    expires = 'EOT'

    def __init__(self, preventable_amt: int | None = None, combat_only: bool = False,
                 protected: Any = None):
        self.preventable_amt = preventable_amt
        self.combat_only = combat_only
        self.protected = protected

    def initialize(self, gs: GameState, source: GameCard, target: Any):
        if not self.protected:
            self.protected = target[0]

    def on_event(self, gs: GameState, source: GameCard, event: DamageProposedEvent) -> None:
        if event.target is not self.protected or (self.combat_only and not event.is_combat):
            return
        if self.preventable_amt is None:
            event.prevented += 999999
        else:
            event.prevented += min(self.preventable_amt, event.remaining)
        event.remaining = event.amt - event.prevented
        self.is_expired = True

class RedirectNextDamageToTarget(Listener):
    """You may declare a damage_dealer_func or inject a known damage_dealer GameCard upon secondary initialization"""
    listens_to = DamageProposedEvent
    expires = 'EOT'

    def __init__(self, protected_func: Callable, new_target_func: Callable,
                 damage_dealer_func: Optional[Callable] = None, redirectable_amt: int | None = None):
        self.protected_func = protected_func
        self.new_target_func = new_target_func
        self.damage_dealer_func = damage_dealer_func
        self.redirectable_amt = redirectable_amt
        self.damage_dealer = None

    def initialize(self, gs: GameState, source: GameCard, target: Any):
        if not self.damage_dealer_func:
            self.damage_dealer = target[0]

    def on_event(self, gs: GameState, source: GameCard, event: DamageProposedEvent) -> None:
        if event.remaining < 1:
            return
        if self.damage_dealer_func:
            self.damage_dealer = self.damage_dealer_func(gs, source)
        protected = self.protected_func(gs, source)
        if event.target is not protected:
            return
        new_target = self.new_target_func(gs, source)
        redirect_amt = min(self.redirectable_amt or 9999, event.remaining)
        event.remaining -= redirect_amt
        event.prevented += redirect_amt
        gs.apply_damage(event.source, redirect_amt, new_target)
        if self.redirectable_amt is not None:
            self.redirectable_amt -= redirect_amt
        self.is_expired = True

class RedirectNextDamageFromCardToOwnerEOT(Listener):
    """Protected card may be initialized in the EffSpec or via AbilityPipeline in the secondary initializer"""
    listens_to = DamageProposedEvent
    expires = 'EOT'

    def __init__(self, protected_card_func: Optional[Callable] = None, redirectable_amt: int | None = None):
        self.protected_card_func = protected_card_func
        self.redirectable_amt = redirectable_amt
        self.target = None

    def initialize(self, gs: GameState, source: GameCard, target: Any):
        if self.target is None:
            self.target = target[0]

    def on_event(self, gs: GameState, source: GameCard, event: DamageProposedEvent) -> None:
        protected_card = self.target or self.protected_card_func(gs, source)
        if event.target is not protected_card:
            return
        redirect_amt = min(self.redirectable_amt or 9999, event.remaining)
        event.remaining -= redirect_amt
        event.prevented += redirect_amt
        gs.apply_damage(source, redirect_amt, source.owner_id)
        if self.redirectable_amt is not None:
            self.redirectable_amt -= redirect_amt
        self.is_expired = True

# --- DIES EVENT ---
class ExileOnDeath(Listener):
    """If a card would die, it is exiled instead"""
    listens_to = DiesEvent

    def __init__(self, target: GameCard, eot: bool = False):
        self.target = target
        if eot:
            self.expires = 'EOT'

    def on_event(self, gs: GameState, source: GameCard, event: DiesEvent) -> None:
        if event.card is not self.target:
            return
        gs.pile_mgr.exile(event.card)

# --- END STEP ---
class BounceAtEndStep(Listener):
    """Bounce at end step if it is still on the battlefield at end step"""
    listens_to = EndStepEvent
    expires = 'EOT'

    def __init__(self, card_to_be_bounced: GameCard):
        self.card_to_be_bounced = card_to_be_bounced

    def on_event(self, gs: GameState, source: GameCard, event: EndStepEvent) -> None:
        if self.card_to_be_bounced not in gs.card_filter.in_play().result():
            return
        gs.pile_mgr.bounce(self.card_to_be_bounced)
        self.is_expired = True

class DestroyAtEndStep(Listener):
    """Destroys target if it is still on the battlefield at end step"""
    listens_to = EndStepEvent
    expires = 'EOT'

    def __init__(self, card_to_be_destroyed: GameCard):
        self.card_to_be_destroyed = card_to_be_destroyed

    def on_event(self, gs: GameState, s: GameCard, event: EndStepEvent):
        if self.card_to_be_destroyed not in gs.card_filter.in_play().result():
            return
        gs.pile_mgr.destroy(self.card_to_be_destroyed)
        self.is_expired = True

class DestroyAtEndStepIfItAttacked(Listener):
    """Destroy target at end step if it is still on the battlefield, and it attacked this turn"""
    listens_to = EndStepEvent
    expires = 'EOT'

    def __init__(self, target: GameCard):
        self.target = target

    def on_event(self, gs: GameState, source: GameCard, event: EndStepEvent) -> None:
        if self.target not in gs.card_filter.in_play().result():
            return
        if self.target not in gs.card_filter.attackers().result():
            return
        gs.pile_mgr.destroy(self.target)
        self.is_expired = True

class DestroyAtEndStepIfItDidntAttack(Listener):
    """Destroy target at end step if it is still on the battlefield, and it attacked this turn"""
    listens_to = EndStepEvent
    expires = 'EOT'

    def __init__(self, target: GameCard):
        self.target = target

    def on_event(self, gs: GameState, source: GameCard, event: EndStepEvent) -> None:
        if self.target not in gs.card_filter.in_play().result():
            return
        if self.target in gs.card_filter.attackers().result():
            return
        gs.pile_mgr.destroy(self.target)
        self.is_expired = True

# --- PASS THE TURN EVENT ---
class TakeAnotherTurn(Listener):
    listens_to = PassTheTurnEvent

    def on_event(self, gs: GameState, source: GameCard, event: PassTheTurnEvent) -> None:
        # need to unregister this way else 'EOT' effects expire in a phase before PassTheTurn
        from models.actions.advance_phase import PassTheTurn
        gs.event_mgr.unregister_specific_effect(self)
        PassTheTurn(source.owner_id, gs, pass_turn_to_opp=False).play()

# --- STACK ADDITION EVENT ---
class CounterEnchantments(Listener):
    """Listens for when something is added to the stack"""
    listens_to = StackAdditionEvent

    def on_event(self, gs: GameState, source: GameCard, event: StackAdditionEvent) -> None:
        print('A', type(event.action), event.action.pipeline.eff_spec, event.action.pipeline.eff_spec.is_spell)
        if isinstance(event.action, AbilityAction) and event.action.pipeline.eff_spec.is_aa:
            return
        source_card = event.action.pipeline.source if isinstance(event.action, AbilityAction) else event.action.source
        if not source_card.is_enchantment:
            return
        gs.action_stack.remove(event.action)
        gs.pile_mgr.move_card(source_card, Zone.GRAVEYARD, cause='fizzled', emit_zone_event=False)

class PayManaOrCounterSpellListener(Listener):
    """Listens for when something is added to the stack; mana_cost parm can be passed if static,
    else spell_mv can be used for the spell's mana value"""
    listens_to = StackAdditionEvent

    def __init__(self, mana_cost: str = None, spell_mv: bool = False):
        self.mana_cost = mana_cost
        self.spell_mv = spell_mv

    def on_event(self, gs: GameState, source: GameCard, event: StackAdditionEvent) -> None:
        if isinstance(event.action, AbilityAction) and not event.action.pipeline.eff_spec.is_spell:
            return
        target_spell = event.action
        p_id = target_spell.player_idx
        mana_cost = event.action.pipeline.source.casting_cost if self.spell_mv else self.mana_cost
        if not gs.mana_pools[p_id].can_pay(mana_cost):
            gs.action_stack.remove(event.action)
            gs.pile_mgr.move_card(target_spell.source, Zone.GRAVEYARD, cause='fizzled', emit_zone_event=False)
            return
        options = [CO(f'Pay {{{self.mana_cost}}} to prevent counterspell by {source}',
                      lambda: pay_mana_to_prevent_counter(gs, p_id, self.mana_cost, target_spell)),
                   CounterSpellAction(p_id, gs, target_spell)]
        gs.choice_mgr.queue(ChoiceAction(options, may=True))

# --- UNTAP CARD EVENT ---
class ReturnToOwnerOnUntap(Listener):
    """Ownership by virtue of an aura or the source being on the battlefield will auto-remove the mod upon LTB;
    This effect removes an ownership mod on any card the source was placed & xfers the stolen GameCard across boards"""
    listens_to = UntapCardEvent

    def on_event(self, gs: GameState, source: GameCard, event: UntapCardEvent):
        if source is not event.card:
            return
        steals: list[OwnershipModQuery] = [mqe.effect for mqe in gs.event_mgr.event_listeners.get(ModQueryEvent)
                                           if isinstance(mqe.effect, OwnershipModQuery) and mqe.source is source]
        for steal in list(steals):
            gs.event_mgr.unregister_specific_effect(steal)
            gs.pile_mgr.boards[source.owner_id].remove(steal.stolen_card)
            gs.pile_mgr.boards[flip(source.owner_id)].append(steal.stolen_card)

class UntapRemovesPumpFromAnotherCard(Listener):
    """If an effect targeted another card and its duration was for as long as the source is tapped,
    we untap here by polling all cards in play and seeing if they were given a Pump by this source"""
    listens_to = UntapCardEvent

    def on_event(self, gs: GameState, s: GameCard, event: UntapCardEvent):
        for c in gs.card_filter.in_play().result():
            for mod in list(c.modifiers):
                if mod.source is s and isinstance(mod, PTMod):
                    event.card.modifiers.remove(mod)


# --- UNTAP PHASE ---
class OptionalUntap(Listener):
    listens_to = UntapPhaseEvent

    def on_event(self, gs: GameState, source: GameCard, event: UntapPhaseEvent):
        if source.owner_id != event.active_player or not source.is_tapped:
            return
        options = [CO(f'Untap {source}', lambda: self.untap_and_log_decision(gs, source)),
                   CO(f'Leave {source} tapped', lambda: self.log_decision(gs, source))]
        # options = [Untap(event.active_player, gs, source), LeaveTapped(event.active_player, gs, source)]
        gs.choice_mgr.queue(ChoiceAction(options))

    @staticmethod
    def untap_and_log_decision(gs: GameState, card: GameCard):
        card.untap()
        gs.turn_mgr.untap_decisions_made.add(card.id_)

    @staticmethod
    def log_decision(gs: GameState, card: GameCard):
        gs.turn_mgr.untap_decisions_made.add(card.id_)

class UnregisterListenerOnYourNextTurn(Listener):
    listens_to = UntapPhaseEvent

    def __init__(self, listener: Listener):
        self.listener = listener

    def on_event(self, gs: GameState, source: GameCard, event: UntapPhaseEvent) -> None:
        if event.active_player != source.owner_id:
            return
        gs.event_mgr.unregister_specific_effect(self.listener)

# --- UPKEEP ---
class PayManaToUntapUpkeep(Listener):
    """Pay [x] to untap at target owner's upkeep"""
    listens_to = UpkeepEvent

    @dataclass
    class PayManaToUntapState:
        subject_cards: list[GameCard]
        handled_cards: list[GameCard] = field(default_factory=list)

        @property
        def remaining_cards(self) -> list[GameCard | None]:
            return [c for c in self.subject_cards if c not in self.handled_cards]

    def __init__(self, mana_cost: str, target_func: Callable):
        self.mana_cost = mana_cost
        self.target_func = target_func

    def on_event(self, gs: GameState, s: GameCard, event: UpkeepEvent) -> None:
        targets = self.target_func(gs, s)
        if not isinstance(targets, list):
            targets = [targets]
        target_owner = targets[0].owner_id
        if event.active_player != target_owner or not gs.mana_pools[target_owner].can_pay(self.mana_cost):
            return
        state = PayManaToUntapUpkeep.PayManaToUntapState(targets)
        self.queue_next_choice(gs, state)

    def queue_next_choice(self, gs: GameState, state: PayManaToUntapUpkeep.PayManaToUntapState):
        if not state.remaining_cards or not gs.mana_pools[gs.player_turn_idx].can_pay(self.mana_cost):
            return
        card = state.remaining_cards[0]
        mc = self.mana_cost
        options = [CO(f"Leave {card} tapped", lambda c=card: self.leave_tapped(gs, state, c)),
                   CO(f"Pay {mc} to untap {card}", lambda c=card: self.untap_card(gs, state, c))]
        gs.choice_mgr.queue(ChoiceAction(options))

    def untap_card(self, gs: GameState, state: PayManaToUntapUpkeep.PayManaToUntapState, c: GameCard):
        gs.mana_pools[c.owner_id].pay(self.mana_cost)
        c.untap()
        state.handled_cards.append(c)
        self.queue_next_choice(gs, state)

    def leave_tapped(self, gs: GameState, state: PayManaToUntapUpkeep.PayManaToUntapState, c: GameCard):
        state.handled_cards.append(c)
        self.queue_next_choice(gs, state)


# --- ZONE CHANGE ---
class LTBTandem(Listener):
    """When any card in the initialized tandem_cards LTB, all others are be destroyed w/o regeneration"""
    listens_to = ZoneChangeEvent

    def __init__(self, tandem_cards: list[GameCard], until_eot: bool = False):
        self.tandem_cards = tandem_cards
        if until_eot:
            self.expires = 'EOT'

    def on_event(self, gs: GameState, source: GameCard, event: ZoneChangeEvent) -> None:
        if event.card not in self.tandem_cards or event.from_zone != Zone.BATTLEFIELD or \
                event.to_zone == Zone.BATTLEFIELD:
            return
        gs.event_mgr.unregister_specific_effect(self)
        for tandem_card in self.tandem_cards:
            if tandem_card is event.card:
                continue
            if tandem_card not in gs.card_filter.in_play().result():
                continue
            gs.pile_mgr.destroy(tandem_card, allow_regeneration=False)

class ReturnToOwnerOnLTB(Listener):
    """Is generally called from Steal() Resolver; shouldn't be much need to use directly in slug-effect map"""
    listens_to = ZoneChangeEvent

    def __init__(self, new_zone: Zone = None):
        self.new_zone = new_zone or Zone.BATTLEFIELD

    def on_event(self, gs: GameState, source: GameCard, event: ZoneChangeEvent):
        if source is not event.card or event.from_zone != Zone.BATTLEFIELD or event.to_zone == Zone.BATTLEFIELD:
            return
        steals: list[OwnershipModQuery] = [mqe.effect for mqe in gs.event_mgr.event_listeners.get(ModQueryEvent)
                                           if isinstance(mqe.effect, OwnershipModQuery) and mqe.source is source]
        for steal in list(steals):
            gs.event_mgr.unregister_specific_effect(steal)
            gs.pile_mgr.boards[source.owner_id].remove(steal.stolen_card)
            gs.pile_mgr.boards[flip(source.owner_id)].append(steal.stolen_card)
