import operator
import re
from typing import Sequence, Any

from models.game_card.card import Card, CardUniverse
from models.constants import OS_SCRYFALL_SETS

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

OPS = {'=': operator.eq, '!=': operator.ne, '>=': operator.ge, '<=': operator.le, '>': operator.gt, '<': operator.lt}

class CardFilter:
    """Creates a CardUniverse of all Old School cards; uses query chaining methods to successively filter the pool;
    caller must use .result() at the end of their statement to reset the card pool ...
    Example usage: CardFilter().mana_value([6, 7], '=').has('Flying').result()"""
    def __init__(self):
        self._all_cards: tuple[Card, ...] = tuple(CardUniverse(OS_SCRYFALL_SETS).cards)
        self._cards: list[Card] = list(self._all_cards)

    def mana_value(self, values: Sequence[int], op: str):
        op_func = OPS[op]
        self._cards = [c for c in self._cards if any(op_func(c.mana_value, v) for v in values)]
        return self

    def is_creature(self, bool_: bool = True):
        self._cards = [c for c in self._cards if c.is_creature] if bool_ else \
            [c for c in self._cards if not c.is_creature]
        return self

    def color(self, values: Sequence[str]):
        self._cards = [c for c in self._cards if any(v in c.colors for v in values)]
        return self

    def has(self, kwa: str, bool_: bool = True):
        if bool_:
            self._cards = [c for c in self._cards if kwa in c.keyword_abilities]
        else:
            self._cards = [c for c in self._cards if kwa not in c.keyword_abilities]
        return self

    def power(self, values: Sequence[int], op: str):
        op_func = OPS[op]
        self._cards = [c for c in self._cards if any(op_func(c.power, v) for v in values)]
        return self

    def toughness(self, values: Sequence[int], op: str):
        op_func = OPS[op]
        self._cards = [c for c in self._cards if any(op_func(c.toughness, v) for v in values)]
        return self

    def set_(self, values: Sequence[str], bool_: bool = True):
        if bool_:
            self._cards = [c for c in self._cards if any(v in c.set_codes for v in values)]
        else:
            self._cards = [c for c in self._cards if not any(v in c.set_codes for v in values)]
        return self

    def result(self) -> list[Card]:
        """Must always be called at the end of the query chain;
        resets the filtered _cards to the original full list for subsequent queries"""
        cards_to_return = self._cards
        self._cards = list(self._all_cards)
        return cards_to_return

    def from_arg_parse(self, arg_str: str) -> list[Card]:
        """Ex use: 'color=R,G p>=3 t<=6 kwa=Trample set=1E,AN creature=True mv>=2' returns:
         two-headed-giant-of-foriys & war-mammoth"""
        parsed: list[tuple[str, operator, list[Any]]] = self._arg_parse(arg_str)
        for key, op_func, values in parsed:
            if key == 'creature':
                self._cards = [c for c in self._cards if op_func(c.is_creature, True)]
            elif key == 'color':
                self._cards = [c for c in self._cards if any(v in c.colors for v in values)]
            elif key == 'kwa':
                self._cards = [c for c in self._cards if any(v in c.keyword_abilities for v in values)]
            elif key == 'set':
                self._cards = [c for c in self._cards if any(v in c.set_codes for v in values)]
            elif key == 'mv':
                self._cards = [c for c in self._cards if any(op_func(c.mana_value, v) for v in values)]
            elif key == 'p':
                self._cards = [c for c in self._cards if c.is_creature and any(op_func(c.power, v) for v in values)]
            elif key == 't':
                self._cards = [c for c in self._cards if c.is_creature and any(op_func(c.toughness, v) for v in values)]
        return self.result()

    @staticmethod
    def _arg_parse(arg_str: str) -> list[tuple[str, operator, list[Any]]]:
        tokens = arg_str.split()
        parsed = []
        for t in tokens:
            key, op, value = re.split(r'([<=\s=\s>=\s!=\s<\s>]+)', t)
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

        return parsed
