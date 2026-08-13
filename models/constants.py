from __future__ import annotations

from enum import Enum, auto, StrEnum
from typing import Union

ALL_PLAYER_INDICES = (0, 1)
BASIC_LANDS = ('forest', 'island', 'mountain', 'plains', 'swamp')
COLOR_LETTERS = ('G', 'U', 'R', 'W', 'B')
COLOR_LETTERS_W_COLORLESS = ('G', 'U', 'R', 'W', 'B', 'C')  # 'C' must be last in the sequence for mana handling
COLOR_LETTER_SLUG = {letter: slug for letter, slug in zip(COLOR_LETTERS, BASIC_LANDS)}
BASIC_LAND_MANA_PRODUCED = {slug: color_letter for slug, color_letter in zip(BASIC_LANDS, COLOR_LETTERS)}

GENTLEMENS_RULES_BANNED_SLUGS = ('library-of-alexandria', 'mind-twist')
OS_SCRYFALL_SETS = ("lea", "leb", "2ed", "arn", "atq", "3ed", "leg", "drk")
OLD_SCHOOL_SETS = ('1E', '2E', '2U', '3E', 'AN', 'AQ', 'DK', 'LE')
OLD_SCHOOL_RESTRICTED_SLUGS = ('ancestral-recall', 'black-lotus', 'braingeyser', 'brainstorm', 'candelabra-of-tawnos',
                               'chaos-orb', 'copy-artifact', 'demonic-tutor', 'ivory-tower', 'library-of-alexandria',
                               'mana-drain', 'mirror-universe', 'mishras-workshop', 'mox-sapphire', 'mox-jet',
                               'mox-ruby', 'mox-pearl', 'mox-emerald', 'regrowth', 'sol-ring', 'strip-mine',
                               'time-walk', 'timetwister', 'wheel-of-fortune')
OLD_SCHOOL_BANNED_SLUGS = ('bronze-tablet', 'contract-from-below', 'darkpact', 'demonic-attorney',
                           'divine-intervention', 'jeweled-bird', 'rebirth', 'shahrazad', 'tempest-efreet')
Target = Union["GameCard", list["GameCard"], int, tuple[int, int], None]

class KW(StrEnum):
    BANDING = 'Banding'
    DEFENDER = 'Defender'
    FIRST_STRIKE = 'First Strike'
    FLYING = 'Flying'
    FORESTHOME = 'Foresthome'
    FORESTWALK = 'Forestwalk'
    GOAD = 'Goad'
    HASTE = 'Haste'
    INDESTRUCTIBLE = 'Indestructible'
    ISLANDHOME = 'Islandhome'
    ISLANDWALK = 'Islandwalk'
    MENACE = 'Menace'
    MOUNTAINHOME = 'Mountainhome'
    MOUNTAINWALK = 'Mountainwalk'
    PLAINSWALK = 'Plainswalk'
    PROTECTION_FROM_BLACK = 'Protection From Black'
    PROTECTION_FROM_BLUE = 'Protection From Blue'
    PROTECTION_FROM_GREEN = 'Protection From Green'
    PROTECTION_FROM_RED = 'Protection From Red'
    PROTECTION_FROM_WHITE = 'Protection From White'
    RAMPAGE_1 = 'Rampage 1'
    RAMPAGE_2 = 'Rampage 2'
    RAMPAGE_3 = 'Rampage 3'
    REACH = 'Reach'
    SWAMPHOME = 'Swamphome'
    SWAMPWALK = 'Swampwalk'
    TRAMPLE = 'Trample'
    VIGILANCE = 'Vigilance'

class Mulligan(Enum):
    ORIGINAL = auto()
    LONDON = auto()
    PARIS = auto()
    ORIGINAL_WITH_GENTLEMENS = auto()
    LONDON_WITH_GENTLEMENS = auto()
    PARIS_WITH_GENTLEMENS = auto()


X_POINTS = {
    'ancestral-recall': 5, 'mind-twist': 4, 'black-lotus': 3, 'demonic-tutor': 3, 'library-of-alexandria': 3,
    'balance': 2, 'braingeyser': 2, 'land-tax': 2,
    'mox-emerald': 2, 'mox-jet': 2, 'mox-pearl': 2, 'mox-ruby': 2, 'mox-sapphire': 2,
    'sol-ring': 2, 'time-walk': 2, 'timetwister': 2, 'wheel-of-fortune': 2,
    'armageddon': 1, 'mana-drain': 1, 'maze-of-ith': 1, 'mishras-factory': 1, 'mishras-workshop': 1,
    'moat': 1, 'recall': 1, 'regrowth': 1, 'the-abyss': 1
}
