from __future__ import annotations
from typing import TYPE_CHECKING

from models.actions.ability_pipeline_support import AbilityAction
from models.actions.draw_discard import DrawCard
from models.actions.special import SacTwoIslandsToAttack, PayManaToPreventCounter
from models.actions.stack_accept_counter import CounterSpellAction
from models.choice_actions_all import ChoiceAction
from models.zone import Zone

if TYPE_CHECKING:
    from models.game_card.game_card import GameCard
    from game_state import GameState

from models.effects.base import Listener
from models.events_all import LifeLossEvent, CastResolvedEvent, MainPhaseEvent, AbilityActivatedEvent, \
    StackAdditionEvent
from models.utils import flip


# --- ABILITY ACTIVATED EVENT ---
class ArtifactPossessionActivation(Listener):
    """Whenever host ... activates an ability without {T} in its activation cost, deal 2 damage to host's controller"""
    listens_to = AbilityActivatedEvent

    def on_event(self, gs: GameState, source: GameCard, event: AbilityActivatedEvent) -> None:
        if event.aa.source is not source.host:
            return
        if 'T' in event.aa.eff_spec.cost:
            return
        gs.apply_damage(source, 2, source.host.owner_id)

class HauntingWindActivation(Listener):
    """Whenever an artifact ... activates an ability without a {T} in its cost,
    deal 1 damage to artifact's controller"""
    listens_to = AbilityActivatedEvent

    def on_event(self, gs: GameState, source: GameCard, event: AbilityActivatedEvent) -> None:
        if not event.aa.source.is_artifact:
            return
        if 'T' in event.aa.eff_spec.cost:
            return
        print(event.aa.eff_spec.cost)
        gs.apply_damage(source, 1, event.aa.source.owner_id)

class PowerleechActivation(Listener):
    """Whenever an opponent's artifact ... activates an ability, you gain 1 life"""
    listens_to = AbilityActivatedEvent

    def on_event(self, gs: GameState, source: GameCard, event: AbilityActivatedEvent) -> None:
        if source.owner_id == event.aa.source.owner_id or not event.aa.source.is_artifact:
            return
        gs.score_mgr.increment_life(source.owner_id, 1, source, gs)

# --- CAST RESOLVED EVENT ---
class IchneumonDruid(Listener):
    """Whenever an opponent casts their non-first instant spell that turn, ID deals 4 damage to that player."""
    listens_to = CastResolvedEvent

    def on_event(self, gs: GameState, source: GameCard, event: CastResolvedEvent) -> None:
        opp = flip(source.owner_id)
        instants_cast_in_turn = len([e for e in gs.event_mgr.get_events(gs.turn_mgr.turn_number, CastResolvedEvent)
                                    if e.owner_id == opp and 'Instant' in e.card.card_types])
        if instants_cast_in_turn > 1:
            gs.apply_damage(source, 4, opp)

class PresenceOfTheMaster(Listener):
    """Whenever a player casts an enchantment spell, counter it"""
    listens_to = CastResolvedEvent

    def on_event(self, gs: GameState, source: GameCard, event: CastResolvedEvent) -> None:
        ...

class VerduranEnchantress(Listener):
    """Whenever you cast an enchantment spell, you may draw a card"""
    listens_to = CastResolvedEvent

    def on_event(self, gs: GameState, source: GameCard, event: CastResolvedEvent):
        if source.owner_id != event.card.owner_id or not event.card.is_enchantment:
            return
        options = [DrawCard(source.owner_id, gs)]
        gs.queue_choice(ChoiceAction(options, may=True))

# --- LIFE LOSS ---
class AliFromCairo(Listener):
    """Damage that would reduce your life total to less than 1 reduces it to 1 instead"""
    listens_to = LifeLossEvent

    def on_event(self, gs: GameState, s: GameCard, event: LifeLossEvent):
        if event.p_id_taking_damage != s.owner_id:
            return

        current_life = gs.life[event.p_id_taking_damage]

        if current_life - event.amt < 1:
            event.amt = max(current_life - 1, 0)

# --- MAIN PHASE ---
class LeviathanAttack(Listener):
    """When attackers are declared (here MainPhase), you may sac 2 Islands to permit Leviathan to attack this turn."""
    listens_to = MainPhaseEvent

    def on_event(self, gs: GameState, source: GameCard, event: MainPhaseEvent):
        if source.owner_id != event.active_p_id or source.is_tapped:
            return

        your_islands = gs.card_filter.on_player_board(source.owner_id).islands().result()
        if len(your_islands) < 2:
            return

        options = [SacTwoIslandsToAttack(event.active_p_id, gs, source, source)]
        gs.queue_choice(ChoiceAction(options, may=True))

class ManaDrainMainPhase(Listener):
    """... At your next main phase, add an amount of {C} equal to that spell's mana value"""
    # TODO: Create ManaDrain(Resolver), which would create & register an instance of this class
    listens_to = MainPhaseEvent

    def __init__(self, mana_value: int):
        self.mana_value = mana_value

    def on_event(self, gs: GameState, source: GameCard, event: MainPhaseEvent) -> None:
        if event.active_p_id != source.owner_id:
            return
        gs.mana_pools[source.owner_id].add_floating('C', self.mana_value)
        gs.event_mgr.unregister_specific_effect(self)


# -- STACK ADDITION EVENT ---
class InTheEyeOfChaos(Listener):
    """Whenever a player casts an instant spell, counter it unless that player pays {X}, where X is its mana value"""
    listens_to = StackAdditionEvent

    def on_event(self, gs: GameState, source: GameCard, event: StackAdditionEvent) -> None:
        if not isinstance(event.action, AbilityAction):
            return
        if isinstance(event.action, AbilityAction) and not event.action.pipeline.eff_spec.is_spell:
            return
        if not event.action.pipeline.source.is_instant:
            return
        target_spell = event.action
        p_id = target_spell.player_idx
        mana_cost = event.action.pipeline.source.casting_cost
        if not gs.mana_pools[p_id].can_pay(mana_cost):
            gs.action_stack.remove(event.action)
            gs.pile_mgr.move_card(target_spell.source, Zone.GRAVEYARD, cause='fizzled', emit_zone_event=False)
            return
        options = [PayManaToPreventCounter(p_id, gs, target_spell, mana_cost),
                   CounterSpellAction(p_id, gs, target_spell)]
        gs.queue_choice(ChoiceAction(options))

class ScarwoodBanditsAAListener(Listener):
    """2GT: Unless opponent pays {2}, gain control of target artifact for as long as SB remains on the battlefield ...
    I don't have a great way of adding an opponent's choice at the exact right time, I'm just creating this Listener
    to add a choice to the stack for the opponent"""
    listens_to = StackAdditionEvent

    def on_event(self, gs: GameState, source: GameCard, event: StackAdditionEvent) -> None:
        if not isinstance(event.action, AbilityAction) or event.action.pipeline.source is not source:
            return
        opp = flip(source.owner_id)
        if not gs.mana_pools[opp].can_pay('2'):
            return
        options = [PayManaToPreventCounter(opp, gs, event.action, '2')]
        gs.queue_choice(ChoiceAction(options, may=True))
