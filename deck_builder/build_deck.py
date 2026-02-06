from dataclasses import dataclass, field
from typing import Iterable, Protocol

from card import Card, CardUniverse
from constants import BASIC_LANDS, OLD_SCHOOL_BANNED_SLUGS, OLD_SCHOOL_RESTRICTED_SLUGS
from models.game_card import GameCard


class AddCardRuleFunc(Protocol):
    def __call__(self, slug: str, cnt: int, cards: list[GameCard]) -> bool:
        ...




@dataclass
class Deck:
    cards: list[GameCard]


@dataclass
class DeckBuilder:
    card_universe: CardUniverse
    player_idx: int
    cards: list[GameCard] = field(default_factory=list)
    min_deck_size: int = 40
    max_deck_size: int = 99
    play_set_cnt: int = 4
    banned_slugs: Iterable[str] = OLD_SCHOOL_BANNED_SLUGS
    restricted_slugs: Iterable[str] = OLD_SCHOOL_RESTRICTED_SLUGS

    @property
    def _next_card_id(self) -> int:
        if not self.cards:
            return 1
        return max([c.id for c in self.cards]) + 1

    @property
    def unique_cards_sorted(self) -> list:
        return sorted({c.props.slug: c for c in self.cards}.values(), key=lambda x: x.props.slug)

    def get_slug_cnt(self, slug: str) -> int:
        return sum([1 for c in self.cards if c.props.slug == slug]) if self.cards else 0

    def add_card(self, c: Card) -> None:
        """Card cannot be on the banned list; only one allowed from restricted; can only have cnt up to max play set"""
        if c.slug in self.banned_slugs:
            raise ValueError(f"{c.name} is on the Banned List and cannot be added to your deck")
        if c.slug in self.restricted_slugs and self.get_slug_cnt(c.slug) == 1:
            raise ValueError(f"{c.name} is on the Restricted List and you already have one in your deck")
        if c.slug not in BASIC_LANDS and self.get_slug_cnt(c.slug) >= self.play_set_cnt:
            raise ValueError(f"You can only have the max play set ({self.play_set_cnt}) for {c.name}")
        game_card = GameCard(self.card_universe[c.slug], self._next_card_id, self.player_idx)
        self.cards.append(game_card)

    def add_card_by_slug(self, slug: str):
        card = next(c for c in self.card_universe.cards if c.slug == slug)
        self.add_card(card)

    def remove_card(self, c: GameCard) -> None:
        if c not in self.cards:
            raise ValueError("That card doesn't exist in your deck")
        self.cards.remove(c)

    def change_image(self, c: GameCard, set_code: str) -> None:
        """For a card already added to a deck, set images on all such card instances"""
        for card in self.cards:
            if card.props.slug == c.props.slug:
                card.set_image(set_code)

    def complete_deck(self) -> Deck:
        if not self.min_deck_size <= len(self.cards) <= self.max_deck_size:
            raise ValueError(f"Your deck has {len(self.cards)} but must have between "
                             f"{self.min_deck_size} & {self.max_deck_size} cards")
        return Deck(self.cards)



