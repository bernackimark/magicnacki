from dataclasses import dataclass, field

from card import Card, CardUniverse
from constants import BASIC_LANDS


@dataclass
class GameCard:
    props: Card
    id: int
    orig_owner_id: int
    img_url: str = field(init=False)
    casting_cost: str = field(init=False)
    is_tapped: bool = False
    can_attack: bool = False
    can_block: bool = True
    has_summoning_sickness: bool = True

    def __post_init__(self):
        self.img_url = next(iter(self.props.images.values()))  # set to the earliest set's image
        self.casting_cost = self.props.casting_cost
        if 'Haste' in self.props.keyword_abilities:
            self.has_summoning_sickness = False
        if self.props.is_creature:
            self.can_attack = True

    def __repr__(self) -> str:
        text = f'{self.props.name} ({self.props.power}/{self.props.toughness})' if self.props.is_creature else self.props.name
        return text.upper() if not self.is_tapped else text.lower()

    def tap(self) -> None:
        self.is_tapped = True

    def untap(self) -> None:
        self.is_tapped = False

    def set_image(self, set_code: str):
        self.img_url = self.props.images.get(set_code) or self.img_url


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
    max_non_basic_land_instances: int = 4

    @property
    def _next_card_id(self) -> int:
        if not self.cards:
            return 1
        return max([c.id for c in self.cards]) + 1

    @property
    def unique_cards_sorted(self) -> list:
        return sorted({c.props.slug: c for c in self.cards}.values(), key=lambda x: x.props.slug)

    def get_slug_cnt(self, slug: str) -> int:
        if not self.cards:
            return 0
        return sum([1 for c in self.cards if c.props.slug == slug])

    def add_card(self, c: Card) -> None:
        if c.slug not in BASIC_LANDS and self.get_slug_cnt(c.slug) >= self.max_non_basic_land_instances:
            raise ValueError(f"You can only have {self.max_non_basic_land_instances} instances of {c.name}")
        game_card = GameCard(self.card_universe[c.slug], self._next_card_id, self.player_idx)
        self.cards.append(game_card)

    def add_card_by_slug(self, slug: str):
        if slug not in BASIC_LANDS and self.get_slug_cnt(slug) >= self.max_non_basic_land_instances:
            raise ValueError(f"You can only have {self.max_non_basic_land_instances} instances of {slug}")
        game_card = GameCard(self.card_universe[slug], self._next_card_id, self.player_idx)
        self.cards.append(game_card)

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



