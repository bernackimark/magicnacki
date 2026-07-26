from __future__ import annotations
from typing import TYPE_CHECKING, Callable, Any

from models.actions.ability_pipeline_support import AbilityAction
from models.actions.base import DoNothing
from models.actions.cast import CastPermanentAction
from models.actions.destroy_sac_regen import Sac
from models.actions.mana import PayMana
from models.actions.special import PayManaForLife, PayManaToPreventCounter
from models.actions.stack_accept_counter import CounterSpellAction

if TYPE_CHECKING:
    from models.game_card.game_card import GameCard
    from game_state import GameState

from models.actions.tap_untap import LeaveTapped, Untap, PayManaToUntapAction
from models.choice_actions_all import ChoiceAction
from models.counter_tokens import CounterType
from models.effects.base import Listener
from models.effects.resolvers_generic import Steal
from models.events_all import CastResolvedEvent, CombatEndEvent, DamageResolvedEvent, EndStepEvent, UntapCardEvent, \
    UntapPhaseEvent, UpkeepEvent, ZoneChangeEvent, DamageProposedEvent, PassTheTurnEvent, \
    CanAttackQueryEvent, AttackEvent, BlockEvent, StackAdditionEvent, Event
from models.modifiers import OwnershipMod, PTMod
from models.utils import flip
from models.zone import Zone


# -- BLOCK EVENT ---
class DestroyCombatantAtCombatEnd(Listener):
    """Ex: Destroying combatant func would return Cockatrice; destroyable func would return non-walls;
    if such a combat is found, all matching creatures against Cockatrice would be destroyed at combat end"""
    listens_to = BlockEvent

    def __init__(self, destroying_combatant_func: Callable, destroyable_func: Callable | None = None):
        self.destroying_combatant_func = destroying_combatant_func
        self.destroyable_func = destroyable_func

    def on_event(self, gs: GameState, source: GameCard, event: BlockEvent) -> None:
        destroying_combatant = self.destroying_combatant_func(gs, source)
        com = gs.combat_mgr.get_combat(destroying_combatant)
        if not com:
            return
        combatants_against = gs.combat_mgr.get_combatants_against(destroying_combatant)
        if not self.destroyable_func:
            for combatant_against in combatants_against:
                delayed = DestroyAtCombatEnd(source, combatant_against)
                gs.event_mgr.register(delayed, source)
                return
        to_be_destroyed = self.destroyable_func(gs, source)
        for combatant_against in combatants_against:
            if combatant_against in to_be_destroyed:
                delayed = DestroyAtCombatEnd(source, combatant_against)
                gs.event_mgr.register(delayed, source)


# --- CAN ATTACK QUERY EVENT ---
class CantAttackIfAttackedLastTurn(Listener):
    """This creature can't attack if it attacked during your last turn"""
    listens_to = CanAttackQueryEvent

    def on_event(self, gs: GameState, source: GameCard, event: CanAttackQueryEvent) -> None:
        if source is not event.attacker:
            return
        p_last_turn_num = gs.turn_mgr.get_players_last_turn_num(source.owner_id)
        for e, turn_num in gs.event_mgr.events[::-1]:
            if turn_num == p_last_turn_num:
                if isinstance(e, AttackEvent) and e.attacker is source:
                    event.permission = False


# --- CAST EVENT ---
class OnColorSpellGainLife(Listener):
    """Whenever a player casts a [certain color] spell, you gain 1 life"""
    listens_to = CastResolvedEvent

    def __init__(self, color: str, life_amt: int = 1):
        self.color = color
        self.life_amt = life_amt

    def on_event(self, gs: GameState, s: GameCard, event: CastResolvedEvent):
        if self.color not in event.card.props.colors:
            return
        gs.score_mgr.increment_life(s.owner_id, self.life_amt, s, gs)


class OnColorSpellPayOneColorlessForOneLifeChoice(Listener):
    """Whenever a player casts a [certain color] spell, you may {1}: Gain 1 life"""
    listens_to = CastResolvedEvent

    def __init__(self, color: str):
        self.color = color

    def on_event(self, gs: GameState, s: GameCard, event: CastResolvedEvent):
        if self.color not in event.card.props.colors:
            return
        if not gs.mana_pools[s.owner_id].can_pay('1'):
            return
        options = [PayManaForLife(s.owner_id, gs, '1', 1), DoNothing(s.owner_id, gs)]
        gs.pending_choice = ChoiceAction(options)


