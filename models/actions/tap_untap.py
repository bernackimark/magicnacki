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
        self.finish()

@dataclass
class Untap(Action):
    card: GameCard

    def __repr__(self) -> str:
        return f"Untap {self.card.__repr__()}"

    def play(self) -> None:
        self.card.untap()
        self.gs.turn_mgr.untap_decisions_made.add(self.card.id_)
        self.finish()

class PayManaToUntapAction(Action):
    """Remaining is for other cards that would be candidates for a successive ChoiceAction"""
    def __init__(self, p_id: int, gs: GameState, s: GameCard, target: GameCard, mana_cost: str,
                 remaining: list[GameCard] | None = None):
        super().__init__(p_id, gs)
        self.source = s
        self.target = target
        self.mana_cost = mana_cost
        self.remaining = remaining or []

    def __repr__(self):
        return f'{{{self.mana_cost}}}: Untap {self.target}'

    def play(self):
        from models.choice_actions_all import ChoiceAction
        if not self.gs.mana_pools[self.target.owner_id].can_pay(self.mana_cost):
            self.finish()
            return
        self.gs.mana_pools[self.target.owner_id].pay(self.mana_cost)
        self.target.untap()
        self.finish()

        remaining = [c for c in self.remaining if c is not self.target and c.is_tapped
                     and self.gs.mana_pools[self.player_idx].can_pay(self.mana_cost)]
        if remaining:
            options = [PayManaToUntapAction(self.player_idx, self.gs, self.source, c, self.mana_cost, remaining)
                       for c in remaining]
            self.finish(ChoiceAction(options, may=True))
        else:
            self.finish()

class LeaveTapped(Action):
    def __init__(self, p_id: int, gs: GameState, card: GameCard):
        super().__init__(p_id, gs)
        self.card = card

    def __repr__(self):
        return f'Leave {self.card} tapped'

    def play(self):
        self.gs.turn_mgr.untap_decisions_made.add(self.card.id_)
        self.finish()
