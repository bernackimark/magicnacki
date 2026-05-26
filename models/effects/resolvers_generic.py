from __future__ import annotations
from typing import TYPE_CHECKING, Optional, Callable, Literal

from models.choice_actions_all import PayManaOrSacUpkeepChoice, DiscardChoice
from models.counter_tokens import CounterType, CHARGE, PLUS_ONE_ZERO, PLUS_ZERO_ONE
from models.damage import PreventNextDamage
from models.effects.base import Effect
from models.effects.queries import UnblockableEOT
from models.modifiers import RegenerationMod, TypeMod, SubTypeMod, ColorMod, KWAMod

if TYPE_CHECKING:
    from game_state import GameState
    from models.game_card.game_card import GameCard


class UnblockableThisTurn(Effect):
    """Target creature can't be blocked this turn"""
    def resolve(self, gs: GameState, source: GameCard, target: Optional[GameCard] = None):
        if not target:
            raise ValueError(f'{source.props.name} needs a target')
        temp_effect = UnblockableEOT(target)
        gs.event_mgr.register_effect_until_eot((temp_effect, source))


class AddCounter(Effect):
    def __init__(self, counter_type: CounterType, cnt: int = 1):
        self.counter_type = counter_type
        self.cnt = cnt

    def resolve(self, gs: GameState, source: GameCard, target=None):
        source.counters.add_counter(self.counter_type, self.cnt)


class AddCounterToHost(Effect):
    def __init__(self, counter_type: CounterType, cnt: int = 1):
        self.counter_type = counter_type
        self.cnt = cnt

    def resolve(self, gs: GameState, source: GameCard, target=None):
        source.host.counters.add_counter(self.counter_type, self.cnt)


class AddCountersOnHostTurn(Effect):
    def __init__(self, counter_type: CounterType, cnt: int = 1):
        self.counter_type = counter_type
        self.cnt = cnt

    def resolve(self, gs: GameState, source: GameCard, target=None):
        if gs.turn_mgr.player_turn_idx != source.host.owner_id:
            return
        source.host.counters.add_counter(self.counter_type, self.cnt)


class ManaBatteriesAddMana(Effect):
    def __init__(self, color: str):
        self.color = color

    def resolve(self, gs: GameState, source: GameCard, target=None):
        x = getattr(source, 'variable_x', 0)  # read X chosen when activating
        source.counters.remove_counter(CHARGE, x)
        gs.mana_pools[source.owner_id].add_floating(self.color, 1 + x)


class RemoveCountersOnHostTurn(Effect):
    def __init__(self, counter_type: CounterType, cnt: int = 1):
        self.counter_type = counter_type
        self.cnt = cnt

    def resolve(self, gs: GameState, source: GameCard, target=None):
        if gs.turn_mgr.player_turn_idx != source.host.owner_id:
            return
        source.host.counters.remove_counter(self.counter_type, self.cnt)


class RemovePlusOneZeroFromCombatant(Effect):
    def resolve(self, gs: GameState, source: GameCard, target: Optional[GameCard] = None):
        if source in gs.card_filter.combatants().result():
            source.counters.remove_counter(PLUS_ONE_ZERO)


class AddCountersYourTurnOnly(Effect):
    def __init__(self, counter_type: CounterType, cnt: int = 1):
        self.counter_type = counter_type
        self.cnt = cnt

    def resolve(self, gs: GameState, s: GameCard, target: Optional[GameCard] = None, x_value: int = None):
        if gs.turn_mgr.player_turn_idx != s.owner_id:
            return
        cnt = self.cnt if x_value is None else x_value
        s.counters.add_counter(self.counter_type, cnt)


class AddCountersIfAnyCreatureDied(Effect):
    def __init__(self, counter_type: CounterType, cnt: int = 1):
        self.counter_type = counter_type
        self.cnt = cnt

    def resolve(self, gs: GameState, s: GameCard, target: Optional[GameCard] = None):
        if gs.cards_that_died_this_turn:
            s.counters.add_counter(self.counter_type, self.cnt)


class AddCounterPerCreatureDeath(Effect):
    def __init__(self, counter_type: CounterType):
        self.counter_type = counter_type

    def resolve(self, gs: GameState, s: GameCard, target: Optional[GameCard] = None):
        if death_cnt := len(gs.cards_that_died_this_turn) > 0:
            s.counters.add_counter(self.counter_type, death_cnt)


