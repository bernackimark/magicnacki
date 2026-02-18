from __future__ import annotations
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from game_state import GameState
    from .game_card import GameCard

class RegenerationShield:
    def __init__(self, protected_card: GameCard):
        self.protected_card = protected_card

    def applies_to(self, card: GameCard) -> bool:
        return card is self.protected_card

    @staticmethod
    def apply(gs: GameState, card: GameCard):
        gs.tap_card(card)
        card.damage = 0
        gs.remove_from_combat(card)
        print(f'{card} has been regenerated')
