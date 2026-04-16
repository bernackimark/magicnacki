import operator
import re

from models.card import Card, CardUniverse
from models.constants import OLD_SCHOOL_SETS

ARG_LOOKUP = {
    'mv': 'casting_weight',
    'creature': 'is_creature',
    'color': 'colors',
    'kwa': 'keyword_abilities',
    'p': 'power',
    't': 'toughness',
    'set': 'set'
}

NUMERIC_KEYS = {'mv', 'p', 't'}

OPS = {
    '=': operator.eq,
    '!=': operator.ne,
    '>=': operator.ge,
    '<=': operator.le,
}


def get_cards(arg_str: str) -> list[Card]:
    tokens = arg_str.split()
    cards = CardUniverse(OLD_SCHOOL_SETS).cards

    parsed = []
    for a in tokens:
        key, op, value = re.split(r'([<=\s=\s>=\s!=]+)', a)
        if key not in ARG_LOOKUP:
            raise ValueError(f'key must be one of: {", ".join(ARG_LOOKUP)}')
        if op not in OPS:
            raise ValueError(f'operator must be one of {OPS}')

        # handle multiple values
        values = value.split(',')

        if key in NUMERIC_KEYS:
            if not all(v.isdigit() for v in values):
                raise ValueError('value must be a digit')
            values = [int(v) for v in values]

        parsed.append((key, OPS[op], values))

    for key, op_func, values in parsed:
        if key == 'creature':
            cards = [c for c in cards if op_func(c.is_creature, True)]

        elif key == 'color':
            cards = [c for c in cards if any(v in c.colors for v in values)]

        elif key == 'kwa':
            cards = [c for c in cards if any(v in c.keyword_abilities for v in values)]

        elif key == 'set':
            cards = [c for c in cards if any(v in c.set_codes for v in values)]

        elif key == 'mv':
            cards = [c for c in cards if any(op_func(c.casting_weight, v) for v in values)]

        elif key == 'p':
            cards = [c for c in cards if c.is_creature and any(op_func(c.power, v) for v in values)]

        elif key == 't':
            cards = [c for c in cards if c.is_creature and any(op_func(c.toughness, v) for v in values)]
    return cards

def format_card_text(card: Card) -> str:
    return (f"{card.slug}: {card.name}: {card.casting_cost}: {card.card_types}: {card.card_sub_types}: "
            f"({card.power}/{card.toughness}): {card.keyword_abilities}: {card.oracle_rules_text}")

def filter_cards():
    args = input(f"Enter args: ({', '.join(ARG_LOOKUP)}) (ex: color=R,G p>=3 kwa=Trample set=1E,AN) ")
    filtered = get_cards(args)
    for c in filtered:
        print(format_card_text(c))


if __name__ == '__main__':
    filter_cards()
