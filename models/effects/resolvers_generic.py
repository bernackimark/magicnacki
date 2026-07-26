from __future__ import annotations

import copy
from typing import TYPE_CHECKING, Optional, Callable, Literal

from models.actions.ability_pipeline import AbilityPipeline
from models.actions.ability_pipeline_support import AbilityAction
from models.actions.base import Action
from models.actions.draw_discard import DiscardCards
from models.actions.special import PayManaToPreventCounter
from models.actions.stack_accept_counter import CounterSpellAction
from models.actions.tap_untap import PayManaToUntapAction, LeaveTapped
from models.choice_actions_all import ChoiceAction
from models.constants import COLOR_LETTERS_W_COLORLESS, BASIC_LANDS, COLOR_LETTERS
from models.counter_tokens import CounterType, CHARGE, PLUS_ZERO_ONE, STUN
from models.effects.base import Resolver
from models.effects.listeners_mod_queries import PumpAppliesEOT, AddCreatureType, PTModEqualsManaValue
from models.events_all import StateBasedEvent, ZoneChangeEvent
from models.modifiers import RegenerationMod, TypeMod, SubTypeMod, ColorMod, KWAMod, OwnershipMod, PTMod
from models.utils import flip
from models.zone import Zone

if TYPE_CHECKING:
    from game_state import GameState
    from models.game_card.game_card import GameCard


class AddCounter(Resolver):
    """If no target is provided, the source card will receive the counter"""
    def __init__(self, counter_type: CounterType, cnt: int = 1):
        self.counter_type = counter_type
        self.cnt = cnt

    def resolve(self, gs: GameState, source: GameCard, target: Optional[GameCard] = None):
        target = source if not target else target
        target.counters.add_counter(self.counter_type, self.cnt)

class AddMana(Resolver):
    def __init__(self, color: str, cnt: int = 1):
        self.color = color
        self.cnt = cnt

        if color not in COLOR_LETTERS_W_COLORLESS:
            raise ValueError(f"Color must be one of: {COLOR_LETTERS_W_COLORLESS}")

    def resolve(self, gs: GameState, source: GameCard, target: GameCard = None):
        gs.mana_pools[source.owner_id].add_floating(self.color, self.cnt)

class AddStunCounter(Resolver):
    """Tap and add stun counter to target"""
    def __init__(self, cnt: int = 1):
        self.cnt = cnt

    def resolve(self, gs: GameState, source: GameCard, target: GameCard = None):
        if not target:
            raise ValueError(f'{source.props.name} needs a target')
        target.tap()
        target.counters.add_counter(STUN, self.cnt)

class AllWalksRemoved(Resolver):
    """Target creature loses all landwalk abilities until end of turn"""
    def resolve(self, gs, source: GameCard, target: Optional[GameCard] = None):
        for land in BASIC_LANDS:
            target.modifiers.append(KWAMod(s=source, add_or_remove='remove',
                                           kwa=f'{land.capitalize()}walk', expires='EOT'))

class BecomeCreature(Resolver):
    def __init__(self, power: int, toughness: int, sub_type: str = None, until_eot: bool = False):
        self.power = power
        self.toughness = toughness
        self.sub_type = sub_type
        self.until_eot = until_eot

    def resolve(self, gs, source: GameCard, target: GameCard = None):
        if not target:
            raise RuntimeError(f'{source.props.name} needs a target')
        target.modifiers.append(TypeMod(s=source, add_or_remove='add', card_type='Creature',
                                        expires='EOT' if self.until_eot else None))
        if self.sub_type:
            target.modifiers.append(SubTypeMod(s=source, add_or_remove='add', card_sub_type=self.sub_type,
                                               expires='EOT' if self.until_eot else None))

class BecomeCreaturePTEqualsManaValue(Resolver):
    def resolve(self, gs: GameState, source: GameCard, target: Optional[GameCard | int | Action] = None) -> None:
        if not target:
            raise ValueError(f'{source.props.name} needs a target')
        add_creature_mod_query = AddCreatureType(target)
        pt_mod_query = PTModEqualsManaValue(target)
        gs.event_mgr.register(add_creature_mod_query, source)
        gs.event_mgr.register(pt_mod_query, source)

class Bounce(Resolver):
    def resolve(self, gs: GameState, source: GameCard, target: Optional[GameCard] = None):
        if not target:
            raise ValueError(f'{source.props.name} needs a target')
        gs.pile_mgr.bounce(target)

