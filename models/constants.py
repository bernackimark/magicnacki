from __future__ import annotations

from typing import Union

ALL_PLAYER_INDICES = (0, 1)
BASIC_LANDS = ('forest', 'island', 'mountain', 'plains', 'swamp')
COLOR_LETTERS = ('G', 'U', 'R', 'W', 'B')
COLOR_LETTERS_W_COLORLESS = ('G', 'U', 'R', 'W', 'B', 'C')  # 'C' must be last in the sequence for mana handling
COLOR_LETTER_SLUG = {letter: slug for letter, slug in zip(COLOR_LETTERS, BASIC_LANDS)}
BASIC_LAND_MANA_PRODUCED = {slug: color_letter for slug, color_letter in zip(BASIC_LANDS, COLOR_LETTERS)}

GENTLEMENS_RULES_BANNED_SLUGS = ('library-of-alexandria', 'mind-twist')
OLD_SCHOOL_SETS = ('1E', '2E', '2U', '3E', 'AN', 'AQ', 'DK', 'LE')
OLD_SCHOOL_RESTRICTED_SLUGS = ('ancestral-recall', 'black-lotus', 'braingeyser', 'brainstorm', 'candelabra-of-tawnos',
                               'chaos-orb', 'copy-artifact', 'demonic-tutor', 'ivory-tower', 'library-of-alexandria',
                               'mana-drain', 'mirror-universe', 'mishras-workshop', 'mox-sapphire', 'mox-jet',
                               'mox-ruby', 'mox-pearl', 'mox-emerald', 'regrowth', 'sol-ring', 'strip-mine',
                               'time-walk', 'timetwister', 'wheel-of-fortune')
OLD_SCHOOL_BANNED_SLUGS = ('bronze-tablet', 'contract-from-below', 'darkpact', 'demonic-attorney',
                           'divine-intervention', 'jeweled-bird', 'rebirth', 'shahrazad', 'tempest-efreet')
Target = Union["GameCard", list["GameCard"], int, tuple[int, int], None]

KEYWORD_ABILITIES = ['Attack', 'Banding', 'Defender', 'First Strike', 'Flying', 'Forestwalk', 'Goad', 'Haste',
                     'Islandwalk', 'Menace',
                     'Mountainwalk', 'Protection From Black', 'Protection From Blue', 'Protection From Green',
                     'Protection From Red', 'Protection From White', 'Rampage 1', 'Rampage 2', 'Rampage 3', 'Reach',
                     'Swampwalk', 'Foresthome', 'Islandhome', 'Mountainhome', 'Plainswalk', 'Swamphome', 'Trample',
                     'Vigilance']

X_POINTS = {
    'ancestral-recall': 5, 'mind-twist': 4, 'black-lotus': 3, 'demonic-tutor': 3, 'library-of-alexandria': 3,
    'balance': 2, 'braingeyser': 2, 'land-tax': 2,
    'mox-emerald': 2, 'mox-jet': 2, 'mox-pearl': 2, 'mox-ruby': 2, 'mox-sapphire': 2,
    'sol-ring': 2, 'time-walk': 2, 'timetwister': 2, 'wheel-of-fortune': 2,
    'armageddon': 1, 'mana-drain': 1, 'maze-of-ith': 1, 'mishras-factory': 1, 'mishras-workshop': 1,
    'moat': 1, 'recall': 1, 'regrowth': 1, 'the-abyss': 1
}
