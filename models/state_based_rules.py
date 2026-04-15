from __future__ import annotations
from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

from models.choice_actions_all import BattlefieldToGraveyardChoice
from models.modifiers import RegenerationMod
from models.utils import flip

if TYPE_CHECKING:
    from game_state import GameState

class StateBasedRule(ABC):
    @staticmethod
    @abstractmethod
    def apply(gs: GameState) -> None:
        """Apply the rule"""


class GameOverSBR(StateBasedRule):
    """Check for game_over (player life <= 0 & poison >= 10); set GameState's winner = -1 draw or 0/1 for win"""
    @staticmethod
    def apply(gs: GameState) -> None:
        if gs.is_game_over:  # there could be a win condition that sets is_game_over to True elsewhere
            return

        """Returns None if game is not over;
        else -1 if a draw, 0 for player #0, 1 for player #1, updates gs.is_game_over"""
        zero_life = [idx for idx, life in enumerate(gs.score_mgr.life) if life <= 0]
        ten_poison = [idx for idx, poison in enumerate(gs.score_mgr.poison_counters) if poison >= 10]

        losers = tuple(set(zero_life + ten_poison))
        if not losers:
            return
        if len(losers) > 1:
            gs.winner = -1
            gs.is_game_over = True
            print('The game ends in a draw')
            return
        else:
            gs.winner = flip(losers[0])
            gs.is_game_over = True
            print(f'Player #{gs.winner} wins the game')
            return

class IslandhomeSBR(StateBasedRule):
    @staticmethod
    def apply(gs: GameState) -> None:
        for creature in gs.card_filter.in_play().has('Islandhome').result():
            if not gs.card_filter.on_player_board(creature.owner_id).islands().result():
                gs.destroy(creature)

class LegendarySBR(StateBasedRule):
    """A state-based action that immediately forces you to choose one and put the other into its owner's graveyard;
    it bypasses hexproof or indestructible; this counts as "dying" and will trigger any such abilities"""
    @staticmethod
    def apply(gs: GameState) -> None:
        for p_id in (0, 1):
            legends_seen = {}
            for c in gs.card_filter.on_player_board(p_id).legendaries().result():
                print('XYZ', legends_seen)
                if c.props.slug not in legends_seen:
                    legends_seen[c.props.slug] = c
                else:
                    gs.pending_choice = BattlefieldToGraveyardChoice(p_id, gs, [legends_seen[c.props.slug], c])
                    changed = True

class ZeroToughnessSBR(StateBasedRule):
    @staticmethod
    def apply(gs: GameState) -> None:
        for creature in gs.card_filter.in_play().creatures().result():
            if creature.damage_received_this_turn >= creature.toughness:
                print(f'ZeroToughnessSBR calls gs.destroy() for {creature}')
                gs.destroy(creature)


STATE_BASED_RULES = (GameOverSBR, IslandhomeSBR, LegendarySBR, ZeroToughnessSBR)
