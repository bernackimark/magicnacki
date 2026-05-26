from __future__ import annotations

import math
from typing import TYPE_CHECKING

from models.choice_actions_all import PayOneColorlessForOneLifeChoice, PayManaToDrawCardsChoice
from models.effects.base import Effect
from models.events_all import DiesEvent

if TYPE_CHECKING:
    from game_state import GameState
    from models.game_card.game_card import GameCard


class Onulet(Effect):
    """When this creature dies, you gain 2 life"""
    listens_to = DiesEvent

    def on_event(self, gs: GameState, source: GameCard, event: DiesEvent):
        if not isinstance(event, DiesEvent) or event.card != source:
            return
        gs.score_mgr.increment_life(source.owner_id, 2, source, gs)


class AbuJafar(Effect):
    """When this creature dies, destroy all creatures blocking or blocked by it. They can't be regenerated."""
    listens_to = DiesEvent

    def on_event(self, gs: GameState, source: GameCard, event: DiesEvent):
        if event.card is not source:
            return
        for com in gs.combats:
            for other_combatant in com.get_combatants_against(event.card):
                gs.destroy(other_combatant, allow_regeneration=False)


class CreatureBond(Effect):
    """When enchanted creature dies, deal damage = to host's toughness to the creature's controller"""
    listens_to = DiesEvent

    def on_event(self, gs: GameState, source: GameCard, event: DiesEvent):
        if not isinstance(event, DiesEvent) or event.card != source.host:
            return
        gs.apply_damage(source, source.host.toughness, source.host.owner_id)


class PersonalIncarnation(Effect):
    """... When this creature dies, its owner loses half their life, rounding up the loss amount"""
    listens_to = DiesEvent

    def on_event(self, gs: GameState, source: GameCard, event: DiesEvent):
        if not isinstance(event, DiesEvent) or event.card != source:
            return
        reduce_life_by = math.ceil(gs.score_mgr.life[source.owner_id] / 2)
        gs.apply_damage(source, reduce_life_by, source.owner_id)


class RukhEgg(Effect):
    """When this creature dies, create a 4/4 red Bird creature token with flying at next end step"""
    listens_to = DiesEvent

    def on_event(self, gs: GameState, source: GameCard, event: DiesEvent):
        if not isinstance(event, DiesEvent) or event.card != source:
            return
        from special import CreateTokenCreature
        obj = CreateTokenCreature('rukh')
        obj.resolve(gs, source)
        # gs.create_token_creature(source.owner_id, 'Bird', 4, 4, ['Flying', 'Attack'], [], ['Bird'], 'R')


class CyclopeanMummy(Effect):
    """When this creature dies, exile it"""
    listens_to = DiesEvent

    def on_event(self, gs: GameState, source: GameCard, event: DiesEvent):
        if not isinstance(event, DiesEvent) or event.card != source:
            return
        gs.exile(source)


class SuChi(Effect):
    """When this creature dies, add {CCCC}"""
    listens_to = DiesEvent

    def on_event(self, gs: GameState, source: GameCard, event: DiesEvent):
        if not isinstance(event, DiesEvent) or event.card != source:
            return
        gs.mana_pools[source.owner_id].add_floating('C', 4)


class SoulNet(Effect):
    """Whenever a creature dies, {1}: Gain 1 life"""
    listens_to = DiesEvent

    def on_event(self, gs: GameState, source: GameCard, event: DiesEvent):
        if not isinstance(event, DiesEvent) or not event.card.is_creature:
            return

        gs.action_stack.push(PayOneColorlessForOneLifeChoice(source.owner_id, gs, source), gs, False)


class TabletOfEpityr(Effect):
    """Whenever an artifact you control dies, {1}: Gain 1 life"""
    listens_to = DiesEvent

    def on_event(self, gs: GameState, source: GameCard, event: DiesEvent):
        if not isinstance(event, DiesEvent) or 'Artifact' not in event.card.props.card_types \
                or event.card.owner_id != source.owner_id:
            return
        gs.action_stack.push(PayOneColorlessForOneLifeChoice(source.owner_id, gs, source), gs, False)


class UrzasMiter(Effect):
    """Whenever an artifact you control dies, if it wasn't sacrificed [not handling this part], {3}: draw a card"""
    listens_to = DiesEvent

    def on_event(self, gs: GameState, source: GameCard, event: DiesEvent):
        if not isinstance(event, DiesEvent) or 'Artifact' not in event.card.props.card_types \
                or event.card.owner_id != source.owner_id:
            return
        gs.action_stack.push(PayManaToDrawCardsChoice(source.owner_id, gs, source), gs, False)


class SandalsOfAbdallahIfCreatureDies(Effect):
    """When that creature [that Sandals gave Islandwalk to] dies this turn, destroy this artifact"""
    listens_to = DiesEvent

    def __init__(self, target_creature: GameCard):
        self.target_creature = target_creature

    def on_event(self, gs: GameState, source: GameCard, event: DiesEvent):
        if not isinstance(event, DiesEvent) or event.card != self.target_creature:
            return
        gs.destroy(source)