class CounterSpell(Resolver):
    """This can be used by all counter spells, not just the card named 'Counterspell'"""
    def resolve(self, gs: GameState, source: GameCard, target: Optional[GameCard | int | AbilityAction] = None) -> None:
        if not isinstance(target, AbilityAction):
            raise TypeError(f'{source.props.name} needs an Action for a target')
        gs.action_stack.remove(target)
        gs.pile_mgr.move_card(target.pipeline.source, Zone.GRAVEYARD, cause='fizzled', emit_zone_event=False)

class CounterSpellUnlessManaPaid(Resolver):
    def __init__(self, mana_cost: str):
        self.mana_cost = mana_cost

    def resolve(self, gs: GameState, source: GameCard, target: Optional[GameCard | int | Action] = None) -> None:
        if not isinstance(target, AbilityPipeline):
            raise ValueError(f"{source.props.name} needs a spell target")
        p_id = target.player_idx
        if not gs.mana_pools[p_id].can_pay(self.mana_cost):
            gs.action_stack.remove(target)
            gs.pile_mgr.move_card(target.source, Zone.GRAVEYARD, cause='fizzled', emit_zone_event=False)
            return
        options = [PayManaToPreventCounter(p_id, gs, target, self.mana_cost), CounterSpellAction(p_id, gs, target)]
        gs.pending_choice = ChoiceAction(options)

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
        gs.pile_mgr.boards[source.owner_id].append(game_card)
        gs.event_mgr.register_card(game_card)

class DeclareAColor(Resolver):
    """Choose a color (ex: when this card ETB, chose a color that can be referenced later)"""
    def resolve(self, gs: GameState, source: GameCard, target: Optional[GameCard] = None) -> None:
        from models.actions.special import StoreColorOnCard
        options = [StoreColorOnCard(source.owner_id, gs, source, color) for color in COLOR_LETTERS]
        gs.pending_choice = ChoiceAction(options)

class DealDamage(Resolver):
    def __init__(self, amt: int = None):  # None is permitted due to the possibility of variable X
        self.amt = amt

    def resolve(self, gs: GameState, source: GameCard, target: GameCard | int = None, variable_amt: int = None):
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

class Destroy(Resolver):
    def __init__(self, allow_regen: bool = True):
        self.allow_regen = allow_regen

    def resolve(self, gs: GameState, source: GameCard, target: Optional[GameCard] = None):
        gs.pile_mgr.destroy(target, allow_regeneration=self.allow_regen)


class DestroyAll(Resolver):
    def __init__(self, card_filter_func: Callable[[GameState, GameCard], list[GameCard]], allow_regen: bool = True):
        self.card_filter_func = card_filter_func
        self.allow_regen = allow_regen

    def resolve(self, gs: GameState, s: GameCard, t: Optional[GameCard] = None):
        for c in self.card_filter_func(gs, s):
            gs.pile_mgr.destroy(c, allow_regeneration=self.allow_regen)

class Discard(Resolver):
    def resolve(self, gs: GameState, source: GameCard, target: int = None):
        if not target:
            raise ValueError(f'{source.props.name} needs a target')
        options = [DiscardCards(target, gs, c) for c in gs.pile_mgr.hands[target]]
        gs.pending_choice = ChoiceAction(options)

class DrawCards(Resolver):
    def __init__(self, card_cnt: int = 1):
        self.card_cnt = card_cnt

    def resolve(self, gs: GameState, source: GameCard, target: Optional[int] = None):
        if target is None:
            return
        gs.pile_mgr.draw(target, self.card_cnt)

class EmptyResolver(Resolver):
    """Used by auras that have complex Listeners but no resolver"""
    def resolve(self, gs: GameState, source: GameCard, target: Optional[GameCard | int | Action] = None) -> None:
        pass

class ExileAllCreatures(Resolver):
    def resolve(self, gs: GameState, source: GameCard, target: Optional[GameCard] = None):
        for c in gs.card_filter.in_play().creatures().result():
            gs.pile_mgr.exile(c)

class GainLife(Resolver):
    def __init__(self, amt: int = 1):
        self.amt = amt

    def resolve(self, gs: GameState, source: GameCard, target: int = None):
        if not target:
            raise RuntimeError(f'{source.props.name} needs a target')
        gs.score_mgr.increment_life(target, self.amt, source, gs)

