from __future__ import annotations
from typing import TYPE_CHECKING

from utils import flip
from ..actions.draw_discard import DiscardCard

if TYPE_CHECKING:
    from ..game_card import GameCard
    from game_state import GameState

from models.effects.base import Effect

def cursed_rack_at_discard_phase():
    """Opponent's maximum hand size is four [at their discard phase]"""
    class E(Effect):
        event = 'end_step'

        def resolve(self, gs: GameState, source: GameCard, target=None):
            opp_id = flip(source.orig_owner_id)
            if gs.player_turn_idx != opp_id:
                return
            hand = gs.hands[opp_id]
            if len(hand.cards) > 4:
                for c in hand.cards:
                    gs.action_stack.push(DiscardCard(opp_id, gs, c), gs, False)
    return E()
