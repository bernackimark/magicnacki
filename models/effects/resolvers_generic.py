from __future__ import annotations
from typing import TYPE_CHECKING, Optional, Callable, Literal

from models.actions.tap_untap import LeaveTapped
from models.choice_actions_all import PayManaOrSacUpkeepChoice, DiscardChoice, UntapWithManaChoice
from models.constants import COLOR_LETTERS_W_COLORLESS
from models.counter_tokens import CounterType, CHARGE, PLUS_ONE_ZERO, PLUS_ZERO_ONE
from models.damage import PreventNextDamage
from models.effects.base import Resolver
from models.effects.queries import UnblockableEOT
from models.events_all import StateBasedEvent, ZoneChangeEvent
from models.modifiers import RegenerationMod, TypeMod, SubTypeMod, ColorMod, KWAMod, OwnershipMod, PTMod
from models.zone import Zone

if TYPE_CHECKING:
    from game_state import GameState
    from models.game_card.game_card import GameCard


class UnblockableThisTurn(Resolver):
    """Target creature can't be blocked this turn"""
    def resolve(self, gs: GameState, source: GameCard, target: Optional[GameCard] = None):
        if not target:
            raise ValueError(f'{source.props.name} needs a target')
        temp_effect = UnblockableEOT(target)
        gs.event_mgr.register_effect_until_eot((temp_effect, source))


class AddCounter(Resolver):
    def __init__(self, counter_type: CounterType, cnt: int = 1):
        self.counter_type = counter_type
        self.cnt = cnt

    def resolve(self, gs: GameState, source: GameCard, target=None):
        source.counters.add_counter(self.counter_type, self.cnt)


class AddCounterToHost(Resolver):
    def __init__(self, counter_type: CounterType, cnt: int = 1):
        self.counter_type = counter_type
        self.cnt = cnt

    def resolve(self, gs: GameState, source: GameCard, target=None):
        source.host.counters.add_counter(self.counter_type, self.cnt)


class AddCountersOnHostTurn(Resolver):
    def __init__(self, counter_type: CounterType, cnt: int = 1):
        self.counter_type = counter_type
        self.cnt = cnt

    def resolve(self, gs: GameState, source: GameCard, target=None):
        if gs.turn_mgr.player_turn_idx != source.host.owner_id:
            return
        source.host.counters.add_counter(self.counter_type, self.cnt)


class ManaBatteriesAddMana(Resolver):
    def __init__(self, color: str):
        self.color = color

    def resolve(self, gs: GameState, source: GameCard, target=None):
        x = getattr(source, 'variable_x', 0)  # read X chosen when activating
        source.counters.remove_counter(CHARGE, x)
        gs.mana_pools[source.owner_id].add_floating(self.color, 1 + x)


class RemoveCountersOnHostTurn(Resolver):
    def __init__(self, counter_type: CounterType, cnt: int = 1):
        self.counter_type = counter_type
        self.cnt = cnt

    def resolve(self, gs: GameState, source: GameCard, target=None):
        if gs.turn_mgr.player_turn_idx != source.host.owner_id:
            return
        source.host.counters.remove_counter(self.counter_type, self.cnt)


class RemovePlusOneZeroFromCombatant(Resolver):
    def resolve(self, gs: GameState, source: GameCard, target: Optional[GameCard] = None):
        if source in gs.card_filter.combatants().result():
            source.counters.remove_counter(PLUS_ONE_ZERO)


class AddCountersYourTurnOnly(Resolver):
    def __init__(self, counter_type: CounterType, cnt: int = 1):
        self.counter_type = counter_type
        self.cnt = cnt

    def resolve(self, gs: GameState, s: GameCard, target: Optional[GameCard] = None, x_value: int = None):
        if gs.turn_mgr.player_turn_idx != s.owner_id:
            return
        cnt = self.cnt if x_value is None else x_value
        s.counters.add_counter(self.counter_type, cnt)


class AddCountersIfAnyCreatureDied(Resolver):
    def __init__(self, counter_type: CounterType, cnt: int = 1):
        self.counter_type = counter_type
        self.cnt = cnt

    def resolve(self, gs: GameState, s: GameCard, target: Optional[GameCard] = None):
        if gs.cards_that_died_this_turn:
            s.counters.add_counter(self.counter_type, self.cnt)


class AddCounterPerCreatureDeath(Resolver):
    def __init__(self, counter_type: CounterType):
        self.counter_type = counter_type

    def resolve(self, gs: GameState, s: GameCard, target: Optional[GameCard] = None):
        if death_cnt := len(gs.cards_that_died_this_turn) > 0:
            s.counters.add_counter(self.counter_type, death_cnt)


