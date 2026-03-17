from __future__ import annotations
from typing import Optional, TYPE_CHECKING, Literal

from models.choice_actions_all import ErhnamDjinnChoice
from models.effects.destroy_sac_regenerate import SandalsOfAbdallahIfCreatureDies
from models.events_all import UpkeepEvent

if TYPE_CHECKING:
    from game_state import GameState
    from models.game_card import GameCard


from models.game_card_filter import CardFilter
from models.actions.kwa import AddKWA
from models.effects.base import Effect
from models.modifiers import KWAModifier, KWATemp
from models.utils import flip

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
class ErhnamDjinn(Effect):
    """At your upkeep, target non-Wall creature an opponent controls gains forestwalk until your next upkeep"""
    listens_to = UpkeepEvent

    def on_event(self, gs: GameState, s: GameCard, event: UpkeepEvent):
        if gs.player_turn_idx != s.owner_id:
            return
        gs.pending_choice = ErhnamDjinnChoice(s.owner_id, gs, s)

class KoboldOverlordCast(Effect):
    """Other Kobold creatures you control have first strike"""
    def resolve(self, gs: GameState, source: GameCard, target: Optional[GameCard] = None):
        targets = gs.card_filter.on_player_board(source.orig_owner_id).creatures().by_sub_type('Kobold').result()
        for t in targets:
            if source != t:
                t.modifiers.auras.append(KWAModifier(source, 'add', 'First Strike'))

class RapidFire(Effect):
    """Cast this spell only before blockers are declared. Target creature gains first strike until end of turn.
    If it doesn't have rampage, that creature gains rampage 2 until end of turn."""
    def resolve(self, gs: GameState, source: GameCard, target: Optional[GameCard] = None):
        if not target:
            raise ValueError(f'{source.props.name} needs a target')
        target.modifiers.temps.append(KWATemp(source, 'add', 'First Strike'))
        if not target.rampage_amt:
            target.modifiers.temps.append(KWATemp(source, 'add', 'Rampage 2'))

class SandalsOfAbdallahIslandWalk(Effect):
    """{T}: Target creature gains islandwalk until end of turn. When that creature dies this turn, destroy Sandals."""
    def resolve(self, gs: GameState, source: GameCard, target: Optional[GameCard] = None):
        if not target:
            raise ValueError(f'{source.props.name} needs a target')
        target.modifiers.temps.append(KWATemp(source, 'add', 'Islandwalk'))

        temp_effect = SandalsOfAbdallahIfCreatureDies(target_creature=target)
        gs.register_effect_until_eot((temp_effect, source))
