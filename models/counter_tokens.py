from dataclasses import dataclass, field
from collections import defaultdict

@dataclass(frozen=True)
class CounterType:
    name: str
    power_delta: int = 0
    toughness_delta: int = 0

    def __repr__(self):
        if self.power_delta or self.toughness_delta:
            return f'{self.name} ({self.power_delta}/{self.toughness_delta})'
        return f'{self.name}'


PLUS_ONE = CounterType('+1/+1', 1, 1)
PLUS_ONE_ZERO = CounterType('+1/+0', 1, 0)
MINUS_ONE = CounterType('-1/-1', -1, -1)
CARRION = CounterType('carrion')
CHARGE = CounterType('charge')
CORPSE = CounterType('corpse')
HATCHLING = CounterType('hatchling')
HUNGER = CounterType('hunger')
MATRIX = CounterType('matrix')
MIRE = CounterType('mire')
LORE = CounterType('lore')
PIN = CounterType('pin')
POISON = CounterType('poison')
PUPA = CounterType('pupa')
SLEEP = CounterType('sleep')
STOARGE = CounterType('storage')
VITALITY = CounterType('vitality')
WIND = CounterType('wind')


@dataclass
class Counters:
    """Example: Counters._counters = {CounterType.PLUS_ONE: 2, CounterType.CHARGE: 1}"""
    _counters: dict[CounterType: int] = field(default_factory=lambda: defaultdict(int))

    def __bool__(self) -> bool:
        """True if anything counter exist"""
        return bool(sum(self._counters.values()))

    def add_counter(self, counter: CounterType, n: int = 1):
        self._counters[counter] += n

    def remove_counter(self, counter: CounterType, n: int = 1):
        self._counters[counter] = max(0, self._counters[counter] - n)
        if self._counters[counter] == 0:
            del self._counters[counter]

    def get_count(self, counter: CounterType) -> int:
        return self._counters.get(counter, 0)

    @property
    def power_delta(self) -> int:
        return sum(ct.power_delta * n for ct, n in self._counters.items())

    @property
    def toughness_delta(self) -> int:
        return sum(ct.toughness_delta * n for ct, n in self._counters.items())

    def __repr__(self):
        return ', '.join(f"{cnt}×{ctr_type}" for ctr_type, cnt in self._counters.items())
