from __future__ import annotations
from dataclasses import dataclass, field
import re
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from models.game_card import GameCard
    from game_state import GameState

from constants import BASIC_LANDS, BASIC_LAND_MANA_PRODUCED, COLOR_LETTERS_W_COLORLESS

def parse_casting_cost(casting_cost: str) -> dict[str, int]:
    """ex '2U' returns {'C': 2, 'U': 1, 'G': 0, ...} where C = colorless."""
    result = {c: 0 for c in COLOR_LETTERS_W_COLORLESS}

    if not casting_cost:
        return result

    # convert numbers to colorless & letters to colors
    for num in re.findall(r'\d+', casting_cost):
        result['C'] += int(num)
    for letter in re.findall(r'[A-Za-z]', casting_cost):
        result[letter] += 1
    return result

def casting_weight(casting_cost: str) -> int:
    return sum(parse_casting_cost(casting_cost).values())

@dataclass
class ManaPool:
    mana: dict[str, int] = field(default_factory=lambda: {c: 0 for c in COLOR_LETTERS_W_COLORLESS})

    def add(self, color: str, amount: int = 1):
        self.mana[color] += amount

    def can_pay(self, cost: dict[str: int] | str | None) -> bool:
        if cost is None:
            return True
        if isinstance(cost, str):
            cost = parse_casting_cost(cost)

        # 1. Pay colored mana first
        remaining_mana = self.mana.copy()

        for color in ('W', 'U', 'B', 'R', 'G'):
            if remaining_mana[color] < cost[color]:
                return False
            remaining_mana[color] -= cost[color]

        # 2. Pay colorless cost with any remaining mana
        total_remaining = sum(remaining_mana.values())

        return total_remaining >= cost['C']

    def pay(self, cost: dict[str: int] | str | None):
        if cost is None:
            return
        if isinstance(cost, str):
            cost = parse_casting_cost(cost)
        if not self.can_pay(cost):
            raise ValueError("Cannot pay mana cost")

        # 1. Pay colored costs first
        for color in ('W', 'U', 'B', 'R', 'G'):
            self.mana[color] -= cost[color]

        # 2. Pay colorless from ANY remaining mana
        remaining_colorless = cost['C']

        for color in ('W', 'U', 'B', 'R', 'G', 'C'):
            if remaining_colorless == 0:
                break

            spend = min(self.mana[color], remaining_colorless)
            self.mana[color] -= spend
            remaining_colorless -= spend

    @staticmethod
    def untap_lands(gs: GameState, p_idx: int):
        for land in gs.card_filter.on_player_board(p_idx).lands().result():
            land.untap()

    def add_mana_from_basic_land_tap(self, card: GameCard):
        if card.props.slug not in BASIC_LANDS:
            print(f"{card} tried to call ManaPool.add_mana_from_basic_land_tap")
            return
        color = BASIC_LAND_MANA_PRODUCED[card.props.slug]
        self.add(color, 1)

    def clear(self):
        for c in COLOR_LETTERS_W_COLORLESS:
            self.mana[c] = 0
