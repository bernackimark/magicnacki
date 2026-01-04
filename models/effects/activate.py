from __future__ import annotations
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ..game_card import GameCard
    from game_state import GameState

from ..damage import PreventNextDamage
from models.effects.base import Effect
from models.effects.global_ import AngelicVoicesEffect, BadMoonEffect, CastleEffect, CrusadeEffect
from models.modifiers import KWAModifier, KWATemp, PTModifier, PTTemp
from card_filter import CardFilter


def cop_blue_effect():
    def effect(gs: GameState, source: GameCard, target: GameCard):
        """target = artifact GameCard chosen as the source to prevent damage from"""
        gs.damage_preventions.append(
            PreventNextDamage(source_filter=lambda src: src is target, target_player=source.orig_owner_id))
    return effect
