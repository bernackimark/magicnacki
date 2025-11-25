from __future__ import annotations
from typing import TYPE_CHECKING, Optional

if TYPE_CHECKING:
    from ..game_card import GameCard
    from game_state import GameState

from models.effects.base import Effect
from models.effects.global_ import CastleEffect, CrusadeEffect
from models.modifiers import KWAModifier, KWATemp, PTModifier
from card_filter import CardFilter


def animate_wall_on_cast():
    class E(Effect):
        event = 'cast'

        def resolve(self, gs, source: GameCard, target: Optional[GameCard] = None):
            target.modifiers.auras.append(KWAModifier(source, 'remove', 'Defender'))

    return E()

def castle_on_cast():
    class E(Effect):
        event = 'cast'
        
        def resolve(self, gs, source: GameCard, target: Optional[GameCard] = None):
            # TODO: Review this new approach where global effects don't directly influence GameCards
            gs.global_effects.append((source, CastleEffect(source.orig_owner_id)))
            # add +0/+2 mod for in-turn player's creatures that are untapped
            # for c in CardFilter(gs).creatures().on_player_board(gs.player_turn_idx).tapped(False).result():
            #     c.pt_modifiers.append(PTModifier(source, 0, 2))
    return E()


def crusade_on_cast():
    class E(Effect):
        event = 'cast'
        
        def resolve(self, gs, source: GameCard, target: Optional[GameCard] = None):
            gs.global_effects.append((source, CrusadeEffect(source.orig_owner_id)))
            # for c in CardFilter(gs).in_play().creatures().white().result():
            #     c.pt_modifiers.append(PTModifier(source, 1, 1))
    return E()


def disenchant_on_cast():
    class E(Effect):
        event = 'cast'
        
        def resolve(self, gs, source: GameCard, target: Optional[GameCard] = None):
            if not target:
                raise ValueError("Disenchant needs a target")
            if target:
                print(f"Disenchant's target is {target}")
                gs.send_to_graveyard_from_play(target)
    return E()


def divine_transformation_on_cast():
    class E(Effect):
        event = 'cast'

        def resolve(self, gs, source: GameCard, target: Optional[GameCard] = None):
            if target:
                target.modifiers.auras.append(PTModifier(source, 3, 3))
    return E()


def add_flying_on_cast():
    class E(Effect):
        event = 'cast'
        
        def resolve(self, gs, source: GameCard, target: Optional[GameCard] = None):
            if target:
                target.modifiers.auras.append(KWAModifier(source, 'add', 'Flying'))
    return E()

def giant_tortoise_on_cast():
    class E(Effect):
        event = 'cast'
        
        def resolve(self, gs, source: GameCard, target: Optional[GameCard] = None):
            source.modifiers.auras.append(PTModifier(source, 0, 3))
    return E()


def holy_armor_on_cast():
    class E(Effect):
        event = 'cast'
        
        def resolve(self, gs, source: GameCard, target: Optional[GameCard] = None):
            if not target:
                raise ValueError("Holy armor didn't get a target!")
            if target:
                target.modifiers.auras.append(PTModifier(source, 0, 2))
    return E()

def holy_strength_on_cast():
    class E(Effect):
        event = 'cast'
        
        def resolve(self, gs, source: GameCard, target: Optional[GameCard] = None):
            if target:
                target.modifiers.auras.append(PTModifier(source, 1, 2))
    return E()

def jump_on_cast():
    class E(Effect):
        event = 'cast'
        
        def resolve(self, gs, source: GameCard, target: Optional[GameCard] = None):
            if target:
                target.modifiers.temps.append(KWATemp('add', 'Flying'))
    return E()


def lance_on_cast():
    class E(Effect):
        event = 'cast'
        
        def resolve(self, gs, source: GameCard, target: Optional[GameCard] = None):
            if target:
                target.modifiers.auras.append(KWAModifier(source, 'add', 'First Strike'))
    return E()

def mana_short_on_cast():
    class E(Effect):
        event = 'cast'

        def resolve(self, gs: GameState, source: GameCard, target: Optional[int] = None):
            """target = player_id whose lands should be tapped"""
            if target is None:
                return
            player_lands = (CardFilter(gs).on_player_board(target).lands().result())
            for land in player_lands:
                land.tap(gs)
            print(f"Mana Short taps {len(player_lands)} lands belonging to player {target}.")
    return E()


def swords_to_plowshares_on_cast():
    class E(Effect):
        event = 'cast'
        
        def resolve(self, gs, source: GameCard, target: Optional[GameCard] = None):
            if target:
                gs.send_to_exile(target)
                gs.increment_life(target.orig_owner_id, target.power)
    return E()


def twiddle_on_cast():
    class E(Effect):
        event = 'cast'
        
        def resolve(self, gs, source: GameCard, target: Optional[GameCard] = None):
            if target:
                # toggle tapped state
                if target.is_tapped:
                    target.untap(gs)
                else:
                    target.tap(gs)
    return E()


def unsummon_on_cast():
    class E(Effect):
        event = 'cast'
        
        def resolve(self, gs, source: GameCard, target: Optional[GameCard] = None):
            if target:
                board = gs.boards[target.orig_owner_id]
                board.remove_from_board(target)
                gs.return_to_hand(target)
    return E()


def wrath_of_god_on_cast():
    class E(Effect):
        event = 'cast'
        
        def resolve(self, gs, source: GameCard, target: Optional[GameCard] = None):
            for c in CardFilter(gs).in_play().creatures().result():
                gs.send_to_exile(c)
    return E()