class XZeroOneCountersByManaValue(Resolver):
    """Put X +0/+1 counters on target creature, where X is that creature's mana value"""
    def resolve(self, gs: GameState, source: GameCard, target: GameCard = None):
        if not target:
            raise RuntimeError(f'{source.props.name} needs a target')
        target.counters.add_counter(PLUS_ZERO_ONE, target.props.mana_value)


class DealDamage(Resolver):
    def __init__(self, amt: int = None):  # None is permitted due to the possibility of variable X
        self.amt = amt

    def resolve(self, gs: GameState, source: GameCard, target: GameCard | int = None, variable_amt: int = None):
        print(source, self.amt, target)
        amt = self.amt if not variable_amt else variable_amt
        gs.apply_damage(source, amt, target)


class DealOneDamageToTargetList(Resolver):
    def resolve(self, gs: GameState, source: GameCard, target: list[GameCard | int] = None):
        for t in target:
            print(source, 1, target)
            gs.apply_damage(source, 1, t)


class DealDamageToAllCreaturesAndPlayers(Resolver):
    def __init__(self, amt: int):
        self.amt = amt

    def resolve(self, gs: GameState, source: GameCard, target: Optional[GameCard] = None):
        [gs.apply_damage(source, self.amt, p_id, is_combat=False) for p_id in (0, 1)]
        [gs.apply_damage(source, self.amt, creature) for creature in gs.card_filter.in_play().creatures().result()]


class DealDamageToTargetAndSelf(Resolver):
    def __init__(self, amt_to_target: int, amt_to_source_card: int):
        self.amt_to_target = amt_to_target
        self.amt_to_source_card = amt_to_source_card

    def resolve(self, gs: GameState, source: GameCard, target: Optional[GameCard] = None):
        if not target:
            raise RuntimeError(f"{source.props.name} needs a target")
        gs.apply_damage(source, self.amt_to_target, target)
        gs.apply_damage(source, self.amt_to_source_card, source)


class DealDamageToTargetAndYou(Resolver):
    def __init__(self, amt_to_target: int, amt_to_you: int):
        self.amt_to_target = amt_to_target
        self.amt_to_you = amt_to_you

    def resolve(self, gs: GameState, source: GameCard, target: Optional[GameCard] = None):
        if not target:
            raise RuntimeError(f"{source.props.name} needs a target")
        gs.apply_damage(source, self.amt_to_target, target)
        gs.apply_damage(source, self.amt_to_you, source.owner_id)


class PreventAllCombatDamageThisTurn(Resolver):
    def resolve(self, gs: GameState, source: GameCard, target=None):
        prevention = PreventNextDamage(source, combat_only=True)
        gs.damage_preventions.append(prevention)
        gs.register_effect_until_eot(prevention)


class PreventNextDamageToCardEffect(Resolver):
    def resolve(self, gs: GameState, source: GameCard, target: Optional[GameCard] = None):
        """target = the GameCard being protected"""
        gs.damage_preventions.append(PreventNextDamage(source, target_card=target))


class Destroy(Resolver):
    def __init__(self, allow_regen: bool = True):
        self.allow_regen = allow_regen

    def resolve(self, gs: GameState, source: GameCard, target: Optional[GameCard] = None):
        gs.destroy(target, allow_regeneration=self.allow_regen)


class DestroyAll(Resolver):
    def __init__(self, card_filter_func: Callable[[GameState, GameCard], list[GameCard]], allow_regen: bool = True):
        self.card_filter_func = card_filter_func
        self.allow_regen = allow_regen

    def resolve(self, gs: GameState, s: GameCard, t: Optional[GameCard] = None):
        for c in self.card_filter_func(gs, s):
            gs.destroy(c, allow_regeneration=self.allow_regen)


class DestroyIfItAttacked(Resolver):
    """Destroy creature if it attacked this turn."""
    def resolve(self, gs: GameState, s: GameCard, t: Optional[GameCard] = None):
        for t in gs.card_filter.attackers().result():
            gs.destroy(t)


class ExileAllCreatures(Resolver):
    def resolve(self, gs: GameState, source: GameCard, target: Optional[GameCard] = None):
        for c in gs.card_filter.in_play().creatures().result():
            gs.exile(c)


class PayManaOrSac(Resolver):
    def __init__(self, mana_cost: str):
        self.mana_cost = mana_cost

    def resolve(self, gs: GameState, source: GameCard, target=None):
        gs.action_stack.push(PayManaOrSacUpkeepChoice(source.owner_id, gs, source, self.mana_cost), gs, False)


class Regenerate(Resolver):
    def resolve(self, gs: GameState, source: GameCard, target: GameCard = None):
        if not target:
            raise ValueError(f'{source.props.name} needs a target')
        target.modifiers.items.append(RegenerationMod(s=source, expires='EOT'))


