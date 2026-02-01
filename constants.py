from __future__ import annotations

from typing import Union

ALL_PLAYER_INDICES = (0, 1)
BASIC_LANDS = ('forest', 'island', 'mountain', 'plains', 'swamp')
COLOR_LETTERS = ('G', 'U', 'R', 'W', 'B')
COLOR_LETTERS_W_COLORLESS = ('G', 'U', 'R', 'W', 'B', 'C')  # 'C' must be last in the sequence for mana handling
COLOR_LETTER_SLUG = {letter: slug for letter, slug in zip(COLOR_LETTERS, BASIC_LANDS)}
BASIC_LAND_MANA_PRODUCED = {slug: color_letter for slug, color_letter in zip(BASIC_LANDS, COLOR_LETTERS)}

OLD_SCHOOL_SETS = ('1E', '2E', '2U', '3E', 'AN', 'AQ', 'DK', 'LE')
OLD_SCHOOL_RESTRICTED_SLUGS = ('ancestral-recall', 'black-lotus', 'braingeyser', 'brainstorm', 'candelabra-of-tawnos',
                               'chaos-orb', 'copy-artifact', 'demonic-tutor', 'ivory-tower', 'library-of-alexandria',
                               'mana-drain', 'mirror-universe', 'mishras-workshop', 'mox-sapphire', 'mox-jet',
                               'mox-ruby', 'mox-pearl', 'mox-emerald', 'regrowth', 'sol-ring', 'strip-mine',
                               'time-walk', 'timetwister', 'wheel-of-fortune')
OLD_SCHOOL_BANNED_SLUGS = ('bronze-tablet', 'contract-from-below', 'darkpact', 'demonic-attorney',
                           'divine-intervention', 'jeweled-bird', 'rebirth', 'shahrazad', 'tempest-efreet')
Target = Union["GameCard", list["GameCard"], int, tuple[int, int], None]
