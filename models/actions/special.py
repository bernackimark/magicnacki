from __future__ import annotations

import copy
from typing import TYPE_CHECKING

from models.counter_tokens import CounterType, WIND
from models.effects.listeners_mod_queries import OwnershipModQuery
from models.events_all import StateBasedEvent
from models.modifiers import SubTypeMod
from models.systems.phase import Phase
from models.utils import flip
from models.zone import Zone

if TYPE_CHECKING:
    from game_state import GameState
    from models.actions.ability_pipeline_support import AbilityAction
    from models.actions.cast import CastPermanentAction
    from models.game_card.game_card import GameCard


from models.actions.base import Action

class Attach(Action):
    def __init__(self, p_id: int, gs: GameState, aura: GameCard, host: GameCard):
        super().__init__(p_id, gs)
        self.aura = aura
        self.host = host

    def __repr__(self):
        return f'Attach {self.aura} to {self.host}'

    def play(self) -> None:
        self.aura.host = self.host
        self.host.auras.append(self.aura)

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
    def __init__(self, p_id: int, gs: GameState, counter_spell: AbilityAction | CastPermanentAction, mana_cost: str):
        super().__init__(p_id, gs)
        self.counter_spell = counter_spell
        self.mana_cost = mana_cost

    def __repr__(self):
        return f'Pay {{{self.mana_cost}}} to prevent counterspell by {self.counter_spell.source.props.name}'

    def play(self):
        if self.gs.mana_pools[self.player_idx].can_pay(self.mana_cost):
            self.gs.mana_pools[self.player_idx].pay(self.mana_cost)
            self.gs.action_stack.remove(self.counter_spell)
        if self.gs.pending_choice:
            self.gs.pending_choice = None

class PayManaToDrawCards(Action):
    def __init__(self, p_id: int, gs: GameState, mana_cost: str, card_cnt: int):
        super().__init__(p_id, gs)
        self.mana_cost = mana_cost
        self.card_cnt = card_cnt

    def play(self):
        self.gs.mana_pools[self.player_idx].pay(self.mana_cost)
        self.gs.pile_mgr.draw(self.player_idx, self.card_cnt)
        self.finish()

class PayManaToPreventDamage(Action):
    def __init__(self, p_id: int, gs: GameState, source: GameCard, protected: GameCard, mana_cost: str,
                 preventable_amt: int | None = None):
        super().__init__(p_id, gs)
        self.source = source
        self.protected = protected
        self.mana_cost = mana_cost
        self.preventable_amt = preventable_amt

    def __repr__(self):
        return f'Pay {{{self.mana_cost}}} to prevent {self.preventable_amt} damage to {self.protected}'

    def play(self) -> None:
        from models.effects.listeners_generic import PreventNextDamageTo
        if not self.gs.mana_pools[self.player_idx].can_pay(self.mana_cost):
            return
        self.gs.mana_pools[self.player_idx].pay(self.mana_cost)
        self.gs.event_mgr.register(PreventNextDamageTo(self.preventable_amt, protected=self.protected), self.source)

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

class SacCreatureAndAddMana(Action):
    def __init__(self, p_id: int, gs: GameState, _: GameCard, creature: GameCard, color: str, amt: int = 0):
        super().__init__(p_id, gs)
        self.creature = creature
        self.color = color
        self.amt = amt

    def play(self):
        # Sacrifice then later apply effect that depends on the creature sacrificed
        self.gs.pile_mgr.destroy(self.creature)
        self.gs.mana_pools[self.gs.player_turn_idx].add_floating(self.color, self.amt)
        self.finish()

class SacTwoIslands(Action):
    def __init__(self, p_id: int, gs: GameState, s: GameCard):
        super().__init__(p_id, gs)
        self.s = s

    def play(self) -> None:
        your_islands = self.gs.card_filter.on_player_board(self.s.owner_id).islands().result()
        for island in your_islands[:2]:
            self.gs.pile_mgr.destroy(island)
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

class SacTwoIslandsToUntap(Action):
    def __init__(self, p_id: int, gs: GameState, s: GameCard, target: GameCard):
        super().__init__(p_id, gs)
        self.s = s
        self.target = target

    def play(self):
        your_islands = self.gs.card_filter.on_player_board(self.s.owner_id).islands().result()
        for island in your_islands[:2]:
            self.gs.pile_mgr.destroy(island)
        self.target.untap()
        self.finish()

