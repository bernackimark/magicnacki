from __future__ import annotations
from typing import TYPE_CHECKING

from models.actions.draw_discard import DiscardCards
from models.effects.base import Listener
from models.events_all import DiscardEvent, DiscardStepEvent, DrawCardEvent, DrawStepEvent
from models.utils import flip

if TYPE_CHECKING:
    from models.game_card.game_card import GameCard
    from game_state import GameState


# --- DISCARD EVENT ---
class PsychicPurgeDiscard(Listener):
    """... When a spell or ability an opponent controls causes you to discard this card, that player loses 5 life"""
    listens_to = DiscardEvent

    def on_event(self, gs: GameState, source: GameCard, event: DiscardEvent):
        if not event.source or event.source.owner_id != source.owner_id:
            return
        gs.apply_damage(source, 5, event.source.owner_id)


# --- DISCARD STEP EVENT ---
class CursedRackEffect(Listener):
    """Opponent's maximum hand size is four [at their discard phase]"""
    listens_to = DiscardStepEvent

    def on_event(self, gs: GameState, source: GameCard, event: DiscardEvent):
        opp_id = flip(source.owner_id)
        if gs.player_turn_idx != opp_id:
            return

        hand = gs.pile_mgr.hands[opp_id]
        for i in range(len(hand) - 4):
            gs.action_stack.push(DiscardCards(opp_id, gs, hand[0]), gs, False)


# --- DRAW EVENT ---
class FastingDestroy(Listener):
    """When you draw a card, destroy this enchantment"""
    listens_to = DrawCardEvent

    def on_event(self, gs: GameState, source: GameCard, event: DrawCardEvent):
        if event.player_id == source.owner_id:
            gs.pile_mgr.destroy(source)

class UnderworldDreams(Listener):
    """Whenever an opponent draws a card, this enchantment deals 1 damage to that player"""
    listens_to = DrawCardEvent

    def on_event(self, gs: GameState, source: GameCard, event: DrawCardEvent):
        if source.owner_id == event.player_id:
            return
        gs.apply_damage(source, 1, event.player_id)


# --- DRAW STEP EVENT ---
class HowlingMine(Listener):
    """At each player's draw step, if this artifact is untapped, that player draws an additional card"""
    listens_to = DrawStepEvent

    def on_event(self, gs: GameState, source: GameCard, event: DrawStepEvent):
        if source.is_tapped:
            return
        gs.pile_mgr.draw(event.active_player)

class ManaVaultDamageIfTapped(Listener):
    """... At your draw step, if this artifact is tapped, it deals 1 damage to you ..."""
    listens_to = DrawStepEvent

    def on_event(self, gs: GameState, s: GameCard, event: DrawStepEvent):
        if event.active_player != s.owner_id or not s.is_tapped:
            return
        gs.apply_damage(s, 1, s.owner_id)
