from __future__ import annotations
from typing import TYPE_CHECKING, Literal, Union, Callable

if TYPE_CHECKING:
    from game_card import GameCard

from dataclasses import dataclass, field

@dataclass(kw_only=True)
class Modifier:
    s: GameCard  # source
    expires: str | None = None  # None, 'EOT', 'UNTIL_SOURCE_LEAVES', 'NEXT_TURN'

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
class KWAMod(Modifier):
    add_or_remove: str
    kwa: str

    def __repr__(self):
        return f"{'gains' if self.add_or_remove == 'add' else 'loses'} {self.kwa}"

@dataclass
class TypeMod(Modifier):
    add_or_remove: Literal['add', 'remove']
    card_type: str

    def __repr__(self):
        return f"{'gains' if self.add_or_remove == 'add' else 'loses'} {self.card_type}"

@dataclass
class SubTypeMod(Modifier):
    add_or_remove: Literal['add', 'remove']
    card_sub_type: str

    def __repr__(self):
        return f"{'gains' if self.add_or_remove == 'add' else 'loses'} {self.card_sub_type}"

@dataclass
class Modifiers:
    """Contains general auras (ex Creature Bond), PTModifiers (ex Holy Strength), and KWA Modifiers (ex Flight)"""
    items: list[Modifier] = field(default_factory=list)

    def __repr__(self):
        return ', '.join([m.__repr__() for m in self.items])

    def __bool__(self) -> bool:
        """True if any modifiers else False"""
        return bool(self.items)

    @property
    def new_owner_id(self) -> int | None:
        for mod in self.items[::-1]:
            if isinstance(mod, OwnershipMod):
                return mod.new_owner_id

    @property
    def power_delta(self) -> int:
        return sum(a.p_adj for a in self.items if isinstance(a, PTMod))

    @property
    def toughness_delta(self) -> int:
        return sum(a.t_adj for a in self.items if isinstance(a, PTMod))

    @property
    def kwa_delta(self) -> tuple[set[str], set[str]]:
        """KWAMod('add', 'Flying'), KWAMod('add', 'Trample'), KWA('remove', 'Trample') returns ({'Flying'}, {})"""
        adds, removes = set(), set()
        for m in self.items:
            if isinstance(m, KWAMod):
                adds.add(m.kwa) if m.add_or_remove == 'add' else removes.add(m.kwa)
        return adds - removes, removes - adds

    @property
    def type_delta(self) -> tuple[set[str], set[str]]:
        adds, removes = set(), set()
        for m in self.items:
            if isinstance(m, TypeMod):
                adds.add(m.card_type) if m.add_or_remove == 'add' else removes.add(m.card_type)
        return adds - removes, removes - adds

    @property
    def sub_type_delta(self) -> tuple[set[str], set[str]]:
        adds, removes = set(), set()
        for m in self.items:
            if isinstance(m, SubTypeMod):
                adds.add(m.card_sub_type) if m.add_or_remove == 'add' else removes.add(m.card_sub_type)
        return adds - removes, removes - adds

    def clear_eots(self) -> None:
        self.items = [m for m in self.items if m.expires != 'EOT']

    def clear_all(self) -> None:
        self.items.clear()


ModType = Union[PTMod | KWAMod | TypeMod | SubTypeMod | OwnershipMod]
