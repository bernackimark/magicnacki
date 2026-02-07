from dataclasses import dataclass, field
from typing import Iterable

from card import Card, CardUniverse
from constants import (BASIC_LANDS, OLD_SCHOOL_BANNED_SLUGS, OLD_SCHOOL_RESTRICTED_SLUGS, X_POINTS,
                       GENTLEMENS_RULES_BANNED_SLUGS, OLD_SCHOOL_SETS)
from models.game_card import GameCard


@dataclass
class DeckBuilderRuleSet:
    card_universe: CardUniverse = CardUniverse(OLD_SCHOOL_SETS)
    min_deck_size: int = 40
    max_deck_size: int = 99
    play_set_cnt: int = 4
    banned_slugs: Iterable[str] = OLD_SCHOOL_BANNED_SLUGS
    restricted_slugs: Iterable[str] = OLD_SCHOOL_RESTRICTED_SLUGS
    max_x_points: int | None = None


OLD_SCHOOL_DB_RULE_SET = DeckBuilderRuleSet()  # all defaults
GENTLEMENS_DB_RULE_SET = DeckBuilderRuleSet(banned_slugs=OLD_SCHOOL_BANNED_SLUGS + GENTLEMENS_RULES_BANNED_SLUGS)
SINGLETON_DB_RULE_SET = DeckBuilderRuleSet(play_set_cnt=1)


@dataclass
class Deck:
    cards: list[GameCard]


@dataclass
class DeckBuilder:
    rule_set: DeckBuilderRuleSet
    player_idx: int
    cards: list[Card] = field(default_factory=list)

    @property
    def unique_cards_sorted(self) -> list:
        return sorted({c.slug: c for c in self.cards}.values(), key=lambda x: x.slug)

    def get_slug_cnt(self, slug: str) -> int:
        return sum([1 for c in self.cards if c.slug == slug]) if self.cards else 0

    def add_card(self, c: Card) -> None:
        """Card cannot be on the banned list; only one allowed from restricted; can only have cnt up to max play set"""
        if c.slug in self.rule_set.banned_slugs:
            raise ValueError(f"{c.name} is on the Banned List and cannot be added to your deck")
        if c.slug in self.rule_set.restricted_slugs and self.get_slug_cnt(c.slug) == 1:
            raise ValueError(f"{c.name} is on the Restricted List and you already have one in your deck")
        if c.slug not in BASIC_LANDS and self.get_slug_cnt(c.slug) >= self.rule_set.play_set_cnt:
            raise ValueError(f"You can only have the max play set ({self.rule_set.play_set_cnt}) for {c.name}")
        if self.rule_set.max_x_points and sum([X_POINTS.get(c.slug, 0) for c in self.cards],
                                              X_POINTS.get(c.slug, 0)) > self.rule_set.max_x_points:
            raise ValueError(f"You have exceeded the allowed X-points")
        self.cards.append(c)

    def add_card_by_slug(self, slug: str):
        card = next(c for c in self.rule_set.card_universe.cards if c.slug == slug)
        self.add_card(card)

    def remove_card(self, c: Card) -> None:
        if c not in self.cards:
            raise ValueError("That card doesn't exist in your deck")
        self.cards.remove(c)

    def complete_deck(self) -> Deck:
        if not self.rule_set.min_deck_size <= len(self.cards) <= self.rule_set.max_deck_size:
            raise ValueError(f"Your deck has {len(self.cards)} but must have between "
                             f"{self.rule_set.min_deck_size} & {self.rule_set.max_deck_size} cards")
        game_cards = [GameCard(c, self.player_idx) for c in self.cards]
        return Deck(game_cards)
