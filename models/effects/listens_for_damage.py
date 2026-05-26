from __future__ import annotations
from typing import TYPE_CHECKING

from models.counter_tokens import PLUS_ONE, VITALITY
from models.effects.base import Effect
from models.events_all import DamageResolvedEvent
from models.utils import flip

if TYPE_CHECKING:
    from game_state import GameState
    from models.game_card.game_card import GameCard


class AddPoisonCounter(Effect):
    """Whenever creature deals damage to a player, that player gets poison counter(s)"""
    listens_to = DamageResolvedEvent

    def __init__(self, cnt: int = 1):
        self.cnt = cnt

    def on_event(self, gs: GameState, source: GameCard, event: DamageResolvedEvent):
        opp = flip(source.owner_id)
        if event.source is source and event.target == opp:
            print(f"{event.source.props.name} adds {self.cnt} poison counter(s) to Player #{opp}. "
                  f"Poison Totals: {gs.score_mgr.poison_counters}")
            gs.score_mgr.add_poison_counter(opp, self.cnt)


class ElHajjaj(Effect):
    """Whenever this creature deals damage, you gain that much life"""
    listens_to = DamageResolvedEvent

    def on_event(self, gs: GameState, source: GameCard, event: DamageResolvedEvent):
        if event.source is source and event.amt > 0:
            gs.score_mgr.increment_life(source.owner_id, event.amt, source, gs)


class HypnoticSpecter(Effect):
    """Whenever this creature deals damage to an opponent, that player discards a card at random"""
    listens_to = DamageResolvedEvent

    def on_event(self, gs: GameState, source: GameCard, event: DamageResolvedEvent):
        opp_id = flip(source.owner_id)
        if event.source is not source or event.target is not opp_id:
            return
        opp_cards = gs.hands[opp_id].cards
        if not opp_cards:
            return
        if len(opp_cards) == 1:
            gs.discard(opp_cards[0], source)
            return
        random_card: GameCard = gs.randomize_event(opp_id, opp_cards)
        gs.discard(random_card, source)


class NicolBolas(Effect):
    """Whenever this creature deals damage to an opponent, that player discards their hand"""
    listens_to = DamageResolvedEvent

    def on_event(self, gs: GameState, source: GameCard, event: DamageResolvedEvent):
        opp_id = flip(source.owner_id)
        if event.source is not source or event.target is not opp_id:
            return
        opp_cards = gs.hands[opp_id].cards
        if not opp_cards:
            return
        for c in opp_cards:
            gs.discard(c, source)


class SpiritLink(Effect):
    """Enchant creature  Whenever enchanted creature deals damage, you gain that much life"""
    listens_to = DamageResolvedEvent

    def on_event(self, gs: GameState, source: GameCard, event: DamageResolvedEvent):
        if event.source is source.host and event.amt > 0:
            gs.score_mgr.increment_life(source.owner_id, event.amt, source, gs)


class GlyphOfLifeListener(Effect):
    """Registered by GlyphOfLife. Whenever that wall is dealt damage by an attacker this turn, gain that much life."""
    listens_to = DamageResolvedEvent

    def __init__(self, the_wall: GameCard):
        self.the_wall = the_wall

    def on_event(self, gs: GameState, s: GameCard, event: DamageResolvedEvent):
        if event.target is not self.the_wall or not event.is_combat:
            return
        gs.score_mgr.increment_life(s.owner_id, event.amt, s, gs)


class Backfire(Effect):
    """Whenever host deals damage to you, this Aura deals that much damage to that creature's controller"""
    listens_to = DamageResolvedEvent

    def on_event(self, gs: GameState, source: GameCard, event: DamageResolvedEvent):
        if event.source is source.host and event.target == source.owner_id:
            gs.apply_damage(source, event.amt, source.host.owner_id)


class FungusaurOnDamage(Effect):
    """Whenever this creature is dealt damage, put a +1/+1 counter on it"""
    listens_to = DamageResolvedEvent

    def on_event(self, gs: GameState, source: GameCard, event: DamageResolvedEvent):
        if event.target is not source:
            return
        source.counters.add_counter(PLUS_ONE)


class LivingArtifactOnDamage(Effect):
    """Enchant artifact Whenever you're dealt damage, put that many vitality counters on this Aura ...
    You can target opponent artifacts. The controller of the Aura controls the Living Artifact ability"""
    listens_to = DamageResolvedEvent

    def on_event(self, gs: GameState, source: GameCard, event: DamageResolvedEvent):
        if event.target is not source:
            return
        source.counters.add_counter(VITALITY)
