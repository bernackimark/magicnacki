from __future__ import annotations
from typing import TYPE_CHECKING, Callable

if TYPE_CHECKING:
    from models.game_card.game_card import GameCard
    from game_state import GameState

from models.actions.tap_untap import LeaveTapped
from models.choice_actions_all import PayOneColorlessForOneLifeChoice, UntapChoice, PayManaOrSacUpkeepChoice
from models.counter_tokens import CounterType
from models.effects.base import Listener
from models.effects.resolvers_generic import Steal
from models.events_all import CastResolvedEvent, CombatEndEvent, DamageResolvedEvent, EndStepEvent, UntapCardEvent, \
    UntapPhaseEvent, UpkeepEvent, ZoneChangeEvent, DamageProposedEvent, Event, PassTheTurnEvent, CanUntapQueryEvent, \
    CanAttackQueryEvent, AttackEvent
from models.modifiers import OwnershipMod, PTMod
from models.utils import flip
from models.zone import Zone

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

# --- CAN UNTAP QUERY EVENT --
class DoesntUntapIfItAttackedLastTurn(Listener):
    listens_to = CanUntapQueryEvent

    def __init__(self, target: GameCard):
        self.target = target

    def on_event(self, gs: GameState, source: GameCard, event: CanUntapQueryEvent) -> None:
        if self.target is not event.card:
            return
        p_last_turn_num = gs.turn_mgr.get_players_last_turn_num(self.target.owner_id)
        for e, turn_num in gs.event_mgr.events[::-1]:
            if turn_num == p_last_turn_num:
                if isinstance(e, AttackEvent) and e.attacker is self.target:
                    event.permission = False

class SkipUntaps(Listener):
    """Card doesn't untap during its controller's next X untap steps;
    set the event's permission to false & expire this listener"""
    listens_to = CanUntapQueryEvent

    def __init__(self, target: GameCard, next_x_turns: int = 1):
        self.target = target
        self.next_x_turns = next_x_turns
        self.skips_used = 0

    def on_event(self, gs: GameState, source: GameCard, event: CanUntapQueryEvent) -> None:
        if event.card is not self.target or gs.turn_mgr.player_turn_idx != self.target.owner_id:
            return
        event.permission = False
        self.skips_used += 1
        if self.skips_used == self.next_x_turns:
            self.is_expired = True

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
        gs.action_stack.push(PayOneColorlessForOneLifeChoice(s.owner_id, gs, s), gs, False)


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
class PreventAllDamageEOT(Listener):
    listens_to = DamageProposedEvent
    expires = 'EOT'

    def __init__(self, combat_only: bool = False):
        self.combat_only = combat_only

    def on_event(self, gs: GameState, source: GameCard, event: DamageProposedEvent) -> None:
        if self.combat_only and not event.is_combat:
            return
        event.prevented += event.remaining
        event.remaining = 0

class PreventCombatDamageFromItsAttackers(Listener):
    listens_to = DamageProposedEvent

    def on_event(self, gs: GameState, source: GameCard, event: DamageProposedEvent) -> None:
        if not event.is_combat or source is not event.target:
            return
        event.prevented += event.remaining
        event.remaining = 0

class PreventCombatDamageFromEnchantedCreatures(Listener):
    """Prevent all combat damage that would be dealt to this creature by enchanted creatures"""
    listens_to = DamageProposedEvent

    def on_event(self, gs: GameState, source: GameCard, event: DamageProposedEvent) -> None:
        if event.target is not source.host or not event.is_combat or not event.source.is_enchanted:
            return
        event.prevented += event.remaining
        event.remaining = 0

class PreventAllDamageByEOT(Listener):
    listens_to = DamageProposedEvent
    expires = 'EOT'

    def __init__(self, damage_dealer: GameCard, combat_only: bool = False):
        self.damage_dealer = damage_dealer
        self.combat_only = combat_only

    def on_event(self, gs: GameState, source: GameCard, event: DamageProposedEvent) -> None:
        if event.source is not self.damage_dealer or (self.combat_only and not event.is_combat):
            return
        event.prevented += event.remaining
        event.remaining = 0

class PreventAllDamageToEOT(Listener):
    listens_to = DamageProposedEvent
    expires = 'EOT'

    def __init__(self, damage_receiver: GameCard, combat_only: bool = False):
        self.damage_receiver = damage_receiver
        self.combat_only = combat_only

    def on_event(self, gs: GameState, source: GameCard, event: DamageProposedEvent) -> None:
        if event.target is not self.damage_receiver or (self.combat_only and not event.is_combat):
            return
        event.prevented += event.remaining
        event.remaining = 0

class PreventAllNoncombatDamageToEOT(Listener):
    listens_to = DamageProposedEvent
    expires = 'EOT'

    def __init__(self, damage_receiver: GameCard):
        self.damage_receiver = damage_receiver

    def on_event(self, gs: GameState, source: GameCard, event: DamageProposedEvent) -> None:
        if event.target is not self.damage_receiver or event.is_combat:
            return
        event.prevented += event.remaining
        event.remaining = 0

class PreventNextDamageByEOT(Listener):
    listens_to = DamageProposedEvent

    def __init__(self, damage_dealer: GameCard, combat_only: bool = False):
        self.damage_dealer = damage_dealer
        self.combat_only = combat_only

    def on_event(self, gs: GameState, source: GameCard, event: DamageProposedEvent) -> None:
        if event.source is not self.damage_dealer or (self.combat_only and not event.is_combat):
            return
        event.prevented += event.remaining
        event.remaining = 0
        self.is_expired = True