class GraveyardToExile(Resolver):
    def resolve(self, gs: GameState, source: GameCard, target: GameCard = None):
        if not target:
            raise RuntimeError(f'{source.props.name} needs a target')
        gs.pile_mgr.exile(target)

class GraveyardToExileInItsEntirety(Resolver):
    """Moves all cards from target player's graveyard to that same player's exile"""
    def resolve(self, gs: GameState, source: GameCard, target: int = None):
        if target is None:
            raise RuntimeError(f'{source.props.name} needs a target')
        gy = gs.pile_mgr.graveyards[target][:]
        for card in gy:
            gs.pile_mgr.exile(card)

class HandToBoard(Resolver):
    def resolve(self, gs: GameState, source: GameCard, target: GameCard = None):
        gs.pile_mgr.cast(target)

class KWAModEffect(Resolver):
    def __init__(self, add_or_remove: Literal['add', 'remove'], kwa: str, eot: bool = False):
        self.add_or_remove = add_or_remove
        self.kwa = kwa
        self.eot = eot

    def resolve(self, gs, s: GameCard, target: Optional[GameCard] = None):
        target.modifiers.append(KWAMod(s=s, add_or_remove=self.add_or_remove, kwa=self.kwa,
                                       expires='EOT' if self.eot else None))

class ManaBatteriesAddMana(Resolver):
    def __init__(self, color: str):
        self.color = color

    def resolve(self, gs: GameState, source: GameCard, target=None):
        x = source.extras.get('x', 0)  # read X chosen when activating
        source.counters.remove_counter(CHARGE, x)
        gs.mana_pools[source.owner_id].add_floating(self.color, 1 + x)

class Pump(Resolver):
    def __init__(self, power_adj: int, toughness_adj: int, eot: bool = False):
        self.p_adj = power_adj
        self.t_adj = toughness_adj
        self.eot = eot

    def resolve(self, gs, s: GameCard, target: Optional[GameCard] = None):
        if not target:
            raise ValueError(f'{s.props.name} needs a target')
        target.modifiers.append(PTMod(s=s, p_adj=self.p_adj, t_adj=self.t_adj, expires='EOT' if self.eot else None))

class Reanimate(Resolver):
    def resolve(self, gs: GameState, source: GameCard, target: GameCard = None):
        if not target:
            raise RuntimeError(f'{source.props.name} needs a target')
        gs.pile_mgr.reanimate(target)

class Regenerate(Resolver):
    def resolve(self, gs: GameState, source: GameCard, target: GameCard = None):
        if not target:
            raise ValueError(f'{source.props.name} needs a target')
        target.modifiers.append(RegenerationMod(s=source, expires='EOT'))

class RemoveCounter(Resolver):
    def __init__(self, counter_type: CounterType):
        self.counter_type = counter_type

    def resolve(self, gs: GameState, source: GameCard, target: Optional[GameCard | int | Action] = None) -> None:
        if not target:
            raise ValueError(f'{source.props.name} needs a target')
        target.counters.remove_counter(self.counter_type)

class RemoveFromCombat(Resolver):
    def resolve(self, gs: GameState, source: GameCard, target: Optional[GameCard] = None):
        if target is None:
            raise ValueError(f'{source.props.name} needs a target')
        gs.combat_mgr.remove_from_combat(target)

class RemoveHostAuras(Resolver):
    """Removes target's existing auras"""
    def resolve(self, gs: GameState, source: GameCard, target: GameCard = None):
        if not target:
            raise RuntimeError(f'{source.props.name} needs a target')
        for aura in list(target.auras):
            gs.event_mgr.emit(ZoneChangeEvent(aura, aura.zone, Zone.GRAVEYARD, cause='detach_aura'))
            gs.pile_mgr.move_card(aura, Zone.GRAVEYARD, cause='detach_aura')
            gs.event_mgr.unregister_effects(aura)

class Reveal(Resolver):
    def resolve(self, gs: GameState, source: GameCard, target: GameCard = None) -> None:
        if not target:
            raise ValueError(f'{source.props.name} needs a target')
        gs.add_presentation_request(flip(target.owner_id), 'view_card', {'cards': [target]})

class RevealHands(Resolver):
    def resolve(self, gs: GameState, source: GameCard, target: int | list[int] = None) -> None:
        if isinstance(target, int):
            target = [target]
        elif target is None:
            target = [0, 1]
        for t in target:
            for c in gs.pile_mgr.hands[t]:
                c.reveal()

