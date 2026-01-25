from __future__ import annotations
from typing import TYPE_CHECKING, Optional

from ..counter_tokens import CARRION, CORPSE, PIN

if TYPE_CHECKING:
    from ..game_card import GameCard
    from game_state import GameState

from models.effects.base import Effect
from card_filter import CardFilter
from utils import flip

def destroy_on_end_step():
    """At the beginning of this turn's end step, destroy this card"""
    class E(Effect):
        event = 'end_step'

        def resolve(self, gs: GameState, source: GameCard, target: Optional[GameCard] = None):
            gs.send_to_graveyard_from_play(source)
    return E()

def dragon_whelp_on_end_step():
    """If this [pump] ability has been activated four or more times this turn,
    sacrifice this creature at the beginning of the next end step.
    Note: this isn't technically correct code.  Because PTTemp doesn't store the source card, I'm counting all +1/+0s"""
    class E(Effect):
        event = 'end_step'

        def resolve(self, gs: GameState, s: GameCard, target: Optional[GameCard] = None):
            cnt = len([temp for temp in s.modifiers.temps if temp.power_delta == 1 and temp.toughness_delta == 0])
            if cnt >= 4:
                gs.send_to_graveyard_from_play(s)
    return E()

def erg_raiders_on_end_step():
    """At YOUR end step, except for summoning sickness, if this creature didn't attack, 2 damage to you"""
    class E(Effect):
        event = 'end_step'

        def resolve(self, gs: GameState, s: GameCard, target: Optional[GameCard] = None):
            if gs.player_turn_idx != s.orig_owner_id:
                return
            if s.has_summoning_sickness:
                return
            if s not in gs.card_filter.attackers().result():
                gs.apply_damage(s, 2, s.orig_owner_id)
    return E()


def nettling_imp_on_end_step():
    """At this end step, destroy all untapped creatures that didn't attack this turn, except those who 'couldn't'."""

    class E(Effect):
        event = 'end_step'

        def resolve(self, gs: GameState, s: GameCard, target: Optional[GameCard] = None):
            """target = GameCard that needed to attack"""
            if target not in gs.card_filter.attackers().result():
                gs.send_to_graveyard_from_play(target)
    return E()

def osai_vultures_on_end_step():
    """At each end step, if a creature died this turn put a carrion counter on this creature"""

    class E(Effect):
        event = 'end_step'

        def resolve(self, gs: GameState, s: GameCard, target: Optional[GameCard] = None):
            if gs.cards_that_died_this_turn:
                s.counters.add_counter(CARRION)
    return E()

def pestilence_on_end_step():
    """At the beginning of the end step, if no creatures are on the battlefield, sacrifice this enchantment"""
    class E(Effect):
        event = 'end_step'

        def resolve(self, gs: GameState, s: GameCard, target: Optional[GameCard] = None):
            if not gs.card_filter.creatures().in_play().result():
                gs.send_to_graveyard_from_play(s)
    return E()

def scavenging_ghoul_on_end_step():
    """At each end step, put a corpse counter on this creature for each creature that died this turn ..."""

    class E(Effect):
        event = 'end_step'

        def resolve(self, gs: GameState, s: GameCard, target: Optional[GameCard] = None):
            if death_cnt := len(gs.cards_that_died_this_turn) > 0:
                s.counters.add_counter(CORPSE, death_cnt)
    return E()

def season_of_the_witch_on_end_step():
    """At YOUR end step, destroy all untapped creatures that didn't attack this turn, except those who 'couldn't'.
    Note: I'm defining 'couldn't' = summoning sickness or has no Attack"""

    class E(Effect):
        event = 'end_step'

        def resolve(self, gs: GameState, s: GameCard, target: Optional[GameCard] = None):
            if gs.player_turn_idx != s.orig_owner_id:
                return
            your_untapped_creatures = gs.card_filter.on_player_board(s.orig_owner_id).creatures().untapped().result()
            attackers = gs.card_filter.attackers().result()
            for creature in your_untapped_creatures:
                if creature in attackers:
                    continue
                if creature.has_summoning_sickness or 'Attack' not in creature.keyword_abilities:
                    continue
                gs.send_to_graveyard_from_play(creature)
    return E()

def voodoo_doll_at_end_step():
    """At your end step, if untapped, destroy this card & it deals damage to you = to the # of pin counters on it"""
    class E(Effect):
        event = 'end_step'

        def resolve(self, gs: GameState, source: GameCard, target: Optional[GameCard] = None):
            if source.is_tapped:
                return
            if pin_cnt := source.counters.get_count(PIN) > 0:
                gs.apply_damage(source, pin_cnt, source.orig_owner_id)
            gs.send_to_graveyard_from_play(source)
    return E()
