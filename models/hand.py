from dataclasses import dataclass, field
from enum import Enum

from models.game_card import GameCard


@dataclass
class Hand:
    class SortOrient(Enum):
        L_TO_R = False
        R_TO_L = True

    cards: list[GameCard] = field(default_factory=list)
    sort_pref: SortOrient = SortOrient.R_TO_L

    @property
    def instants(self) -> list[GameCard]:
        return [c for c in self.cards if 'Instant' in c.props.card_types]

    @property
    def sorceries(self) -> list[GameCard]:
        return [c for c in self.cards if 'Sorcery' in c.props.card_types]

    def sort_cards(self):
        self.cards.sort(key=lambda x: x.props.mana_value, reverse=self.sort_pref.value)
