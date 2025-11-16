from dataclasses import dataclass, field

from models.game_card import GameCard
from constants import COLOR_LETTERS


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
        for color_code, color_cnt in c.props.casting_dict.items():
            if color_code != 'C' and color_cnt > self.available_mana[color_code]:
                return False
            if color_code == 'C' and c.props.casting_weight > self.available_mana_cnt:
                return False
        return True

    def play_to_board(self, c: GameCard):
        self._cards.append(c)
        self._cards.sort(key=lambda c: c.props.is_land)

    def remove_from_board(self, c: GameCard):
        self._cards.remove(c)
        self._cards.sort(key=lambda c: c.props.is_land)

    def add_mana(self, mana_color: str, cnt: int) -> None:
        self.available_mana[mana_color] += cnt

    def subtract_mana(self, mana_color: str, cnt: int) -> None:
        self.available_mana[mana_color] -= cnt

    def pay_casting_weight(self, casting_weight: int) -> None:
        for _ in range(casting_weight):
            untapped_lands = [c for c in self.cards if c.props.is_land and not c.is_tapped]
            untapped_lands[0].tap()
