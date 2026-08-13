from __future__ import annotations
from typing import TYPE_CHECKING, Callable, Literal

from models.action_stack import StackItemType
from models.actions.draw_discard import DiscardCards
from models.actions.special import PayManaToPreventCounter
from models.actions.stack_accept_counter import CounterSpellAction
from models.choice_actions_all import ChoiceAction
from models.constants import COLOR_LETTERS_W_COLORLESS, BASIC_LANDS, COLOR_LETTERS
from models.counter_tokens import CounterType, CHARGE, PLUS_ZERO_ONE, STUN
from models.effects.base import Resolver
from models.effects.listeners_mod_queries import AddCreatureType, PTModEqualsManaValue, OwnershipModQuery
from models.events_all import StateBasedEvent, ZoneChangeEvent
from models.modifiers import RegenerationMod, TypeMod, SubTypeMod, ColorMod, KWAMod, PTMod, BasePTMod
from models.utils import flip
from models.zone import Zone

if TYPE_CHECKING:
    from game_state import GameState
    from models.game_card.game_card import GameCard
    from models.effects.base import RTarget, ResContext


class AddCounter(Resolver):
    """If no target is provided, the source card will receive the counter"""
    def __init__(self, counter_type: CounterType, cnt: int = 1):
        self.counter_type = counter_type
        self.cnt = cnt

    def resolve(self, gs: GameState, source: GameCard, t: RTarget = None, context: ResContext = None) -> None:
        target = source if not t else t
        target.counters.add_counter(self.counter_type, self.cnt)

class AddMana(Resolver):
    def __init__(self, color: str, cnt: int = 1):
        self.color = color
        self.cnt = cnt

        if color not in COLOR_LETTERS_W_COLORLESS:
            raise ValueError(f"Color must be one of: {COLOR_LETTERS_W_COLORLESS}")

    def resolve(self, gs: GameState, source: GameCard, t: RTarget = None, context: ResContext = None) -> None:
        gs.mana_pools[source.owner_id].add_floating(self.color, self.cnt)

class AddStunCounter(Resolver):
    """Tap and add stun counter to target"""
    def __init__(self, cnt: int = 1):
        self.cnt = cnt

    @Resolver.target_required
    def resolve(self, gs: GameState, source: GameCard, t: RTarget = None, context: ResContext = None):
        t.tap()
        t.counters.add_counter(STUN, self.cnt)

class AllWalksRemoved(Resolver):
    """Target creature loses all landwalk abilities until end of turn"""
    def resolve(self, gs: GameState, source: GameCard, t: RTarget = None, context: ResContext = None) -> None:
        for land in BASIC_LANDS:
            t.modifiers.append(KWAMod(s=source, add_or_remove='remove', item=f'{land.capitalize()}walk', expires='EOT'))

class BasePT(Resolver):
    def __init__(self, base_p: int = None, base_t: int = None, eot: bool = False):
        self.base_p = base_p
        self.base_t = base_t
        self.eot = eot

    @Resolver.target_required
    def resolve(self, gs: GameState, source: GameCard, t: RTarget = None, context: ResContext = None):
        base_p = self.base_p if self.base_p is not None else t.base_pt[0]
        base_t = self.base_t if self.base_t is not None else t.base_pt[1]
        t.modifiers.append(BasePTMod(s=source, base_p=base_p, base_t=base_t, expires='EOT' if self.eot else None))

class BecomeCreature(Resolver):
    def __init__(self, power: int, toughness: int, sub_type: str = None, until_eot: bool = False):
        self.power = power
        self.toughness = toughness
        self.sub_type = sub_type
        self.until_eot = until_eot

    @Resolver.target_required
    def resolve(self, gs: GameState, source: GameCard, t: RTarget = None, context: ResContext = None):
        t.modifiers.append(TypeMod(s=source, add_or_remove='add', item='Creature',
                                   expires='EOT' if self.until_eot else None))
        if self.sub_type:
            t.modifiers.append(SubTypeMod(s=source, item=self.sub_type, expires='EOT' if self.until_eot else None))

