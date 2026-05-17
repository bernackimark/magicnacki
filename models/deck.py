from dataclasses import dataclass, field
from typing import Iterable, Literal, Self

from data.deck_data import DeckData, get_deck, get_decks
from models.card import Card, CardUniverse
from models.constants import (BASIC_LANDS, OLD_SCHOOL_BANNED_SLUGS, OLD_SCHOOL_RESTRICTED_SLUGS, X_POINTS,
                              GENTLEMENS_RULES_BANNED_SLUGS, OLD_SCHOOL_SETS, OS_SCRYFALL_SETS)

@dataclass
class DeckBuilderRuleSet:
    card_universe: CardUniverse
    min_deck_size: int = 40
    max_deck_size: int = 99
    play_set_cnt: int = 4
    banned_slugs: Iterable[str] = OLD_SCHOOL_BANNED_SLUGS
    restricted_slugs: Iterable[str] = OLD_SCHOOL_RESTRICTED_SLUGS
    max_x_points: int | None = None
    max_side_cnt: int = 15


OS_CARD_UNIV = CardUniverse(OS_SCRYFALL_SETS)
OLD_SCHOOL_DB_RULE_SET = DeckBuilderRuleSet(OS_CARD_UNIV)  # all defaults
GENTLEMENS_DB_RULE_SET = DeckBuilderRuleSet(OS_CARD_UNIV,
                                            banned_slugs=OLD_SCHOOL_BANNED_SLUGS + GENTLEMENS_RULES_BANNED_SLUGS)
SINGLETON_DB_RULE_SET = DeckBuilderRuleSet(OS_CARD_UNIV, play_set_cnt=1)


@dataclass
class Deck:
    deck_id: str
    user_id: str
    name: str
    main: list[Card] = field(default_factory=list)
    side: list[Card] = field(default_factory=list)

    def __post_init__(self):
        if not self.deck_id:
            self.deck_id = str(max([int(d.deck_id) for d in get_decks()]) + 1) if get_decks() else "0"

    @property
    def unique_cards_sorted(self) -> list:
        return sorted({c.slug: c for c in self.main}.values(), key=lambda x: x.slug)

    @property
    def colors(self) -> str:
        colors_seen = set()
        for c in self.main:
            for color in c.colors:
                colors_seen.add(color)
        return ''.join(colors_seen)

    def add_card(self, c: Card, to_pile: str = 'main') -> None:
        self.main.append(c) if to_pile == 'main' else self.side.append(c)

    def remove_card(self, c: Card, from_pile: Literal['main', 'side'] = 'main') -> None:
        if from_pile == 'main':
            if c not in self.main:
                raise ValueError("That card doesn't exist in your deck")
            self.main.remove(c)
        else:
            if c not in self.side:
                raise ValueError("That card doesn't exist in your deck")
            self.side.remove(c)

    def promote(self, c: Card) -> None:
        card = next(x for x in self.side if x is c)
        self.side.remove(card)
        self.main.append(card)

    def demote(self, c: Card) -> None:
        card = next(x for x in self.main if x is c)
        self.main.remove(card)
        self.side.append(card)

    @classmethod
    def from_json(cls, deck_id: str, user_id: str) -> Self | None:
        """Obtains existing deck slugs & quantities; converts it to a card; returns a fully-formed Deck object"""
        deck_data: DeckData = get_deck(deck_id, user_id)
        if not deck_data:
            raise ValueError('No such deck found')
        main = [OS_CARD_UNIV[slug] for slug, qty in deck_data.main for _ in range(qty)]
        side = [OS_CARD_UNIV[slug] for slug, qty in deck_data.side for _ in range(qty)]
        return cls(deck_id, user_id, deck_data.name, main, side)

    def save_to_json(self, deck: Self) -> None:
        raise NotImplementedError

    def get_slug_cnt(self, slug: str) -> tuple[int, int]:
        """Returns tuple of int -- slug count in main & slug count in side"""
        main_cnt = len([c for c in self.main if c.slug == slug])
        side_cnt = len([c for c in self.side if c.slug == slug])
        return main_cnt, side_cnt


"""Validations for Match Manager, comparing cards to format rules:

    def complete_deck(self) -> Self:
        # if not self.rule_set.min_deck_size <= len(self.main) <= self.rule_set.max_deck_size:
        #     raise ValueError(f"Your deck has {len(self.main)} but must have between "
        #                      f"{self.rule_set.min_deck_size} & {self.rule_set.max_deck_size} cards")
        # if len(self.side) > self.rule_set.max_side_cnt:
        #     raise ValueError(f"Your sideboard may only contain up to {self.rule_set.max_side_cnt} cards")

    def add_card(self, c: Card, to_pile: str = 'main') -> None:
        # Card can't be on the banned list; only one allowed from restricted; can only have cnt up to max play set
        # if c.slug in self.rule_set.banned_slugs:
        #     raise ValueError(f"{c.name} is on the Banned List and cannot be added to your deck")
        # if c.slug in self.rule_set.restricted_slugs and self.get_slug_cnt(c.slug) == 1:
        #     raise ValueError(f"{c.name} is on the Restricted List and you already have one in your deck")
        # if c.slug not in BASIC_LANDS and self.get_slug_cnt(c.slug) >= self.rule_set.play_set_cnt:
        #     raise ValueError(f"You can only have the max play set ({self.rule_set.play_set_cnt}) for {c.name}")
        # if self.rule_set.max_x_points and sum([X_POINTS.get(c.slug, 0) for c in self.cards],
        #                                       X_POINTS.get(c.slug, 0)) > self.rule_set.max_x_points:
        #     raise ValueError(f"You have exceeded the allowed X-points")

"""