class SacAll(Resolver):
    def __init__(self, card_filter_func: Callable[[GameState, GameCard], list[GameCard]]):
        self.card_filter_func = card_filter_func

    def resolve(self, gs: GameState, s: GameCard, t: Optional[GameCard] = None):
        for c in self.card_filter_func(gs, s):
            gs.destroy(c, allow_regeneration=False)


class DrawCards(Resolver):
    def __init__(self, card_cnt: int = 1):
        self.card_cnt = card_cnt

    def resolve(self, gs: GameState, source: GameCard, target: Optional[int] = None):
        if target is None:
            return
        gs.draw(target, self.card_cnt)


class Discard(Resolver):
    def resolve(self, gs: GameState, source: GameCard, target: int = None):
        if not target:
            raise ValueError(f'{source.props.name} needs a target')
        gs.pending_choice = DiscardChoice(target, gs, source, target)


class RevealLibrary(Resolver):
    def __init__(self, viewer_id: int | None = None, top_x: int | None = None):
        self.viewer_id = viewer_id
        self.top_x = top_x

    def resolve(self, gs: GameState, source: GameCard, target=None):
        if self.viewer_id is None:
            self.viewer_id = source.owner_id
        cards = gs.libraries[source.owner_id] if not self.top_x else gs.libraries[source.owner_id][:self.top_x]
        gs.add_presentation_request(self.viewer_id, 'view_library', {'cards': cards})


class BecomeCreature(Resolver):
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


class SetColor(Resolver):
    def __init__(self, color: str, expires: str | None = None):
        self.color = color
        self.expires = expires

    def resolve(self, gs: GameState, source: GameCard, target: GameCard = None):
        if target is None:
            raise ValueError(f'{source.props.name} needs a target')
        target.modifiers.items.append(ColorMod(s=source, expires=self.expires, new_colors=self.color))


class AllWalksRemoved(Resolver):
    """Target creature loses all landwalk abilities until end of turn"""
    def resolve(self, gs, source: GameCard, target: Optional[GameCard] = None):
        for land in ('Island', 'Forest', 'Mountain', 'Swamps', 'Plains'):
            target.modifiers.items.append(KWAMod(s=source, add_or_remove='remove', kwa=f'{land}walk', expires='EOT'))


class KWAModEffect(Resolver):
    def __init__(self, add_or_remove: Literal['add', 'remove'], kwa: str, eot: bool = False):
        self.add_or_remove = add_or_remove
        self.kwa = kwa
        self.eot = eot

    def resolve(self, gs, s: GameCard, target: Optional[GameCard] = None):
        target.modifiers.items.append(KWAMod(s=s, add_or_remove=self.add_or_remove, kwa=self.kwa,
                                             expires='EOT' if self.eot else None))


class GainLife(Resolver):
    def __init__(self, amt: int = 1):
        self.amt = amt

    def resolve(self, gs: GameState, source: GameCard, target: int = None):
        if not target:
            raise RuntimeError(f'{source.props.name} needs a target')
        gs.score_mgr.increment_life(target, self.amt, source, gs)


class AddMana(Resolver):
    def __init__(self, color: str, cnt: int = 1):
        self.color = color
        self.cnt = cnt

        if color not in COLOR_LETTERS_W_COLORLESS:
            raise ValueError(f"Color must be one of: {COLOR_LETTERS_W_COLORLESS}")

    def resolve(self, gs: GameState, source: GameCard, target: GameCard = None):
        gs.mana_pools[source.owner_id].add_floating(self.color, self.cnt)


class Bounce(Resolver):
    def resolve(self, gs: GameState, source: GameCard, target: Optional[GameCard] = None):
        if not target:
            raise RuntimeError(f'{source.props.name} needs a target')
        gs.bounce(target)


class Reanimate(Resolver):
    def resolve(self, gs: GameState, source: GameCard, target: GameCard = None):
        if not target:
            raise RuntimeError(f'{source.props.name} needs a target')
        gs.reanimate(target)


class Steal(Resolver):
    def __init__(self, new_zone: Zone = None):
        self.new_zone = new_zone or Zone.BATTLEFIELD

    def resolve(self, gs: GameState, source: GameCard, target: Optional[GameCard] = None):
        """If the zone is going from battlefield to battlefield, then move_card() will not trigger"""
        if not target:
            raise RuntimeError(f'{source.props.name} needs a target')
        original_owner_id = int(target.owner_id)
        target.modifiers.items.append(OwnershipMod(s=source, new_owner_id=source.owner_id))
        target.turn_entered_for_owner = gs.turn_mgr
        if target.zone == Zone.BATTLEFIELD:
            gs.boards[original_owner_id].remove(target)
            gs.boards[source.owner_id].append(target)
        else:
            gs.move_card(target, self.new_zone, cause='steal')
        gs.event_mgr.emit(StateBasedEvent(), gs)


