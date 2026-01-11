from __future__ import annotations
from typing import TYPE_CHECKING, Optional

from ..actions.choices import UntapOrDont

if TYPE_CHECKING:
    from ..game_card import GameCard
    from game_state import GameState

from models.effects.base import Effect

def untap_option_on_untap_phase():
    class E(Effect):
        event = 'on_untap_phase'

        def resolve(self, gs: GameState, source: GameCard, target=None):
            gs.action_stack.push(UntapOrDont(source.orig_owner_id, gs, source), gs, False)
    return E()
