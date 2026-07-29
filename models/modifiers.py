from __future__ import annotations
from typing import TYPE_CHECKING, Literal, Union, Iterator, TypeVar

if TYPE_CHECKING:
    from .game_card.game_card import GameCard

from dataclasses import dataclass, field

@dataclass(kw_only=True)
class Modifier:
    s: GameCard  # source
    expires: str | None = None  # None, 'EOT', 'UNTIL_SOURCE_LEAVES', 'NEXT_TURN'


@dataclass
class ColorMod(Modifier):
    new_colors: str

    def __repr__(self):
        return f'is now colored {self.new_colors}'

@dataclass
class KWAMod(Modifier):
    add_or_remove: str
    kwa: str

    def __repr__(self):
        return f"{'gains' if self.add_or_remove == 'add' else 'loses'} {self.kwa}"

@dataclass
class ManaProdMod(Modifier):
    add_or_remove: str
    colors: list[str]

    def __repr__(self):
        return f"{'gains' if self.add_or_remove == 'add' else 'loses'} {self.colors} mana prod"

@dataclass
class OwnershipMod(Modifier):
    new_owner_id: int

    def __repr__(self):
        return f'being stolen by {self.s.props.name}'

@dataclass
class PTMod(Modifier):
    p_adj: int = 0
    t_adj: int = 0

    def __repr__(self):
        power_symbol = '+' if self.p_adj > 0 else ''
        toughness_symbol = '+' if self.t_adj > 0 else ''
        end_of_turn_text = ' until end of turn' if self.expires == 'EOT' else ''
        return f"({power_symbol}{self.p_adj}/{toughness_symbol}{self.t_adj}){end_of_turn_text}"

@dataclass
class RegenerationMod(Modifier):
    """Prevents next destruction"""
    def __repr__(self):
        return f"regeneration shield"

@dataclass
class SubTypeMod(Modifier):
    add_or_remove: Literal['add', 'remove']
    card_sub_type: str

    def __repr__(self):
        return f"{'gains' if self.add_or_remove == 'add' else 'loses'} {self.card_sub_type}"

@dataclass
class TypeMod(Modifier):
    add_or_remove: Literal['add', 'remove']
    card_type: str

    def __repr__(self):
        return f"{'gains' if self.add_or_remove == 'add' else 'loses'} {self.card_type}"


T = TypeVar('T', bound=Modifier)
ModType = Union[KWAMod | ManaProdMod | OwnershipMod | PTMod | RegenerationMod | SubTypeMod | TypeMod]

@dataclass
class Modifiers:
    """Contains general auras (ex Creature Bond), PTModifiers (ex Holy Strength), and KWA Modifiers (ex Flight)"""
    items: list[Modifier] = field(default_factory=list)

    def __repr__(self):
        return ', '.join([m.__repr__() for m in self.items])

    def __bool__(self) -> bool:
        """True if any modifiers else False"""
        return bool(self.items)

    def append(self, modifier: Modifier) -> None:
        self.items.append(modifier)

    def remove(self, modifier: Modifier) -> None:
        self.items.remove(modifier)

    def get(self, mod_cls):
        return list(self.iter_type(mod_cls))

    def iter_type(self, mod_type: type[T]) -> Iterator[T]:
        yield from (m for m in self.items if isinstance(m, mod_type))

    def iter_type_reverse(self, mod_type: type[T]) -> Iterator[T]:
        yield from (m for m in reversed(self.items) if isinstance(m, mod_type))

    @property
    def new_owner_id(self) -> int | None:
        for m in self.iter_type_reverse(OwnershipMod):
            return m.new_owner_id

    @property
    def power_delta(self) -> int:
        return sum(m.p_adj for m in self.iter_type(PTMod))

    @property
    def toughness_delta(self) -> int:
        return sum(m.t_adj for m in self.iter_type(PTMod))

    @property
    def kwa_delta(self) -> tuple[set[str], set[str]]:
        """KWAMod('add', 'Flying'), KWAMod('add', 'Trample'), KWA('remove', 'Trample') returns ({'Flying'}, {})"""
        adds, removes = set(), set()
        for m in self.iter_type(KWAMod):
            adds.add(m.kwa) if m.add_or_remove == 'add' else removes.add(m.kwa)
        return adds - removes, removes - adds

    @property
    def type_delta(self) -> tuple[set[str], set[str]]:
        adds, removes = set(), set()
        for m in self.iter_type(TypeMod):
            adds.add(m.card_type) if m.add_or_remove == 'add' else removes.add(m.card_type)
        return adds - removes, removes - adds

    @property
    def sub_type_delta(self) -> tuple[set[str], set[str]]:
        adds, removes = set(), set()
        for m in self.iter_type(SubTypeMod):
            adds.add(m.card_sub_type) if m.add_or_remove == 'add' else removes.add(m.card_sub_type)
        return adds - removes, removes - adds

    @property
    def colors(self) -> str:
        """Returns the last color(s) assigned; does not currently support adding/subtracting multiple color layers"""
        for m in self.iter_type_reverse(ColorMod):
            return m.new_colors

    @property
    def mana_prod_delta(self) -> tuple[set[str], set[str]]:
        adds, removes = set(), set()
        for m in self.iter_type(ManaProdMod):
            [adds.add(c) for c in m.colors] if m.add_or_remove == 'add' else [removes.add(c) for c in m.colors]
        return adds - removes, removes - adds

    def clear_eots(self) -> None:
        self.items = [m for m in self.items if m.expires != 'EOT']

    def clear_all(self) -> None:
        self.items.clear()

