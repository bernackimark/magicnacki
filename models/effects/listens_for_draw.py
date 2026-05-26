from __future__ import annotations
from typing import TYPE_CHECKING

from models.effects.base import Effect
from models.events_all import DrawCardEvent

if TYPE_CHECKING:
    from game_state import GameState
    from models.game_card.game_card import GameCard


class UnderworldDreams(Effect):
    """Whenever an opponent draws a card, this enchantment deals 1 damage to that player"""
    listens_to = DrawCardEvent

    def on_event(self, gs: GameState, source: GameCard, event: DrawCardEvent):
        if source.owner_id == event.player_id:
            return
        gs.apply_damage(source, 1, event.player_id)
