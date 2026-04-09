from __future__ import annotations
from typing import Optional, TYPE_CHECKING

from models.counter_tokens import MINUS_ZERO_ONE
from models.effects.until_end_of_turn import HellSwarmEOT, HolyLightEOT, ArmyOfAllahEOT, BoneFluteEOT, MarshGasEOT, \
    MoraleEOT, PietyEOT, ShieldWallEOT, TransmutationEOT
from models.events_all import UnblockedAttackerEvent, UntapCardEvent, EndStepEvent

if TYPE_CHECKING:
    from game_state import GameState
    from models.game_card import GameCard

from models.effects.base import Effect
from models.modifiers import PTMod, KWAMod


# --- GENERIC ---
class PumpEffect(Effect):
    def __init__(self, power_adj: int, toughness_adj: int, eot: bool = False):
        self.p_adj = power_adj
        self.t_adj = toughness_adj
        self.eot = eot

    def resolve(self, gs, s: GameCard, target: Optional[GameCard] = None):
        if not target:
            raise ValueError(f'{s.props.name} needs a target')
        target.modifiers.items.append(PTMod(s=s, p_adj=self.p_adj, t_adj=self.t_adj,
                                            expires='EOT' if self.eot else None))

class UntapRemovesPumpFromAnotherCard(Effect):
    """If an effect targeted another card and its duration was for as long as the source is tapped,
    we untap here by polling all cards in play and seeing if they were given a Pump by this source"""
    listens_to = UntapCardEvent

    def on_event(self, gs: GameState, s: GameCard, event: UntapCardEvent):
        for c in gs.card_filter.in_play().result():
            for mod in list(c.modifiers):
                if mod.source is s and isinstance(mod, PTMod):
                    event.card.modifiers.items.remove(mod)

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
        target.modifiers.items.append(PTMod(s=source, p_adj=int(target.power) * 2, expires='EOT'))
        target.modifiers.items.append(KWAMod(s=source, add_or_remove='add', kwa='Trample', expires='EOT'))

class BloodLust(Effect):
    """Target creature gains +4/-4 until end of turn. If this reduces creature's toughness < 1, toughness = 1."""
    def resolve(self, gs, source: GameCard, target: Optional[GameCard] = None):
        if not target:
            raise RuntimeError(f'{source.props.name} needs a target')
        new_toughness = max(1, target.toughness - 4)
        toughness_mod = new_toughness - target.toughness
        target.modifiers.items.append(PTMod(s=source, p_adj=4, t_adj=toughness_mod, expires='EOT'))

class BoneFlute(Effect):
    """All creatures get -1/-0 until end of turn"""
    def resolve(self, gs: GameState, source: GameCard, target: Optional[GameCard] = None):
        gs.register_effect_until_eot((BoneFluteEOT(), source))

class DragonWhelpEndStep(Effect):
    """If this [pump] ability has been activated 4+ times this turn, sac at end step."""
    listens_to = EndStepEvent

    def on_event(self, gs: GameState, s: GameCard, event: EndStepEvent):
        if len([temp for temp in s.modifiers.items if temp.source is s]) >= 4:
            gs.destroy(s, allow_regeneration=False)

class GreatDefender(Effect):
    def resolve(self, gs, source: GameCard, target: Optional[GameCard] = None):
        """Target creature gets +0/+X until end of turn, where X is its mana value."""
        if target:
            target.modifiers.items.append(PTMod(s=source, t_adj=target.props.casting_weight, expires='EOT'))

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
            target.modifiers.items.append(PTMod(s=source, p_adj=x, expires='EOT'))

class LesserWerewolf(Effect):
    """If this creature's power is >= 1, it gets -1/-0 until EOT & put a -0/-1 counter on
    target creature blocking/blocked by this creature. Activate only during the declare blockers step."""
    def resolve(self, gs: GameState, source: GameCard, target: Optional[GameCard] = None):
        if source.power < 1:
            return
        source.modifiers.items.append(PTMod(s=source, p_adj=-1, expires='EOT'))
        target.counters.add_counter(MINUS_ZERO_ONE)

class MarshGas(Effect):
    """All creatures get -2/-0 until end of turn"""
    def resolve(self, gs: GameState, source: GameCard, target: Optional[GameCard] = None):
        gs.register_effect_until_eot((MarshGasEOT(), source))

class Morale(Effect):
    """Attacking creatures get +1/+1 until end of turn"""
    def resolve(self, gs: GameState, source: GameCard, target: Optional[GameCard] = None):
        gs.register_effect_until_eot((MoraleEOT(), source))

class MurkDwellers(Effect):
    """Whenever this creature attacks and isn't blocked, it gets +2/+0 until end of combat"""
    listens_to = UnblockedAttackerEvent

    def on_event(self, gs: GameState, s: GameCard, event: UnblockedAttackerEvent):
        if event.attacker != s:
            return
        s.modifiers.items.append(PTMod(s=s, p_adj=2, expires='EOT'))

class Piety(Effect):
    """Blocking creatures get 0/+3 until end of turn"""
    def resolve(self, gs: GameState, source: GameCard, target: Optional[GameCard] = None):
        gs.register_effect_until_eot((PietyEOT(), source))

class ShieldWall(Effect):
    """Creatures you control get +0/+2 until end of turn"""
    def resolve(self, gs: GameState, source: GameCard, target: Optional[GameCard] = None):
        gs.register_effect_until_eot((ShieldWallEOT(), source))

class SingingTree(Effect):
    """Target attacking creature has base power 0 until end of turn"""
    def resolve(self, gs: GameState, source: GameCard, target: Optional[GameCard] = None):
        if not target:
            raise ValueError(f'{source.props.name} needs a target')
        target.modifiers.items.append(PTMod(s=source, p_adj=-target.base_pt[0], expires='EOT'))

class Transmutation(Effect):
    """Switch target creature's power and toughness until end of turn"""
    def resolve(self, gs: GameState, source: GameCard, target: GameCard = None):
        if not target:
            raise ValueError(f'{source.props.name} needs a target')
        gs.register_effect_until_eot((TransmutationEOT(), source))
