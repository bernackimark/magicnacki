from __future__ import annotations

import copy
from dataclasses import dataclass
from typing import Callable, TYPE_CHECKING

from models.systems.phase import Phase

if TYPE_CHECKING:
    from models.action_stack import StackItemType
    from models.game_card.game_card import GameCard
    from game_state import GameState


@dataclass
class ChoiceOption:
    description: str
    callback: Callable[[], None]

    def __repr__(self):
        return self.description

    def play(self):
        self.callback()

def copy_card(gs: GameState, to: GameCard, from_: GameCard, additional_types: list[str] | None = None,
              copy_color: bool = True):
    the_copy = copy.deepcopy(from_)
    if additional_types:
        to._card_types = list(set(additional_types + the_copy.props.card_types))
    else:
        to._card_types = the_copy.props.card_types
    to._card_sub_types = the_copy.props.card_sub_types
    if copy_color:
        to.colors = the_copy.props.colors
    to.base_pt = the_copy.base_pt
    to._base_kwa = the_copy.props.keyword_abilities
    to.abilities = the_copy.abilities
    if gs.phase_mgr.phase != Phase.UPKEEP:  # hack. Vesuvan Doppel =only card that calls this during upkeep
        gs.pile_mgr.cast(to)

def pay_mana_to_bounce(gs: GameState, p_id: int, mana_cost: str, target: GameCard):
    if gs.mana_pools[p_id].can_pay(mana_cost):
        gs.mana_pools[p_id].pay(mana_cost)
        gs.pile_mgr.bounce(target)

def pay_mana_to_draw_cards(gs: GameState, p_id: int, mana_cost: str, card_cnt: int = 1):
    if gs.mana_pools[p_id].can_pay(mana_cost):
        gs.mana_pools[p_id].pay(mana_cost)
        gs.pile_mgr.draw(p_id, card_cnt)

def pay_mana_to_gain_life(gs: GameState, p_id: int, mana_cost: str, life_amt: int = 1):
    if gs.mana_pools[p_id].can_pay(mana_cost):
        gs.mana_pools[p_id].pay(mana_cost)
        gs.score_mgr.increment_life(p_id, life_amt, source=None, gs=gs)

def pay_mana_to_prevent_counter(gs: GameState, p_id: int, mana_cost: str, counter_spell: StackItemType):
    if gs.mana_pools[p_id].can_pay(mana_cost):
        gs.mana_pools[p_id].pay(mana_cost)
        gs.action_stack.remove(counter_spell)