class XZeroOneCountersByManaValue(Effect):
    """Put X +0/+1 counters on target creature, where X is that creature's mana value"""
    def resolve(self, gs: GameState, source: GameCard, target: GameCard = None):
        if not target:
            raise RuntimeError(f'{source.props.name} needs a target')
        target.counters.add_counter(PLUS_ZERO_ONE, target.props.mana_value)


class DealDamage(Effect):
    def __init__(self, amt: int = None):  # None is permitted due to the possibility of variable X
        self.amt = amt

    def resolve(self, gs: GameState, source: GameCard, target: GameCard | int = None, variable_amt: int = None):
        print(source, self.amt, target)
        amt = self.amt if not variable_amt else variable_amt
        gs.apply_damage(source, amt, target)


class DealOneDamageToTargetList(Effect):
    def resolve(self, gs: GameState, source: GameCard, target: list[GameCard | int] = None):
        for t in target:
            print(source, 1, target)
            gs.apply_damage(source, 1, t)


class DealDamageToAllCreaturesAndPlayers(Effect):
    def __init__(self, amt: int):
        self.amt = amt

    def resolve(self, gs: GameState, source: GameCard, target: Optional[GameCard] = None):
        [gs.apply_damage(source, self.amt, p_id, is_combat=False) for p_id in (0, 1)]
        [gs.apply_damage(source, self.amt, creature) for creature in gs.card_filter.in_play().creatures().result()]


class DealDamageToTargetAndSelf(Effect):
    def __init__(self, amt_to_target: int, amt_to_source_card: int):
        self.amt_to_target = amt_to_target
        self.amt_to_source_card = amt_to_source_card

    def resolve(self, gs: GameState, source: GameCard, target: Optional[GameCard] = None):
        if not target:
            raise RuntimeError(f"{source.props.name} needs a target")
        gs.apply_damage(source, self.amt_to_target, target)
        gs.apply_damage(source, self.amt_to_source_card, source)


class DealDamageToTargetAndYou(Effect):
    def __init__(self, amt_to_target: int, amt_to_you: int):
        self.amt_to_target = amt_to_target
        self.amt_to_you = amt_to_you

    def resolve(self, gs: GameState, source: GameCard, target: Optional[GameCard] = None):
        if not target:
            raise RuntimeError(f"{source.props.name} needs a target")
        gs.apply_damage(source, self.amt_to_target, target)
        gs.apply_damage(source, self.amt_to_you, source.owner_id)


class PreventAllCombatDamageThisTurn(Effect):
    def resolve(self, gs: GameState, source: GameCard, target=None):
        prevention = PreventNextDamage(source, combat_only=True)
        gs.damage_preventions.append(prevention)
        gs.register_effect_until_eot(prevention)


class PreventNextDamageToCardEffect(Effect):
    def resolve(self, gs: GameState, source: GameCard, target: Optional[GameCard] = None):
        """target = the GameCard being protected"""
        gs.damage_preventions.append(PreventNextDamage(source, target_card=target))


class Destroy(Effect):
    def __init__(self, allow_regen: bool = True):
        self.allow_regen = allow_regen

    def resolve(self, gs: GameState, source: GameCard, target: Optional[GameCard] = None):
        gs.destroy(target, allow_regeneration=self.allow_regen)


class DestroyAll(Effect):
    def __init__(self, card_filter_func: Callable[[GameState, GameCard], list[GameCard]], allow_regen: bool = True):
        self.card_filter_func = card_filter_func
        self.allow_regen = allow_regen

    def resolve(self, gs: GameState, s: GameCard, t: Optional[GameCard] = None):
        for c in self.card_filter_func(gs, s):
            gs.destroy(c, allow_regeneration=self.allow_regen)


class DestroyIfItAttacked(Effect):
    """Destroy creature if it attacked this turn."""
    def resolve(self, gs: GameState, s: GameCard, t: Optional[GameCard] = None):
        for t in gs.card_filter.attackers().result():
            gs.destroy(t)


class ExileAllCreatures(Effect):
    def resolve(self, gs: GameState, source: GameCard, target: Optional[GameCard] = None):
        for c in gs.card_filter.in_play().creatures().result():
            gs.exile(c)