class SkipDrawPhaseGainLife(Action):
    def __init__(self, p_id: int, gs: GameState, amt: int):
        super().__init__(p_id, gs)
        self.amt = amt

    def play(self):
        self.gs.phase_mgr.set_phase(Phase.MAIN)
        self.gs.score_mgr.increment_life(self.player_idx, self.amt, source=None, gs=self.gs)
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
        self.gs.pending_choice = None

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
        self.gs.pending_choice = None

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
            self.gs.pile_mgr.destroy(creature)
        for p_id in range(2):
            self.gs.apply_damage(self.s, self.wind_counters, p_id)
        self.finish()

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

class PrimalClayA(Action):
    def __init__(self, p_id: int, gs: GameState, s: GameCard):
        super().__init__(p_id, gs)
        self.s = s

    def __repr__(self):
        return 'Cast as a 3/3'

    def play(self) -> None:
        self.s.base_pt = (3, 3)
        self.gs.pile_mgr.cast(self.s)
        self.finish()


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
        self.gs.pile_mgr.cast(self.s)
        self.finish()

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
        self.s._base_kwa = kwa
        self.gs.pile_mgr.cast(self.s)
        self.finish()

class RogahhOfKherKeepTapAndStealAction(Action):
    def __init__(self, p_id, gs, source: GameCard, targets: list[GameCard]):
        super().__init__(p_id, gs)
        self.source = source
        self.targets = targets
        # self.owner_upon_class_creation = int(source.owner_id)  # fixes multiple flips in .play() for unknown reason

    def __repr__(self):
        return f'Tapping & transferring control of Rogahh Of Kher Keep & all Kobolds Of Kher Keep'

    def play(self):
        old_controller = int(self.source.owner_id)
        new_controller = int(flip(self.source.owner_id))
        for t in self.targets:
            t.tap()
            self.gs.event_mgr.register(OwnershipModQuery(t, lambda gs, s: new_controller), self.source)
            t.turn_entered_for_owner = self.gs.turn_mgr.turn_number
            if t.zone == Zone.BATTLEFIELD:
                self.gs.pile_mgr.boards[old_controller].remove(t)
                self.gs.pile_mgr.boards[new_controller].append(t)
        self.gs.event_mgr.emit(StateBasedEvent())
        self.finish()

class TimeVaultSkipTurnAction(Action):
    def __init__(self, p_id, gs, source: GameCard):
        super().__init__(p_id, gs)
        self.source = source

    def __repr__(self):
        return f'Skip turn and untap {self.source.props.name}'

    def play(self) -> None:
        self.source.untap()
        self.gs.phase_mgr.set_phase(Phase.PASS_THE_TURN)
        self.finish()

class WoodElementalETBAction(Action):
    def __init__(self, p_id: int, gs: GameState, s: GameCard, cards_to_sac: list[GameCard]):
        super().__init__(p_id, gs)
        self.s = s
        self.cards_to_sac = cards_to_sac

    def __repr__(self):
        return f'Sac {self.amt} to make {self.s.props.name} a {self.amt}/{self.amt} creature'

    @property
    def amt(self) -> int:
        return len(self.cards_to_sac)

    def play(self) -> None:
        self.s.base_pt = (self.amt, self.amt)
        for card in self.cards_to_sac:
            self.gs.pile_mgr.destroy(card, allow_regeneration=False)
        self.finish()

class WormsOfTheEarthSacTwoLands(Action):
    def __init__(self, p_id: int, gs: GameState, s: GameCard):
        super().__init__(p_id, gs)
        self.s = s

    def __repr__(self):
        return f'Sac two lands and destroy Worms Of The Earth'

    def play(self) -> None:
        your_islands = self.gs.card_filter.on_player_board(self.player_idx).lands().result()
        for island in your_islands[:2]:
            self.gs.pile_mgr.destroy(island)
        self.gs.pile_mgr.destroy(self.s)
        self.finish()

class WormsOfTheEarthTake5Damage(Action):
    def __init__(self, p_id: int, gs: GameState, s: GameCard):
        super().__init__(p_id, gs)
        self.s = s

    def __repr__(self):
        return f'Take 5 damage and destroy Worms Of The Earth'

    def play(self) -> None:
        self.gs.apply_damage(self.s, 5, self.player_idx)
        self.gs.pile_mgr.destroy(self.s)
        self.finish()

class YawgmothDemonUnpaidUpkeep(Action):
    def __init__(self, p_id: int, gs: GameState, s: GameCard):
        super().__init__(p_id, gs)
        self.s = s

    def __repr__(self):
        return f'{self.s.props.name} taps and deals 2 damage to you'

    def play(self) -> None:
        self.s.tap()
        self.gs.apply_damage(self.s, 2, self.s.owner_id)
        self.finish()