class BecomeCreaturePTEqualsManaValue(Resolver):
    @Resolver.target_required
    def resolve(self, gs: GameState, source: GameCard, t: RTarget = None, context: ResContext = None):
        add_creature_mod_query = AddCreatureType(t)
        pt_mod_query = PTModEqualsManaValue(t)
        gs.event_mgr.register(add_creature_mod_query, source)
        gs.event_mgr.register(pt_mod_query, source)

class Bounce(Resolver):
    @Resolver.target_required
    def resolve(self, gs: GameState, source: GameCard, t: RTarget = None, context: ResContext = None):
        gs.pile_mgr.bounce(t)

class CounterSpell(Resolver):
    """This can be used by all counter spells, not just the card named 'Counterspell'"""
    def resolve(self, gs: GameState, source: GameCard, t: RTarget = None, context: ResContext = None) -> None:
        if not isinstance(t, StackItemType):
            raise TypeError(f'{source.props.name} needs a StackItemType for a target')
        print('T', t)
        gs.action_stack.remove(t)
        gs.pile_mgr.move_card(t.source, Zone.GRAVEYARD, cause='fizzled', emit_zone_event=False)

class CounterSpellUnlessManaPaid(Resolver):
    def __init__(self, mana_cost: str = None, mana_cost_eq_to_mv: bool = False):
        self.mana_cost = mana_cost
        self.mana_cost_eq_to_mv = mana_cost_eq_to_mv

    def resolve(self, gs: GameState, source: GameCard, t: RTarget = None, context: ResContext = None) -> None:
        if not isinstance(t, StackItemType):
            raise ValueError(f"{source.props.name} needs a spell target")
        p_id = t.player_idx
        if not gs.mana_pools[p_id].can_pay(t.total_mana_cost):
            gs.action_stack.remove(t)
            gs.pile_mgr.move_card(t.source, Zone.GRAVEYARD, cause='fizzled', emit_zone_event=False)
            return
        options = [PayManaToPreventCounter(p_id, gs, t, t.total_mana_cost), CounterSpellAction(p_id, gs, t)]
        gs.queue_choice(ChoiceAction(options))

class CreateTokenCreature(Resolver):
    """Looks-up token slug in GameState's 'tokens' dict; creates GameCard with .is_token = True; adds to board"""
    def __init__(self, slug: str):
        self.slug = slug

    def resolve(self, gs: GameState, source: GameCard, t: RTarget = None, context: ResContext = None) -> None:
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
    def resolve(self, gs: GameState, source: GameCard, t: RTarget = None, context: ResContext = None) -> None:
        from models.actions.special import StoreColorOnCard
        options = [StoreColorOnCard(source.owner_id, gs, source, color) for color in COLOR_LETTERS]
        gs.queue_choice(ChoiceAction(options))

class DealDamage(Resolver):
    """Supply a static amount in the initializer or declare x via AbilityPipeline -> ResContext -> .resolve()"""
    def __init__(self, amt: int = None):
        self.amt = amt

    def resolve(self, gs: GameState, source: GameCard, t: RTarget = None, context: ResContext = None) -> None:
        amt = context.x_value if context and context.x_value is not None else self.amt
        gs.apply_damage(source, amt, t)

class DealOneDamageToTargetList(Resolver):
    def resolve(self, gs: GameState, source: GameCard, t: RTarget = None, context: ResContext = None) -> None:
        for target in t:
            gs.apply_damage(source, 1, target)

class DealDamageToAllCreaturesAndPlayers(Resolver):
    def __init__(self, amt: int):
        self.amt = amt

    def resolve(self, gs: GameState, source: GameCard, t: RTarget = None, context: ResContext = None) -> None:
        [gs.apply_damage(source, self.amt, p_id, is_combat=False) for p_id in (0, 1)]
        [gs.apply_damage(source, self.amt, creature) for creature in gs.card_filter.in_play().creatures().result()]