class PreventNextDamageToCardEOT(Listener):
    listens_to = DamageProposedEvent
    expires = 'EOT'

    def __init__(self, damage_receiver: GameCard, prevented_amt: int = None, combat_only: bool = False):
        self.damage_receiver = damage_receiver
        self.prevented_amt = prevented_amt
        self.combat_only = combat_only

    def on_event(self, gs: GameState, source: GameCard, event: DamageProposedEvent) -> None:
        if event.target is not self.damage_receiver or (self.combat_only and not event.is_combat):
            return
        if self.prevented_amt is None:
            self.prevented_amt = event.amt
        event.prevented += self.prevented_amt
        event.remaining = event.amt - self.prevented_amt

class PreventNextDamageToSourceOwnerEOT(Listener):
    listens_to = DamageProposedEvent
    expires = 'EOT'

    def __init__(self, preventable_amt: int | None = None, combat_only: bool = False):
        self.preventable_amt = preventable_amt
        self.combat_only = combat_only

    def on_event(self, gs: GameState, source: GameCard, event: DamageProposedEvent) -> None:
        if event.target is not source.owner_id or (self.combat_only and not event.is_combat):
            return
        if self.preventable_amt is None:
            event.prevented += 999999
        else:
            event.prevented += min(self.preventable_amt, event.remaining)
        event.remaining = event.amt - event.prevented
        self.is_expired = True

class PreventNextDamageToEOT(Listener):
    listens_to = DamageProposedEvent
    expires = 'EOT'

    def __init__(self, protected_target: GameCard | int, preventable_amt: int | None = None, combat_only: bool = False):
        self.protected_target = protected_target
        self.preventable_amt = preventable_amt
        self.combat_only = combat_only

    def on_event(self, gs: GameState, source: GameCard, event: DamageProposedEvent) -> None:
        if event.target is not self.protected_target or (self.combat_only and not event.is_combat):
            return
        event.prevented += min(self.preventable_amt, event.remaining)
        event.remaining = event.amt - event.prevented
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

# --- PASS THE TURN EVENT ---
class TakingAnotherTurnEOT(Listener):
    listens_to = PassTheTurnEvent
    expires = 'EOT'

    def on_event(self, gs: GameState, source: GameCard, event: PassTheTurnEvent) -> None:
        from models.actions.end_step_pass_turn import PassTheTurn
        PassTheTurn(source.owner_id, gs, pass_turn_to_opp=False).play()

# --- UNTAP CARD EVENT ---
class ReturnToOwnerOnUntap(Listener):
    """Ownership by virtue of an aura or the source being on the battlefield will auto-remove the mod upon LTB;
    This effect removes an ownership mod on any card the source was placed & xfers the stolen GameCard across boards"""
    listens_to = UntapCardEvent

    def on_event(self, gs: GameState, source: GameCard, event: UntapCardEvent):
        if source is not event.card:
            return
        for c in gs.pile_mgr.boards[source.owner_id]:
            for mod in c.auras:
                if isinstance(mod, OwnershipMod):
                    c.modifiers.remove(mod)
                    gs.pile_mgr.boards[source.owner_id].remove(c)
                    gs.pile_mgr.boards[flip(source.owner_id)].append(c)
                    break

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
class CardsDontUntapAtUntapPhase(Listener):
    """Cards [from card_filter_func] don't untap during their controllers' untap steps"""
    listens_to = UntapPhaseEvent

    def __init__(self, card_filter_func: Callable[[GameState, GameCard], list[GameCard | None]]):
        self.card_filter_func = card_filter_func

    def on_event(self, gs: GameState, s: GameCard, event: UntapPhaseEvent):
        for c in self.card_filter_func(gs, s):
            gs.action_stack.push(LeaveTapped(event.active_player, gs, c), gs, False)


class OptionalUntap(Listener):
    listens_to = UntapPhaseEvent

    def on_event(self, gs: GameState, source: GameCard, event: UntapPhaseEvent):
        if source.owner_id != event.active_player or not source.is_tapped:
            return
        gs.action_stack.push(UntapChoice(gs.turn_mgr.player_turn_idx, gs, source), gs, False)


# --- UPKEEP ---
class DealDamageToOwnerOnUpkeep(Listener):
    listens_to = UpkeepEvent

    def __init__(self, amount: int):
        self.amount = amount

    def on_event(self, gs: GameState, source: GameCard, event: UpkeepEvent):
        if gs.turn_mgr.player_turn_idx != source.owner_id:
            return
        gs.apply_damage(source, self.amount, source.owner_id)


class DealDamageOnHostUpkeep(Listener):
    listens_to = UpkeepEvent

    def __init__(self, amount: int):
        self.amount = amount

    def on_event(self, gs: GameState, source: GameCard, event: UpkeepEvent):
        if not source.host or gs.turn_mgr.player_turn_idx != source.host.owner_id:
            return
        gs.apply_damage(source, self.amount, source.host.owner_id)

class PayManaOrSacAtUpkeep(Listener):
    listens_to = UpkeepEvent

    def __init__(self, mana_cost: str):
        self.mana_cost = mana_cost

    def on_event(self, gs: GameState, source: GameCard, event: UpkeepEvent):
        gs.action_stack.push(PayManaOrSacUpkeepChoice(source.owner_id, gs, source, self.mana_cost), gs, False)

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
