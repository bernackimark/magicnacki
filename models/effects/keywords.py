from __future__ import annotations
from typing import Optional, TYPE_CHECKING, Literal

from models.effects.destroy_sac_regenerate import SandalsOfAbdallahIfCreatureDies

if TYPE_CHECKING:
    from game_state import GameState
    from models.game_card import GameCard


from card_filter import CardFilter
from models.actions.kwa import AddKWA
from models.effects.base import Effect
from models.modifiers import KWAModifier, KWATemp
from utils import flip

# --- GENERIC ---
class AllWalksRemoved(Effect):
    """Target creature loses all landwalk abilities until end of turn"""
    def resolve(self, gs, source: GameCard, target: Optional[GameCard] = None):
        for land in ('Island', 'Forest', 'Mountain', 'Swamps', 'Plains'):
            target.modifiers.temps.append(KWATemp(source, 'remove', f'{land}walk'))

class KWAModEffect(Effect):
    def __init__(self, add_or_remove: Literal['add', 'remove'], kwa: str, eot: bool = False):
        self.add_or_remove = add_or_remove
        self.kwa = kwa
        self.eot = eot

    def resolve(self, gs, source: GameCard, target: Optional[GameCard] = None):
        if not self.eot:
            target.modifiers.auras.append(KWAModifier(source, self.add_or_remove, self.kwa))
        else:
            target.modifiers.temps.append(KWATemp(source, self.add_or_remove, self.kwa))

# --- CARD-SPECIFIC
class AkronLegionnaireCast(Effect):
    """Except for creatures named Akron Legionnaire and artifact creatures, creatures you control can't attack"""
    def resolve(self, gs, source: GameCard, target: Optional[GameCard] = None):
        my_creatures = CardFilter(gs).creatures().on_player_board(source.orig_owner_id).result()
        artifact_creatures = CardFilter(gs).creatures().on_player_board(source.orig_owner_id).by_color('C').result()
        akron_legionnaires = CardFilter(gs).creatures().on_player_board(source.orig_owner_id).by_slug(
            'akron-legionnaire').result()
        for my_creature in my_creatures:
            if my_creature not in [artifact_creatures + akron_legionnaires]:
                my_creature.modifiers.auras.append(KWAModifier(source, 'remove', 'Attack'))

class ErhnamDjinn(Effect):
    """At your upkeep, target non-Wall creature an opponent controls gains forestwalk until your next upkeep"""
    def resolve(self, gs: GameState, source: GameCard, target: Optional[GameCard] = None):
        if gs.player_turn_idx != source.orig_owner_id:
            return
        opp_id = flip(source.orig_owner_id)
        for c in gs.card_filter.on_player_board(opp_id).non_wall_creatures().result():
            gs.action_stack.push(AddKWA(opp_id, gs, source, c, 'Forestwalk'))

class EvilEyeOfOrmsByGoreCast(Effect):
    """Non-Eye creatures you control can't attack."""
    def resolve(self, gs, source: GameCard, target: Optional[GameCard] = None):
        my_creatures = CardFilter(gs).creatures().on_player_board(source.orig_owner_id).result()
        my_eyes = CardFilter(gs).creatures().on_player_board(source.orig_owner_id).by_sub_type('Eye').result()
        for my_creature in my_creatures:
            if my_creature not in my_eyes:
                my_creature.modifiers.auras.append(KWAModifier(source, 'remove', 'Attack'))

class KoboldOverlordCast(Effect):
    """Other Kobold creatures you control have first strike"""
    def resolve(self, gs: GameState, source: GameCard, target: Optional[GameCard] = None):
        targets = gs.card_filter.on_player_board(source.orig_owner_id).creatures().by_sub_type('Kobold').result()
        for t in targets:
            if source != t:
                t.modifiers.auras.append(KWAModifier(source, 'add', 'First Strike'))

class SandalsOfAbdallahIslandWalk(Effect):
    """{T}: Target creature gains islandwalk until end of turn. When that creature dies this turn, destroy Sandals."""
    def resolve(self, gs: GameState, source: GameCard, target: Optional[GameCard] = None):
        if not target:
            raise RuntimeError(f'{source.props.name} needs a target')
        target.modifiers.temps.append(KWATemp(source, 'add', 'Islandwalk'))

        temp_effect = SandalsOfAbdallahIfCreatureDies(target_creature=target)
        gs.register_effect_until_eot((temp_effect, source))