class DealDamageToTargetAndSelf(Resolver):
    def __init__(self, amt_to_target: int, amt_to_source_card: int):
        self.amt_to_target = amt_to_target
        self.amt_to_source_card = amt_to_source_card

    @Resolver.target_required
    def resolve(self, gs: GameState, source: GameCard, t: RTarget = None, context: ResContext = None):
        gs.apply_damage(source, self.amt_to_target, t)
        gs.apply_damage(source, self.amt_to_source_card, source)


class DealDamageToTargetAndYou(Resolver):
    def __init__(self, amt_to_target: int, amt_to_you: int):
        self.amt_to_target = amt_to_target
        self.amt_to_you = amt_to_you

    @Resolver.target_required
    def resolve(self, gs: GameState, source: GameCard, t: RTarget = None, context: ResContext = None):
        gs.apply_damage(source, self.amt_to_target, t)
        gs.apply_damage(source, self.amt_to_you, source.owner_id)

class Destroy(Resolver):
    def __init__(self, allow_regen: bool = True):
        self.allow_regen = allow_regen

    def resolve(self, gs: GameState, source: GameCard, t: RTarget = None, context: ResContext = None) -> None:
        gs.pile_mgr.destroy(t, allow_regeneration=self.allow_regen)

class DestroyAll(Resolver):
    def __init__(self, card_filter_func: Callable[[GameState, GameCard], list[GameCard]], allow_regen: bool = True):
        self.card_filter_func = card_filter_func
        self.allow_regen = allow_regen

    def resolve(self, gs: GameState, source: GameCard, t: RTarget = None, context: ResContext = None) -> None:
        for c in self.card_filter_func(gs, source):
            gs.pile_mgr.destroy(c, allow_regeneration=self.allow_regen)

class Discard(Resolver):
    @Resolver.target_required
    def resolve(self, gs: GameState, source: GameCard, t: RTarget = None, context: ResContext = None):
        options = [DiscardCards(t, gs, c) for c in gs.pile_mgr.hands[t]]
        gs.queue_choice(ChoiceAction(options))

class DrawCards(Resolver):
    def __init__(self, card_cnt: int = 1):
        self.card_cnt = card_cnt

    @Resolver.target_required
    def resolve(self, gs: GameState, source: GameCard, t: RTarget = None, context: ResContext = None):
        gs.pile_mgr.draw(t, self.card_cnt)

class EmptyResolver(Resolver):
    """Used by auras that have complex Listeners but no resolver"""
    def resolve(self, gs: GameState, source: GameCard, t: RTarget = None, context: ResContext = None) -> None:
        pass

class ExileAllCreatures(Resolver):
    def resolve(self, gs: GameState, source: GameCard, t: RTarget = None, context: ResContext = None) -> None:
        for c in gs.card_filter.in_play().creatures().result():
            gs.pile_mgr.exile(c)

class GainLife(Resolver):
    def __init__(self, amt: int = 1):
        self.amt = amt

    @Resolver.target_required
    def resolve(self, gs: GameState, source: GameCard, t: RTarget = None, context: ResContext = None):
        gs.score_mgr.increment_life(t, self.amt, source, gs)

class GraveyardToExile(Resolver):
    @Resolver.target_required
    def resolve(self, gs: GameState, source: GameCard, t: RTarget = None, context: ResContext = None):
        gs.pile_mgr.exile(t)

class GraveyardToExileInItsEntirety(Resolver):
    """Moves all cards from target player's graveyard to that same player's exile"""
    @Resolver.target_required
    def resolve(self, gs: GameState, source: GameCard, t: RTarget = None, context: ResContext = None):
        gy = gs.pile_mgr.graveyards[t][:]
        for card in gy:
            gs.pile_mgr.exile(card)

class HandToBoard(Resolver):
    def resolve(self, gs: GameState, source: GameCard, t: RTarget = None, context: ResContext = None) -> None:
        gs.pile_mgr.cast(t)