# --- COMBAT END ---
class DestroyAtCombatEnd(Listener):
    """Destroys target if it is still on the battlefield; unregisters itself"""
    listens_to = CombatEndEvent

    def __init__(self, source: GameCard, target: GameCard):
        self.source = source
        self.target = target

    def on_event(self, gs: GameState, s: GameCard, event: CombatEndEvent):
        if self.target.zone == Zone.BATTLEFIELD:
            gs.pile_mgr.destroy(self.target)
        gs.event_mgr.unregister_specific_effect(self)


# --- DAMAGE PROPOSED EVENT ---
class PreventCombatDamageFromItsAttackers(Listener):
    listens_to = DamageProposedEvent

    def on_event(self, gs: GameState, source: GameCard, event: DamageProposedEvent) -> None:
        if not event.is_combat or source is not event.target:
            return
        event.prevented += event.remaining
        event.remaining = 0

class PreventAllDamage(Listener):
    listens_to = DamageProposedEvent

    def __init__(self, protected_func: Callable, dealer_func: Callable, combat_only: bool = False):
        self.protected_func = protected_func
        self.dealer_func = dealer_func
        self.combay_only = combat_only

    def on_event(self, gs: GameState, source: GameCard, event: DamageProposedEvent) -> None:
        if self.combay_only and not event.is_combat:
            return
        protected = self.protected_func(gs, source)
        if not isinstance(protected, list):
            protected = [protected]
        dealers = self.dealer_func(gs, source)
        if not isinstance(dealers, list):
            dealers = [dealers]
        if event.source in dealers and event.target in protected:
            event.prevented += event.remaining
            event.remaining = 0

class PreventAllDamageEOT(Listener):
    # new: 7/16/2026: flexible class to consolidate micro-variations
    listens_to = DamageProposedEvent
    expires = 'EOT'

    def __init__(self, protected_func: Callable = None, dealer_func: Callable = None, combat_only: bool = False):
        self.protected_func = protected_func
        self.dealer_func = dealer_func
        self.combay_only = combat_only

    def on_event(self, gs: GameState, source: GameCard, event: DamageProposedEvent) -> None:
        if self.combay_only and not event.is_combat:
            return
        if not self.protected_func and not self.dealer_func:
            event.prevented += event.remaining
            event.remaining = 0
            return
        protected = self.protected_func(gs, source)
        if not isinstance(protected, list):
            protected = [protected]
        dealers = self.dealer_func(gs, source)
        if not isinstance(dealers, list):
            dealers = [dealers]
        if event.source in dealers and event.target in protected:
            event.prevented += event.remaining
            event.remaining = 0

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

    def __init__(self, combat_only: bool = False):
        self.combat_only = combat_only
        self.target: GameCard | None = None

    def initialize(self, gs: GameState, source: GameCard, targets: Any):
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

class RedirectNextDamageFromCardToOwnerEOT(Listener):
    """Protected card may be initialized in the EffSpec or via AbilityPipeline in the secondary initializer"""
    listens_to = DamageProposedEvent
    expires = 'EOT'

    def __init__(self, protected_card_func: Callable | None = None, redirectable_amt: int | None = None):
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

# --- DAMAGE RESOLVED EVENT ---
class AddPoisonCounter(Listener):
    """Whenever creature deals damage to a player, that player gets poison counter(s)"""
    listens_to = DamageResolvedEvent

    def __init__(self, cnt: int = 1):
        self.cnt = cnt

    def on_event(self, gs: GameState, source: GameCard, event: DamageResolvedEvent):
        opp = flip(source.owner_id)
        if event.source is source and event.target == opp:
            print(f"{event.source.props.name} adds {self.cnt} poison counter(s) to Player #{opp}. "
                  f"Poison Totals: {gs.score_mgr.poison_counters}")
            gs.score_mgr.add_poison_counter(opp, self.cnt)


# --- END STEP ---
class AddCounterAtEndStep(Listener):
    """Add counter to target if it is still on the battlefield"""
    listens_to = EndStepEvent

    def __init__(self, source: GameCard, target: GameCard, counter_type: CounterType, cnt: int = 1):
        self.source = source
        self.target = target
        self.counter_type = counter_type
        self.cnt = cnt

    def on_event(self, gs: GameState, s: GameCard, event: EndStepEvent):
        if self.target.zone != Zone.BATTLEFIELD:
            return
        self.target.counters.add_counter(self.counter_type, self.cnt)
        gs.event_mgr.unregister_specific_effect(self)

