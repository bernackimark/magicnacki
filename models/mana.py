from __future__ import annotations
from dataclasses import dataclass, field
import re
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from game_state import GameState

from models.constants import COLOR_LETTERS_W_COLORLESS, COLOR_LETTER_SLUG, BASIC_LAND_MANA_PRODUCED, COLOR_LETTERS


def parse_casting_cost(casting_cost: str) -> dict[str, int]:
    """ex '2U' returns {'C': 2, 'U': 1, 'G': 0, ...} where C = colorless."""
    result = {c: 0 for c in COLOR_LETTERS_W_COLORLESS}

    if not casting_cost:
        return result

    if 'X' in casting_cost:
        result['X'] = 0

    # convert numbers to colorless & letters to colors
    for num in re.findall(r'\d+', casting_cost):
        result['C'] += int(num)
    for letter in re.findall(r'[A-Za-z]', casting_cost):
        if letter == 'T':
            continue
        result[letter] += 1
    return result

def casting_weight(casting_cost: str) -> int:
    return sum(parse_casting_cost(casting_cost).values())

@dataclass
class ManaPool:
    gs: GameState
    owner_id: int
    _floating_mana: dict[str, int] = field(default_factory=lambda: {c: 0 for c in COLOR_LETTERS_W_COLORLESS})

    def add_floating(self, color: str, amount: int = 1):
        self._floating_mana[color] += amount

    def clear_floating(self):
        for c in COLOR_LETTERS_W_COLORLESS:
            self._floating_mana[c] = 0

    def can_pay(self, cost: dict[str, int] | str | None) -> bool:
        if cost is None:
            return True
        if isinstance(cost, str):
            cost: dict[str, int] = parse_casting_cost(cost)

        available = self.available_mana.copy()

        # Pay colored first
        for color in COLOR_LETTERS:
            if available[color] < cost[color]:
                return False
            available[color] -= cost[color]

        # Can/Can't Pay colorless
        return sum(available.values()) >= cost['C']

    def pay(self, cost: dict[str, int] | str | None):
        """Payment order: pay color cost w floating, pay color w basic land,
        pay colorless w floating, pay colorless w random basic land.
        Other land sources (ex: colorless producers) are not yet considered."""
        if cost is None:
            return
        if isinstance(cost, str):
            cost = parse_casting_cost(cost)
        if not self.can_pay(cost):
            raise ValueError("Cannot pay mana cost")

        # 1. Pay colored costs (everything except 'C')
        for c in cost:
            if c == 'C':
                continue

            paid = min(self._floating_mana[c], cost[c])
            self._floating_mana[c] -= paid
            cost[c] -= paid

            paid = min(self._untapped_basic_land_mana[c], cost[c])
            self._untapped_basic_land_mana[c] -= paid
            self._tap_lands_for_color(c, paid)
            cost[c] -= paid

        # 2. Pay colorless cost using ANY remaining mana
        remaining = cost['C']

        if remaining:
            # floating mana first
            for c in self._floating_mana:
                paid = min(self._floating_mana[c], remaining)
                self._floating_mana[c] -= paid
                remaining -= paid
                if not remaining:
                    break

        if remaining:
            # then iterate over basic land items until cost is zeroed out
            for c, amt in self._untapped_basic_land_mana.items():
                if not amt:
                    continue
                paid = min(self._untapped_basic_land_mana[c], remaining)
                self._untapped_basic_land_mana[c] -= paid
                self._tap_lands_for_color(c, paid)
                remaining -= paid
                if not remaining:
                    break

        cost['C'] = remaining

        # use other sources (not yet considered)
        # a to-do

        assert sum(cost.values()) == 0, "The cost wasn't fully paid"

    @property
    def _untapped_basic_land_mana(self) -> dict[str, int]:
        basic_land_mana = {c: 0 for c in COLOR_LETTERS_W_COLORLESS}
        untapped_lands = self.gs.card_filter.on_player_board(self.owner_id).basic_lands().untapped().result()
        for land in untapped_lands:
            color = BASIC_LAND_MANA_PRODUCED[land.props.slug]  # ex: 'W' for plains
            basic_land_mana[color] += 1
        return basic_land_mana

    @property
    def available_mana(self) -> dict[str, int]:
        """Single dictionary with six key-values summing all untapped basic land & floating mana.
        Ex: {'W': 1, 'U': 0, 'G': 3, 'B': 2, 'R': 0, 'C': 0}.
        Note: other mana sources aren't yet considered (ex: Birds of Paradise),
        so those would have to be tapped/activated first to add floating mana"""
        return {color: self._untapped_basic_land_mana[color] + self._floating_mana[color]
                for color in self._untapped_basic_land_mana}

    def get_max_x(self, casting_cost: str) -> int:
        """Return the maximum X value the player can pay for a card with X in its casting cost."""
        if 'X' not in casting_cost:
            raise ValueError(f"X is not in the casting cost")
        cost = parse_casting_cost(casting_cost)  # {'X': 0, 'U': 2, ...}
        cost['X'] = 0  # since 'X' is in the cast cost, it's being treated as {'X': 1 ...}
        non_x_casting_weight = sum(cost.values())
        available_mana_amt = sum(self.available_mana.values())
        max_x = available_mana_amt - non_x_casting_weight
        return max(max_x, 0)

    def _tap_lands_for_color(self, color: str, amount: int):
        lands = self.gs.card_filter.on_player_board(self.owner_id).by_slug(COLOR_LETTER_SLUG[color]).untapped().result()
        if len(lands) < amount:
            raise RuntimeError("Not enough untapped lands")
        for land in lands[:amount]:
            land.tap(self.gs)

    def _tap_lands_for_colorless(self, amount: int):
        # currently unused, but may be helpful if functionality is added?
        lands = self.gs.card_filter.on_player_board(self.owner_id).basic_lands().tapped(False).result()
        if len(lands) < amount:
            raise RuntimeError("Not enough untapped lands")
        for land in lands[:amount]:
            land.tap(self.gs)


# TODO:
#  1) Tally Available Mana:
#  - untapped basic lands
#  - floating
#  - other mana (ignore for now)
#  2) Pay:
#  - reduce floating
#  - tap basic lands
#  - other mana sources (ignore for now)