class GraveyardToExile(Resolver):
    def resolve(self, gs: GameState, source: GameCard, target: GameCard = None):
        if not target:
            raise RuntimeError(f'{source.props.name} needs a target')
        gs.exile(target)


class GraveyardToExileInItsEntirety(Resolver):
    """Moves all cards from target player's graveyard to that same player's exile"""
    def resolve(self, gs: GameState, source: GameCard, target: int = None):
        if not target:
            raise RuntimeError(f'{source.props.name} needs a target')
        gy = gs.graveyards[target][:]
        gs.graveyards[target].clear()
        for card in gy:
            gs.exile(card)


class HandToBoard(Resolver):
    def resolve(self, gs: GameState, source: GameCard, target: GameCard = None):
        gs.cast(source)


class Pump(Resolver):
    def __init__(self, power_adj: int, toughness_adj: int, eot: bool = False):
        self.p_adj = power_adj
        self.t_adj = toughness_adj
        self.eot = eot

    def resolve(self, gs, s: GameCard, target: Optional[GameCard] = None):
        if not target:
            raise ValueError(f'{s.props.name} needs a target')
        target.modifiers.items.append(PTMod(s=s, p_adj=self.p_adj, t_adj=self.t_adj,
                                            expires='EOT' if self.eot else None))


class CreateTokenCreature(Resolver):
    """Looks-up token slug in GameState's 'tokens' dict; creates GameCard with .is_token = True; adds to board"""
    def __init__(self, slug: str):
        self.slug = slug

    def resolve(self, gs: GameState, source: GameCard, target=None):
        from models.game_card.game_card import GameCard
        from models.zone import Zone
        card = gs.tokens.get(self.slug)
        if not card:
            raise ValueError(f'No token found for {self.slug}')
        game_card = GameCard(card, source.owner_id, is_token=True)
        game_card.zone = Zone.BATTLEFIELD
        game_card.game_state = gs
        gs.boards[source.owner_id].append(game_card)


class RemoveHostAuras(Resolver):
    """Removes target's existing auras"""
    def resolve(self, gs: GameState, source: GameCard, target: GameCard = None):
        if not target:
            raise RuntimeError(f'{source.props.name} needs a target')
        for aura in list(target.auras):
            gs.event_mgr.emit(ZoneChangeEvent(aura, aura.zone, Zone.GRAVEYARD, cause='detach_aura'), self)
            gs.move_card(aura, Zone.GRAVEYARD, cause='detach_aura')
            gs.event_mgr.unregister_effects(aura)


class TapCardEffect(Resolver):
    def resolve(self, gs: GameState, source: GameCard, target: GameCard = None):
        gs.tap_card(target)


class TapCardsEffect(Resolver):
    """Accepts a list of targets and taps each"""
    def resolve(self, gs: GameState, source: GameCard, target: list[GameCard] = None):
        if not target:
            raise ValueError(f'{source.props.name} needs a list of targets')
        for t in target:
            gs.tap_card(t)


class UntapCardEffect(Resolver):
    def resolve(self, gs: GameState, source: GameCard, target: GameCard = None):
        gs.untap_card(target)


class UntapCardsEffect(Resolver):
    """Accepts a list of targets and untaps each"""
    def resolve(self, gs: GameState, source: GameCard, target: list[GameCard] = None):
        if not target:
            raise ValueError(f'{source.props.name} needs a list of targets')
        for t in target:
            gs.untap_card(t)


class HostStaysTapped(Resolver):
    def resolve(self, gs: GameState, source: GameCard, _: GameCard = None):
        if not source.host:
            raise RuntimeError(f"{source.props.name} needs a host at untap phase")
        if gs.turn_mgr.player_turn_idx != source.host.owner_id:
            return
        gs.action_stack.push(LeaveTapped(source.owner_id, gs, source.host), gs, False)


class StaysTapped(Resolver):
    def resolve(self, gs: GameState, source: GameCard, _: GameCard = None):
        gs.action_stack.push(LeaveTapped(source.owner_id, gs, source), gs, False)


class UntapForManaEffect(Resolver):
    def __init__(self, mana_cost: str):
        self.mana_cost = mana_cost

    def resolve(self, gs: GameState, source: GameCard, _: GameCard = None):
        gs.action_stack.push(UntapWithManaChoice(source.owner_id, gs, source, self.mana_cost))


class UntapHostForManaEffect(Resolver):
    def __init__(self, mana_cost: str):
        self.mana_cost = mana_cost

    def resolve(self, gs: GameState, source: GameCard, _: GameCard = None):
        gs.action_stack.push(UntapWithManaChoice(source.host.owner_id, gs, source, self.mana_cost))
