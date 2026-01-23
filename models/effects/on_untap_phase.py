from __future__ import annotations
from typing import TYPE_CHECKING

from ..actions.choices import UntapChoice

if TYPE_CHECKING:
    from ..game_card import GameCard
    from game_state import GameState

from models.effects.base import Effect

def untap_option_on_untap_phase():
    class E(Effect):
        event = 'on_untap_phase'

        def resolve(self, gs: GameState, source: GameCard, _: GameCard = None):
            gs.action_stack.push(UntapChoice(gs.player_turn_idx, gs, source), gs, False)
    return E()
