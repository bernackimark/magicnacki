from __future__ import annotations
from typing import TYPE_CHECKING

from models.choice_actions_all import FloralSpuzzemChoice
from models.effects.base import Listener
from models.events_all import UnblockedAttackerEvent
from models.modifiers import PTMod
from models.utils import flip

if TYPE_CHECKING:
    from game_state import GameState
    from models.game_card.game_card import GameCard


class MerchantShip(Listener):
    """Whenever this creature attacks and isn't blocked, you gain 2 life"""
    listens_to = UnblockedAttackerEvent

    def on_event(self, gs: GameState, s: GameCard, event: UnblockedAttackerEvent):
        if event.attacker != s:
            return
        gs.score_mgr.increment_life(s.owner_id, 2, s, gs)


class MurkDwellers(Listener):
    """Whenever this creature attacks and isn't blocked, it gets +2/+0 until end of combat"""
    listens_to = UnblockedAttackerEvent

    def on_event(self, gs: GameState, s: GameCard, event: UnblockedAttackerEvent):
        if event.attacker != s:
            return
        s.modifiers.items.append(PTMod(s=s, p_adj=2, expires='EOT'))


class FloralSpuzzem(Listener):
    """Whenever this creature walks, you may destroy target opp artifact instead of dealing the combat damage."""
    listens_to = UnblockedAttackerEvent

    def on_event(self, gs: GameState, s: GameCard, event: UnblockedAttackerEvent):
        if event.attacker != s or not gs.card_filter.on_player_board(flip(s.owner_id)).artifacts().result():
            return
        gs.action_stack.push(FloralSpuzzemChoice(s.owner_id, gs, s), gs, False)
