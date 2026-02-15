from __future__ import annotations

import copy
from typing import TYPE_CHECKING

from models.counter_tokens import CounterType
from models.damage import PreventNextDamage
from models.effects.damage_preventions import PreventAllDamage, PreventNextDamageEffect
from phase_fsm import Phase
from utils import flip

if TYPE_CHECKING:
    from game_state import GameState
    from models.game_card import GameCard

from models.actions.base import Action

class CopyCard(Action):
    def __init__(self, p_id: int, gs: GameState, source: GameCard, target: GameCard,
                 addtional_types: list[str] = None, copy_color: bool = True):
        super().__init__(p_id, gs)
        self.s = source
        self.t = target
        self.additional_types = addtional_types
        self.copy_color = copy_color

    def __repr__(self):
        return f'{self.s} copies {self.t}'

    def play(self) -> None:
        the_copy = copy.deepcopy(self.t)
        if self.additional_types:
            self.s._card_types = list(set(self.additional_types + the_copy.props.card_types))
        else:
            self.s._card_types = the_copy.props.card_types
        self.s._card_sub_types = the_copy.props.card_sub_types
        if self.copy_color:
            self.s.colors = the_copy.props.colors
        self.s.has_summoning_sickness = the_copy.props.is_creature and 'Haste' not in the_copy.props.keyword_abilities
        self.s.base_pt = the_copy.base_pt
        self.s._base_kwa = self._handle_kwa(the_copy, the_copy.props.keyword_abilities)
        self.s.activated_abilities = the_copy.activated_abilities
        self.s.static_abilities = the_copy.static_abilities
        self.s.triggered_abilities = the_copy.triggered_abilities
        self.gs.action_stack.pop()  # remove choice
        self.gs.cast(self.s)

    def _handle_kwa(self, copied_card: GameCard, prop_kwas: list[str | None]) -> tuple[str | None]:
        my_base_kwa = []
        if copied_card.props.is_creature and 'Defender' not in copied_card.props.keyword_abilities:
            self.s._base_kwa = my_base_kwa.append('Attack')
        else:
            my_base_kwa = prop_kwas
        return tuple(my_base_kwa)

class DestroyAndForegoCombatDamage(Action):
    def __init__(self, p_id: int, gs: GameState, source: GameCard, target: GameCard):
        super().__init__(p_id, gs)
        self.source = source
        self.target = target

    def __repr__(self):
        return f'Destroy {self.target} & forego combat damage assigned by {self.source.props.name}'

    def play(self):
        self.gs.destroy(self.target)
        pnd = PreventNextDamage(self.source, target_player=flip(self.source.owner_id), combat_only=True)
        self.gs.damage_preventions.append(pnd)
        self.gs.action_stack.pop()

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
        self.gs.draw(self.player_idx, self.card_cnt)
        self.gs.action_stack.pop()

class RemoveCounterGainLife(Action):
    def __init__(self, p_id: int, gs: GameState, s: GameCard,
                 counter_type: CounterType, counter_cnt: int = 1, gain_life_amt: int = 1):
        super().__init__(p_id, gs)
        self.source = s
        self.counter_type = counter_type
        self.counter_cnt = counter_cnt
        self.gain_life_amt = gain_life_amt
        self.gs.action_stack.pop()

    def play(self):
        self.source.counters.remove_counter(self.counter_type, self.counter_cnt)
        self.gs.increment_life(self.source.owner_id, self.gain_life_amt)
        self.gs.action_stack.pop()

class SacCreatureAndAddMana(Action):
    def __init__(self, p_id: int, gs: GameState, _: GameCard, creature: GameCard, color: str, amt: int = 0):
        super().__init__(p_id, gs)
        self.creature = creature
        self.color = color
        self.amt = amt

    def play(self):
        # Sacrifice then later apply effect that depends on the creature sacrificed
        self.gs.destroy(self.creature)
        self.gs.mana_pools[self.gs.player_turn_idx].add_floating(self.color, self.amt)
        self.gs.action_stack.pop()

class SacTwoIslands(Action):
    def __init__(self, p_id: int, gs: GameState, s: GameCard):
        super().__init__(p_id, gs)
        self.s = s

    def play(self):
        your_islands = self.gs.card_filter.on_player_board(self.s.orig_owner_id).islands().result()
        for island in your_islands[:2]:
            self.gs.destroy(island)
        self.gs.action_stack.pop()

class SkipDrawPhaseGainLife(Action):
    def __init__(self, p_id: int, gs: GameState, amt: int):
        super().__init__(p_id, gs)
        self.amt = amt

    def play(self):
        self.gs.phase = Phase.CAST
        self.gs.increment_life(self.player_idx, self.amt)
        self.gs.action_stack.pop()

# --- CARD-SPECIFIC ---
class PrimalClayA(Action):
    def __init__(self, p_id: int, gs: GameState, s: GameCard):
        super().__init__(p_id, gs)
        self.s = s

    def __repr__(self):
        return 'Cast as a 3/3'

    def play(self) -> None:
        self.s.base_pt = (3, 3)
        self.gs.action_stack.pop()
        self.gs.cast(self.s)


class PrimalClayB(Action):
    def __init__(self, p_id: int, gs: GameState, s: GameCard):
        super().__init__(p_id, gs)
        self.s = s

    def __repr__(self):
        return 'Cast as a 2/2 flier'

    def play(self) -> None:
        self.s.base_pt = (2, 2)
        kwa = list(self.s._base_kwa)
        kwa.append('Flying')
        self.s._base_kwa = kwa
        self.gs.action_stack.pop()
        self.gs.cast(self.s)

class PrimalClayC(Action):
    def __init__(self, p_id: int, gs: GameState, s: GameCard):
        super().__init__(p_id, gs)
        self.s = s

    def __repr__(self):
        return 'Cast as a 1/6 wall'

    def play(self) -> None:
        self.s.base_pt = (1, 6)
        kwa = list(self.s._base_kwa)
        kwa.append('Defender')
        kwa.remove('Attack')
        self.s._base_kwa = kwa
        self.gs.action_stack.pop()
        self.gs.cast(self.s)
