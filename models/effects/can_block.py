from __future__ import annotations
from typing import TYPE_CHECKING

from constants import BASIC_LANDS

if TYPE_CHECKING:
    from ..game_card import GameCard
    from game_state import GameState

from models.effects.base import Effect


def can_block_base_rule():
    class E(Effect):
        event = "query"

        def on_query(self, gs: GameState, event: str, card: GameCard, **kwargs):
            """Query: card = blocker, mandatory kwarg: attacker"""
            if event != "can_block":
                return None
            attacker: GameCard = kwargs.get("attacker")
            if not attacker or not card:
                return None

            # Global land walk rule
            defender_idx = card.orig_owner_id
            for walk, basic_land in zip([land.capitalize() + 'walk' for land in BASIC_LANDS], BASIC_LANDS):
                if walk in attacker.keyword_abilities and gs.card_filter.on_player_board(defender_idx).by_slug(basic_land).result():
                    return False

            # Global Flying/Reach rule
            if ('Flying' in attacker.keyword_abilities and
                    not any(kwa for kwa in card.keyword_abilities if kwa in ('Flying', 'Reach'))):
                return False

            return None  # no opinion if can_block ... might need this in case there are other rules added in elsewhere?
    return E()

