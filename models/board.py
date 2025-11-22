from dataclasses import dataclass, field

from models.game_card import GameCard
from constants import COLOR_LETTERS


def casting_dict(casting_cost: str) -> dict[str: int]:
    d = {color: 0 for color in COLOR_LETTERS}
    d['C'] = 0  # colorless
    for char in casting_cost:
        if char in COLOR_LETTERS:
            d[char] += 1
        elif char in ('0', '1', '2', '3', '4', '5', '6', '7', '8', '9'):
            d['C'] += int(char)
        else:
            raise NotImplementedError(f"This card has a casting cost of '{casting_cost}' that I can't handle")
    return d

def casting_weight(casting_cost: str) -> int:
    # TODO: what happens if there's a "10" colorless"?
    if not casting_cost:
        return 0
    weight = 0
    for char in casting_cost:
        try:
            colorless = int(char)
            weight += colorless
            continue
        except ValueError:
            pass
        if char in COLOR_LETTERS:
            weight += 1
    return weight


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

    def can_card_meet_casting_cost(self, c: GameCard) -> bool:
        if not c.casting_cost:
            return True
        for color_code, color_cnt in c.props.casting_dict.items():
            if color_code != 'C' and color_cnt > self.available_mana[color_code]:
                return False
            if color_code == 'C' and c.props.casting_weight > self.available_mana_cnt:
                return False
        return True

    def can_meet_casting_cost(self, casting_cost: str) -> bool:
        # using this for activating abilities
        if not casting_cost:
            return True
        for color_code, color_cnt in casting_dict(casting_cost).items():
            if color_code != 'C' and color_cnt > self.available_mana[color_code]:
                return False
            if color_code == 'C' and casting_weight(casting_cost) > self.available_mana_cnt:
                return False
        return True

    def play_to_board(self, c: GameCard):
        self._cards.append(c)
        self._cards.sort(key=lambda c: (c.props.is_land, c.props.is_creature))

    def remove_from_board(self, c: GameCard):
        self._cards.remove(c)
        self._cards.sort(key=lambda c: (c.props.is_land, c.props.is_creature))

    def pay_casting_weight(self, cast_weight: int, gs: "GameState") -> None:
        if not cast_weight:
            return
        for _ in range(cast_weight):
            untapped_lands = [c for c in self.cards if c.props.is_land and not c.is_tapped]
            untapped_lands[0].tap(gs)
