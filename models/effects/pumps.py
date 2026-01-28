from __future__ import annotations
from typing import Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from game_state import GameState
    from models.game_card import GameCard

from models.effects.base import Effect
from models.modifiers import PTModifier, PTTemp

# --- GENERIC ---
class PumpEffect(Effect):
    def __init__(self, power_adj: int, toughness_adj: int, eot: bool = False):
        self.power_adj = power_adj
        self.toughness_adj = toughness_adj
        self.eot = eot

    def resolve(self, gs, source: GameCard, target: Optional[GameCard] = None):
        if not target:
            raise RuntimeError(f'{source.props.name} needs a target')
        if not self.eot:
            target.modifiers.auras.append(PTModifier(source, self.power_adj, self.toughness_adj))
        else:
            target.modifiers.temps.append(PTTemp(source, self.power_adj, self.toughness_adj))

# --- CARD-SPECIFIC ---
class BloodLust(Effect):
    """Target creature gains +4/-4 until end of turn. If this reduces creature's toughness < 1, toughness = 1."""
    def resolve(self, gs, source: GameCard, target: Optional[GameCard] = None):
        if not target:
            raise RuntimeError(f'{source.props.name} needs a target')
        new_toughness = max(1, target.toughness - 4)
        toughness_mod = new_toughness - target.toughness
        target.modifiers.auras.append(PTModifier(source, 4, toughness_mod))

class DragonWhelpEndStep(Effect):
    """If this [pump] ability has been activated four or more times this turn,
        sacrifice this creature at the beginning of the next end step.
        Note: this isn't technically correct code.  Because PTTemp doesn't store the source card, I'm counting all +1/+0s"""
    def resolve(self, gs: GameState, s: GameCard, target: Optional[GameCard] = None):
        cnt = len([temp for temp in s.modifiers.temps if temp.power_delta == 1 and temp.toughness_delta == 0])
        if cnt >= 4:
            gs.send_to_graveyard_from_play(s)

class GreatDefender(Effect):
    def resolve(self, gs, source: GameCard, target: Optional[GameCard] = None):
        """Target creature gets +0/+X until end of turn, where X is its mana value."""
        if target:
            target.modifiers.auras.append(PTTemp(source, 0, target.props.casting_weight))

class HowlFromBeyond(Effect):
    """Target creature gets +X/+0 until end of turn"""
    def resolve(self, gs: GameState, source: GameCard, target: GameCard = None):
        if target is not None:
            x = getattr(source, 'variable_x', 0)  # read X chosen when casting
            target.modifiers.temps.append(PTTemp(source, x, 0))

class KoboldTaskmaster(Effect):
    """Other Kobold creatures you control get +1/+0"""
    def resolve(self, gs: GameState, source: GameCard, target: Optional[GameCard] = None):
        for t in gs.card_filter.on_player_board(source.orig_owner_id).creatures().by_sub_type('Kobold').result():
            if source != t:
                t.modifiers.auras.append(PTModifier(source, 1, 0))

