from __future__ import annotations

from typing import TYPE_CHECKING

from models.modifiers import KWAModifier, KWATemp

if TYPE_CHECKING:
    from game_state import GameState
    from models.game_card import GameCard

from models.effects.base import Effect
from utils import flip

# --- GENERICS ---
class AddCreatureType(Effect):
    def __init__(self, power: int, toughness: int, sub_type: str = None, until_eot: bool = False):
        self.power = power
        self.toughness = toughness
        self.sub_type = sub_type
        self.until_eot = until_eot

    def resolve(self, gs: GameState, source: GameCard, target: GameCard = None):
        if target is None:
            raise ValueError(f'{source.props.name} needs a target')
        target.card_types.append('Creature')
        if self.until_eot:
            target.modifiers.temps.append(KWATemp(source, 'add', 'Attack'))
        else:
            target.modifiers.auras.append(KWAModifier(source, 'add', 'Attack'))
        target.base_pt = (self.power, self.toughness)
        if self.sub_type:
            target.card_sub_types.append(self.sub_type)

class AddCreatureTypePTManaValue(Effect):
    def __init__(self, sub_type: str = None, until_eot: bool = False):
        self.sub_type = sub_type
        self.until_eot = until_eot

    def resolve(self, gs: GameState, source: GameCard, target: GameCard = None):
        if target is None:
            raise ValueError(f'{source.props.name} needs a target')
        target.card_types.append('Creature')
        if self.until_eot:
            target.modifiers.temps.append(KWATemp(source, 'add', 'Attack'))
        else:
            target.modifiers.auras.append(KWAModifier(source, 'add', 'Attack'))
        target.base_pt = (target.props.casting_weight, target.props.casting_weight)
        if self.sub_type:
            target.card_sub_types.append(self.sub_type)

class NoLongerACreature(Effect):
    def resolve(self, gs: GameState, source: GameCard, target: GameCard = None):
        if target is None:
            raise ValueError(f'{source.props.name} needs a target')
        if 'Creature' not in target.card_types:
            return
        target.card_types.remove('Creature')
        target.modifiers.temps.append(KWATemp(source, 'remove', 'Attack'))
        target.base_pt = (None, None)
        if target.card_sub_types:
            target.card_sub_types = target.props.card_sub_types

class SetColor(Effect):
    def __init__(self, color: str):
        self.color = color

    def resolve(self, gs: GameState, source: GameCard, target: GameCard = None):
        if target is None:
            raise ValueError(f'{source.props.name} needs a target')
        target.colors = self.color
