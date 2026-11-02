from __future__ import annotations
from dataclasses import dataclass, field
import re
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from game_state import GameState

from models.constants import COLOR_LETTERS_W_COLORLESS, COLOR_LETTER_SLUG, BASIC_LAND_MANA_PRODUCED, COLOR_LETTERS
from models.events_all import LandTappedForManaEvent

@dataclass
class ManaCost:
    cost: str
    x_value: int = 0

    def __add__(self, other: ManaCost) -> str:
        """Sums ManaCost objects; ex ManaCost('2U') + ManaCost('1GG') -> '3UGG'"""
        decoded = [self._decode(cost) for cost in (self.cost, other.cost)]
        combined = {k: sum(d[k] for d in decoded) for k in decoded[0]}
        return self._encode(combined)

    def __sub__(self, other: ManaCost) -> str:
        """Subtracts ManaCost objects; ex ManaCost('2GB') - ManaCost('1BU') -> '1G'; only validated for two objects"""
        decoded = [self._decode(cost) for cost in (self.cost, other.cost)]
        combined = {k: decoded[0][k] - sum(d[k] for d in decoded[1:]) for k in decoded[0]}
        return self._encode(combined)

    @property
    def decoded(self) -> dict[str, int]:
        return self._decode(self.cost, self.x_value)

    @property
    def mana_value(self) -> int:
        return sum(self.decoded.values())

    @staticmethod
    def _decode(cost_str: str, x_value: int = 0) -> dict[str, int]:
        """ex '2U' returns {'U': 1, 'G': 0, ... 'C': 2} where C = colorless; 'C' is guaranteed to be the last key;
        ex 'XU', x_value = 2 returns {'U': 1 ... 'C': 2}; ex 'XXU', x_value = 1 returns {'U': 1, 'C': 2}"""
        result = {c: 0 for c in COLOR_LETTERS_W_COLORLESS}

        if not cost_str:
            return result

        if x_value:
            result['C'] += cost_str.count('X') * x_value

        cost_str = cost_str.replace('X', '')

        # convert numbers to colorless & letters to colors
        for num in re.findall(r'\d+', cost_str):
            result['C'] += int(num)
        for letter in re.findall(r'[A-Za-z]', cost_str):
            if letter == 'T':
                continue
            result[letter] += 1
        return result

    @staticmethod
    def _encode(cost_dict: dict[str, int]) -> str:
        """Ex {'U': 1, 'G': 0, ... 'C': 2} returns '2U';
        iterate backward since 'C' is the last key; and colorless is expressed first in a cost string"""
        values = []
        for color, amt in reversed(cost_dict.items()):
            if amt < 1:
                continue
            values.append(str(amt)) if color == 'C' else values.append(color * amt)
        return ''.join(values)


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

    def can_pay(self, cost: str, x_value: int = 0) -> bool:
        if cost in {None, ''}:
            return True
        cost = ManaCost(cost, x_value=x_value).decoded
        available = self.available_mana.copy()

        # Pay colored first
        for color in COLOR_LETTERS:
            if available[color] < cost[color]:
                return False
            available[color] -= cost[color]

        # Can/Can't Pay colorless
        return sum(available.values()) >= cost['C']

    def pay(self, cost: str, x_value: int = 0) -> None:
        """Payment order: pay color cost w floating, pay color w basic land,
        pay colorless w floating, pay colorless w random basic land.
        Other land sources (ex: colorless producers) are not yet considered."""
        if cost in {None, ''}:
            return

        if not self.can_pay(cost, x_value=x_value):
            raise ValueError("Cannot pay mana cost")

        cost = ManaCost(cost, x_value=x_value).decoded

        # 1. Pay colored costs (everything except 'C')
        for c in cost:
            if c == 'C':
                continue

            paid = min(self._floating_mana[c], cost[c])
            self._floating_mana[c] -= paid
            cost[c] -= paid

            paid = min(self._untapped_basic_land_mana[c], cost[c])
            self._untapped_basic_land_mana[c] -= paid
            self._tap_lands_for_mana(c, paid)
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
                self._tap_lands_for_mana(c, paid)
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
        """Return the maximum X value the player can pay for a card with at least one X in its casting cost;
        If X is not in the provided casting cost, this will raise a ValueError"""
        x_cnt = casting_cost.count('X')
        if not x_cnt:
            raise ValueError("X not found in the cost")
        available_mana_amt = sum(self.available_mana.values())
        non_x_cost_dict = ManaCost(casting_cost).decoded
        non_x_casting_weight = sum(non_x_cost_dict.values())
        available_for_x: int = available_mana_amt - non_x_casting_weight
        max_x = available_for_x // x_cnt
        return max(max_x, 0)

    def _tap_lands_for_mana(self, color: str, amount: int):
        lands = self.gs.card_filter.on_player_board(self.owner_id).by_slug(COLOR_LETTER_SLUG[color]).untapped().result()
        if len(lands) < amount:
            raise RuntimeError("Not enough untapped lands")
        for land in lands[:amount]:
            land.tap()
            event = LandTappedForManaEvent(land, color)
            self.gs.event_mgr.emit(event, suppress_print=True)


# TODO:
#  1) Tally Available Mana:
#  - untapped basic lands
#  - floating
#  - other mana (ignore for now)
#  2) Pay:
#  - reduce floating
#  - tap basic lands
#  - other mana sources (ignore for now)
