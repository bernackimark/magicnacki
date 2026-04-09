from __future__ import annotations
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from game_state import GameState
    from models.game_card import GameCard

from models.effects.base import Effect
from models.modifiers import PTMod

"""EOT Effects are stored in GameState.until_eot_effects_and_cards and removed at the end of the turn;
They must implement and on_query() method;
They are called from another Effect (ex: UnblockableEOT is called by UnblockableThisTurn(Effect))"""

# --- GENERICS ---
class UnblockableEOT(Effect):
    """Stored in GameState & cleared EOT; target creature can't be blocked this turn"""
    def __init__(self, target: GameCard):
        self.target = target

    def on_query(self, gs: GameState, event: str, card: GameCard, **kwargs):
        attacker: GameCard = kwargs.get('attacker')
        if event != 'can_block' or attacker is not self.target:
            return None
        return False


# --- CARD-SPECIFIC ---
class ArmyOfAllahEOT(Effect):
    """This will be called only by ArmyOfAllah(); this effect is stored in GameState and cleared at EOT;
    Attacking creatures get +2/+0 until end of turn"""
    def on_query(self, gs: GameState, event: str, card: GameCard, **kwargs):
        source: GameCard = kwargs.get('source')
        if event != 'pt_mod':
            return None
        if card not in gs.card_filter.in_play().attackers().result():
            return None
        return PTMod(s=source, p_adj=2, expires='EOT')

class BoneFluteEOT(Effect):
    """This will be called only by BoneFlute(); this effect is stored in GameState and cleared at EOT;
    All creatures get -1/-0 until end of turn"""
    def on_query(self, gs: GameState, event: str, card: GameCard, **kwargs):
        source: GameCard = kwargs.get('source')
        if event != 'pt_mod':
            return None
        if card not in gs.card_filter.in_play().creatures().result():
            return None
        return PTMod(s=source, p_adj=-1, expires='EOT')

class HellSwarmEOT(Effect):
    """This will be called only by HellSwarm(); this effect is stored in GameState and cleared at EOT;
    All creatures get -1/-0 until end of turn"""
    def on_query(self, gs: GameState, event: str, card: GameCard, **kwargs):
        source: GameCard = kwargs.get('source')
        if event != 'pt_mod':
            return None
        if card not in gs.card_filter.in_play().creatures().result():
            return None
        return PTMod(s=source, p_adj=-1, expires='EOT')

class HolyLightEOT(Effect):
    """This will be called only by HolyLight(); this effect is stored in GameState and cleared at EOT
    Nonwhite creatures get -1/-1 until end of turn"""
    def on_query(self, gs: GameState, event: str, card: GameCard, **kwargs):
        source: GameCard = kwargs.get('source')
        if event != 'pt_mod':
            return None
        creatures = gs.card_filter.in_play().creatures().result()
        white_creatures = gs.card_filter.in_play().creatures().white().result()
        non_white_creatures = [c for c in creatures if c not in white_creatures]
        if card not in non_white_creatures:
            return None
        return PTMod(s=source, p_adj=-1, t_adj=-1, expires='EOT')

class MarshGasEOT(Effect):
    """This will be called only by MarshGas(); this effect is stored in GameState and cleared at EOT;
    All creatures get -2/-0 until end of turn"""
    def on_query(self, gs: GameState, event: str, card: GameCard, **kwargs):
        source: GameCard = kwargs.get('source')
        if event != 'pt_mod':
            return None
        if card not in gs.card_filter.in_play().creatures().result():
            return None
        return PTMod(s=source, p_adj=-2, expires='EOT')

class MoraleEOT(Effect):
    """This will be called only by Morale(); this effect is stored in GameState and cleared at EOT;
    Attacking creatures get +1/+1 until end of turn"""
    def on_query(self, gs: GameState, event: str, card: GameCard, **kwargs):
        source: GameCard = kwargs.get('source')
        if event != 'pt_mod':
            return None
        if card not in gs.card_filter.in_play().attackers().result():
            return None
        return PTMod(s=source, p_adj=1, t_adj=1, expires='EOT')

class PietyEOT(Effect):
    """This will be called only by Piety(); this effect is stored in GameState and cleared at EOT;
    Blocking creatures get 0/+3 until end of turn"""
    def on_query(self, gs: GameState, event: str, card: GameCard, **kwargs):
        source: GameCard = kwargs.get('source')
        if event != 'pt_mod':
            return None
        if card not in gs.card_filter.in_play().blockers().result():
            return None
        return PTMod(s=source, t_adj=3, expires='EOT')

class ShieldWallEOT(Effect):
    """This will be called only by ShieldWall(); this effect is stored in GameState and cleared at EOT;
    Creatures you control get +0/+2 until end of turn"""
    def on_query(self, gs: GameState, event: str, card: GameCard, **kwargs):
        source: GameCard = kwargs.get('source')
        if event != 'pt_mod':
            return None
        if card not in gs.card_filter.in_play().on_player_board(source.owner_id).creatures().result():
            return None
        return PTMod(s=source, t_adj=2, expires='EOT')

class TransmutationEOT(Effect):
    """Stored in GameState & cleared EOT; how does this class know who the target is?"""
    def on_query(self, gs: GameState, event: str, card: GameCard, **kwargs):
        source: GameCard = kwargs.get('source')
        if event != 'pt_mod':
            return None
        power_delta = card.toughness - card.power
        toughness_delta = card.power - card.toughness
        return PTMod(s=source, p_adj=power_delta, t_adj=toughness_delta, expires='EOT')

class TowerOfCoireallEOT(Effect):
    """Stored in GameState & cleared EOT; target creature can't be blocked by Walls this turn"""
    def __init__(self, target: GameCard):
        self.target = target

    def on_query(self, gs: GameState, event: str, card: GameCard, **kwargs):
        attacker: GameCard = kwargs.get('attacker')
        if event != 'can_block' or attacker is not self.target or card not in gs.card_filter.walls().result():
            return None
        return False
