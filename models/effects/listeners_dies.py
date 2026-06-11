from __future__ import annotations

import math
from typing import TYPE_CHECKING

from models.choice_actions_all import PayOneColorlessForOneLifeChoice, PayManaToDrawCardsChoice
from models.counter_tokens import PLUS_ONE
from models.effects.base import Listener
from models.events_all import DiesEvent, DamageResolvedEvent

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
        for e in gs.turn_mgr.events:
            if not isinstance(e, DamageResolvedEvent):
                continue
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
        total_damage = 3 + sum([e.amt for e in gs.turn_mgr.events if isinstance(e, DamageResolvedEvent)
                                and e.target is source and e.source.props.slug == 'blazing-effigy'])
        # TODO: How do I get the target creature from the user?


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


class Onulet(Listener):
    """When this creature dies, you gain 2 life"""
    listens_to = DiesEvent

    def on_event(self, gs: GameState, source: GameCard, event: DiesEvent):
        if not isinstance(event, DiesEvent) or event.card != source:
            return
        gs.score_mgr.increment_life(source.owner_id, 2, source, gs)


class PersonalIncarnation(Listener):
    """... When this creature dies, its owner loses half their life, rounding up the loss amount"""
    listens_to = DiesEvent

    def on_event(self, gs: GameState, source: GameCard, event: DiesEvent):
        if not isinstance(event, DiesEvent) or event.card != source:
            return
        reduce_life_by = math.ceil(gs.score_mgr.life[source.owner_id] / 2)
        gs.apply_damage(source, reduce_life_by, source.owner_id)


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
        for e in gs.turn_mgr.events:
            if not isinstance(e, DamageResolvedEvent):
                continue
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
        if not isinstance(event, DiesEvent) or not event.card.is_creature:
            return

        gs.action_stack.push(PayOneColorlessForOneLifeChoice(source.owner_id, gs, source), gs, False)


class TabletOfEpityr(Listener):
    """Whenever an artifact you control dies, {1}: Gain 1 life"""
    listens_to = DiesEvent

    def on_event(self, gs: GameState, source: GameCard, event: DiesEvent):
        if not isinstance(event, DiesEvent) or 'Artifact' not in event.card.props.card_types \
                or event.card.owner_id != source.owner_id:
            return
        gs.action_stack.push(PayOneColorlessForOneLifeChoice(source.owner_id, gs, source), gs, False)


class UrzasMiter(Listener):
    """Whenever an artifact you control dies, if it wasn't sacrificed [not handling this part], {3}: draw a card"""
    listens_to = DiesEvent

    def on_event(self, gs: GameState, source: GameCard, event: DiesEvent):
        if not isinstance(event, DiesEvent) or 'Artifact' not in event.card.props.card_types \
                or event.card.owner_id != source.owner_id:
            return
        gs.action_stack.push(PayManaToDrawCardsChoice(source.owner_id, gs, source), gs, False)
