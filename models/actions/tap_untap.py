from __future__ import annotations
from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from models.game_card.game_card import GameCard
    from game_state import GameState

from models.actions.base import Action

@dataclass
class TapCard(Action):
    card: GameCard

    def __repr__(self) -> str:
        return f"Tap {self.card.__repr__()}"

    def play(self) -> None:
        self.card.tap()


@dataclass
class UntapCard(Action):
    card: GameCard

    def __repr__(self) -> str:
        return f"Untap {self.card.__repr__()}"

    def play(self) -> None:
        self.card.untap()


class UntapCardStackPop(Action):
    def __init__(self, p_id: int, gs: GameState, s: GameCard):
        super().__init__(p_id, gs)
        self.source = s

    def __repr__(self):
        return f'Untap {self.source}'

    def play(self):
        self.source.untap()
        self.gs.turn_mgr.untap_decisions_made.add(self.source.id_)
        self.gs.action_stack.pop()

class UntapWithManaAction(Action):
    def __init__(self, p_id: int, gs: GameState, s: GameCard, mana_cost: str):
        super().__init__(p_id, gs)
        self.source = s
        self.mana_cost = mana_cost

    def __repr__(self):
        return f'{{{self.mana_cost}}}: Untap {self.source}'

    def play(self):
        self.gs.mana_pools[self.source.owner_id].pay(self.mana_cost)
        self.source.untap()
        self.gs.action_stack.pop()

class LeaveTapped(Action):
    def __init__(self, p_id: int, gs: GameState, s: GameCard):
        super().__init__(p_id, gs)
        self.card = s

    def __repr__(self):
        return f'Leave {self.card} tapped'

    def play(self):
        self.gs.turn_mgr.untap_decisions_made.add(self.card.id_)
        self.gs.action_stack.pop()
