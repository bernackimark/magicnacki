from __future__ import annotations
from typing import TYPE_CHECKING

from models.damage import DamageReplacement, DamageEvent

if TYPE_CHECKING:
    from game_state import GameState
    from models.game_card import GameCard

class MartyrsOfKorlisReplacement(DamageReplacement):
    """As long as this creature is untapped,
    all damage that would be dealt to you by artifacts is dealt to this creature instead"""
    def __init__(self, card: GameCard):
        self.card = card

    def applies(self, gs: GameState, event: DamageEvent) -> bool:
        if self.card.is_tapped:
            return False
        if event.target != self.card.owner_id:
            return False
        if 'Artifact' not in event.source.props.card_types:
            return False
        return True

    def replace(self, gs: GameState, event: DamageEvent) -> None:
        event.target = self.card
