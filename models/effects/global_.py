from __future__ import annotations
from typing import TYPE_CHECKING, Optional

from utils import flip
from ..damage import DamageEvent

if TYPE_CHECKING:
    from ..game_card import GameCard
    from game_state import GameState

from .base import Effect
from card_filter import CardFilter

class GlobalEffect:
    """A continuous non-target-specific effect that can modify card properties (ex Castle, Crusade)"""
    def applies_to(self, card, gs: "GameState") -> bool:
        return False

    def pt_offset(self, card=None, power=None, toughness=None):
        # Returns the delta to power/toughness
        return 0, 0

    def on_damage(self, gs: GameState, event: DamageEvent):
        return

    def on_query(self, gs: GameState, event: str, **kwargs):
        return None

    def resolve(self):
        ...

class AngelicVoicesEffect(GlobalEffect):
    def __init__(self, owner_id: int):
        self.owner_id = owner_id

    def applies_to(self, card, gs: "GameState") -> bool:
        # All of your creatures, so long as you don't have any creatures of another color (artifacts are OK)
        for my_creature in CardFilter(gs).creatures().on_player_board(self.owner_id).result():
            if 'W' not in my_creature.props.colors or 'C' not in my_creature.props.colors:
                return False
        return True

    def pt_offset(self, card=None, power=None, toughness=None):
        return 1, 1

class BadMoonEffect(GlobalEffect):
    def __init__(self, owner_id: Optional[int] = None):
        self.owner_id = owner_id  # Optional, can affect all players

    def applies_to(self, card, gs: "GameState") -> bool:
        # All untapped creatures on any board (or specific player if owner_id set)
        return card in CardFilter(gs).in_play().creatures().black().result()

    def pt_offset(self, card=None, power=None, toughness=None):
        return 1, 1

class CastleEffect(GlobalEffect):
    def __init__(self, owner_id: int):
        self.owner_id = owner_id

    def applies_to(self, card, gs: "GameState") -> bool:
        # White creatures, untapped, owned by castle owner
        return card in CardFilter(gs).creatures().on_player_board(self.owner_id).tapped(False).white().result()

    def pt_offset(self, card=None, power=None, toughness=None):
        return 0, 2

class CrusadeEffect(GlobalEffect):
    def __init__(self, owner_id: Optional[int] = None):
        self.owner_id = owner_id  # Optional, can affect all players

    def applies_to(self, card, gs: "GameState") -> bool:
        # All untapped creatures on any board (or specific player if owner_id set)
        return card in CardFilter(gs).in_play().creatures().white().result()

    def pt_offset(self, card=None, power=None, toughness=None):
        return 1, 1

class SunkenCityEffect(GlobalEffect):
    def __init__(self, owner_id: Optional[int] = None):
        self.owner_id = owner_id  # Optional, can affect all players

    def applies_to(self, card, gs: "GameState") -> bool:
        # All untapped creatures on any board (or specific player if owner_id set)
        return card in CardFilter(gs).in_play().creatures().blue().result()

    def pt_offset(self, card=None, power=None, toughness=None):
        return 1, 1

def all_combat_damage_prevented():
    class E(Effect):
        def on_damage(self, gs: GameState, event: DamageEvent):
            if event.is_combat:
                event.prevented += event.remaining
    return E()

def all_damage_prevented_to_target_card(c: GameCard):
    class E(Effect):
        def on_damage(self, gs: GameState, event: DamageEvent):
            if event.target == c:
                event.prevented += event.remaining
    return E()

def scarecrow_func():
    class E(Effect):
        def on_damage(self, gs: GameState, event: DamageEvent):
            if event.target == flip(gs.player_turn_idx):
                if event.source in gs.card_filter.in_play().creatures().has('Flying').result():
                    event.prevented += event.remaining
    return E()
