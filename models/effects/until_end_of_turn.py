from __future__ import annotations
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from game_state import GameState
    from models.game_card import GameCard

from models.effects.base import Effect
from models.modifiers import PTModifier, PTTemp

class ArmyOfAllahEOT(Effect):
    """This will be called only by ArmyOfAllah(); this effect is stored in GameState and cleared at EOT;
    Attacking creatures get +2/+0 until end of turn"""
    event = 'query'

    def on_query(self, gs: GameState, event: str, card: GameCard, **kwargs):
        source: GameCard = kwargs.get('source')
        if event != 'pt_mod':
            return None
        if card not in gs.card_filter.in_play().attackers().result():
            return None
        return PTTemp(source, 2, 0)

class BoneFluteEOT(Effect):
    """This will be called only by BoneFlute(); this effect is stored in GameState and cleared at EOT;
    All creatures get -1/-0 until end of turn"""
    event = 'query'

    def on_query(self, gs: GameState, event: str, card: GameCard, **kwargs):
        source: GameCard = kwargs.get('source')
        if event != 'pt_mod':
            return None
        if card not in gs.card_filter.in_play().creatures().result():
            return None
        return PTTemp(source, -1, 0)

class HellSwarmEOT(Effect):
    """This will be called only by HellSwarm(); this effect is stored in GameState and cleared at EOT;
    All creatures get -1/-0 until end of turn"""
    event = 'query'

    def on_query(self, gs: GameState, event: str, card: GameCard, **kwargs):
        source: GameCard = kwargs.get('source')
        if event != 'pt_mod':
            return None
        if card not in gs.card_filter.in_play().creatures().result():
            return None
        return PTTemp(source, -1, 0)

class HolyLightEOT(Effect):
    """This will be called only by HolyLight(); this effect is stored in GameState and cleared at EOT
    Nonwhite creatures get -1/-1 until end of turn"""
    event = 'query'

    def on_query(self, gs: GameState, event: str, card: GameCard, **kwargs):
        source: GameCard = kwargs.get('source')
        if event != 'pt_mod':
            return None
        creatures = gs.card_filter.in_play().creatures().result()
        white_creatures = gs.card_filter.in_play().creatures().white().result()
        non_white_creatures = [c for c in creatures if c not in white_creatures]
        if card not in non_white_creatures:
            return None
        return PTTemp(source, -1, -1)

class MarshGasEOT(Effect):
    """This will be called only by MarshGas(); this effect is stored in GameState and cleared at EOT;
    All creatures get -2/-0 until end of turn"""
    event = 'query'

    def on_query(self, gs: GameState, event: str, card: GameCard, **kwargs):
        source: GameCard = kwargs.get('source')
        if event != 'pt_mod':
            return None
        if card not in gs.card_filter.in_play().creatures().result():
            return None
        return PTTemp(source, -2, 0)

class MoraleEOT(Effect):
    """This will be called only by Morale(); this effect is stored in GameState and cleared at EOT;
    Attacking creatures get +1/+1 until end of turn"""
    event = 'query'

    def on_query(self, gs: GameState, event: str, card: GameCard, **kwargs):
        source: GameCard = kwargs.get('source')
        if event != 'pt_mod':
            return None
        if card not in gs.card_filter.in_play().attackers().result():
            return None
        return PTTemp(source, 1, 1)

class PietyEOT(Effect):
    """This will be called only by Piety(); this effect is stored in GameState and cleared at EOT;
    Blocking creatures get 0/+3 until end of turn"""
    event = 'query'

    def on_query(self, gs: GameState, event: str, card: GameCard, **kwargs):
        source: GameCard = kwargs.get('source')
        if event != 'pt_mod':
            return None
        if card not in gs.card_filter.in_play().blockers().result():
            return None
        return PTTemp(source, 0, 3)

class ShieldWallEOT(Effect):
    """This will be called only by ShieldWall(); this effect is stored in GameState and cleared at EOT;
    Creatures you control get +0/+2 until end of turn"""
    event = 'query'

    def on_query(self, gs: GameState, event: str, card: GameCard, **kwargs):
        source: GameCard = kwargs.get('source')
        if event != 'pt_mod':
            return None
        if card not in gs.card_filter.in_play().on_player_board(source.orig_owner_id).creatures().result():
            return None
        return PTTemp(source, 0, 2)