class AddCounterPerCreatureDeathAtEndStep(Listener):
    """At the beginning of each end step, put a counter on this creature for each creature that died this turn"""
    listens_to = EndStepEvent

    def __init__(self, counter_type: CounterType):
        self.counter_type = counter_type

    def on_event(self, gs: GameState, source: GameCard, event: EndStepEvent) -> None:
        if death_cnt := len(gs.turn_mgr.cards_that_died) > 0:
            source.counters.add_counter(self.counter_type, death_cnt)

class AddCountersIfAnyCreatureDied(Listener):
    """At each end step, if a creature died this turn, put a counter on this creature"""
    listens_to = EndStepEvent

    def __init__(self, counter_type: CounterType, cnt: int = 1):
        self.counter_type = counter_type
        self.cnt = cnt

    def on_event(self, gs: GameState, source: GameCard, event: EndStepEvent) -> None:
        if gs.turn_mgr.cards_that_died:
            source.counters.add_counter(self.counter_type, self.cnt)

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
        from models.actions.end_step_pass_turn import PassTheTurn
        gs.event_mgr.unregister_specific_effect(self)
        PassTheTurn(source.owner_id, gs, pass_turn_to_opp=False).play()

# --- STACK ADDITION EVENT ---
class PayManaOrCounterSpellListener(Listener):
    """Listens for when something is added to the stack"""
    listens_to = StackAdditionEvent

    def __init__(self, mana_cost: str):
        self.mana_cost = mana_cost

    def on_event(self, gs: GameState, source: GameCard, event: StackAdditionEvent) -> None:
        if isinstance(event.action, AbilityAction) and not event.action.pipeline.eff_spec.is_spell:
            return
        target_spell = event.action
        p_id = target_spell.player_idx
        if not gs.mana_pools[p_id].can_pay(self.mana_cost):
            gs.action_stack.remove(event.action)
            gs.pile_mgr.move_card(target_spell.source, Zone.GRAVEYARD, cause='fizzled', emit_zone_event=False)
            return
        options = [PayManaToPreventCounter(p_id, gs, target_spell, self.mana_cost),
                   CounterSpellAction(p_id, gs, target_spell)]
        gs.pending_choice = ChoiceAction(options)

# --- UNTAP CARD EVENT ---
class ReturnToOwnerOnUntap(Listener):
    """Ownership by virtue of an aura or the source being on the battlefield will auto-remove the mod upon LTB;
    This effect removes an ownership mod on any card the source was placed & xfers the stolen GameCard across boards"""
    listens_to = UntapCardEvent

    def on_event(self, gs: GameState, source: GameCard, event: UntapCardEvent):
        if source is not event.card:
            return
        for c in gs.pile_mgr.boards[source.owner_id]:
            for mod in c.modifiers.iter_type_reverse(OwnershipMod):
                c.modifiers.remove(mod)
                gs.pile_mgr.boards[source.owner_id].remove(c)
                gs.pile_mgr.boards[flip(source.owner_id)].append(c)
                return

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
        options = [Untap(event.active_player, gs, source), LeaveTapped(event.active_player, gs, source)]
        gs.pending_choice = ChoiceAction(options)


# --- UPKEEP ---
class AddCounterAtTargetUpkeep(Listener):
    """At target owner's upkeep, put counter(s) on this card"""
    listens_to = UpkeepEvent

    def __init__(self, target_func: Callable[..., GameCard], counter_type: CounterType, amt: int = 1):
        self.target_func = target_func
        self.counter_type = counter_type
        self.amt = amt

    def on_event(self, gs: GameState, source: GameCard, event: UpkeepEvent) -> None:
        target = self.target_func(gs, source)
        if target is None:
            return
        if event.active_player != target.owner_id:
            return
        target.counters.add_counter(self.counter_type, self.amt)

class DealDamageOnEveryUpkeep(Listener):
    listens_to = UpkeepEvent

    def __init__(self, target: GameCard | int, amt: int):
        self.target = target
        self.amt = amt

    def on_event(self, gs: GameState, source: GameCard, event: UpkeepEvent):
        gs.apply_damage(source, self.amt, self.target)

