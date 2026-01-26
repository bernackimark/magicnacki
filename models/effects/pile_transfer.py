from __future__ import annotations

from game_state import GameState
from models.effects.base import Effect
from models.game_card import GameCard


class GraveyardToHand(Effect):
    def resolve(self, gs: GameState, source: GameCard, target: GameCard = None):
        card = gs.remove_from_your_graveyard(target, source.orig_owner_id)
        gs.add_to_hand(card, source.orig_owner_id)
