from __future__ import annotations
from typing import TYPE_CHECKING, Optional

from .base import Effect
from .damage import all_combat_damage_prevented
from ..damage import DamageEvent
from ..game_card import GameCard

if TYPE_CHECKING:
    from game_state import GameState

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


def global_on_leave():
    class E(Effect):
        event = 'leave'

        def resolve(self, gs, source: GameCard, target: Optional[GameCard] = None):
            for e in gs.global_effects:
                if source == e[0]:
                    gs.global_effects.remove(e)
                    break
    return E()


def angelic_voices_on_cast():
    class E(Effect):
        event = 'cast'

        def resolve(self, gs, source: GameCard, target: Optional[GameCard] = None):
            # TODO: Review this new approach where global effects don't directly influence GameCards
            gs.global_effects.append((source, AngelicVoicesEffect(source.orig_owner_id), False))
            # add +0/+2 mod for in-turn player's creatures that are untapped
            # for c in CardFilter(gs).creatures().on_player_board(gs.player_turn_idx).tapped(False).result():
            #     c.pt_modifiers.append(PTModifier(source, 0, 2))

    return E()


def bad_moon_on_cast():
    class E(Effect):
        event = 'cast'

        def resolve(self, gs, source: GameCard, target: Optional[GameCard] = None):
            # TODO: Review this new approach where global effects don't directly influence GameCards
            gs.global_effects.append((source, BadMoonEffect(source.orig_owner_id), False))

    return E()


def castle_on_cast():
    class E(Effect):
        event = 'cast'

        def resolve(self, gs, source: GameCard, target: Optional[GameCard] = None):
            # TODO: Review this new approach where global effects don't directly influence GameCards
            gs.global_effects.append((source, CastleEffect(source.orig_owner_id), False))
            # add +0/+2 mod for in-turn player's creatures that are untapped
            # for c in CardFilter(gs).creatures().on_player_board(gs.player_turn_idx).tapped(False).result():
            #     c.pt_modifiers.append(PTModifier(source, 0, 2))
    return E()


def crusade_on_cast():
    class E(Effect):
        event = 'cast'

        def resolve(self, gs, source: GameCard, target: Optional[GameCard] = None):
            # TODO: Review this new approach where global effects don't directly influence GameCards
            gs.global_effects.append((source, CrusadeEffect(source.orig_owner_id), False))
            # for c in CardFilter(gs).in_play().creatures().white().result():
            #     c.pt_modifiers.append(PTModifier(source, 1, 1))
    return E()


def darkness_or_fog_or_holy_day_on_cast():
    class E(Effect):
        event = 'cast'

        def resolve(self, gs: GameState, source: GameCard, target=None):
            gs.global_effects.append((source, all_combat_damage_prevented(), True))
    return E()


def sunken_city_on_cast():
    class E(Effect):
        event = 'cast'

        def resolve(self, gs, source: GameCard, target: Optional[GameCard] = None):
            # TODO: Review this new approach where global effects don't directly influence GameCards
            gs.global_effects.append((source, SunkenCityEffect(source.orig_owner_id), False))
    return E()
