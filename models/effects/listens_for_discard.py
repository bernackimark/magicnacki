from __future__ import annotations

from game_state import GameState
from models.effects.base import Effect
from models.events_all import DiscardEvent
from models.game_card.game_card import GameCard


class PsychicPurgeDiscard(Effect):
    """... When a spell or ability an opponent controls causes you to discard this card, that player loses 5 life"""
    listens_to = DiscardEvent

    def on_event(self, gs: GameState, source: GameCard, event: DiscardEvent):
        if not event.source or event.source.owner_id != source.owner_id:
            return
        gs.apply_damage(source, 5, event.source.owner_id)
