from __future__ import annotations
from typing import Optional, TYPE_CHECKING

from models.events.events_all import DamageResolvedEvent

if TYPE_CHECKING:
    from game_state import GameState
    from models.game_card import GameCard

from models.effects.base import Effect
from utils import flip


# --- GENERICS ---
class AddPoisonCounter(Effect):
    """Whenever creature deals damage to a player, that player gets poison counter(s)"""
    listens_to = DamageResolvedEvent

    def __init__(self, cnt: int = 1):
        self.cnt = cnt

    def on_event(self, gs: GameState, source: GameCard, event: DamageResolvedEvent):
        opp = flip(source.orig_owner_id)
        if event.source is source and event.target == opp:
            print(f"{event.source.props.name} adds {self.cnt} poison counter(s) to Player #{opp}. "
                  f"Poison Totals: {gs.poison_counters}")
            gs.add_poison_counter(opp, self.cnt)

class GainLife(Effect):
    def __init__(self, amt: int = 1):
        self.amt = amt

    def resolve(self, gs: GameState, source: GameCard, target: int = None):
        if not target:
            raise RuntimeError(f'{source.props.name} needs a target')
        gs.increment_life(target, self.amt)

# --- CARD-SPECIFIC ---
class ElHajjaj(Effect):
    """Whenever this creature deals damage, you gain that much life"""
    listens_to = DamageResolvedEvent

    def on_event(self, gs: GameState, source: GameCard, event: DamageResolvedEvent):
        if event.source is source and event.amt > 0:
            gs.increment_life(source.orig_owner_id, event.amt)

class IvoryTower(Effect):
    """At the beginning of your upkeep, you gain X life, where X is the number of cards in your hand minus 4"""
    def resolve(self, gs: GameState, source: GameCard, target: Optional[GameCard] = None):
        p_id = source.orig_owner_id
        if p_id != gs.player_turn_idx:
            return
        if (hand_size := len(gs.hands[p_id].cards)) > 4:
            gs.increment_life(p_id, hand_size - 4)

class SpiritLink(Effect):
    """Enchant creature  Whenever enchanted creature deals damage, you gain that much life"""
    listens_to = DamageResolvedEvent

    def on_event(self, gs: GameState, source: GameCard, event: DamageResolvedEvent):
        if event.source is source.attached_to and event.amt > 0:
            gs.increment_life(source.orig_owner_id, event.amt)

class SpiritualSanctuary(Effect):
    """At the beginning of each player's upkeep, if that player controls a Plains, they gain 1 life"""
    def resolve(self, gs: GameState, source: GameCard, target: Optional[GameCard] = None):
        if 'plains' in gs.card_filter.on_player_board(gs.player_turn_idx).by_slug('plains').result():
            gs.increment_life(gs.player_turn_idx, 1)

class StreamOfLife(Effect):
    def resolve(self, gs: GameState, source: GameCard, target: int = None):
        x = getattr(source, 'variable_x', 0)  # read X chosen when casting
        gs.increment_life(target, x)
