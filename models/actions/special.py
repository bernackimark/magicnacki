from __future__ import annotations
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from game_state import GameState
    from models.game_card import GameCard

from models.actions.base import Action

class PayManaForLife(Action):
    def __init__(self, p_id: int, gs: GameState, mana_cost: str, gain_life_amt: int):
        super().__init__(p_id, gs)
        self.mana_cost = mana_cost
        self.gain_life_amt = gain_life_amt

    def play(self):
        self.gs.mana_pools[self.player_idx].pay(self.mana_cost)
        self.gs.increment_life(self.player_idx, self.gain_life_amt)
        self.gs.action_stack.pop()

class PayManaToDrawCards(Action):
    def __init__(self, p_id: int, gs: GameState, mana_cost: str, card_cnt: int):
        super().__init__(p_id, gs)
        self.mana_cost = mana_cost
        self.card_cnt = card_cnt

    def play(self):
        self.gs.mana_pools[self.player_idx].pay(self.mana_cost)
        self.gs.draw(self.gs.hands[self.player_idx], self.gs.decks[self.player_idx].cards, self.card_cnt)
        self.gs.action_stack.pop()

class SacCreatureAndAddMana(Action):
    def __init__(self, p_id: int, gs: GameState, _: GameCard, creature: GameCard, color: str, amt: int = 0):
        super().__init__(p_id, gs)
        self.creature = creature
        self.color = color
        self.amt = amt

    def play(self):
        # Sacrifice then later apply effect that depends on the creature sacrificed
        self.gs.send_to_graveyard_from_play(self.creature)
        self.gs.mana_pools[self.gs.player_turn_idx].add_floating(self.color, self.amt)
        self.gs.action_stack.pop()
