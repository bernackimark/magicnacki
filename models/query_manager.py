from __future__ import annotations
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from game_state import GameState
    from models.game_card.game_card import GameCard

from models.events_all import CanBlockQueryEvent, CanAttackQueryEvent, CanCastQueryEvent, CanTargetQueryEvent, \
    CanUntapQueryEvent, CanDamageQueryEvent

class PermissionQuerier:
    def __init__(self, gs: GameState):
        self._gs = gs

    def can_attack(self, card: GameCard) -> bool:
        event = CanAttackQueryEvent(attacker=card)
        self._gs.event_mgr.emit(event, self._gs)
        return event.permission

    def can_block(self, blocker: GameCard, attacker: GameCard) -> bool:
        event = CanBlockQueryEvent(blocker=blocker, attacker=attacker)
        print(f'Checking if {blocker} can block {attacker}')
        self._gs.event_mgr.emit(event, self._gs)
        print(f'The event permission is {event.permission}')
        return event.permission is not False

    def can_cast(self, card: GameCard, p_id: int) -> bool:
        event = CanCastQueryEvent(card=card, p_id=p_id)
        self._gs.event_mgr.emit(event, self._gs)
        return event.permission

    def can_damage(self, target: GameCard, source: GameCard) -> bool:
        event = CanDamageQueryEvent(source=source, target=target)
        self._gs.event_mgr.emit(event, self._gs)
        return event.permission

    def can_target(self, target: GameCard | int, source: GameCard) -> bool:
        if isinstance(target, int):
            return True
        event = CanTargetQueryEvent(source=source, target=target)
        self._gs.event_mgr.emit(event, self._gs)
        return False if event.permission is False else True

    def can_untap(self, card: GameCard) -> bool:
        event = CanUntapQueryEvent(card=card)
        self._gs.event_mgr.emit(event, self._gs)
        return event.permission

