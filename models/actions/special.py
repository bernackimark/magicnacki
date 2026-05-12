from __future__ import annotations

import copy
from typing import TYPE_CHECKING

from models.actions.cast import CastToTargetAddToStack
from models.counter_tokens import CounterType, WIND
from models.damage import PreventNextDamage
from models.effects.base import ActivatedAbility
from models.modifiers import OwnershipMod
from phase_fsm import Phase
from models.utils import flip

if TYPE_CHECKING:
    from game_state import GameState
    from models.game_card import GameCard
    from models.choice_actions_all import XValueChoice


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
        if self.gs.phase_mgr.phase != Phase.UPKEEP:  # hack. Vesuvan Doppel =only card that calls this during upkeep
            self.gs.cast(self.s)
        if self.gs.pending_choice:
            self.gs.pending_choice = None
        else:
            self.gs.action_stack.pop()

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
        self.gs.score_mgr.increment_life(self.player_idx, self.gain_life_amt, source=None, gs=self.gs)
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
        self.gs.score_mgr.increment_life(self.source.owner_id, self.gain_life_amt, self.source, self.gs)
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
        self.gs.mana_pools[self.gs.turn_mgr.player_turn_idx].add_floating(self.color, self.amt)
        self.gs.action_stack.pop()

class SacTwoIslands(Action):
    def __init__(self, p_id: int, gs: GameState, s: GameCard):
        super().__init__(p_id, gs)
        self.s = s

    def play(self):
        your_islands = self.gs.card_filter.on_player_board(self.s.owner_id).islands().result()
        for island in your_islands[:2]:
            self.gs.destroy(island)
        self.gs.action_stack.pop()

class SelectXAction(Action):
    def __init__(self, p_id: int, gs: GameState, source: GameCard, choice: XValueChoice, x_value: int,
                 activated_ability: ActivatedAbility | None = None):
        super().__init__(p_id, gs)
        self.source = source
        self.choice = choice
        self.x_value = x_value
        self.activated_ability = activated_ability

    def __repr__(self):
        record = self.gs.game_history.last_action
        return f'{record}, X={self.x_value}'

    def play(self):
        self.choice.selected_x = self.x_value
        self.source.variable_x = self.x_value

        # After selecting X, check if the spell also has targets
        if self.choice.eff_spec.target_spec:
            from models.choice_actions_all import MultiTargetChoice
            self.choice.gs.pending_choice = MultiTargetChoice(self.choice.player_idx, self.choice.gs,
                                                              self.choice.source, self.choice.eff_spec,
                                                              x_value_for_variable_cast=self.choice.selected_x)
        else:
            # No targets → spell goes straight to stack
            if self.activated_ability:
                from models.actions.activate_ability import ActivateAbility
                next_action = ActivateAbility(self.choice.player_idx, self.choice.gs, self.activated_ability,
                                              target=None, x_value=self.x_value)
            else:
                next_action = CastToTargetAddToStack(self.choice.player_idx, self.choice.gs, self.choice.source,
                                                     target=None, eff_spec=self.choice.eff_spec)
            self.gs.action_stack.push(next_action, self.gs)
            self.choice.gs.pending_choice = None

class SkipDrawPhaseGainLife(Action):
    def __init__(self, p_id: int, gs: GameState, amt: int):
        super().__init__(p_id, gs)
        self.amt = amt

    def play(self):
        self.gs.phase_mgr.set_phase(Phase.MAIN, self.gs)
        self.gs.score_mgr.increment_life(self.player_idx, self.amt, source=None, gs=self.gs)
        self.gs.action_stack.pop()

# --- CARD-SPECIFIC ---
class CyclonePayManaPerCounterDealDamage(Action):
    def __init__(self, p_id: int, gs: GameState, s: GameCard):
        super().__init__(p_id, gs)
        self.s = s
        self.wind_counters = self.s.counters.get_count(WIND)

    def __repr__(self):
        return f'Pay {self.wind_counters} G to deal {self.wind_counters} damage to all creatures & players'

    def play(self) -> None:
        self.gs.mana_pools[self.s.owner_id].pay('G' * self.wind_counters)
        for creature in list(self.gs.card_filter.in_play().creatures().result()):
            self.gs.destroy(creature)
        for p_id in range(2):
            self.gs.apply_damage(self.s, self.wind_counters, p_id)
        self.gs.action_stack.pop()

class HealingSalveA(Action):
    def __init__(self, p_id: int, gs: GameState, s: GameCard):
        super().__init__(p_id, gs)
        self.s = s

    def __repr__(self):
        return 'You gain 3 life'

    def play(self) -> None:
        self.gs.score_mgr.increment_life(self.player_idx, 3, self.s, self.gs)
        if self.gs.pending_choice:
            self.gs.pending_choice = None

class HealingSalveB(Action):
    def __init__(self, p_id: int, gs: GameState, s: GameCard, t: GameCard | int):
        super().__init__(p_id, gs)
        self.s = s
        self.target = t

    def __repr__(self):
        return 'Prevent the next 3 damage that would be dealt to any target this turn'

    def play(self) -> None:
        if isinstance(self.target, int):
            pnd = PreventNextDamage(self.s, 3, target_player=self.target)
        else:
            pnd = PreventNextDamage(self.s, 3, target_card=self.target)
        self.gs.damage_preventions.append(pnd)
        self.gs.action_stack.pop()

class PrimalClayA(Action):
    def __init__(self, p_id: int, gs: GameState, s: GameCard):
        super().__init__(p_id, gs)
        self.s = s

    def __repr__(self):
        return 'Cast as a 3/3'

    def play(self) -> None:
        self.s.base_pt = (3, 3)
        self.gs.cast(self.s)
        if self.gs.pending_choice:
            self.gs.pending_choice = None


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
        self.gs.cast(self.s)
        if self.gs.pending_choice:
            self.gs.pending_choice = None

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
        self.gs.cast(self.s)
        if self.gs.pending_choice:
            self.gs.pending_choice = None

class RogahhOfKherKeepTapAndStealAction(Action):
    def __init__(self, p_id, gs, source: GameCard, targets: list[GameCard]):
        super().__init__(p_id, gs)
        self.source = source
        self.targets = targets

    def __repr__(self):
        return f'Tapping & transferring control of Rogahh Of Kher Keep & all Kobolds Of Kher Keep'

    def play(self):
        for t in self.targets:
            self.gs.tap_card(t)
            t.modifiers.items.append(OwnershipMod(flip(self.source.owner_id), s=self.source))
        if self.gs.action_stack.actions:
            self.gs.action_stack.pop()

class YawgmothDemonUnpaidUpkeep(Action):
    def __init__(self, p_id: int, gs: GameState, s: GameCard):
        super().__init__(p_id, gs)
        self.s = s

    def __repr__(self):
        return f'{self.s.props.name} taps and deals 2 damage to you'

    def play(self) -> None:
        self.gs.tap_card(self.s)
        self.gs.apply_damage(self.s, 2, self.s.owner_id)
        self.gs.action_stack.pop()
