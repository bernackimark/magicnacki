from __future__ import annotations
from typing import TYPE_CHECKING

from models.actions.draw_discard import DiscardCard
from models.effects.base import Effect
from models.events_all import DiscardStepEvent, DiscardEvent
from models.utils import flip

if TYPE_CHECKING:
    from game_state import GameState
    from models.game_card.game_card import GameCard


class CursedRackEffect(Effect):
    """Opponent's maximum hand size is four [at their discard phase]"""
    listens_to = DiscardStepEvent

    def on_event(self, gs: GameState, source: GameCard, event: DiscardEvent):
        opp_id = flip(source.owner_id)
        if gs.turn_mgr.player_turn_idx != opp_id:
            return

        hand = gs.hands[opp_id]
        for i in range(len(hand.cards) - 4):
            gs.action_stack.push(DiscardCard(opp_id, gs, hand.cards[0]), gs, False)
