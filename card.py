from dataclasses import dataclass, field
from functools import cached_property
from typing import Iterator

from ability import creature_keyword_abilities
from file_utils import read_json_file

COLOR_LETTERS = ('W', 'G', 'R', 'U', 'B')


# TODO: should Card be: (frozen=True)?

@dataclass
class Ruling:
    ruling_date: str
    ruling_statement: str

@dataclass
class Card:
    slug: str
    name: str
    casting_cost: str
    card_types: list
    card_sub_types: list  # comes from the JS schema scrape
    card_super_types: list  # comes from the JS schema scrape
    rarity: str
    rules_text: str
    oracle_rules_text: str  # more modern & logical than rules_text, ex. '{X}, {T}' instead of 'oX, ocT'
    power: int | None
    toughness: int | None
    set_codes: list[str]
    data_url: str
    images: dict[str]
    rulings: list[Ruling]
    keyword_abilities: list[str] = field(default=list)

    def __post_init__(self):
        self.keyword_abilities = creature_keyword_abilities.get(self.slug) or []
        self.power = self._str_to_int(self.power) if self.power else None
        self.toughness = self._str_to_int(self.toughness) if self.toughness else None

    # def __repr__(self) -> str:
    #     return (f"{self.name} ({self.casting_cost or 0}, {'/'.join(self.card_types)}"
    #             f"{f', {self.oracle_rules_text}' if self.oracle_rules_text else ''})")

    @cached_property
    def is_permanent(self) -> bool:
        if 'Artifact' in self.card_types or 'Creature' in self.card_types or 'Enchantment' in self.card_types or 'Land' in self.card_types:
            return True
        return False

    @cached_property
    def is_land(self) -> bool:
        return 'Land' in self.card_types

    @cached_property
    def is_creature(self) -> bool:
        return 'Creature' in self.card_types

    @cached_property
    def casting_weight(self) -> int:
        # TODO: what happens if there's a "10" colorless"?
        if not self.casting_cost:
            return 0
        weight = 0
        for char in self.casting_cost:
            try:
                colorless = int(char)
                weight += colorless
                continue
            except ValueError:
                pass
            if char in COLOR_LETTERS:
                weight += 1
        return weight

    @cached_property
    def casting_dict(self) -> dict:
        d = {color: 0 for color in COLOR_LETTERS}
        d['C'] = 0  # colorless
        for char in self.casting_cost:
            if char in COLOR_LETTERS:
                d[char] += 1
            elif char in ('0', '1', '2', '3', '4', '5', '6', '7', '8', '9'):
                d['C'] += int(char)
            else:
                raise NotImplementedError(f"This card has a casting cost of '{self.casting_cost}' that I can't handle")
        return d

    @staticmethod
    def _str_to_int(string_: str) -> int:
        try:
            number = int(string_)
            return number
        except ValueError:
            return 0

    @cached_property
    def colors(self) -> str:
        if not self.casting_cost:
            return 'C'
        colors = ''.join({char for char in self.casting_cost if not char.isnumeric() and char != 'X'})
        return colors if colors else 'C'

@dataclass
class CardUniverse:
    set_codes: list[str]
    file_path: str = '/Users/Bernacki_Laptop/PycharmProjects/magicnacki/gatherer/card_data.json'  # TODO: make relative
    cards: list[Card] = field(default_factory=list)
    all_cards_dict: dict = field(default=dict)  # bypasses set_codes and always pulls entire card_data.json file

    def __post_init__(self):
        self.cards = self.create_card_universe_from_json()

    def __getitem__(self, slug: str) -> Card:
        return next(c for c in self.cards if slug == c.slug)

    def __iter__(self) -> Iterator:
        return iter(self.cards)

    @property
    def all_card_types(self) -> list[str]:
        return sorted({ct for c in self.cards for ct in c.card_types})

    @property
    def all_card_sub_types(self) -> list[str]:
        return sorted({ct for c in self.cards for ct in c.card_sub_types})

    @property
    def all_card_super_types(self) -> list[str]:
        return sorted({ct for c in self.cards for ct in c.card_super_types})

    def _create_slug_pix_and_sets(self) -> dict[str: dict[str: list | dict]]:
        """ex return: {'air-elemental':
                          {sets: ['1E', '2E'],
                          images: {'1E': 'x.com/DAD.webp',
                                   '2E': 'x.com/DAC.webp'}},
                       'ancestral-recall':
                          {sets: ['1E'],
                          images: {'1E': 'x.com/7B9.webp'}}"""
        slug_pix_and_sets = {}
        for card_set_code, card_set_data in self.all_cards_dict.items():
            for card_slug, card_dict in card_set_data.items():
                if not slug_pix_and_sets.get(card_slug):
                    slug_pix_and_sets[card_slug] = {'sets': [], 'images': {}}
                slug_pix_and_sets[card_slug]['images'][card_set_code] = card_dict['img_url']
                slug_pix_and_sets[card_slug]['sets'].append(card_set_code)
        return slug_pix_and_sets

    def create_card_universe_from_json(self) -> list[Card]:
        self.all_cards_dict: dict = read_json_file(self.file_path)
        slug_pix_and_sets = self._create_slug_pix_and_sets()

        cards = []
        for card_set_code, card_set_data in self.all_cards_dict.items():
            if card_set_code not in self.set_codes:
                continue
            for card_slug, card_dict in card_set_data.items():
                if card_slug in {c.slug for c in cards}:
                    continue
                card_dict['set_codes'] = slug_pix_and_sets[card_slug]['sets']
                card_dict['slug'] = card_slug
                card_dict['images'] = slug_pix_and_sets[card_slug]['images']
                del card_dict['card_type']  # string, replaced by three separate attributes
                del card_dict['img_url']  # single string replaced by 'images' attribute
                card = Card(**card_dict)
                cards.append(card)

        return cards


# cuniv = CardUniverse(['1E', '2E', '3E', '4E', '5E'])

