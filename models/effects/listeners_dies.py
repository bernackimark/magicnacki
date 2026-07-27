from __future__ import annotations

import math
from typing import TYPE_CHECKING

from models.actions.damage import DealDamageTo
from models.actions.special import PayManaToDrawCards, PayManaForLife, PayManaToBounce
from models.choice_actions_all import ChoiceAction
from models.counter_tokens import PLUS_ONE
from models.effects.base import Listener
from models.events_all import DiesEvent, DamageResolvedEvent, Event

if TYPE_CHECKING:
    from models.game_card.game_card import GameCard
    from game_state import GameState


class AbuJafar(Listener):
    """When this creature dies, destroy all creatures blocking or blocked by it. They can't be regenerated."""
    listens_to = DiesEvent

    def on_event(self, gs: GameState, source: GameCard, event: DiesEvent):
        if event.card is not source:
            return
        for combatant in gs.combat_mgr.get_combatants_against(event.card):
            gs.pile_mgr.destroy(combatant, allow_regeneration=False)

class AxelrodGunnarson(Listener):
    """Whenever a creature dealt damage by AG this turn dies, you gain 1 life & AG deals 1 damage to [opponent]"""
    listens_to = DiesEvent

    def on_event(self, gs: GameState, source: GameCard, event: DiesEvent):
        for e in gs.event_mgr.get_events(gs.turn_mgr.turn_number, DamageResolvedEvent):
            if e.source is not source or e.target is not event.card:
                continue
            gs.score_mgr.increment_life(source.owner_id, 1, source, gs)
            gs.apply_damage(source, 1, event.card.owner_id)
            return

class BlazingEffigy(Listener):
    """When this creature dies, it deals X damage to target creature.
    X is 3 plus the amount of damage dealt to this creature this turn by other sources named Blazing Effigy."""
    listens_to = DiesEvent

    def on_event(self, gs: GameState, source: GameCard, event: DiesEvent) -> None:
        if source is not event.card:
            return
        all_creatures = gs.card_filter.creatures().in_play().result()
        if not all_creatures:
            return
        total_damage = 3 + sum([e.amt for e in gs.event_mgr.get_events(gs.turn_mgr.turn_number, DamageResolvedEvent)
                                if e.target is source and e.source.props.slug == 'blazing-effigy'])
        options = [DealDamageTo(source.owner_id, gs, source, total_damage, target) for target in all_creatures]
        gs.pending_choice = ChoiceAction(options)

class CreatureBond(Listener):
    """When enchanted creature dies, deal damage = to host's toughness to the creature's controller"""
    listens_to = DiesEvent

    def on_event(self, gs: GameState, source: GameCard, event: DiesEvent):
        if not isinstance(event, DiesEvent) or event.card != source.host:
            return
        gs.apply_damage(source, source.host.toughness, source.host.owner_id)


class CyclopeanMummy(Listener):
    """When this creature dies, exile it"""
    listens_to = DiesEvent

    def on_event(self, gs: GameState, source: GameCard, event: DiesEvent):
        if not isinstance(event, DiesEvent) or event.card != source:
            return
        gs.pile_mgr.exile(source)

class FirestormPhoenix(Listener):
    """If this card would die, bounce it instead; it cannot be re-summoned this turn"""
    listens_to = DiesEvent

    def on_event(self, gs: GameState, source: GameCard, event: DiesEvent) -> None:
        if event.card is not source:
            return
        gs.pile_mgr.bounce(source)
        from models.effects.listeners_permission import CantCastEOT
        gs.event_mgr.register(CantCastEOT(source), source)

class Onulet(Listener):
    """When this creature dies, you gain 2 life"""
    listens_to = DiesEvent

    def on_event(self, gs: GameState, source: GameCard, event: DiesEvent):
        if not isinstance(event, DiesEvent) or event.card != source:
            return
        gs.score_mgr.increment_life(source.owner_id, 2, source, gs)


