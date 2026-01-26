from __future__ import annotations

from typing import Optional

from game_state import GameState
from models.damage import DamageEvent
from models.effects.base import Effect
from models.game_card import GameCard
from utils import flip


def spirit_link_on_damage():
    """Enchant creature  Whenever enchanted creature deals damage, you gain that much life"""
    class E(Effect):
        event = 'on_damage'

        def resolve(self, gs: GameState, event: DamageEvent, this_card: GameCard = None):
            if event.source == this_card.attached_to:
                gs.increment_life(this_card.attached_to.orig_owner_id, event.remaining)
    return E()


def add_poison_counter_on_damage():
    """Whenever this creature deals damage to a player, that player gets a poison counter"""

    class E(Effect):
        event = 'on_damage'

        def resolve(self, gs: GameState, event: DamageEvent, this_card: GameCard = None):
            opp = flip(this_card.orig_owner_id)
            if event.source == this_card and event.target == opp:
                gs.add_poison_counter(opp)
                print(f"{event.source.props.name} adds a poison counter to Player #{opp}. "
                      f"Poison Totals: {gs.poison_counters}")

    return E()


def add_two_poison_counters_on_damage():
    """Whenever this creature deals damage to a player, that player gets two poison counters"""

    class E(Effect):
        event = 'on_damage'

        def resolve(self, gs: GameState, event: DamageEvent, this_card: GameCard = None):
            opp = flip(this_card.orig_owner_id)
            if event.source == this_card and event.target == flip(opp):
                print(f"{event.source.props.name} adds two poison counters to Player #{opp}. "
                      f"Poison Totals: {gs.poison_counters}")
                gs.add_poison_counter(opp, 2)

    return E()


def el_hajjaj_on_damage():
    """Whenever this creature deals damage, you gain that much life"""
    class E(Effect):
        event = 'on_damage'

        def resolve(self, gs: GameState, event: DamageEvent, this_card: GameCard = None):
            if event.source == this_card and event.remaining > 0:
                gs.increment_life(this_card.orig_owner_id, event.remaining)
    return E()


def ivory_tower_on_upkeep():
    class E(Effect):
        event = 'upkeep'

        def resolve(self, gs: GameState, source: GameCard, target: Optional[GameCard] = None):
            # At the beginning of your upkeep, you gain X life, where X is the number of cards in your hand minus 4
            p_id = source.orig_owner_id
            if (hand_size := len(gs.hands[p_id].cards)) > 4:
                gs.increment_life(p_id, hand_size - 4)
    return E()


def spiritual_sanctuary_on_upkeep():
    """At the beginning of each player's upkeep, if that player controls a Plains, they gain 1 life"""
    class E(Effect):
        event = 'upkeep'

        def resolve(self, gs: GameState, source: GameCard, target: Optional[GameCard] = None):
            if 'plains' in gs.card_filter.on_player_board(gs.player_turn_idx).by_slug('plains').result():
                gs.increment_life(gs.player_turn_idx, 1)
    return E()


def stream_of_life_on_cast():
    class E(Effect):
        event = 'cast'

        def resolve(self, gs: GameState, source: GameCard, target: int = None):
            x = getattr(source, 'variable_x', 0)  # read X chosen when casting
            gs.increment_life(target, x)
    return E()
