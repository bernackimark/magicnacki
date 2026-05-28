from dataclasses import dataclass, field, InitVar
from functools import cached_property
from pathlib import Path
from typing import Iterator, Any

from .kwa_abilities import CREATURE_KW_ABILITIES
from common.file_utils import read_json_file
from models.constants import BASIC_LANDS
from models.utils import str_to_int


@dataclass
class Ruling:
    ruling_date: str
    ruling_statement: str

@dataclass(frozen=True)
class Card:
    slug: str
    name: str
    casting_cost: str
    casting_cost_brackets: list
    mana_value: int
    card_types: list
    card_sub_types: list
    card_super_types: list
    rarity: str
    oracle_text: str
    power: str | int | None
    toughness: str | int | None
    set_data: dict = field(repr=False)
    keywords: list[str | None] = InitVar  # storing, but not yet using the keywords from Scryfall
    keyword_abilities: list[str | None] = field(default_factory=list)  # not yet using the keywords from Scryfall
    mana_produced: list[str] | None = None
    ids: dict = field(default_factory=dict, repr=False)
    uris: dict = field(default_factory=dict, repr=False)
    rulings: list[Ruling] = field(default_factory=list)

    def __post_init__(self):
        if not self.keyword_abilities:  # token creatures may arrive w keyword_abilities declared at construction
            object.__setattr__(self, 'keyword_abilities', CREATURE_KW_ABILITIES.get(self.slug, []).copy())
        object.__setattr__(self, 'power', str_to_int(self.power) if self.power is not None else None)
        object.__setattr__(self, 'toughness', str_to_int(self.toughness) if self.toughness is not None else None)

    @cached_property
    def set_codes(self) -> list[str]:
        return [k for k in self.set_data]

    @cached_property
    def first_image_uri(self) -> str:
        for set_code, d in self.set_data.items():
            return d['image_uris']['normal']

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
    def colors(self) -> str:
        if not self.casting_cost:
            return 'C'
        colors = ''.join({char for char in self.casting_cost if not char.isnumeric() and char != 'X'})
        return colors if colors else 'C'

@dataclass
class CardUniverse:
    set_codes: list[str]
    file_path: str = Path(__file__).resolve().parent / "card_data.json"
    cards: list[Card] = field(default_factory=list)
    all_cards_dict: dict = field(default=dict)  # bypasses set_codes and always pulls entire card_data.json file
    token_file_path: str = Path(__file__).resolve().parent / "tokens.json"
    token_cards: dict[str: Card] = field(default_factory=list)

    def __post_init__(self):
        self.cards = self.create_card_universe_from_json()
        self.token_cards = self.create_tokens_from_json()

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

    @staticmethod
    def _update_protection_kwa(keywords: list[str | None], oracle_text: str) -> list[str | None]:
        """Leverages oracle text to: ['First Strike', 'Protection'] -> ['First Strike', 'Protection From White']"""
        if 'Protection' not in keywords:
            return keywords
        _, text_after_protection_from = oracle_text.split('Protection from ')
        color = text_after_protection_from.split()[0].replace(';', '').capitalize()
        new_kwa = f'Protection From {color}'
        keywords.remove('Protection')
        keywords.append(new_kwa)
        return keywords

    @staticmethod
    def _capitalize_first_strike(keywords: list[str | None]) -> list[str | None]:
        if 'First strike' not in keywords:
            return keywords
        keywords.remove('First strike')
        keywords.append('First Strike')
        return keywords

    @staticmethod
    def _update_rampage_amt(keywords: list[str | None], oracle_text: str) -> list[str | None]:
        if 'Rampage' not in keywords:
            return keywords
        rampage_amt_str_idx = oracle_text.index('Rampage ') + 8
        rampage_amt = oracle_text[rampage_amt_str_idx:rampage_amt_str_idx + 1]
        keywords.remove('Rampage')
        keywords.append(f'Rampage {rampage_amt}')
        return keywords

    def create_card_universe_from_json(self) -> list[Card]:
        self.all_cards_dict: dict = read_json_file(self.file_path)

        in_scope_sets = set(self.set_codes)
        cards = []
        for slug, card_dict in self.all_cards_dict.items():
            sets = {s for s in card_dict['sets']}
            if not sets & in_scope_sets:
                continue

            card_dict['set_data'] = card_dict.pop('sets')  # rename key
            card_dict['slug'] = slug
            card_dict['keyword_abilities'] = card_dict['keywords']
            card_dict['mana_value'] = card_dict['mana_value'] if card_dict['mana_value'] else 0  # convert None to 0
            del card_dict['card_type']  # single string, replaced by three separate attributes
            card_dict['keywords'] = self._update_protection_kwa(card_dict['keywords'], card_dict['oracle_text'])
            card_dict['keywords'] = self._capitalize_first_strike(card_dict['keywords'])
            card_dict['keywords'] = self._update_rampage_amt(card_dict['keywords'], card_dict['oracle_text'])
            card = Card(**card_dict)
            cards.append(card)

        return cards

    def create_tokens_from_json(self) -> dict[str: Card]:
        cards = {}
        data: dict[str: dict[str: Any]] = read_json_file(self.token_file_path)
        for slug, card_data in data.items():
            card = Card(slug=slug, name=card_data['name'], casting_cost='', casting_cost_brackets=[],
                        mana_value=0,
                        card_types=card_data['card_types'], card_sub_types=card_data['card_sub_types'],
                        card_super_types=card_data['card_super_types'], rarity='', oracle_text='',
                        power=card_data['power'], toughness=card_data['toughness'], set_data={}, keywords=[],
                        keyword_abilities=card_data['kwa'])
            cards[slug] = card
        return cards