class KWAModEffect(Resolver):
    def __init__(self, add_or_remove: Literal['add', 'remove'], kwa: str, eot: bool = False):
        self.add_or_remove = add_or_remove
        self.kwa = kwa
        self.eot = eot

    def resolve(self, gs: GameState, source: GameCard, t: RTarget = None, context: ResContext = None) -> None:
        t.modifiers.append(KWAMod(s=source, add_or_remove=self.add_or_remove, item=self.kwa,
                                  expires='EOT' if self.eot else None))

class ManaBatteriesAddMana(Resolver):
    def __init__(self, color: str):
        self.color = color

    def resolve(self, gs: GameState, source: GameCard, t: RTarget = None, context: ResContext = None) -> None:
        x = context.x_value
        source.counters.remove_counter(CHARGE, x)
        gs.mana_pools[source.owner_id].add_floating(self.color, 1 + x)

class Pump(Resolver):
    def __init__(self, power_adj: int, toughness_adj: int, eot: bool = False):
        self.p_adj = power_adj
        self.t_adj = toughness_adj
        self.eot = eot

    @Resolver.target_required
    def resolve(self, gs: GameState, source: GameCard, t: RTarget = None, context: ResContext = None):
        t.modifiers.append(PTMod(s=source, p_adj=self.p_adj, t_adj=self.t_adj, expires='EOT' if self.eot else None))

class Reanimate(Resolver):
    @Resolver.target_required
    def resolve(self, gs: GameState, source: GameCard, t: RTarget = None, context: ResContext = None):
        gs.pile_mgr.reanimate(t)

class Regenerate(Resolver):
    @Resolver.target_required
    def resolve(self, gs: GameState, source: GameCard, t: RTarget = None, context: ResContext = None):
        t.modifiers.append(RegenerationMod(s=source, expires='EOT'))

class RemoveCounter(Resolver):
    def __init__(self, counter_type: CounterType):
        self.counter_type = counter_type

    @Resolver.target_required
    def resolve(self, gs: GameState, source: GameCard, t: RTarget = None, context: ResContext = None):
        t.counters.remove_counter(self.counter_type)

class RemoveFromCombat(Resolver):
    @Resolver.target_required
    def resolve(self, gs: GameState, source: GameCard, t: RTarget = None, context: ResContext = None):
        gs.combat_mgr.remove_from_combat(t)

class RemoveHostAuras(Resolver):
    """Removes target's existing auras"""
    @Resolver.target_required
    def resolve(self, gs: GameState, source: GameCard, t: RTarget = None, context: ResContext = None):
        for aura in list(t.auras):
            gs.event_mgr.emit(ZoneChangeEvent(aura, aura.zone, Zone.GRAVEYARD, cause='detach_aura'))
            gs.pile_mgr.move_card(aura, Zone.GRAVEYARD, cause='detach_aura')
            gs.event_mgr.unregister_effects(aura)

class Reveal(Resolver):
    @Resolver.target_required
    def resolve(self, gs: GameState, source: GameCard, t: RTarget = None, context: ResContext = None):
        gs.add_presentation_request(flip(t.owner_id), 'view_card', {'cards': [t]})

class RevealHands(Resolver):
    def resolve(self, gs: GameState, source: GameCard, t: RTarget = None, context: ResContext = None) -> None:
        target = [t] if isinstance(t, int) else [0, 1] if t is None else t
        for tar in target:
            for c in gs.pile_mgr.hands[tar]:
                c.reveal()

class RevealLibrary(Resolver):
    def __init__(self, viewer_id: int | None = None, top_x: int | None = None):
        self.viewer_id = viewer_id
        self.top_x = top_x

    def resolve(self, gs: GameState, source: GameCard, t: RTarget = None, context: ResContext = None) -> None:
        if self.viewer_id is None:
            self.viewer_id = source.owner_id
        if self.top_x:
            cards = gs.pile_mgr.libraries[source.owner_id][:self.top_x]
        else:
            cards = gs.pile_mgr.libraries[source.owner_id]
        gs.add_presentation_request(self.viewer_id, 'view_library', {'cards': cards})

