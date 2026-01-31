from __future__ import annotations
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from game_state import GameState
    from models.game_card import GameCard

from models.damage_replacements import MartyrsOfKorlisReplacement
from models.effects.specifications import Static


class MartyrsOfKorlisDamageReplacement:
    def apply(self, gs: GameState, source: GameCard):
        gs.damage_replacements.append(MartyrsOfKorlisReplacement(source))

    def remove(self, gs: GameState, source: GameCard):
        gs.damage_replacements = [r for r in gs.damage_replacements
                                  if not (isinstance(r, MartyrsOfKorlisReplacement) and r.card is source)]
