from __future__ import annotations
from typing import TYPE_CHECKING

from ..actions.choices import UntapChoice, LeaveTapped
from ..counter_tokens import PUPA

if TYPE_CHECKING:
    from ..game_card import GameCard
    from game_state import GameState

from models.effects.base import Effect

def cocoon_on_untap_phase():
    """Enchanted creature doesn't untap during your untap step if this Aura has a pupa counter on it"""
    class E(Effect):
        event = 'on_untap_phase'

        def resolve(self, gs: GameState, source: GameCard, _: GameCard = None):
            if source.attached_to.counters.get_count(PUPA):
                gs.action_stack.push(LeaveTapped(source.orig_owner_id, gs, source.attached_to), gs, False)
    return E()

def untap_option_on_untap_phase():
    class E(Effect):
        event = 'on_untap_phase'

        def resolve(self, gs: GameState, source: GameCard, _: GameCard = None):
            gs.action_stack.push(UntapChoice(gs.player_turn_idx, gs, source), gs, False)
    return E()
