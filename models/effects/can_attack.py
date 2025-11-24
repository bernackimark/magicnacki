from __future__ import annotations
from typing import TYPE_CHECKING, Optional

if TYPE_CHECKING:
    from ..game_card import GameCard
    from game_state import GameState

from models.effects.base import Effect
from utils import flip

def islandhome_can_attack_effect():
    class E(Effect):
        event = 'query'   # this aligns with your new "query" dispatch

        def on_query(self, gs: GameState, event: str, **kwargs):
            """event = query name, like 'can_attack', kwargs = includes 'card' when checking if a card can attack"""
            if event != 'can_attack' and not kwargs.get('card'):
                return None

            card = kwargs.get("card")
            if not card or 'Islandhome' not in card.props.keyword_abilities:
                return None

            opp_islands = (gs.card_filter.on_player_board(flip(card.orig_owner_id)).by_slug('island').result())
            return True if opp_islands else False
    return E()
