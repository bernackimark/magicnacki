from __future__ import annotations
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from models.game_card import GameCard
    from game_state import GameState

from constants import BASIC_LANDS

class CardFilter:
    """Filters a list of cards based on chained predicates; does not modify the original list.
    ex usage: card_filter.in_play().creatures().result(); .result() must always be at end of chain to return cards.
    in_play(), on_player_board(p_id), in_graveyards(), in_player_graveyard(p_id), by_slug(slug),
    creatures(), by_type(type_: str | list), by_sub_type(type_: str | list), by_color(color: str | list),
    tapped(is_tapped: bool = True), has(kwa: str, bool_: bool = True)"""
    def __init__(self, gs: GameState):
        self._gs = gs
        self._cards = self._gs.all_cards

    # --- in what pile, card is located ---
    def in_play(self):
        self._cards = [c for b in self._gs.boards for c in b.cards]
        return self

    def on_player_board(self, p_id: int):
        self._cards = [c for c in self._gs.boards[p_id].cards]
        return self

    def in_graveyards(self):
        self._cards = [c for g in self._gs.graveyards for c in g]
        return self

    def in_player_graveyard(self, p_id: int):
        self._cards = [_ for _ in self._gs.graveyards[p_id]]
        return self

    # --- by slug ---
    def by_slug(self, slug: str):
        self._cards = [c for c in self._cards if c.props.slug == slug]
        return self

    # --- by type/sub-type ---
    def artifacts(self):
        self._cards = [c for c in self._cards if 'Artifact' in c.props.card_types]
        return self

    def basic_lands(self):
        self._cards = [c for c in self._cards if c.props.slug in BASIC_LANDS]
        return self

    def creatures(self):
        self._cards = [c for c in self._cards if 'Creature' in c.props.card_types]
        return self

    def lands(self):
        self._cards = [c for c in self._cards if 'Land' in c.props.card_types]
        return self

    def permanents(self):
        permanent_types = {'Artifact', 'Enchantment', 'Creature', 'Land'}
        self._cards = [c for c in self._cards if any(t in c.props.card_types for t in permanent_types)]
        return self

    def walls(self):
        self._cards = [c for c in self._cards if 'Wall' in c.props.card_sub_types]
        return self

    def by_type(self, type_: str | list):
        if isinstance(type_, list):
            self._cards = [c for c in self._cards for t in type_ if t in c.props.card_types]
        else:
            self._cards = [c for c in self._cards if type_ in c.props.card_types]
        return self

    def by_sub_type(self, type_: str | list):
        if isinstance(type_, list):
            self._cards = [c for c in self._cards for t in type_ if t in c.props.card_sub_types]
        else:
            self._cards = [c for c in self._cards if type_ in c.props.card_sub_types]
        return self

    # --- by color ---
    def by_color(self, color: str | list):
        if isinstance(color, list):
            self._cards = [c for c in self._cards for col in color if col in c.props.colors]
        else:
            self._cards = [c for c in self._cards if color in c.props.colors]
        return self

    def white(self):
        self._cards = [c for c in self._cards if 'W' in c.props.colors]
        return self

    def black(self):
        self._cards = [c for c in self._cards if 'B' in c.props.colors]
        return self

    def blue(self):
        self._cards = [c for c in self._cards if 'U' in c.props.colors]
        return self

    def red(self):
        self._cards = [c for c in self._cards if 'R' in c.props.colors]
        return self

    def green(self):
        self._cards = [c for c in self._cards if 'G' in c.props.colors]
        return self

    def tapped(self, is_tapped: bool = True):
        self._cards = [c for c in self._cards if c.is_tapped == is_tapped]
        return self

    def untapped(self):
        self._cards = [c for c in self._cards if not c.is_tapped]
        return self

    def has(self, kwa: str, bool_: bool = True):
        if bool_:
            self._cards = [c for c in self._cards if kwa in c.keyword_abilities]
        else:
            self._cards = [c for c in self._cards if kwa not in c.keyword_abilities]
        return self

    def result(self) -> list[GameCard]:
        cards_to_return = self._cards
        self._cards = self._gs.all_cards  # since self._cards continuously filters, must reset it for subsequent use
        return cards_to_return
