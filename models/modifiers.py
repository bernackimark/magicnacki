from __future__ import annotations
from typing import TYPE_CHECKING, Union, TypeVar

if TYPE_CHECKING:
    from .game_card.game_card import GameCard

from dataclasses import dataclass, field

"""
Modifier (attributes: s (source) & expires (defaults to None)
 |- CollectionMod (attributes: item (str) & add_or_remove (str) (defaults to 'add')
    |- ColorMod
    |- KWAMod
    |- ManaProdMod
    |- SubTypeMod
    |- TypeMod
 |- BasePTMod (special because of its integer attributes)
 |- PTMod (special because of its integer attributes)
 |- RegenerationMod (possesses no other attributes)
"""


@dataclass(kw_only=True)
class Modifier:
    s: GameCard  # source
    expires: str | None = None  # None, 'EOT', 'UNTIL_SOURCE_LEAVES', 'NEXT_TURN'

@dataclass(kw_only=True)
class CollectionMod(Modifier):
    item: str
    add_or_remove: str = 'add'

    def __repr__(self):
        return f" {'gains' if self.add_or_remove == 'add' else 'loses'} {self.item}"

@dataclass
class ColorMod(CollectionMod):
    pass

@dataclass
class KWAMod(CollectionMod):
    pass

@dataclass
class ManaProdMod(CollectionMod):
    def __repr__(self):
        return f" {'gains' if self.add_or_remove == 'add' else 'loses'} {self.item} mana prod"

@dataclass
class SubTypeMod(CollectionMod):
    pass

@dataclass
class TypeMod(CollectionMod):
    pass

@dataclass
class OwnershipMod(Modifier):
    new_owner_id: int

    def __repr__(self):
        return f' stolen by {self.s.props.name}'

@dataclass
class BasePTMod(Modifier):
    base_p: int | None = None
    base_t: int | None = None

    def __repr__(self):
        end_of_turn_text = ' until end of turn' if self.expires == 'EOT' else ''
        return f" base=({self.base_p}/{self.base_t}){end_of_turn_text}"

@dataclass
class PTMod(Modifier):
    p_adj: int = 0
    t_adj: int = 0

    def __repr__(self):
        power_symbol = '+' if self.p_adj > 0 else '-'
        toughness_symbol = '+' if self.t_adj > 0 else '-'
        end_of_turn_text = ' until end of turn' if self.expires == 'EOT' else ''
        return f" ({power_symbol}{self.p_adj}/{toughness_symbol}{self.t_adj}){end_of_turn_text}"

@dataclass
class RegenerationMod(Modifier):
    """Prevents next destruction"""
    def __repr__(self):
        return f"regeneration shield"


T = TypeVar('T', bound=Modifier)
ModType = Union[KWAMod | ManaProdMod | OwnershipMod | BasePTMod | PTMod | RegenerationMod | SubTypeMod | TypeMod]

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

    def get(self, mod_cls: type[T], reverse: bool = False) -> list[T]:
        items = self.items if not reverse else reversed(self.items)
        return [m for m in items if isinstance(m, mod_cls)]

    def clear_eots(self) -> None:
        self.items = [m for m in self.items if m.expires != 'EOT']

    def clear_all(self) -> None:
        self.items.clear()
