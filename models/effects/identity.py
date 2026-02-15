from __future__ import annotations

from typing import TYPE_CHECKING, Optional, Literal

from models.choice_actions_all import CopyCardChoice, PrimalClayChoice
from models.events_all import BlockEvent, UpkeepEvent
from models.modifiers import TypeModifier, PTModifier, SubTypeModifier, SubTypeTemp, TypeTemp

if TYPE_CHECKING:
    from game_state import GameState
    from models.game_card import GameCard

from models.effects.base import Effect

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

# --- CARD-SPECIFIC ---
class AislingLeprechaun(Effect):
    """Whenever this creature blocks or becomes blocked, that creature becomes green indefinitely;
    from Google: causes the creature to become green, which removes its existing colors & replaces with green only"""
    listens_to = BlockEvent

    def on_event(self, gs: GameState, s: GameCard, event: BlockEvent):
        if event.attacker == s:
            other = event.blocker
        elif event.blocker == s:
            other = event.attacker
        else:
            return
        other.colors = 'G'

class Clone(Effect):
    """You may have this creature enter as a copy of any creature on the battlefield;
    pushes valid targets to the stack for user selection, which then calls an Action that copies select target attrs"""
    def resolve(self, gs: GameState, s: GameCard, t: GameCard = None):
        card_options = [c for c in gs.card_filter.in_play().creatures().result() if c is not s]
        if not card_options:
            return
        gs.action_stack.push(CopyCardChoice(s.owner_id, gs, s, card_options), gs, False)

class CopyArtifact(Effect):
    """You may have this enchantment enter as a copy of any artifact on the battlefield,
    except it's an enchantment in addition to its other types"""
    def resolve(self, gs: GameState, s: GameCard, t: GameCard = None):
        card_options = [c for c in gs.card_filter.in_play().artifacts().result() if c is not s]
        if not card_options:
            return
        gs.action_stack.push(CopyCardChoice(s.owner_id, gs, s, card_options,), gs, False)

class EvilPresence(Effect):
    """Enchant land Enchanted land is a Swamp"""

    def resolve(self, gs, source: GameCard, target: Optional[GameCard] = None):
        if target is None:
            raise ValueError(f'{source.props.name} needs a target')
        sub_types = target.card_sub_types.copy()
        target.modifiers.auras.append(SubTypeModifier(source, 'add', 'Swamp'))
        for sub_type in sub_types:
            target.modifiers.auras.append(SubTypeModifier(source, 'remove', sub_type))

class PhantasmalTerrain(Effect):
    """Enchant land As this Aura enters, choose a basic land type. Enchanted land is the chosen type"""
    def __init__(self, land_type: Literal['Swamp', 'Island', 'Forest', 'Mountain', 'Plains']):
        self.land_type = land_type

    def resolve(self, gs, source: GameCard, target: Optional[GameCard] = None):
        if target is None:
            raise ValueError(f'{source.props.name} needs a target')
        sub_types = target.card_sub_types.copy()
        target.modifiers.auras.append(SubTypeModifier(source, 'add', self.land_type))
        for sub_type in sub_types:
            target.modifiers.auras.append(SubTypeModifier(source, 'remove', sub_type))

class PrimalClay(Effect):
    """As this creature enters, it becomes your choice of a 3/3 artifact creature, a 2/2 artifact creature with flying,
    or a 1/6 Wall artifact creature with defender in addition to its other types."""
    def resolve(self, gs: GameState, s: GameCard, t: GameCard = None):
        gs.action_stack.push(PrimalClayChoice(s.owner_id, gs, s), gs, False)

class VesuvanDoppelgangerCast(Effect):
    """You may have this creature enter as a copy of any creature on the battlefield,
    except it doesn't copy that creature's color & you may select a different creature on each of your upkeeps"""
    def resolve(self, gs: GameState, s: GameCard, t: GameCard = None):
        print('AA')
        if gs.player_turn_idx != s.owner_id:
            return
        card_options = [c for c in gs.card_filter.in_play().creatures().result() if c is not s]
        if not card_options:
            print('BB')
            return
        print('CC')
        gs.action_stack.push(CopyCardChoice(s.owner_id, gs, s, card_options, copy_color=False), gs, False)

class VesuvanDoppelgangerUpkeep(Effect):
    """You may have this creature enter as a copy of any creature on the battlefield,
    except it doesn't copy that creature's color & you may select a different creature on each of your upkeeps"""
    listens_to = UpkeepEvent

    def on_event(self, gs: GameState, s: GameCard, event: UpkeepEvent):
        print('A')
        if gs.player_turn_idx != s.owner_id:
            return
        card_options = [c for c in gs.card_filter.in_play().creatures().result() if c is not s]
        print('B', card_options)
        if not card_options:
            return
        print('C')
        gs.action_stack.push(CopyCardChoice(s.owner_id, gs, s, card_options, copy_color=False), gs, False)