class RevealLibrary(Resolver):
    def __init__(self, viewer_id: int | None = None, top_x: int | None = None):
        self.viewer_id = viewer_id
        self.top_x = top_x

    def resolve(self, gs: GameState, source: GameCard, target=None):
        if self.viewer_id is None:
            self.viewer_id = source.owner_id
        cards = gs.pile_mgr.libraries[source.owner_id] if not self.top_x else gs.pile_mgr.libraries[source.owner_id][:self.top_x]
        gs.add_presentation_request(self.viewer_id, 'view_library', {'cards': cards})

class RevealTopLibraryCard(Resolver):
    """Reveal top card of each library; if library_id is not provided, reveal for all libraries"""
    def __init__(self, library_id: int = None):
        self.library_id = library_id

    def resolve(self, gs: GameState, source: GameCard, target=None):
        libraries = (0, 1) if self.library_id is None else (self.library_id, )
        for p_id in libraries:
            if gs.pile_mgr.libraries[p_id]:
                gs.pile_mgr.libraries[p_id][0].reveal()

class SacAll(Resolver):
    def __init__(self, card_filter_func: Callable[[GameState, GameCard], list[GameCard]]):
        self.card_filter_func = card_filter_func

    def resolve(self, gs: GameState, s: GameCard, t: Optional[GameCard] = None):
        for c in self.card_filter_func(gs, s):
            gs.pile_mgr.destroy(c, allow_regeneration=False)

class SetColor(Resolver):
    def __init__(self, color: str, expires: str | None = None):
        self.color = color
        self.expires = expires

    def resolve(self, gs: GameState, source: GameCard, target: GameCard = None):
        if target is None:
            raise ValueError(f'{source.props.name} needs a target')
        target.modifiers.append(ColorMod(s=source, expires=self.expires, new_colors=self.color))

class Steal(Resolver):
    def __init__(self, new_zone: Zone = None):
        self.new_zone = new_zone or Zone.BATTLEFIELD

    def resolve(self, gs: GameState, source: GameCard, target: Optional[GameCard] = None):
        """If the zone is going from battlefield to battlefield, then move_card() will not trigger"""
        if not target:
            raise RuntimeError(f'{source.props.name} needs a target')
        original_owner_id = int(target.owner_id)
        target.modifiers.append(OwnershipMod(s=source, new_owner_id=source.owner_id))
        target.turn_entered_for_owner = gs.turn_mgr
        if target.zone == Zone.BATTLEFIELD:
            gs.pile_mgr.boards[original_owner_id].remove(target)
            gs.pile_mgr.boards[source.owner_id].append(target)
        else:
            gs.pile_mgr.move_card(target, self.new_zone, cause='steal')
        gs.event_mgr.emit(StateBasedEvent())

class TapCardEffect(Resolver):
    def resolve(self, gs: GameState, source: GameCard, target: GameCard = None):
        target.tap()

class TapCardsEffect(Resolver):
    """Accepts a list of targets and taps each"""
    def resolve(self, gs: GameState, source: GameCard, target: list[GameCard] = None):
        if not target:
            raise ValueError(f'{source.props.name} needs a list of targets')
        for t in target:
            t.tap()

class UntapCardEffect(Resolver):
    def resolve(self, gs: GameState, source: GameCard, target: GameCard = None):
        target.untap()

class UntapCardsEffect(Resolver):
    """Accepts a list of targets and untaps each"""
    def resolve(self, gs: GameState, source: GameCard, target: list[GameCard] = None):
        if not target:
            raise ValueError(f'{source.props.name} needs a list of targets')
        for t in target:
            t.untap()

class UntapForManaEffect(Resolver):
    def __init__(self, mana_cost: str):
        self.mana_cost = mana_cost

    def resolve(self, gs: GameState, s: GameCard, t: GameCard = None):
        if t is None:
            t = s
        options = [PayManaToUntapAction(s.owner_id, gs, s, t, self.mana_cost), LeaveTapped(s.owner_id, gs, s)]
        gs.pending_choice = ChoiceAction(options)

class XZeroOneCountersByManaValue(Resolver):
    """Put X +0/+1 counters on target creature, where X is that creature's mana value"""
    def resolve(self, gs: GameState, source: GameCard, target: GameCard = None):
        if not target:
            raise RuntimeError(f'{source.props.name} needs a target')
        target.counters.add_counter(PLUS_ZERO_ONE, target.props.mana_value)
