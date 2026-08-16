from __future__ import annotations

import copy
from typing import TYPE_CHECKING

from models.action_stack import StackItemType
from models.actions.base import Action
from models.constants import KW, Zone
from models.game_card.counter_tokens import CounterType, WIND, PLUS_ONE
from models.effects.listeners_mod_queries import OwnershipModQuery
from models.events_all import StateBasedEvent
from models.game_card.modifiers import SubTypeMod
from models.systems.phase import Phase
from models.utils import flip

if TYPE_CHECKING:
    from game_state import GameState
    from models.game_card.game_card import GameCard


class CopyCardAction(Action):
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
        self.s.base_pt = the_copy.base_pt
        self.s._base_kwa = the_copy.props.keyword_abilities
        self.s.abilities = the_copy.abilities
        if self.gs.phase_mgr.phase != Phase.UPKEEP:  # hack. Vesuvan Doppel =only card that calls this during upkeep
            self.gs.pile_mgr.cast(self.s)
        self.finish()

class DestroyAndForegoCombatDamage(Action):
    def __init__(self, p_id: int, gs: GameState, source: GameCard, target: GameCard):
        super().__init__(p_id, gs)
        self.source = source
        self.target = target

    def __repr__(self):
        return f'Destroy {self.target} & forego combat damage assigned by {self.source.props.name}'

    def play(self):
        from models.effects.listeners_generic import PreventNextDamageBy
        self.gs.pile_mgr.destroy(self.target)
        self.gs.event_mgr.register(PreventNextDamageBy(self.source, combat_only=True))
        self.finish()

class PayManaAndOrTakeDamage(Action):
    def __init__(self, p_id: int, gs: GameState, source: GameCard, pay_mana_amt: int, damage_amt: int):
        super().__init__(p_id, gs)
        self.source = source
        self.pay_mana_amt = pay_mana_amt
        self.damage_amt = damage_amt

    def __repr__(self):
        return f'Pay {self.pay_mana_amt} mana & take {self.damage_amt} amount assigned by {self.source.props.name}'

    def play(self):
        if self.pay_mana_amt:
            self.gs.mana_pools[self.player_idx].pay(str(self.pay_mana_amt))
        if self.damage_amt:
            self.gs.apply_damage(self.source, self.damage_amt, self.player_idx)
        self.finish()

class PayManaForLife(Action):
    def __init__(self, p_id: int, gs: GameState, mana_cost: str, gain_life_amt: int):
        super().__init__(p_id, gs)
        self.mana_cost = mana_cost
        self.gain_life_amt = gain_life_amt

    def play(self):
        self.gs.mana_pools[self.player_idx].pay(self.mana_cost)
        self.gs.score_mgr.increment_life(self.player_idx, self.gain_life_amt, source=None, gs=self.gs)
        self.finish()

class PayManaToBounce(Action):
    def __init__(self, p_id: int, gs: GameState, source: GameCard, target: GameCard, mana_cost: str):
        super().__init__(p_id, gs)
        self.source = source
        self.target = target
        self.mana_cost = mana_cost

    def __repr__(self):
        return f'Pay {{{self.mana_cost}}} to bounce {self.target}'

    def play(self) -> None:
        if self.gs.mana_pools[self.player_idx].can_pay(self.mana_cost):
            self.gs.mana_pools[self.player_idx].pay(self.mana_cost)
            self.gs.pile_mgr.bounce(self.target)
            self.finish()

class PayManaToPreventCounter(Action):
    def __init__(self, p_id: int, gs: GameState, counter_spell: StackItemType, mana_cost: str):
        super().__init__(p_id, gs)
        self.counter_spell = counter_spell
        self.mana_cost = mana_cost

    def __repr__(self):
        source = self.counter_spell.source
        return f'Pay {{{self.mana_cost}}} to prevent counterspell by {source.props.name}'

    def play(self):
        if self.gs.mana_pools[self.player_idx].can_pay(self.mana_cost):
            self.gs.mana_pools[self.player_idx].pay(self.mana_cost)
            self.gs.action_stack.remove(self.counter_spell)
        self.finish()