class PayManaOrSac(Effect):
    def __init__(self, mana_cost: str):
        self.mana_cost = mana_cost

    def resolve(self, gs: GameState, source: GameCard, target=None):
        gs.action_stack.push(PayManaOrSacUpkeepChoice(source.owner_id, gs, source, self.mana_cost), gs, False)


class Regenerate(Effect):
    def resolve(self, gs: GameState, source: GameCard, target: GameCard = None):
        if not target:
            raise ValueError(f'{source.props.name} needs a target')
        target.modifiers.items.append(RegenerationMod(s=source, expires='EOT'))


class SacAll(Effect):
    def __init__(self, card_filter_func: Callable[[GameState, GameCard], list[GameCard]]):
        self.card_filter_func = card_filter_func

    def resolve(self, gs: GameState, s: GameCard, t: Optional[GameCard] = None):
        for c in self.card_filter_func(gs, s):
            gs.destroy(c, allow_regeneration=False)


class DrawCards(Effect):
    def __init__(self, card_cnt: int = 1):
        self.card_cnt = card_cnt

    def resolve(self, gs: GameState, source: GameCard, target: Optional[int] = None):
        if target is None:
            return
        gs.draw(target, self.card_cnt)


class Discard(Effect):
    def resolve(self, gs: GameState, source: GameCard, target: int = None):
        if not target:
            raise ValueError(f'{source.props.name} needs a target')
        gs.pending_choice = DiscardChoice(target, gs, source, target)


class RevealLibrary(Effect):
    def __init__(self, viewer_id: int | None = None, top_x: int | None = None):
        self.viewer_id = viewer_id
        self.top_x = top_x

    def resolve(self, gs: GameState, source: GameCard, target=None):
        if self.viewer_id is None:
            self.viewer_id = source.owner_id
        cards = gs.libraries[source.owner_id] if not self.top_x else gs.libraries[source.owner_id][:self.top_x]
        gs.add_presentation_request(self.viewer_id, 'view_library', {'cards': cards})


class BecomeCreature(Effect):
    def __init__(self, power: int, toughness: int, sub_type: str = None, until_eot: bool = False):
        self.power = power
        self.toughness = toughness
        self.sub_type = sub_type
        self.until_eot = until_eot

    def resolve(self, gs, source: GameCard, target: GameCard = None):
        if not target:
            raise RuntimeError(f'{source.props.name} needs a target')
        target.modifiers.items.append(TypeMod(s=source, add_or_remove='add', card_type='Creature',
                                              expires='EOT' if self.until_eot else None))
        if self.sub_type:
            target.modifiers.items.append(SubTypeMod(s=source, add_or_remove='add', card_sub_type=self.sub_type,
                                                     expires='EOT' if self.until_eot else None))


class SetColor(Effect):
    def __init__(self, color: str, expires: str | None = None):
        self.color = color
        self.expires = expires

    def resolve(self, gs: GameState, source: GameCard, target: GameCard = None):
        if target is None:
            raise ValueError(f'{source.props.name} needs a target')
        target.modifiers.items.append(ColorMod(s=source, expires=self.expires, new_colors=self.color))


class AllWalksRemoved(Effect):
    """Target creature loses all landwalk abilities until end of turn"""
    def resolve(self, gs, source: GameCard, target: Optional[GameCard] = None):
        for land in ('Island', 'Forest', 'Mountain', 'Swamps', 'Plains'):
            target.modifiers.items.append(KWAMod(s=source, add_or_remove='remove', kwa=f'{land}walk', expires='EOT'))


class KWAModEffect(Effect):
    def __init__(self, add_or_remove: Literal['add', 'remove'], kwa: str, eot: bool = False):
        self.add_or_remove = add_or_remove
        self.kwa = kwa
        self.eot = eot

    def resolve(self, gs, s: GameCard, target: Optional[GameCard] = None):
        target.modifiers.items.append(KWAMod(s=s, add_or_remove=self.add_or_remove, kwa=self.kwa,
                                             expires='EOT' if self.eot else None))


class GainLife(Effect):
    def __init__(self, amt: int = 1):
        self.amt = amt

    def resolve(self, gs: GameState, source: GameCard, target: int = None):
        if not target:
            raise RuntimeError(f'{source.props.name} needs a target')
        gs.score_mgr.increment_life(target, self.amt, source, gs)