class RevealTopLibraryCard(Resolver):
    """Reveal top card of each library; if library_id is not provided, reveal for all libraries"""
    def __init__(self, library_id: int = None):
        self.library_id = library_id

    def resolve(self, gs: GameState, source: GameCard, t: RTarget = None, context: ResContext = None) -> None:
        libraries = (0, 1) if self.library_id is None else (self.library_id, )
        for p_id in libraries:
            if gs.pile_mgr.libraries[p_id]:
                gs.pile_mgr.libraries[p_id][0].reveal()

class SacAll(Resolver):
    def __init__(self, card_filter_func: Callable[[GameState, GameCard], list[GameCard]]):
        self.card_filter_func = card_filter_func

    def resolve(self, gs: GameState, source: GameCard, t: RTarget = None, context: ResContext = None) -> None:
        for c in self.card_filter_func(gs, source):
            gs.pile_mgr.destroy(c, allow_regeneration=False)

class SetColor(Resolver):
    def __init__(self, color: str, expires: str | None = None):
        self.color = color
        self.expires = expires

    @Resolver.target_required
    def resolve(self, gs: GameState, source: GameCard, t: RTarget = None, context: ResContext = None):
        t.modifiers.append(ColorMod(s=source, expires=self.expires, add_or_remove='add', item=self.color))

class Steal(Resolver):
    """Registers an OwnershipModQuery.  Default behavior is to transfer the card across boards upon stealer's LTB"""
    def __init__(self, new_zone: Zone = None, return_on_ltb: bool = True, return_on_untap: bool = False):
        self.new_zone = new_zone or Zone.BATTLEFIELD
        self.return_on_source_ltb = return_on_ltb
        self.return_on_source_untap = return_on_untap

    @Resolver.target_required
    def resolve(self, gs: GameState, source: GameCard, t: RTarget = None, context: ResContext = None):
        """If the zone is going from battlefield to battlefield, then move_card() will not trigger"""
        from models.effects.listeners_generic import ReturnToOwnerOnLTB, ReturnToOwnerOnUntap
        original_owner_id = int(t.owner_id)
        gs.event_mgr.register(OwnershipModQuery(t), source)

        t.turn_entered_for_owner = gs.turn_mgr.turn_number
        if t.zone == Zone.BATTLEFIELD:
            gs.pile_mgr.boards[original_owner_id].remove(t)
            gs.pile_mgr.boards[source.owner_id].append(t)
        else:
            gs.pile_mgr.move_card(t, self.new_zone, cause='steal')

        if self.return_on_source_ltb:
            gs.event_mgr.register(ReturnToOwnerOnLTB(), source)

        if self.return_on_source_untap:
            gs.event_mgr.register(ReturnToOwnerOnUntap(), source)

        gs.event_mgr.emit(StateBasedEvent())

class TapCardEffect(Resolver):
    def resolve(self, gs: GameState, source: GameCard, t: RTarget = None, context: ResContext = None) -> None:
        t.tap()

class TapCardsEffect(Resolver):
    """Accepts a list of targets and taps each"""
    @Resolver.target_required
    def resolve(self, gs: GameState, source: GameCard, t: RTarget = None, context: ResContext = None):
        for target in t:
            target.tap()

class UntapCardEffect(Resolver):
    def resolve(self, gs: GameState, source: GameCard, t: RTarget = None, context: ResContext = None) -> None:
        t.untap()

class UntapCardsEffect(Resolver):
    """Accepts a list of targets and untaps each"""
    @Resolver.target_required
    def resolve(self, gs: GameState, source: GameCard, t: RTarget = None, context: ResContext = None):
        for target in t:
            target.untap()

class XZeroOneCountersByManaValue(Resolver):
    """Put X +0/+1 counters on target creature, where X is that creature's mana value"""
    @Resolver.target_required
    def resolve(self, gs: GameState, source: GameCard, t: RTarget = None, context: ResContext = None):
        t.counters.add_counter(PLUS_ZERO_ONE, t.props.mana_value)