class PayManaToDrawCards(Action):
    def __init__(self, p_id: int, gs: GameState, mana_cost: str, card_cnt: int):
        super().__init__(p_id, gs)
        self.mana_cost = mana_cost
        self.card_cnt = card_cnt

    def play(self):
        self.gs.mana_pools[self.player_idx].pay(self.mana_cost)
        self.gs.pile_mgr.draw(self.player_idx, self.card_cnt)
        self.finish()

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
        self.finish()

class SacTwoIslandsToAttack(Action):
    def __init__(self, p_id: int, gs: GameState, s: GameCard, target: GameCard):
        super().__init__(p_id, gs)
        self.s = s
        self.target = target

    def play(self) -> None:
        from models.effects.listeners_permission import CanAttackEOT
        your_islands = self.gs.card_filter.on_player_board(self.s.owner_id).islands().result()
        for island in your_islands[:2]:
            self.gs.pile_mgr.destroy(island)
        self.gs.event_mgr.register(CanAttackEOT(self.target), self.s)
        self.finish()

class StoreColorOnCard(Action):
    def __init__(self, p_id: int, gs: GameState, card: GameCard, color_letter: str):
        super().__init__(p_id, gs)
        self.card = card
        self.color_letter = color_letter

    def __repr__(self):
        return f"Declare {self.card.props.name}'s color as {self.color_letter}"

    def play(self) -> None:
        self.card.extras['color_declaration'] = self.color_letter
        # TODO: make presentation request, as this selection is public
        self.finish()

class SubTypeReplacement(Action):
    """In the target's modifiers, add a specific sub_type & remove all of its existing sub_types"""
    def __init__(self, p_id: int, gs: GameState, source: GameCard, target: GameCard, sub_type: str):
        super().__init__(p_id, gs)
        self.s = source
        self.target = target
        self.sub_type = sub_type.capitalize()

    def __repr__(self):
        return f"Turn {self.target} into a {self.sub_type}"

    def play(self) -> None:
        sub_types = self.target.card_sub_types.copy()
        self.target.modifiers.append(SubTypeMod(s=self.s, item=self.sub_type))
        for sub_type in sub_types:
            self.target.modifiers.append(SubTypeMod(s=self.s, add_or_remove='remove', item=sub_type))
        self.finish()

# --- CARD-SPECIFIC ---
class CleansingDeclineAction(Action):
    def __init__(self, p_id: int, gs: GameState, s: GameCard, state: "CleansingState"):
        super().__init__(p_id, gs)
        self.s = s
        self.state = state

    def __repr__(self):
        return f"Decline saving Player #{self.state.active_land.owner_id}'s {self.state.active_land}"

    def play(self):
        from models.effects.resolvers_a_to_e import Cleansing
        self.state.player_cnt_acted_on_this_land += 1
        # Ask the next player
        self.gs.action_on_idx = flip(self.gs.action_on_idx)
        Cleansing.queue_next_choice(self.gs, self.s, self.state)

class CleansingPayAction(Action):
    def __init__(self, p_id: int, gs: GameState, s: GameCard, state: "CleansingState"):
        super().__init__(p_id, gs)
        self.s = s
        self.state = state

    def __repr__(self):
        return f"Pay 1 life to save Player #{self.state.active_land.owner_id}'s {self.state.active_land}"

    def play(self):
        from models.effects.resolvers_a_to_e import Cleansing
        self.gs.score_mgr.decrement_life(self.player_idx, 1, self.s, self.gs)
        self.state.saved_lands.append(self.state.active_land)

        # Move immediately to next land
        self.state.land_idx += 1
        self.gs.action_on_idx = flip(self.gs.action_on_idx)
        Cleansing.queue_next_choice(self.gs, self.s, self.state)

class DrafnaFinishAction(Action):
    def __init__(self, p_id: int, gs: GameState, s: GameCard, state: "DrafnasRestoration.DrafnasRestorationState"):
        super().__init__(p_id, gs)
        self.s = s
        self.state = state

    def __repr__(self):
        return "Finish selecting artifacts"

    def play(self) -> None:
        for card in self.state.selected_cards:
            self.gs.pile_mgr.move_card(card, Zone.LIBRARY)
        self.finish()