class DealDamageToOwnerOnUpkeep(Listener):
    listens_to = UpkeepEvent

    def __init__(self, amount: int):
        self.amount = amount

    def on_event(self, gs: GameState, source: GameCard, event: UpkeepEvent):
        if gs.player_turn_idx != source.owner_id:
            return
        gs.apply_damage(source, self.amount, source.owner_id)


class DealDamageOnHostUpkeep(Listener):
    listens_to = UpkeepEvent

    def __init__(self, amount: int):
        self.amount = amount

    def on_event(self, gs: GameState, source: GameCard, event: UpkeepEvent):
        if not source.host or gs.player_turn_idx != source.host.owner_id:
            return
        gs.apply_damage(source, self.amount, source.host.owner_id)

class PayManaOrSacAtUpkeep(Listener):
    """At owner's upkeep, if owner cannot pay mana, card is destroyed on the spot"""
    listens_to = UpkeepEvent

    def __init__(self, mana_cost: str):
        self.mana_cost = mana_cost

    def on_event(self, gs: GameState, source: GameCard, event: UpkeepEvent):
        if event.active_player != source.owner_id:
            return
        if not gs.mana_pools[source.owner_id].can_pay(self.mana_cost):
            gs.pile_mgr.destroy(source, allow_regeneration=False)
            return
        options = [PayMana(source.owner_id, gs, source, self.mana_cost), Sac(source.owner_id, gs, source)]
        gs.pending_choice = ChoiceAction(options)

class PayManaToUntapUpkeep(Listener):
    """Pay [x] to untap at target owner's upkeep"""
    listens_to = UpkeepEvent

    def __init__(self, mana_cost: str, target_func: Callable):
        self.mana_cost = mana_cost
        self.target_func = target_func

    def on_event(self, gs: GameState, s: GameCard, event: UpkeepEvent) -> None:
        target = self.target_func(gs, s)
        if event.active_player != target.owner_id:
            return
        if not gs.mana_pools[target.owner_id].can_pay(self.mana_cost):
            return
        options = [PayManaToUntapAction(target.owner_id, gs, s, target, self.mana_cost),
                   LeaveTapped(target.owner_id, gs, s)]
        gs.pending_choice = ChoiceAction(options)

class RemoveCounterAtTargetUpkeep(Listener):
    """At target owner's upkeep, put counter(s) on this card"""
    listens_to = UpkeepEvent

    def __init__(self, target: GameCard, counter_type: CounterType, amt: int = 1):
        self.target = target
        self.counter_type = counter_type
        self.amt = amt

    def on_event(self, gs: GameState, source: GameCard, event: UpkeepEvent) -> None:
        if event.active_player != self.target.owner_id:
            return
        self.target.counters.remove_counter(self.counter_type, self.amt)

# --- ZONE CHANGE ---
class ReturnToOwnerOnLTB(Listener):
    """Although the OnwershipMod will be removed upon LTB; need to transfer the stolen GameCard across boards"""
    listens_to = ZoneChangeEvent

    def __init__(self, new_zone: Zone = None):
        self.new_zone = new_zone or Zone.BATTLEFIELD

    def on_event(self, gs: GameState, source: GameCard, event: ZoneChangeEvent):
        if source is not event.card or event.from_zone != Zone.BATTLEFIELD or event.to_zone == Zone.BATTLEFIELD:
            return
        for c in gs.pile_mgr.boards[source.owner_id]:
            for mod in c.auras:
                if isinstance(mod, OwnershipMod):
                    gs.pile_mgr.boards[source.owner_id].remove(c)
                    gs.pile_mgr.boards[flip(source.owner_id)].append(c)
            for mod in c.modifiers.iter_type_reverse(OwnershipMod):
                c.modifiers.remove(mod)
                gs.pile_mgr.boards[source.owner_id].remove(c)
                gs.pile_mgr.boards[flip(source.owner_id)].append(c)
                break

class StealCardLeaves(Listener):
    """You control enchanted creature; must return if Control Magic leaves board"""
    listens_to = ZoneChangeEvent

    def on_event(self, gs: GameState, source: GameCard, event: ZoneChangeEvent):
        print(source, event, f'The host {event.card.host} belongs to player #{event.card.host.owner_id if event.card.host else "no host"}')
        if source is not event.card or event.from_zone != Zone.BATTLEFIELD or event.to_zone == Zone.BATTLEFIELD:
            return
        host = event.card.host
        Steal().resolve(gs, source, host)
        print('I think I returned control to', flip(host.owner_id))
