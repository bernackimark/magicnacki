from __future__ import annotations
from typing import Optional, TYPE_CHECKING

from models.effects.until_end_of_turn import HellSwarmEOT, HolyLightEOT, ArmyOfAllahEOT, BoneFluteEOT, MarshGasEOT, \
    MoraleEOT, PietyEOT, ShieldWallEOT

if TYPE_CHECKING:
    from game_state import GameState
    from models.game_card import GameCard

from models.effects.base import Effect
from models.modifiers import PTModifier, PTTemp, KWATemp


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
class ArmyOfAllah(Effect):
    """Attacking creatures get +2/0 until end of turn"""
    def resolve(self, gs: GameState, source: GameCard, target: Optional[GameCard] = None):
        gs.register_effect_until_eot((ArmyOfAllahEOT(), source))

class BerserkPump(Effect):
    """Cast this spell only before the combat damage step.
    Target creature gains trample and gets +X/+0 until end of turn, where X is its power.
    At the beginning of the next end step, destroy that creature if it attacked this turn."""
    def resolve(self, gs: GameState, source: GameCard, target: Optional[GameCard] = None):
        if not target:
            raise RuntimeError(f'{source.props.name} needs a target')
        target.modifiers.temps.append(PTTemp(source, int(target.power) * 2, 0))
        target.modifiers.temps.append(KWATemp(source, 'add', 'Trample'))

class BloodLust(Effect):
    """Target creature gains +4/-4 until end of turn. If this reduces creature's toughness < 1, toughness = 1."""
    def resolve(self, gs, source: GameCard, target: Optional[GameCard] = None):
        if not target:
            raise RuntimeError(f'{source.props.name} needs a target')
        new_toughness = max(1, target.toughness - 4)
        toughness_mod = new_toughness - target.toughness
        target.modifiers.auras.append(PTTemp(source, 4, toughness_mod))

class BoneFlute(Effect):
    """All creatures get -1/-0 until end of turn"""
    def resolve(self, gs: GameState, source: GameCard, target: Optional[GameCard] = None):
        gs.register_effect_until_eot((BoneFluteEOT(), source))

class DragonWhelpEndStep(Effect):
    """If this [pump] ability has been activated 4+ times this turn, sac at end step."""
    def resolve(self, gs: GameState, s: GameCard, target: Optional[GameCard] = None):
        cnt = len([temp for temp in s.modifiers.temps if temp.source is s])
        if cnt >= 4:
            gs.destroy(s)

class GreatDefender(Effect):
    def resolve(self, gs, source: GameCard, target: Optional[GameCard] = None):
        """Target creature gets +0/+X until end of turn, where X is its mana value."""
        if target:
            target.modifiers.auras.append(PTTemp(source, 0, target.props.casting_weight))

class HellSwarm(Effect):
    """All creatures get -1/-0 until end of turn"""
    def resolve(self, gs: GameState, source: GameCard, target: Optional[GameCard] = None):
        gs.register_effect_until_eot((HellSwarmEOT(), source))

class HolyLight(Effect):
    """Nonwhite creatures get -1/-1 until end of turn"""
    def resolve(self, gs: GameState, source: GameCard, target: Optional[GameCard] = None):
        gs.register_effect_until_eot((HolyLightEOT(), source))

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

class MarshGas(Effect):
    """All creatures get -2/-0 until end of turn"""
    def resolve(self, gs: GameState, source: GameCard, target: Optional[GameCard] = None):
        gs.register_effect_until_eot((MarshGasEOT(), source))

class Morale(Effect):
    """Attacking creatures get +1/+1 until end of turn"""
    def resolve(self, gs: GameState, source: GameCard, target: Optional[GameCard] = None):
        gs.register_effect_until_eot((MoraleEOT(), source))

class Piety(Effect):
    """Blocking creatures get 0/+3 until end of turn"""
    def resolve(self, gs: GameState, source: GameCard, target: Optional[GameCard] = None):
        gs.register_effect_until_eot((PietyEOT(), source))

class ShieldWall(Effect):
    """Creatures you control get +0/+2 until end of turn"""
    def resolve(self, gs: GameState, source: GameCard, target: Optional[GameCard] = None):
        gs.register_effect_until_eot((ShieldWallEOT(), source))
