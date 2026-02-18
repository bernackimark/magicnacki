from __future__ import annotations
from typing import Optional, TYPE_CHECKING

from models.choice_actions_all import PayOneColorlessForOneLifeChoice
from models.events_all import DamageResolvedEvent, DiesEvent, CastResolvedEvent, LifeLossEvent, \
    UnblockedAttackerEvent

if TYPE_CHECKING:
    from game_state import GameState
    from models.game_card import GameCard

from models.effects.base import Effect
from models.utils import flip


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

class OnColorSpellGainLife(Effect):
    """Whenever a player casts a [certain color] spell, you gain 1 life"""
    listens_to = CastResolvedEvent

    def __init__(self, color: str, life_amt: int = 1):
        self.color = color
        self.life_amt = life_amt

    def on_event(self, gs: GameState, s: GameCard, event: CastResolvedEvent):
        if self.color not in event.card.props.colors:
            return
        gs.increment_life(s.owner_id, self.life_amt)

class OnColorSpellPayOneColorlessForOneLifeChoice(Effect):
    """Whenever a player casts a [certain color] spell, you may {1}: Gain 1 life"""
    listens_to = CastResolvedEvent

    def __init__(self, color: str):
        self.color = color

    def on_event(self, gs: GameState, s: GameCard, event: CastResolvedEvent):
        if self.color not in event.card.props.colors:
            return
        if not gs.mana_pools[s.owner_id].can_pay('1'):
            return
        gs.action_stack.push(PayOneColorlessForOneLifeChoice(s.owner_id, gs, s), gs, False)

class GainLife(Effect):
    def __init__(self, amt: int = 1):
        self.amt = amt

    def resolve(self, gs: GameState, source: GameCard, target: int = None):
        if not target:
            raise RuntimeError(f'{source.props.name} needs a target')
        gs.increment_life(target, self.amt)

# --- CARD-SPECIFIC ---
class AliFromCairo(Effect):
    """Damage that would reduce your life total to less than 1 reduces it to 1 instead"""
    listens_to = LifeLossEvent

    def on_event(self, gs: GameState, s: GameCard, event: LifeLossEvent):
        if event.p_id_taking_damage != s.owner_id:
            return

        current_life = gs.life[event.p_id_taking_damage]

        if current_life - event.amt < 1:
            event.amt = max(current_life - 1, 0)

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

class MerchantShip(Effect):
    """Whenever this creature attacks and isn't blocked, you gain 2 life"""
    listens_to = UnblockedAttackerEvent

    def on_event(self, gs: GameState, s: GameCard, event: UnblockedAttackerEvent):
        if event.attacker != s:
            return
        gs.increment_life(s.owner_id, 2)

class Onulet(Effect):
    """When this creature dies, you gain 2 life"""
    listens_to = DiesEvent

    def on_event(self, gs: GameState, source: GameCard, event: DiesEvent):
        if not isinstance(event, DiesEvent) or event.card != source:
            return
        gs.increment_life(source.orig_owner_id, 2)

class SpiritLink(Effect):
    """Enchant creature  Whenever enchanted creature deals damage, you gain that much life"""
    listens_to = DamageResolvedEvent

    def on_event(self, gs: GameState, source: GameCard, event: DamageResolvedEvent):
        if event.source is source.attached_to and event.amt > 0:
            gs.increment_life(source.orig_owner_id, event.amt)

class SpiritualSanctuary(Effect):
    """At the beginning of each player's upkeep, if that player controls a Plains, they gain 1 life"""
    def resolve(self, gs: GameState, source: GameCard, target: Optional[GameCard] = None):
        if 'plains' in gs.card_filter.on_player_board(gs.player_turn_idx).plains().result():
            gs.increment_life(gs.player_turn_idx, 1)

class StreamOfLife(Effect):
    def resolve(self, gs: GameState, source: GameCard, target: int = None):
        x = getattr(source, 'variable_x', 0)  # read X chosen when casting
        gs.increment_life(target, x)
