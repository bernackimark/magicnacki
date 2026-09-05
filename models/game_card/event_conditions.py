from typing import Callable

from models.events_all import DamageResolvedEvent
from models.utils import flip

class EC:
    """Event conditions that return a lambda accepting GameState, source: GameState, event: Event; returns a bool"""
    @staticmethod
    def card_is_artifact():
        return lambda gs, s, e: e.card.is_artifact

    @staticmethod
    def card_is_color(colors: str):
        """Can be used for multiple colors or a single color"""
        matching_colors = set(colors)
        return lambda gs, s, e: bool(matching_colors & set(e.card.colors))

    @staticmethod
    def card_is_host():
        return lambda gs, s, e: e.card is s.host

    @staticmethod
    def card_is_forest():
        return lambda gs, s, e: 'Forest' in e.card.card_sub_types

    @staticmethod
    def card_is_mountain():
        # TODO: candidate for card_is_sub_type(subp_type: str)
        return lambda gs, s, e: 'Mountain' in e.card.card_sub_types

    @staticmethod
    def card_is_opponents():
        return lambda gs, s, e: e.card.owner_id != s.owner_id

    @staticmethod
    def card_is_source():
        return lambda gs, s, e: e.card is s

    @staticmethod
    def caster_is_opp():
        return lambda gs, s, e: e.owner_id != s.owner_id

    @staticmethod
    def any_creature_died_this_turn():
        return lambda gs, s, e: len(gs.turn_mgr.cards_that_died) > 0

    @staticmethod
    def damage_source_in(target_filter: Callable):
        return lambda gs, source, event: (event.source in target_filter(gs, source)
                                          if isinstance(target_filter(gs, source), list)
                                          else [target_filter(gs, source)])

    @staticmethod
    def damage_target_in(target_filter: Callable):
        return lambda gs, source, event: (event.target in target_filter(gs, source)
                                          if isinstance(target_filter(gs, source), list)
                                          else [target_filter(gs, source)])

    @staticmethod
    def dier_is_creature():
        return lambda gs, s, e: e.card.is_creature

    @staticmethod
    def dier_is_your_artifact():
        return lambda gs, s, e: e.card.is_artifact and s.owner_id == e.card.owner_id

    @staticmethod
    def host_is_combatant():
        return lambda gs, s, e: s.host in gs.card_filter.combatants().result()

    @staticmethod
    def is_combat_damage():
        return lambda gs, s, e: e.is_combat

    @staticmethod
    def is_host_turn():
        return lambda gs, s, e: gs.turn_mgr.player_turn_idx == s.host.owner_id

    @staticmethod
    def is_your_turn():
        return lambda gs, s, e: gs.turn_mgr.player_turn_idx == s.owner_id

    @staticmethod
    def no_creatures_in_play():
        return lambda gs, s, e: not gs.card_filter.creatures().in_play().result()

    @staticmethod
    def opp_is_damage_receiver():
        return lambda gs, s, e: e.target == flip(s.owner_id)

    @staticmethod
    def opp_is_drawer():
        return lambda gs, s, e: e.player_id != s.owner_id

    @staticmethod
    def source_damaged_opp():
        return lambda gs, s, _: any(e.source is s and e.target == flip(s.owner_id)
                                    for e in gs.event_mgr.get_events(gs.turn_mgr.turn_number, DamageResolvedEvent))

    @staticmethod
    def self_is_a_blocker():
        return lambda gs, s, e: s in gs.card_filter.blockers().result()

    @staticmethod
    def self_is_attacker():
        return lambda gs, s, e: e.attacker is s

    @staticmethod
    def self_is_blocker():
        return lambda gs, s, e: e.blocker is s

    @staticmethod
    def self_is_combatant():
        return lambda gs, s, e: s in gs.card_filter.combatants().result()

    @staticmethod
    def self_is_damager():
        return lambda gs, s, e: e.source is s

    @staticmethod
    def self_is_damage_receiver():
        return lambda gs, s, e: e.target is s

    @staticmethod
    def self_is_tapped():
        return lambda gs, s, e: s.is_tapped

    @staticmethod
    def self_is_unblocked_attacker():
        return lambda gs, s, e: e.attacker is s

    @staticmethod
    def self_is_untapped():
        return lambda gs, s, e: not s.is_tapped

    @staticmethod
    def you_are_drawer():
        return lambda gs, s, e: e.player_id == s.owner_id