class PersonalIncarnationDies(Listener):
    """... When this creature dies, its owner loses half their life, rounding up the loss amount"""
    listens_to = DiesEvent

    def on_event(self, gs: GameState, source: GameCard, event: DiesEvent):
        if not isinstance(event, DiesEvent) or event.card is not source:
            return
        reduce_life_by = math.ceil(gs.life[source.owner_id] / 2)
        gs.apply_damage(source, reduce_life_by, source.owner_id)

class PuppetMaster(Listener):
    """When host dies, bounce host instead. You may pay {UUU} to bounce this aura."""
    listens_to = DiesEvent

    def on_event(self, gs: GameState, source: GameCard, event: DiesEvent) -> None:
        if event.card is not source.host:
            return
        gs.pile_mgr.bounce(event.card)
        if gs.mana_pools[source.owner_id].can_pay('UUU'):
            options = [PayManaToBounce(source.owner_id, gs, source, source, 'UUU')]
            gs.pending_choice = ChoiceAction(options, may=True)

class RukhEgg(Listener):
    """When this creature dies, create a 4/4 red Bird creature token with flying at next end step"""
    listens_to = DiesEvent

    def on_event(self, gs: GameState, source: GameCard, event: DiesEvent):
        if not isinstance(event, DiesEvent) or event.card != source:
            return
        from models.effects.resolvers_generic import CreateTokenCreature
        obj = CreateTokenCreature('rukh')
        obj.resolve(gs, source)
        # gs.create_token_creature(source.owner_id, 'Bird', 4, 4, ['Flying', 'Attack'], [], ['Bird'], 'R')


class SandalsOfAbdallahIfCreatureDies(Listener):
    """When that creature [that Sandals gave Islandwalk to] dies this turn, destroy this artifact"""
    listens_to = DiesEvent
    expires = 'EOT'

    def __init__(self, target_creature: GameCard):
        self.target_creature = target_creature

    def on_event(self, gs: GameState, source: GameCard, event: DiesEvent):
        if not isinstance(event, DiesEvent) or event.card != self.target_creature:
            return
        gs.pile_mgr.destroy(source)
        self.is_expired = True


class SengirVampire(Listener):
    """Whenever a creature dealt damage by this creature this turn dies, put a +1/+1 counter on this creature"""
    listens_to = DiesEvent

    def on_event(self, gs: GameState, source: GameCard, event: DiesEvent):
        for e in gs.event_mgr.get_events(gs.turn_mgr.turn_number, DamageResolvedEvent):
            if e.source is not source or e.target is not event.card:
                continue
            source.counters.add_counter(PLUS_ONE)
            return


class SuChi(Listener):
    """When this creature dies, add {CCCC}"""
    listens_to = DiesEvent

    def on_event(self, gs: GameState, source: GameCard, event: DiesEvent):
        if not isinstance(event, DiesEvent) or event.card != source:
            return
        gs.mana_pools[source.owner_id].add_floating('C', 4)


class SoulNet(Listener):
    """Whenever a creature dies, {1}: Gain 1 life"""
    listens_to = DiesEvent

    def on_event(self, gs: GameState, source: GameCard, event: DiesEvent):
        if not event.card.is_creature:
            return
        options = [PayManaForLife(source.owner_id, gs, '1', 1)]
        gs.pending_choice = ChoiceAction(options, may=True)


class TabletOfEpityr(Listener):
    """Whenever an artifact you control dies, {1}: Gain 1 life"""
    listens_to = DiesEvent

    def on_event(self, gs: GameState, source: GameCard, event: DiesEvent):
        if not event.card.is_artifact or event.card.owner_id != source.owner_id:
            return
        options = [PayManaForLife(source.owner_id, gs, '1', 1)]
        gs.pending_choice = ChoiceAction(options, may=True)


class UrzasMiter(Listener):
    """Whenever an artifact you control dies, if it wasn't sacrificed [not handling this part], {3}: draw a card"""
    listens_to = DiesEvent

    def on_event(self, gs: GameState, source: GameCard, event: DiesEvent):
        if event.card.owner_id != source.owner_id or 'Artifact' not in event.card.card_types:
            return
        options = [PayManaToDrawCards(source.owner_id, gs, '3', 1)]
        gs.pending_choice = ChoiceAction(options, may=True)
