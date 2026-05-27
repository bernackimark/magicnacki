from __future__ import annotations
from typing import TYPE_CHECKING

from models.counter_tokens import CounterType, PIN
from models.effects.base import Listener
from models.events_all import EndStepEvent
from models.zone import Zone

if TYPE_CHECKING:
    from game_state import GameState
    from models.game_card.game_card import GameCard


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


class ErgRaiders(Listener):
    """At YOUR end step, except for summoning sickness, if this creature didn't attack, 2 damage to you"""
    listens_to = EndStepEvent

    def on_event(self, gs: GameState, s: GameCard, event: EndStepEvent):
        if gs.turn_mgr.player_turn_idx != s.owner_id or s.has_summoning_sickness:
            return
        if s not in gs.card_filter.attackers().result():
            gs.apply_damage(s, 2, s.owner_id)


class PestilenceEndStep(Listener):
    """At the beginning of the end step, if no creatures are on the battlefield, sacrifice this enchantment"""
    listens_to = EndStepEvent

    def on_event(self, gs: GameState, source: GameCard, event: EndStepEvent):
        if not gs.card_filter.creatures().in_play().result():
            gs.destroy(source)


class SeasonOfTheWitchEndStep(Listener):
    """At YOUR end step, destroy all untapped creatures that didn't attack this turn, except those who 'couldn't'.
    Note: I'm defining 'couldn't' = summoning sickness or has Defender"""
    listens_to = EndStepEvent

    def on_event(self, gs: GameState, s: GameCard, event: EndStepEvent):
        if gs.turn_mgr.player_turn_idx != s.owner_id:
            return
        your_untapped_creatures = gs.card_filter.on_player_board(s.owner_id).creatures().untapped().result()
        attackers = gs.card_filter.attackers().result()
        for creature in your_untapped_creatures:
            if creature in attackers:
                continue
            if creature.has_summoning_sickness or 'Defender' in creature.keyword_abilities:
                continue
            gs.destroy(creature)


class VoodooDollEndStep(Listener):
    """At your end step, if untapped, destroy this card & it deals damage to you = to the # of pin counters on it"""
    listens_to = EndStepEvent

    def on_event(self, gs: GameState, source: GameCard, event: EndStepEvent):
        if gs.turn_mgr.player_turn_idx != source.owner_id:
            return
        if source.is_tapped:
            return
        if pin_cnt := source.counters.get_count(PIN) > 0:
            gs.apply_damage(source, pin_cnt, source.owner_id)
        gs.destroy(source)


class DragonWhelpEndStep(Listener):
    """If this [pump] ability has been activated 4+ times this turn, sac at end step."""
    listens_to = EndStepEvent

    def on_event(self, gs: GameState, s: GameCard, event: EndStepEvent):
        if len([temp for temp in s.modifiers.items if temp.source is s]) >= 4:
            gs.destroy(s, allow_regeneration=False)
