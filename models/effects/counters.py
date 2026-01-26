from __future__ import annotations

from typing import Optional

from game_state import GameState
from models.counter_tokens import STORAGE, PLUS_ONE_ZERO, CARRION, CORPSE, PLUS_ZERO_ONE, MINUS_ZERO_TWO, PLUS_ONE, \
    VITALITY, HUNGER, MINUS_ONE, SLEEP, PIN, PUPA
from models.damage import DamageEvent
from models.effects.base import Effect
from models.game_card import GameCard


class CityOfShadowsAA1(Effect):
    """{T}, Exile a creature you control: Put a storage counter on this land"""
    def resolve(self, gs: GameState, source: GameCard, target: GameCard = None):
        source.counters.add_counter(STORAGE)


class CityOfShadowsAA2(Effect):
    """{T}: Add {C} for each storage counter on this land"""
    def resolve(self, gs: GameState, source: GameCard, target: GameCard = None):
        cnt = len(source.counters.get_count(STORAGE))
        gs.mana_pools[source.orig_owner_id].add_floating('C', cnt)


def remove_plus_one_zero():
    """... At end of combat, if this creature attacked or blocked this combat, remove a +1/+0 counter from it ..."""
    class E(Effect):
        event = 'combat_end'

        def resolve(self, gs: GameState, source: GameCard, target: Optional[GameCard] = None):
            if source in gs.card_filter.combatants().result():
                source.counters.remove_counter(PLUS_ONE_ZERO)
    return E()


def osai_vultures_on_end_step():
    """At each end step, if a creature died this turn put a carrion counter on this creature"""

    class E(Effect):
        event = 'end_step'

        def resolve(self, gs: GameState, s: GameCard, target: Optional[GameCard] = None):
            if gs.cards_that_died_this_turn:
                s.counters.add_counter(CARRION)
    return E()


def scavenging_ghoul_on_end_step():
    """At each end step, put a corpse counter on this creature for each creature that died this turn ..."""

    class E(Effect):
        event = 'end_step'

        def resolve(self, gs: GameState, s: GameCard, target: Optional[GameCard] = None):
            if death_cnt := len(gs.cards_that_died_this_turn) > 0:
                s.counters.add_counter(CORPSE, death_cnt)
    return E()


class XZeroOneCountersByManaValue(Effect):
    """Put X +0/+1 counters on target creature, where X is that creature's mana value"""
    def resolve(self, gs: GameState, source: GameCard, target: GameCard = None):
        if not target:
            raise RuntimeError(f'{source.props.name} needs a target')
        target.counters.add_counter(PLUS_ZERO_ONE, target.props.casting_weight)


def spirit_shackle_on_tap():
    """Whenever enchanted creature becomes tapped, put a -0/-2 counter on it. [the counters persist]"""
    class E(Effect):
        event = 'tap'

        def resolve(self, gs: GameState, source: GameCard, target: Optional[GameCard] = None):
            source.attached_to.counters.add_counter(MINUS_ZERO_TWO)
    return E()


def fungusaur_on_damage():
    """Whenever this creature is dealt damage, put a +1/+1 counter on it"""
    class E(Effect):
        event = 'on_damage'

        def resolve(self, gs: GameState, event: DamageEvent, this_card: GameCard = None):
            if event.target == this_card:
                this_card.counters.add_counter(PLUS_ONE)
    return E()


def living_artifact_on_damage():
    """Enchant artifact Whenever you're dealt damage, put that many vitality counters on this Aura ... """
    class E(Effect):
        event = 'on_damage'

        def resolve(self, gs: GameState, event: DamageEvent, this_card: GameCard = None):
            if event.target == this_card.orig_owner_id:
                this_card.counters.add_counter(VITALITY)
    return E()


def fasting_on_upkeep():
    """At your upkeep, put a hunger counter on this enchantment. Destroy Fasting if 5+ hunger counters on it ..."""
    class E(Effect):
        event = 'upkeep'

        def resolve(self, gs: GameState, source: GameCard, target=None):
            if gs.player_turn_idx != source.orig_owner_id:
                return
            source.counters.add_counter(HUNGER)
            if source.counters.get_count(HUNGER) > 4:
                gs.send_to_graveyard_from_play(source)
    return E()


def primordial_ooze_on_upkeep():
    """... At your upkeep, put a +1/+1 counter on this creature ..."""
    class E(Effect):
        event = 'upkeep'

        def resolve(self, gs: GameState, source: GameCard, target=None):
            if gs.player_turn_idx != source.attached_to.orig_owner_id:
                return
            source.attached_to.counters.add_counter(PLUS_ZERO_ONE)
    return E()


def unstable_mutation_on_upkeep():
    """At upkeep of enchanted creature's controller, put a -1/-1 counter on that creature"""
    class E(Effect):
        event = 'upkeep'

        def resolve(self, gs: GameState, source: GameCard, target=None):
            if gs.player_turn_idx != source.attached_to.orig_owner_id:
                return
            source.attached_to.counters.add_counter(MINUS_ONE)
    return E()


def venarian_gold_on_upkeep():
    """... At upkeep of enchanted creature's controller, remove a sleep counter from that creature"""
    class E(Effect):
        event = 'upkeep'

        def resolve(self, gs: GameState, source: GameCard, target=None):
            if gs.player_turn_idx != source.attached_to.orig_owner_id:
                return
            source.attached_to.counters.remove_counter(SLEEP)
    return E()


def voodoo_doll_on_upkeep():
    """At your upkeep, put a pin counter on this artifact"""
    class E(Effect):
        event = 'upkeep'

        def resolve(self, gs: GameState, source: GameCard, target=None):
            if gs.player_turn_idx != source.orig_owner_id:
                return
            source.counters.add_counter(PIN)
    return E()


def clockwork_avian_on_cast():
    """This creature enters with four +1/+0 counters on it ..."""
    class E(Effect):
        event = 'cast'

        def resolve(self, gs: GameState, source: GameCard, target=None):
            source.counters.add_counter(PLUS_ONE_ZERO, 4)
    return E()


def clockwork_beast_on_cast():
    """This creature enters with seven +1/+0 counters on it ..."""
    class E(Effect):
        event = 'cast'

        def resolve(self, gs: GameState, source: GameCard, target=None):
            source.counters.add_counter(PLUS_ONE_ZERO, 7)
    return E()


def cocoon_on_cast():
    """When this Aura enters, tap enchanted creature and put three pupa counters on this Aura ..."""
    class E(Effect):
        event = 'cast'

        def resolve(self, gs: GameState, source: GameCard, target=None):
            target.tap(gs)
            source.counters.add_counter(PUPA, 3)
    return E()


def tetravus_and_triskelion_on_cast():
    """This creature enters with three +1/+1 counters on it ..."""
    class E(Effect):
        event = 'cast'

        def resolve(self, gs: GameState, source: GameCard, target=None):
            source.counters.add_counter(PLUS_ONE, 3)
    return E()


def rock_hydra_on_cast():
    """This creature enters with X +1/+1 counters on it ..."""
    class E(Effect):
        event = 'cast'

        def resolve(self, gs: GameState, source: GameCard, target=None):
            if x := getattr(source, 'variable_x', 0):  # read X chosen when casting
                source.counters.add_counter(PLUS_ONE, x)
    return E()
