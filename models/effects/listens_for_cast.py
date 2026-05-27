from __future__ import annotations
from typing import TYPE_CHECKING

from models.choice_actions_all import PayOneColorlessForOneLifeChoice
from models.effects.base import Listener
from models.events_all import CastResolvedEvent

if TYPE_CHECKING:
    from game_state import GameState
    from models.game_card.game_card import GameCard


class OnColorSpellGainLife(Listener):
    """Whenever a player casts a [certain color] spell, you gain 1 life"""
    listens_to = CastResolvedEvent

    def __init__(self, color: str, life_amt: int = 1):
        self.color = color
        self.life_amt = life_amt

    def on_event(self, gs: GameState, s: GameCard, event: CastResolvedEvent):
        if self.color not in event.card.props.colors:
            return
        gs.score_mgr.increment_life(s.owner_id, self.life_amt, s, gs)


class OnColorSpellPayOneColorlessForOneLifeChoice(Listener):
    """Whenever a player casts a [certain color] spell, you may {1}: Gain 1 life"""
    listens_to = CastResolvedEvent

    def __init__(self, color: str):
        self.color = color

    def on_event(self, gs: GameState, s: GameCard, event: CastResolvedEvent):
        if self.color not in event.card.props.colors:
            return
        if not gs.mana_pools[s.owner_id].can_pay('1'):
            return
        gs.action_stack.push(PayOneColorlessForOneLifeChoice(s.owner_id, gs, s), gs, False)
