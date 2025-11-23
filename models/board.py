from dataclasses import dataclass, field
import re

from models.game_card import GameCard
from constants import COLOR_LETTERS


def parse_casting_cost(casting_cost: str) -> dict[str, int]:
    """ex return {'C': 2, 'U': 1, 'G': 0, ...} where C = colorless."""
    result = {c: 0 for c in COLOR_LETTERS}
    result['C'] = 0

    if not casting_cost:
        return result

    # extract multi-digit numbers → colorless mana
    for num in re.findall(r'\d+', casting_cost):
        result['C'] += int(num)

    # extract letters → colored mana
    for letter in re.findall(r'[A-Za-z]', casting_cost):
        if letter not in COLOR_LETTERS:
            raise NotImplementedError(f"Unknown mana symbol '{letter}' in '{casting_cost}'")
        result[letter] += 1

    return result

def casting_weight(casting_cost: str) -> int:
    parsed = parse_casting_cost(casting_cost)
    return parsed['C'] + sum(parsed[color] for color in COLOR_LETTERS)


@dataclass
class Board:
    player_idx: int
    _cards: list[GameCard] = field(default_factory=list)

    @property
    def cards(self) -> list[GameCard]:
        return self._cards

    @property
    def available_mana(self) -> dict:
        # TODO: needs to be thought thru; needs to handle cards that can spontaneously add mana
        d = {color: 0 for color in COLOR_LETTERS}
        d['C'] = 0
        d['W'] = sum([1 for c in self.cards if c.props.slug == 'plains' and not c.is_tapped])
        d['U'] = sum([1 for c in self.cards if c.props.slug == 'island' and not c.is_tapped])
        d['B'] = sum([1 for c in self.cards if c.props.slug == 'swamp' and not c.is_tapped])
        return d

    @property
    def available_mana_cnt(self) -> int:
        return sum([v for v in self.available_mana.values()])

    @property
    def available_blockers(self) -> list[GameCard]:
        return [c for c in self.cards if c.can_block and not c.is_tapped]

    def can_meet_casting_cost(self, casting_cost: str) -> bool:
        if not casting_cost:
            return True
        cost: dict[str: int] = parse_casting_cost(casting_cost)

        # Check colored mana
        for color, need in cost.items():
            if color != 'C' and need > self.available_mana[color]:
                return False

        # Check total mana requirement
        total_cost = sum(cost.values())
        if total_cost > self.available_mana_cnt:
            return False

        return True

    def play_to_board(self, c: GameCard):
        self._cards.append(c)
        self._cards.sort(key=lambda card: (card.props.is_land, card.props.is_creature))

    def remove_from_board(self, c: GameCard):
        self._cards.remove(c)
        self._cards.sort(key=lambda c: (c.props.is_land, c.props.is_creature))

    def pay_casting_weight(self, cast_weight: int, gs: "GameState") -> None:
        if not cast_weight:
            return
        for _ in range(cast_weight):
            untapped_lands = [c for c in self.cards if c.props.is_land and not c.is_tapped]
            untapped_lands[0].tap(gs)
