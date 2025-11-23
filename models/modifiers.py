from dataclasses import dataclass


@dataclass(frozen=True)
class BasePT:
    power: int
    toughness: int


@dataclass
class PTModifier:
    card: "GameCard"
    power_delta: int = 0
    toughness_delta: int = 0

    def __repr__(self):
        return f'{self.card.props.name}({self.power_delta}/{self.toughness_delta})'


@dataclass
class PTTemp:
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
    card: "GameCard"
    add_or_remove: str
    kwa: str

    def __repr__(self):
        return f"{'gains' if self.add_or_remove == 'add' else 'loses'} {self.kwa}"


@dataclass
class KWATemp:
    add_or_remove: str
    kwa: str
    expires_end_of_turn: bool = True

    def __repr__(self):
        return f"{'gains' if self.add_or_remove == 'add' else 'loses'} {self.kwa} until end of turn"
