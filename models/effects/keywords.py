from __future__ import annotations
from typing import Optional, TYPE_CHECKING, Literal

from models.choice_actions_all import ErhnamDjinnChoice
from models.effects.destroy_sac_regenerate import SandalsOfAbdallahIfCreatureDies
from models.events_all import UpkeepEvent

if TYPE_CHECKING:
    from game_state import GameState
    from models.game_card.game_card import GameCard

from models.effects.base import Effect
from models.modifiers import KWAMod

# --- GENERIC ---
class AllWalksRemoved(Effect):
    """Target creature loses all landwalk abilities until end of turn"""
    def resolve(self, gs, source: GameCard, target: Optional[GameCard] = None):
        for land in ('Island', 'Forest', 'Mountain', 'Swamps', 'Plains'):
            target.modifiers.items.append(KWAMod(s=source, add_or_remove='remove', kwa=f'{land}walk', expires='EOT'))

class KWAModEffect(Effect):
    def __init__(self, add_or_remove: Literal['add', 'remove'], kwa: str, eot: bool = False):
        self.add_or_remove = add_or_remove
        self.kwa = kwa
        self.eot = eot

    def resolve(self, gs, s: GameCard, target: Optional[GameCard] = None):
        target.modifiers.items.append(KWAMod(s=s, add_or_remove=self.add_or_remove, kwa=self.kwa,
                                             expires='EOT' if self.eot else None))

# --- CARD-SPECIFIC
class ErhnamDjinn(Effect):
    """At your upkeep, target non-Wall creature an opponent controls gains forestwalk until your next upkeep"""
    listens_to = UpkeepEvent

    def on_event(self, gs: GameState, s: GameCard, event: UpkeepEvent):
        if gs.turn_mgr.player_turn_idx != s.owner_id:
            return
        gs.pending_choice = ErhnamDjinnChoice(s.owner_id, gs, s)

class RapidFire(Effect):
    """Cast this spell only before blockers are declared. Target creature gains first strike until end of turn.
    If it doesn't have rampage, that creature gains rampage 2 until end of turn."""
    def resolve(self, gs: GameState, source: GameCard, target: Optional[GameCard] = None):
        if not target:
            raise ValueError(f'{source.props.name} needs a target')
        target.modifiers.items.append(KWAMod(s=source, add_or_remove='add', kwa='First Strike', expires='EOT'))
        if not target.rampage_amt:
            target.modifiers.items.append(KWAMod(s=source, add_or_remove='add', kwa='Rampage 2', expires='EOT'))

class SandalsOfAbdallahIslandWalk(Effect):
    """{T}: Target creature gains islandwalk until end of turn. When that creature dies this turn, destroy Sandals."""
    def resolve(self, gs: GameState, source: GameCard, target: Optional[GameCard] = None):
        if not target:
            raise ValueError(f'{source.props.name} needs a target')
        target.modifiers.items.append(KWAMod(s=source, add_or_remove='add', kwa='Islandwalk', expires='EOT'))

        temp_effect = SandalsOfAbdallahIfCreatureDies(target_creature=target)
        gs.register_effect_until_eot((temp_effect, source))

class UrborgLoseFirstStrike(Effect):
    """{T}: Target creature loses FIRST STRIKE or swampwalk until end of turn"""
    def resolve(self, gs: GameState, source: GameCard, target: Optional[GameCard] = None):
        if not target:
            raise ValueError(f'{source.props.name} needs a target')
        target.modifiers.items.append(KWAMod(s=source, add_or_remove='remove', kwa='First Strike', expires='EOT'))

class UrborgLoseSwampwalk(Effect):
    """{T}: Target creature loses first strike or SWAMPWALK until end of turn"""
    def resolve(self, gs: GameState, source: GameCard, target: Optional[GameCard] = None):
        if not target:
            raise ValueError(f'{source.props.name} needs a target')
        target.modifiers.items.append(KWAMod(s=source, add_or_remove='remove', kwa='Swampwalk', expires='EOT'))
