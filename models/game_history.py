from __future__ import annotations
from datetime import datetime
from dataclasses import dataclass, field, asdict
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from game_state import GameState
    from models.actions.base import Action


@dataclass
class GameHistory:
    _items: list[dict] = field(default_factory=list)

    @property
    def items(self) -> list[dict]:
        return self._items

    def append_action(self, item: Action, gs: GameState) -> None:
        d = {'player_idx': item.player_idx,
             'turn_num': gs.turn_mgr.turn_number,
             'type': item.__class__.__name__,
             'ts': datetime.now()}
        if hasattr(item, 'card'):
            d['card'] = item.card
            d['card_id'] = item.card.id_
        self._items.append(d)

    def append_non_action(self, gs: GameState, **kwargs) -> None:
        d = kwargs
        d['turn_num'] = gs.turn_mgr.turn_number
        d['ts'] = datetime.now()
        if d.get('card'):
            d['card_id'] = d['card'].id_
        self._items.append(d)

    @property
    def last_action(self) -> dict | None:
        if not self._items:
            return None
        return self.items[-1]

    def get_last_n(self, n: int) -> list[dict] | None:
        return self._items[-n:]