class DrafnaSelectCardAction(Action):
    def __init__(self, p_id: int, gs: GameState, s: GameCard, state: "DrafnasRestoration.DrafnasRestorationState",
                 card: GameCard):
        super().__init__(p_id, gs)
        self.s = s
        self.state = state
        self.card = card

    def __repr__(self):
        return f"Move {self.card.props.name} to library; subsequent artifacts will be placed above this card"

    def play(self) -> None:
        self.state.selected_cards.append(self.card)

class EurekaPlayCardAction(Action):
    def __init__(self, p_id: int, gs: GameState, state: "Eureka.EurekaState", card: GameCard):
        super().__init__(p_id, gs)
        self.state = state
        self.card = card

    def __repr__(self):
        return f"Play {self.card.props.name} to your board"

    def play(self) -> None:
        from models.effects.resolvers_a_to_e import Eureka
        self.gs.pile_mgr.move_card(self.card, Zone.BATTLEFIELD, cause='eureka', emit_zone_event=False)
        self.state.current_player = flip(self.player_idx)
        self.gs.pending_choice = None
        Eureka.queue_next_choice(self.gs, self.state)

class EurekaPlayerFinishAction(Action):
    def __init__(self, p_id: int, gs: GameState, state: "Eureka.EurekaState"):
        super().__init__(p_id, gs)
        self.state = state

    def __repr__(self):
        return f"Finish playing permanents to your board"

    def play(self) -> None:
        from models.effects.resolvers_a_to_e import Eureka
        self.state.players_who_are_done.append(self.player_idx)
        self.state.current_player = flip(self.player_idx)
        self.gs.pending_choice = None
        Eureka.queue_next_choice(self.gs, self.state)

class HealingSalveA(Action):
    def __init__(self, p_id: int, gs: GameState, s: GameCard):
        super().__init__(p_id, gs)
        self.s = s

    def __repr__(self):
        return 'You gain 3 life'

    def play(self) -> None:
        self.gs.score_mgr.increment_life(self.player_idx, 3, self.s, self.gs)
        self.finish()

class HealingSalveB(Action):
    def __init__(self, p_id: int, gs: GameState, s: GameCard, t: GameCard | int):
        super().__init__(p_id, gs)
        self.s = s
        self.target = t

    def __repr__(self):
        return 'Prevent the next 3 damage that would be dealt to any target this turn'

    def play(self) -> None:
        from models.effects.listeners_generic import PreventNextDamageTo
        self.gs.event_mgr.register(PreventNextDamageTo(3, False, self.target))
        self.finish()

class IslandSanctuaryAction(Action):
    def __init__(self, p_id: int, gs: GameState, source: GameCard):
        super().__init__(p_id, gs)
        self.source = source

    def __repr__(self):
        return 'Skip your draw & until your next turn, you can only be attacked by fliers and/or islandwalkers'

    def play(self) -> None:
        from models.effects.listeners_permission import IslandSanctuaryRestriction
        from models.effects.listeners_generic import UnregisterListenerOnYourNextTurn
        self.gs.phase_mgr.set_phase(Phase.MAIN)
        listener = IslandSanctuaryRestriction()
        self.gs.event_mgr.register(listener, self.source)
        self.gs.event_mgr.register(UnregisterListenerOnYourNextTurn(listener), self.source)
        self.finish()

class NamelessRaceETBAction(Action):
    def __init__(self, p_id: int, gs: GameState, s: GameCard, amt: int):
        super().__init__(p_id, gs)
        self.s = s
        self.amt = amt

    def __repr__(self):
        return f'Pay {self.amt} life to make {self.s.props.name} a {self.amt}/{self.amt} creature'

    def play(self) -> None:
        self.s.base_pt = (self.amt, self.amt)
        self.gs.apply_damage(self.s, self.amt, self.s.owner_id)
        self.finish()

