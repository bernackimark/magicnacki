from __future__ import annotations
from typing import TYPE_CHECKING, Literal

if TYPE_CHECKING:
    from game_card import GameCard

from dataclasses import dataclass, field


@dataclass(frozen=True)
class BasePT:
    power: int
    toughness: int


@dataclass
class PTModifier:
    card: GameCard
    power_delta: int = 0
    toughness_delta: int = 0

    def __repr__(self):
        return f'{self.card.props.name}({self.power_delta}/{self.toughness_delta})'


@dataclass
class PTTemp:
    source: GameCard
    power_delta: int
    toughness_delta: int
    expires_end_of_turn: bool = True

    def __repr__(self):
        power_symbol = '+' if self.power_delta > 0 else ''
        toughness_symbol = '+' if self.toughness_delta > 0 else ''
        end_of_turn_text = ' until end of turn' if self.expires_end_of_turn else ''
        return f"({power_symbol}{self.power_delta}/{toughness_symbol}{self.toughness_delta}){end_of_turn_text}"


@dataclass
class KWAModifier:
    card: GameCard
    add_or_remove: str
    kwa: str

    def __repr__(self):
        return f"{'gains' if self.add_or_remove == 'add' else 'loses'} {self.kwa}"


@dataclass
class KWATemp:
    source: GameCard
    add_or_remove: str
    kwa: str
    expires_end_of_turn: bool = True

    def __post_init__(self):
        if self.add_or_remove not in ('add', 'remove'):
            raise ValueError(f"attribute add_or_remove must be: 'add' or 'remove', instead got {self.add_or_remove}")

    def __repr__(self):
        return f"{'gains' if self.add_or_remove == 'add' else 'loses'} {self.kwa} until end of turn"

@dataclass
class TypeModifier:
    source: GameCard
    add_or_remove: Literal['add', 'remove']
    card_type: str
    expires_end_of_turn: bool = False

@dataclass
class TypeTemp:
    source: GameCard
    add_or_remove: Literal['add', 'remove']
    card_type: str
    expires_end_of_turn: bool = True

@dataclass
class Modifiers:
    """Contains general auras (ex Creature Bond), PTModifiers (ex Holy Strength), and KWA Modifiers (ex Flight)"""
    auras: list[GameCard | PTModifier | KWAModifier | TypeModifier] = field(default_factory=list)
    temps: list[PTTemp | KWATemp | TypeTemp] = field(default_factory=list)

    def __repr__(self):
        pt_mod_cards = (ptm.card for ptm in self.auras if isinstance(ptm, PTModifier))
        return ', '.join([a.__repr__() for a in self.auras if a not in pt_mod_cards] +
                         [t.__repr__() for t in self.temps])

    def __bool__(self) -> bool:
        """True if anything contained in self.auras or self.temps"""
        return bool(self.auras or self.temps)

    @property
    def power_delta(self) -> int:
        return (sum(a.power_delta for a in self.auras if isinstance(a, PTModifier)) +
                sum(a.power_delta for a in self.temps if isinstance(a, PTTemp)))

    @property
    def toughness_delta(self) -> int:
        return (sum(a.toughness_delta for a in self.auras if isinstance(a, PTModifier)) +
                sum(a.toughness_delta for a in self.temps if isinstance(a, PTTemp)))

    @property
    def kwa_delta(self) -> tuple[set[str], set[str]]:
        """KWAMod('add', 'Flying'), KWAMod('add', 'Trample'), KWA('remove', 'Trample') returns ({'Flying'}, {})"""
        return self._kwa_adds - self._kwa_subtracts, self._kwa_subtracts - self._kwa_adds

    @property
    def type_delta(self) -> tuple[set[str], set[str]]:
        return self._type_adds - self._type_subtracts, self._type_subtracts - self._type_adds

    @property
    def _kwa_adds(self) -> set[str]:
        return ({a.kwa for a in self.auras if isinstance(a, KWAModifier) if a.add_or_remove == 'add'} |
                {a.kwa for a in self.temps if isinstance(a, KWATemp) if a.add_or_remove == 'add'})

    @property
    def _kwa_subtracts(self) -> set[str]:
        return ({a.kwa for a in self.auras if isinstance(a, KWAModifier) if a.add_or_remove == 'remove'} |
                {a.kwa for a in self.temps if isinstance(a, KWATemp) if a.add_or_remove == 'remove'})

    @property
    def _type_adds(self) -> set[str]:
        return ({a.kwa for a in self.auras if isinstance(a, KWAModifier) if a.add_or_remove == 'add'} |
                {a.kwa for a in self.temps if isinstance(a, KWATemp) if a.add_or_remove == 'add'})

    @property
    def _type_subtracts(self) -> set[str]:
        return ({a.kwa for a in self.auras if isinstance(a, KWAModifier) if a.add_or_remove == 'remove'} |
                {a.kwa for a in self.temps if isinstance(a, KWATemp) if a.add_or_remove == 'remove'})

    @property
    def is_enchanted(self) -> bool:
        auras = [a for a in self.auras if isinstance(a, GameCard)]
        return True if auras else False

    def is_enchanted_by(self, slug: str) -> bool:
        return slug in {a.props.slug for a in self.auras if hasattr(a, 'props')}

    def remove_aura(self, item: GameCard | PTModifier | KWAModifier) -> None:
        for a in self.auras:
            if a == item:
                self.auras.remove(a)
        else:
            print(f"Warning: Attempted to remove {item} but it wasn't found")

    def clear_temps(self) -> None:
        self.temps.clear()

    def clear_perms(self) -> None:
        self.auras.clear()

    def clear_all(self) -> None:
        self.auras.clear()
