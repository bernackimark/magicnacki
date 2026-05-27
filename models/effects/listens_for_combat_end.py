from __future__ import annotations
from typing import TYPE_CHECKING

from models.effects.base import Listener
from models.events_all import CombatEndEvent, BlockEvent
from models.zone import Zone

if TYPE_CHECKING:
    from game_state import GameState
    from models.game_card.game_card import GameCard


class TimeElementalAttackedOrBlocked(Listener):
    """When this creature attacks or blocks, at end of combat, sacrifice it & it deals 5 damage to you"""
    listens_to = CombatEndEvent

    def on_event(self, gs: GameState, s: GameCard, event: BlockEvent):
        if s not in gs.card_filter.combatants().result():
            return
        gs.apply_damage(s, 5, s.owner_id)
        gs.destroy(s)


class DestroyAtCombatEnd(Listener):
    """Destroys target if it is still on the battlefield; unregisters itself"""
    listens_to = CombatEndEvent

    def __init__(self, source: GameCard, target: GameCard):
        self.source = source
        self.target = target

    def on_event(self, gs: GameState, s: GameCard, event: CombatEndEvent):
        if self.target.zone == Zone.BATTLEFIELD:
            gs.destroy(self.target)
        gs.event_mgr.unregister_specific_effect(self)