# --- OLD GATHERER APPROACH
# from dataclasses import dataclass, field
# from functools import cached_property
# import re
# from pathlib import Path
# from typing import Iterator, Any
#
# from models.card_attributes.kwa_abilities import CREATURE_KW_ABILITIES
# from common.file_utils import read_json_file
# from models.constants import COLOR_LETTERS, BASIC_LANDS
# from models.utils import str_to_int
#
#
# @dataclass
# class Ruling:
#     ruling_date: str
#     ruling_statement: str
#
# @dataclass(frozen=True)
# class Card:
#     slug: str
#     name: str
#     casting_cost: str
#     card_types: list
#     card_sub_types: list  # comes from the JS schema scrape
#     card_super_types: list  # comes from the JS schema scrape
#     rarity: str
#     rules_text: str
#     oracle_rules_text: str  # more modern & logical than rules_text, ex. '{X}, {T}' instead of 'oX, ocT'
#     power: str | int | None
#     toughness: str | int | None
#     set_codes: list[str]
#     data_url: str = field(repr=False)
#     images: dict[str: str] = field(repr=False)
#     rulings: list[Ruling] = field(repr=False)
#     keyword_abilities: list[str] = field(default_factory=list)
#
#     def __post_init__(self):
#         if not self.keyword_abilities:  # token creatures may arrive w keyword_abilities declared at construction
#             object.__setattr__(self, 'keyword_abilities', CREATURE_KW_ABILITIES.get(self.slug, []).copy())
#         object.__setattr__(self, 'power', str_to_int(self.power) if self.power is not None else None)
#         object.__setattr__(self, 'toughness', str_to_int(self.toughness) if self.toughness is not None else None)
#
#     @cached_property
#     def is_permanent(self) -> bool:
#         return any(t in ('Artifact', 'Creature', 'Enchantment', 'Land') for t in self.card_types)
#
#     @cached_property
#     def is_aura(self) -> bool:
#         return 'Aura' in self.card_sub_types
#
#     @cached_property
#     def is_land(self) -> bool:
#         return 'Land' in self.card_types
#
#     @cached_property
#     def is_basic_land(self) -> bool:
#         return self.slug in BASIC_LANDS
#
#     @cached_property
#     def is_creature(self) -> bool:
#         return 'Creature' in self.card_types
#
#     @cached_property
#     def casting_weight(self) -> int:
#         if not self.casting_cost:
#             return 0
#         # find numbers (could be multiple digits) and letters separately
#         numbers = re.findall(r'\d+', self.casting_cost)
#         letters = re.findall(r'[A-Za-z]', self.casting_cost)
#         return sum(map(int, numbers)) + len(letters)
#
#     @cached_property
#     def colors(self) -> str:
#         if not self.casting_cost:
#             return 'C'
#         colors = ''.join({char for char in self.casting_cost if not char.isnumeric() and char != 'X'})
#         return colors if colors else 'C'
#
# @dataclass
# class CardUniverse:
#     set_codes: list[str]
#     file_path: str = Path(__file__).resolve().parents[1] / "gatherer" / "card_data.json"
#     cards: list[Card] = field(default_factory=list)
#     all_cards_dict: dict = field(default=dict)  # bypasses set_codes and always pulls entire card_data.json file
#     token_file_path: str = Path(__file__).resolve().parents[1] / "gatherer" / "tokens.json"
#     token_cards: dict[str: Card] = field(default_factory=list)
#
#     def __post_init__(self):
#         self.cards = self.create_card_universe_from_json()
#         self.token_cards = self.create_tokens_from_json()
#
#     def __getitem__(self, slug: str) -> Card:
#         return next(c for c in self.cards if slug == c.slug)
#
#     def __iter__(self) -> Iterator:
#         return iter(self.cards)
#
#     @property
#     def all_card_types(self) -> list[str]:
#         return sorted({ct for c in self.cards for ct in c.card_types})
#
#     @property
#     def all_card_sub_types(self) -> list[str]:
#         return sorted({ct for c in self.cards for ct in c.card_sub_types})
#
#     @property
#     def all_card_super_types(self) -> list[str]:
#         return sorted({ct for c in self.cards for ct in c.card_super_types})
#
#     def _create_slug_pix_and_sets(self) -> dict[str: dict[str: list | dict]]:
#         """ex return: {'air-elemental':
#                           {sets: ['1E', '2E'],
#                           images: {'1E': 'x.com/DAD.webp',
#                                    '2E': 'x.com/DAC.webp'}},
#                        'ancestral-recall':
#                           {sets: ['1E'],
#                           images: {'1E': 'x.com/7B9.webp'}}"""
#         slug_pix_and_sets = {}
#         for card_set_code, card_set_data in self.all_cards_dict.items():
#             for card_slug, card_dict in card_set_data.items():
#                 if not slug_pix_and_sets.get(card_slug):
#                     slug_pix_and_sets[card_slug] = {'sets': [], 'images': {}}
#                 slug_pix_and_sets[card_slug]['images'][card_set_code] = card_dict['img_url']
#                 slug_pix_and_sets[card_slug]['sets'].append(card_set_code)
#         return slug_pix_and_sets
#
#     def create_card_universe_from_json(self) -> list[Card]:
#         self.all_cards_dict: dict = read_json_file(self.file_path)
#         slug_pix_and_sets = self._create_slug_pix_and_sets()
#
#         cards = []
#         for card_set_code, card_set_data in self.all_cards_dict.items():
#             if card_set_code not in self.set_codes:
#                 continue
#             for card_slug, card_dict in card_set_data.items():
#                 if card_slug in {c.slug for c in cards}:
#                     continue
#                 card_dict['set_codes'] = slug_pix_and_sets[card_slug]['sets']
#                 card_dict['slug'] = card_slug
#                 card_dict['images'] = slug_pix_and_sets[card_slug]['images']
#                 del card_dict['card_type']  # string, replaced by three separate attributes
#                 del card_dict['img_url']  # single string replaced by 'images' attribute
#                 card = Card(**card_dict)
#                 cards.append(card)
#
#         return cards
#
#     def create_tokens_from_json(self) -> dict[str: Card]:
#         cards = {}
#         data: dict[str: dict[str: Any]] = read_json_file(self.token_file_path)
#         for slug, card_data in data.items():
#             card = Card(slug=slug, name=card_data['name'], casting_cost='',
#                         card_types=card_data['card_types'], card_sub_types=card_data['card_sub_types'],
#                         card_super_types=card_data['card_super_types'], rarity='', rules_text='', oracle_rules_text='',
#                         power=card_data['power'], toughness=card_data['toughness'], set_codes=[], data_url='',
#                         images={'1E': ''}, rulings=[], keyword_abilities=card_data['kwa'])
#             cards[slug] = card
#         return cards
