from __future__ import annotations
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from models.game_card.game_card import GameCard
    from game_state import GameState

from models.constants import BASIC_LANDS

class CardFilter:
    """Filters a list of cards based on chained predicates; does not modify the original list.
    ex usage: card_filter.in_play().creatures().result(); .result() must always be at end of chain to return cards.
    in_play(), on_player_board(p_id), in_graveyards(), in_player_graveyard(p_id), by_slug(slug),
    creatures(), by_type(type_: str | list), by_sub_type(type_: str | list), by_color(color: str | list),
    tapped(is_tapped: bool = True), has(kwa: str, bool_: bool = True)"""
    def __init__(self, gs: GameState):
        self._gs = gs
        self._cards = self._gs.pile_mgr.all_cards

    # --- in what pile, card is located ---
    def in_player_hand(self, p_id: int):
        hand = self._gs.pile_mgr.hands[p_id]
        self._cards = [c for c in self._cards if c in hand]
        return self

    def in_play(self):
        board = [c for b in self._gs.pile_mgr.boards for c in b]
        self._cards = [c for c in self._cards if c in board]
        return self

    def on_player_board(self, p_id: int):
        board = self._gs.pile_mgr.boards[p_id]
        self._cards = [c for c in self._cards if c in board]
        return self

    def in_graveyards(self):
        board = self._gs.pile_mgr.graveyards
        self._cards = [c for c in self._cards if c in board]
        return self

    def in_player_graveyard(self, p_id: int):
        gy = self._gs.pile_mgr.graveyards[p_id]
        self._cards = [c for c in self._cards if c in gy]
        return self

    def in_player_library(self, p_id: int):
        lib = self._gs.pile_mgr.libraries[p_id]
        self._cards = [c for c in self._cards if c in lib]
        return self

    # --- by slug ---
    def by_slug(self, slug: str):
        self._cards = [c for c in self._cards if c.props.slug == slug]
        return self

    # -- by super-type ---
    def legendary(self):
        self._cards = [c for c in self._cards if 'Legendary' in c.props.card_super_types]
        return self

    # --- by type/sub-type ---
    def artifacts(self):
        self._cards = [c for c in self._cards if 'Artifact' in c.card_types]
        return self

    def auras(self):
        self._cards = [c for c in self._cards if 'Aura' in c.card_sub_types]
        return self

    def basic_lands(self):
        self._cards = [c for c in self._cards if c.props.slug in BASIC_LANDS]
        return self

    def creatures(self):
        self._cards = [c for c in self._cards if 'Creature' in c.card_types]
        return self

    def enchantments(self):
        self._cards = [c for c in self._cards if 'Enchantment' in c.card_types]
        return self

    def lands(self):
        self._cards = [c for c in self._cards if 'Land' in c.card_types]
        return self

    def permanents(self):
        permanent_types = {'Artifact', 'Enchantment', 'Creature', 'Land'}
        self._cards = [c for c in self._cards if any(t in c.card_types for t in permanent_types)]
        return self

    def walls(self):
        self._cards = [c for c in self._cards if 'Wall' in c.card_sub_types]
        return self

    def non_wall_creatures(self):
        self._cards = [c for c in self._cards if 'Creature' in c.card_types and 'Wall' not in c.card_sub_types]
        return self

    def non_artifact_creatures(self):
        self._cards = [c for c in self._cards if 'Creature' in c.card_types and 'Artifact' not in c.card_types]
        return self

    def non_creature_artifacts(self):
        self._cards = [c for c in self._cards if 'Artifact' in c.card_types and 'Creature' not in c.card_types]
        return self

    def non_token(self):
        self._cards = [c for c in self._cards if not c.is_token]
        return self

    def by_type(self, type_: str | list):
        if isinstance(type_, list):
            self._cards = [c for c in self._cards for t in type_ if t in c.card_types]
        else:
            self._cards = [c for c in self._cards if type_ in c.card_types]
        return self

    def by_sub_type(self, type_: str | list):
        if isinstance(type_, list):
            self._cards = [c for c in self._cards for t in type_ if t in c.card_sub_types]
        else:
            self._cards = [c for c in self._cards if type_ in c.card_sub_types]
        return self

    def legendaries(self):
        self._cards = [c for c in self._cards if 'Legendary' in c.props.card_super_types]
        return self

    # --- by color ---
    def by_color(self, colors: str | list):
        if isinstance(colors, str):
            colors = [colors]
        self._cards = [c for c in self._cards if any(color in c.colors for color in colors)]
        return self

    def white(self):
        self._cards = [c for c in self._cards if 'W' in c.colors]
        return self

    def black(self):
        self._cards = [c for c in self._cards if 'B' in c.colors]
        return self

    def blue(self):
        self._cards = [c for c in self._cards if 'U' in c.colors]
        return self

    def red(self):
        self._cards = [c for c in self._cards if 'R' in c.colors]
        return self

    def green(self):
        self._cards = [c for c in self._cards if 'G' in c.colors]
        return self

    def non_white(self):
        self._cards = [c for c in self._cards if 'W' not in c.colors]
        return self

    def non_black(self):
        self._cards = [c for c in self._cards if 'B' not in c.colors]
        return self

    def non_blue(self):
        self._cards = [c for c in self._cards if 'U' not in c.colors]
        return self

    def non_red(self):
        self._cards = [c for c in self._cards if 'R' not in c.colors]
        return self

    def non_green(self):
        self._cards = [c for c in self._cards if 'G' not in c.colors]
        return self

    # -- land type ---
    def swamps(self):
        self._cards = [c for c in self._cards if 'Swamp' in c.card_sub_types]
        return self

    def islands(self):
        self._cards = [c for c in self._cards if 'Island' in c.card_sub_types]
        return self

    def forests(self):
        self._cards = [c for c in self._cards if 'Forest' in c.card_sub_types]
        return self

    def mountains(self):
        self._cards = [c for c in self._cards if 'Mountain' in c.card_sub_types]
        return self

    def plains(self):
        self._cards = [c for c in self._cards if 'Plains' in c.card_sub_types]
        return self

    # --- Tapped/Untapped ---
    def tapped(self):
        self._cards = [c for c in self._cards if c.is_tapped]
        return self

    def untapped(self):
        self._cards = [c for c in self._cards if not c.is_tapped]
        return self

    # --- Attackers/Blockers ---
    def attackers(self):
        attackers = [com.declared_attacker for com in self._gs.combat_mgr.combats]
        self._cards = [c for c in self._cards if c in attackers]
        return self

    def blockers(self):
        blockers = [blocker for com in self._gs.combat_mgr.combats for blocker in com.all_declared_blockers]
        self._cards = [c for c in self._cards if c in blockers]
        return self

    def unblocked_attackers(self):
        attackers = [combat.attacker for combat in self._gs.combat_mgr.combats if not combat.blockers]
        self._cards = [c for c in self._cards if c in attackers]
        return self

    def combatants(self):
        combatants = [com.attacker for com in self._gs.combat_mgr.combats] + \
                     [b for com in self._gs.combat_mgr.combats for b in com.blockers]
        self._cards = [c for c in self._cards if c in combatants]
        return self

    def combating_against(self, c: GameCard):
        opponents = [b for com in self._gs.combat_mgr.combats for b in com.blockers if com.attacker is c] + \
                    [com.attacker for com in self._gs.combat_mgr.combats for b in com.blockers if b is c]
        self._cards = [card for card in self._cards if card in opponents]
        return self

    # --- is enchanted ---
    def is_enchanted(self, bool_: bool = True):
        if bool_:
            self._cards = [c for c in self._cards if c.is_enchanted]
        else:
            self._cards = [c for c in self._cards if not c.is_enchanted]
        return self

    # --- Has a Keyword Ability ---
    def has(self, kwa: str, bool_: bool = True):
        if bool_:
            self._cards = [c for c in self._cards if kwa in c.keyword_abilities]
        else:
            self._cards = [c for c in self._cards if kwa not in c.keyword_abilities]
        return self

    # -- by set code ---
    def by_set_code(self, set_code: str):
        self._cards = [c for c in self._cards if set_code in c.props.set_codes]
        return self

    def result(self) -> list[GameCard]:
        cards_to_return = self._cards
        self._cards = self._gs.pile_mgr.all_cards  # since self._cards continuously filters, must reset for next use
        return cards_to_return
