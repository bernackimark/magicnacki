from dataclasses import dataclass, field
from functools import cached_property
import re
from typing import Iterator

from models.card_attributes.kwa_abilities import CREATURE_KW_ABILITIES
from common.file_utils import read_json_file
from constants import COLOR_LETTERS, BASIC_LANDS
from utils import str_to_int


@dataclass
class Ruling:
    ruling_date: str
    ruling_statement: str

@dataclass(frozen=True)
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
    power: str | int | None
    toughness: str | int | None
    set_codes: list[str]
    data_url: str
    images: dict[str: str]
    rulings: list[Ruling]
    keyword_abilities: list[str] = field(default=list)

    def __post_init__(self):
        object.__setattr__(self, 'keyword_abilities', CREATURE_KW_ABILITIES.get(self.slug, []).copy())
        object.__setattr__(self, 'power', str_to_int(self.power) if self.power is not None else None)
        object.__setattr__(self, 'toughness', str_to_int(self.toughness) if self.toughness is not None else None)

    @cached_property
    def is_permanent(self) -> bool:
        return any(t in ('Artifact', 'Creature', 'Enchantment', 'Land') for t in self.card_types)

    @cached_property
    def is_aura(self) -> bool:
        return 'Aura' in self.card_sub_types

    @cached_property
    def is_land(self) -> bool:
        return 'Land' in self.card_types

    @cached_property
    def is_basic_land(self) -> bool:
        return self.slug in BASIC_LANDS

    @cached_property
    def is_creature(self) -> bool:
        return 'Creature' in self.card_types

    @cached_property
    def casting_weight(self) -> int:
        if not self.casting_cost:
            return 0
        # find numbers (could be multiple digits) and letters separately
        numbers = re.findall(r'\d+', self.casting_cost)
        letters = re.findall(r'[A-Za-z]', self.casting_cost)
        return sum(map(int, numbers)) + len(letters)

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

