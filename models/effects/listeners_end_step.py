from __future__ import annotations
from typing import TYPE_CHECKING

from models.counter_tokens import PLUS_ONE, PIN
from models.effects.base import Listener
from models.events_all import EndStepEvent
from models.utils import flip

if TYPE_CHECKING:
    from models.game_card.game_card import GameCard
    from game_state import GameState


class DragonWhelpEndStep(Listener):
    """If this [pump] ability has been activated 4+ times this turn, sac at end step."""
    listens_to = EndStepEvent

    def on_event(self, gs: GameState, s: GameCard, event: EndStepEvent):
        if len([temp for temp in s.modifiers.items if temp.s is s]) >= 4:
            gs.pile_mgr.sacrifice(s)


class ErgRaiders(Listener):
    """At YOUR end step, except for summoning sickness, if this creature didn't attack, 2 damage to you"""
    listens_to = EndStepEvent

    def on_event(self, gs: GameState, s: GameCard, event: EndStepEvent):
        if gs.player_turn_idx != s.owner_id or s.has_summoning_sickness:
            return
        if s not in gs.card_filter.attackers().result():
            gs.apply_damage(s, 2, s.owner_id)


class InfiniteAuthorityEndStep(Listener):
    """At end step, if [that other] creature was destroyed [this] way, put a +1/+1 counter on host."""
    listens_to = EndStepEvent

    def on_event(self, gs: GameState, source: GameCard, event: EndStepEvent) -> None:
        from models.events_all import DiesEvent
        if not source.host:
            return
        other_combatants = gs.card_filter.combating_against(source.host).result()
        for e in gs.event_mgr.get_events(gs.turn_mgr.turn_number, DiesEvent):
            if e.card in other_combatants:
                source.host.counters.add_counter(PLUS_ONE)


class PestilenceEndStep(Listener):
    """At the beginning of the end step, if no creatures are on the battlefield, sacrifice this enchantment"""
    listens_to = EndStepEvent

    def on_event(self, gs: GameState, source: GameCard, event: EndStepEvent):
        if not gs.card_filter.creatures().in_play().result():
            gs.pile_mgr.destroy(source)


class SeasonOfTheWitchEndStep(Listener):
    """At YOUR end step, destroy all untapped creatures that didn't attack this turn, except those who 'couldn't'.
    Note: I'm defining 'couldn't' = summoning sickness or has Defender"""
    listens_to = EndStepEvent

    def on_event(self, gs: GameState, s: GameCard, event: EndStepEvent):
        if gs.player_turn_idx != s.owner_id:
            return
        your_untapped_creatures = gs.card_filter.on_player_board(s.owner_id).creatures().untapped().result()
        attackers = gs.card_filter.attackers().result()
        for creature in your_untapped_creatures:
            if creature in attackers:
                continue
            if creature.has_summoning_sickness or 'Defender' in creature.keyword_abilities:
                continue
            gs.pile_mgr.destroy(creature)


class SirensCallEndStep(Listener):
    """At next end step, destroy all non-Wall creatures that player controls that didn't attack this turn.
    Ignore this effect for each creature the player didn't control continuously since the beginning of the turn."""
    listens_to = EndStepEvent

    def on_event(self, gs: GameState, source: GameCard, event: EndStepEvent) -> None:
        if gs.player_turn_idx != source.owner_id:
            return
        non_wall_creatures = gs.card_filter.on_player_board(event.active_player).non_wall_creatures().result()
        attackers = gs.card_filter.attackers().result()
        for creature in non_wall_creatures:
            if not creature.has_summoning_sickness and creature not in attackers:
                gs.pile_mgr.destroy(creature)


class VoodooDollEndStep(Listener):
    """At your end step, if untapped, destroy this card & it deals damage to you = to the # of pin counters on it"""
    listens_to = EndStepEvent

    def on_event(self, gs: GameState, source: GameCard, event: EndStepEvent):
        if gs.player_turn_idx != source.owner_id:
            return
        if source.is_tapped:
            return
        if pin_cnt := source.counters.get_count(PIN) > 0:
            gs.apply_damage(source, pin_cnt, source.owner_id)
        gs.pile_mgr.destroy(source)


class WhirlingDervish(Listener):
    """At each end step, if this creature dealt damage to an opponent this turn, put a +1/+1 counter on it"""
    listens_to = EndStepEvent

    def on_event(self, gs: GameState, source: GameCard, event: EndStepEvent) -> None:
        from models.events_all import DamageResolvedEvent
        for e in gs.event_mgr.get_events(gs.turn_mgr.turn_number, DamageResolvedEvent):
            if e.source is source and e.target == flip(source.owner_id):
                source.counters.add_counter(PLUS_ONE)
                return
