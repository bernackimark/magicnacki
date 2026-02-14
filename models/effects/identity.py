from __future__ import annotations

from typing import TYPE_CHECKING

from models.modifiers import KWAModifier, KWATemp, TypeModifier, PTModifier, SubTypeModifier, SubTypeTemp, TypeTemp

if TYPE_CHECKING:
    from game_state import GameState
    from models.game_card import GameCard

from models.effects.base import Effect
from utils import flip

# --- GENERICS ---
class AddCreatureType(Effect):
    """Turns the card into a creature"""
    event = 'query'

    def __init__(self, power: int, toughness: int, sub_type: str = None):
        self.power = power
        self.toughness = toughness
        self.sub_type = sub_type

    def on_query(self, gs: GameState, event: str, card: GameCard, **kwargs):
        source: GameCard = kwargs.get('source')
        if card is not source:
            return None
        if event == 'type_mod':
            return TypeModifier(source, 'add', 'Creature')
        if event == 'sub_type_mod':
            return SubTypeModifier(source, 'add', self.sub_type)
        if event == 'pt_mod':
            return PTModifier(source, self.power, self.toughness)

class AddCreatureTypePTManaValue(Effect):
    """Turns card into a creature with power and toughness each equal to its mana value"""
    event = 'query'

    def on_query(self, gs: GameState, event: str, card: GameCard, **kwargs):
        source: GameCard = kwargs.get('source')
        if card is not source:
            return None
        if event == 'type_mod':
            return TypeModifier(source, 'add', 'Creature')
        if event == 'pt_mod':
            return PTModifier(source, card.props.casting_weight, card.props.casting_weight)

class BecomeCreature(Effect):
    def __init__(self, power: int, toughness: int, sub_type: str = None, until_eot: bool = False):
        self.power = power
        self.toughness = toughness
        self.sub_type = sub_type
        self.until_eot = until_eot

    def resolve(self, gs, source: GameCard, target: GameCard = None):
        if not target:
            raise RuntimeError(f'{source.props.name} needs a target')
        if not self.until_eot:
            target.modifiers.auras.append(TypeModifier(source, 'add', 'Creature'))
            if self.sub_type:
                target.modifiers.auras.append(SubTypeModifier(source, 'add', self.sub_type, False))
        else:
            target.modifiers.auras.append(TypeTemp(source, 'add', 'Creature'))
            if self.sub_type:
                target.modifiers.auras.append(SubTypeTemp(source, 'add', self.sub_type, True))

class SetColor(Effect):
    def __init__(self, color: str):
        self.color = color

    def resolve(self, gs: GameState, source: GameCard, target: GameCard = None):
        if target is None:
            raise ValueError(f'{source.props.name} needs a target')
        target.colors = self.color
