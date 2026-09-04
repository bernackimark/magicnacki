from __future__ import annotations
from typing import TYPE_CHECKING, Callable, Literal

from models.action_stack import StackItemType
from models.actions.stack_accept_counter import CounterSpellAction
from models.choice_actions_all import ChoiceAction
from models.choice_options import CO, pay_mana_to_prevent_counter
from models.constants import COLOR_LETTERS_W_COLORLESS, BASIC_LANDS, COLOR_LETTERS, Zone
from models.game_card.counter_tokens import CounterType, CHARGE, PLUS_ZERO_ONE, STUN
from models.effects.base import Resolver, RTarget, ResContext
from models.effects.listeners_mod_queries import AddCreatureType, PTModEqualsManaValue, OwnershipModQuery
from models.events_all import StateBasedEvent, ZoneChangeEvent, ModQueryEvent
from models.game_card.modifiers import RegenerationMod, TypeMod, SubTypeMod, ColorMod, KWAMod, PTMod, BasePTMod
from models.utils import flip

if TYPE_CHECKING:
    from game_state import GameState
    from models.game_card.game_card import GameCard
    from models.effects.base import RTarget, ResContext

class Do(Resolver):
    """Accepts mulptiple resolvers & executes them in succession; the target & context will be the same for all"""
    def __init__(self, *resolvers: Resolver):
        self.resolvers = resolvers

    def resolve(self, gs, source, t=None, context=None):
        for resolver in self.resolvers:
            resolver.resolve(gs, source, t, context)


class AddCounter(Resolver):
    """If no target is provided, the source card will receive the counter"""
    def __init__(self, counter_type: CounterType, cnt: int = 1):
        self.counter_type = counter_type
        self.cnt = cnt

    def resolve(self, gs: GameState, source: GameCard, t: RTarget = None, context: ResContext = None) -> None:
        target = source if not t else t
        target.counters.add_counter(self.counter_type, self.cnt)

class AddCounterPerCreatureDeath(Resolver):
    """Adds a counter per each creature death that turn"""
    def __init__(self, counter_type: CounterType):
        self.counter_type = counter_type

    def resolve(self, gs: GameState, source: GameCard, t: RTarget = None, context: ResContext = None) -> None:
        if death_cnt := len(gs.turn_mgr.cards_that_died) > 0:
            source.counters.add_counter(self.counter_type, death_cnt)

class AddCounterToHost(Resolver):
    def __init__(self, counter_type: CounterType, cnt: int = 1):
        self.counter_type = counter_type
        self.cnt = cnt

    def resolve(self, gs: GameState, source: GameCard, t: RTarget = None, context: ResContext = None) -> None:
        source.host.counters.add_counter(self.counter_type, self.cnt)

class AddMana(Resolver):
    """The source's owner gets the mana"""
    def __init__(self, color: str, cnt: int = 1):
        self.color = color
        self.cnt = cnt

        if color not in COLOR_LETTERS_W_COLORLESS:
            raise ValueError(f"Color must be one of: {COLOR_LETTERS_W_COLORLESS}")

    def resolve(self, gs: GameState, source: GameCard, t: RTarget = None, context: ResContext = None) -> None:
        gs.mana_pools[source.owner_id].add_floating(self.color, self.cnt)

class AddPoisonCounter(Resolver):
    def __init__(self, cnt: int = 1):
        self.cnt = cnt

    def resolve(self, gs: GameState, source: GameCard, t: RTarget = None, context: ResContext = None) -> None:
        gs.score_mgr.add_poison_counter(flip(source.owner_id), self.cnt)

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
        gs.action_stack.remove(t)
        gs.pile_mgr.move_card(t.source, Zone.GRAVEYARD, cause='fizzled', emit_zone_event=False)

class CounterSpellUnlessManaPaid(Resolver):
    def __init__(self, mana_cost: str = None, mana_cost_eq_to_mv: bool = False):
        self.mana_cost = mana_cost
        self.mana_cost_eq_to_mv = mana_cost_eq_to_mv

    def resolve(self, gs: GameState, source: GameCard, t: RTarget = None, context: ResContext = None) -> None:
        if not isinstance(t, StackItemType):
            raise ValueError(f"{source.props.name} needs a spell target")
        target_spell = t
        p_id = target_spell.player_idx
        if not gs.mana_pools[p_id].can_pay(self.mana_cost):
            gs.action_stack.remove(target_spell)
            gs.pile_mgr.move_card(target_spell.source, Zone.GRAVEYARD, cause='fizzled', emit_zone_event=False)
            return
        options = [CO(f'Pay {{{self.mana_cost}}} to prevent counterspell by {source}',
                      lambda: pay_mana_to_prevent_counter(gs, p_id, self.mana_cost, target_spell)),
                   CounterSpellAction(p_id, gs, target_spell)]
        gs.choice_mgr.queue(ChoiceAction(options, on_complete=lambda: gs.action_stack.pop()))

class CreateTokenCreature(Resolver):
    """Looks-up token slug in GameState's 'tokens' dict; creates GameCard with .is_token = True; adds to board"""
    def __init__(self, slug: str, cnt: int = 1):
        self.slug = slug
        self.cnt = cnt

    def resolve(self, gs: GameState, source: GameCard, t: RTarget = None, context: ResContext = None) -> None:
        from models.game_card.game_card import GameCard
        from models.constants import Zone
        for _ in range(self.cnt):
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
        options = [CO(f"Declare {source}'s color as {color}", lambda: self.etb_action(source, color))
                   for color in COLOR_LETTERS]
        gs.choice_mgr.queue(ChoiceAction(options))

    @staticmethod
    def etb_action(s: GameCard, color: str):
        s.extras['color_declaration'] = color
        # TODO: make presentation request, as this selection is public

class DealDamage(Resolver):
    """Supply a static amount in the initializer or declare x via AbilityPipeline -> ResContext -> .resolve();
    target func can be provided in initializer or supplied as an RTarget in .resolve()"""
    def __init__(self, amt: int = None, to: Callable | None = None):
        self.amt = amt
        self.to = to

    def resolve(self, gs: GameState, source: GameCard, t: RTarget = None, context: ResContext = None) -> None:
        amt = context.x_value if context and context.x_value is not None else self.amt
        target = self.to(gs, source) if self.to is not None else t
        if isinstance(target, list):
            for tar in target:
                gs.apply_damage(source, amt, tar)
            return
        gs.apply_damage(source, amt, target)

class Destroy(Resolver):
    """The target can be provided via 'who' [a func(gs, s)] or via .resolve()"""
    def __init__(self, who: Callable | None = None, allow_regen: bool = True):
        self.who = who
        self.allow_regen = allow_regen

    def resolve(self, gs: GameState, source: GameCard, t: RTarget = None, context: ResContext = None) -> None:
        target = self.who(gs, source) if self.who is not None else t
        gs.pile_mgr.destroy(target, allow_regeneration=self.allow_regen)

class DestroyAll(Resolver):
    def __init__(self, card_filter_func: Callable[[GameState, GameCard], list[GameCard]], allow_regen: bool = True):
        self.card_filter_func = card_filter_func
        self.allow_regen = allow_regen

    def resolve(self, gs: GameState, source: GameCard, t: RTarget = None, context: ResContext = None) -> None:
        for c in self.card_filter_func(gs, source):
            gs.pile_mgr.destroy(c, allow_regeneration=self.allow_regen)

class DestroyHostCombatants(Resolver):
    def __init__(self, allow_regen: bool = True, filter_func: Callable[[GameState, GameCard], list[GameCard]] = None):
        self.allow_regen = allow_regen
        self.filter_func = filter_func

    def resolve(self, gs: GameState, source: GameCard, t: RTarget = None, context: ResContext = None) -> None:
        all_combatants = gs.combat_mgr.get_combatants_against(source.host)
        if self.filter_func:
            filtered_cards = self.filter_func(gs, source)
            for c in all_combatants:
                if c in filtered_cards:
                    gs.pile_mgr.destroy(c, allow_regeneration=self.allow_regen)
        else:
            for c in all_combatants:
                gs.pile_mgr.destroy(c, allow_regeneration=self.allow_regen)

class DestroySelfCombatants(Resolver):
    def __init__(self, allow_regen: bool = True, filter_func: Callable[[GameState, GameCard], list[GameCard]] = None):
        self.allow_regen = allow_regen
        self.filter_func = filter_func

    def resolve(self, gs: GameState, source: GameCard, t: RTarget = None, context: ResContext = None) -> None:
        all_combatants = gs.combat_mgr.get_combatants_against(source)
        if self.filter_func:
            filtered_cards = self.filter_func(gs, source)
            for c in all_combatants:
                if c in filtered_cards:
                    gs.pile_mgr.destroy(c, allow_regeneration=self.allow_regen)
        else:
            for c in all_combatants:
                gs.pile_mgr.destroy(c, allow_regeneration=self.allow_regen)

class Discard(Resolver):
    @Resolver.target_required
    def resolve(self, gs: GameState, source: GameCard, t: RTarget = None, context: ResContext = None):
        """t is the player id"""
        options = [CO(f'Discard {c}', lambda: gs.pile_mgr.discard(c)) for c in gs.hands[t]]
        gs.choice_mgr.queue(ChoiceAction(options))

class DiscardAtRandom(Resolver):
    """Target can be received via .resolve() else use opp_is_discarder from init"""
    def __init__(self, cnt: int = 1, opp_is_discarder: bool = True):
        self.cnt = cnt
        self.opp_is_discarder = opp_is_discarder

    def resolve(self, gs: GameState, source: GameCard, t: RTarget = None, context: ResContext = None) -> None:
        if t is not None:
            p_id = t
        else:
            p_id = flip(source.owner_id) if self.opp_is_discarder else source.owner_id
        cards = gs.pile_mgr.hands[p_id]
        if not cards:
            return
        discard_cnt = min(self.cnt, len(cards))
        for _ in range(discard_cnt):
            random_card: GameCard = gs.randomize_event(p_id, cards)
            gs.pile_mgr.discard(random_card, source)

class DiscardHand(Resolver):
    """Discards entire hand; if a target is not provided it is assumed to be the opponent"""
    def resolve(self, gs: GameState, source: GameCard, t: RTarget = None, context: ResContext = None) -> None:
        target = t if t is not None else flip(source.owner_id)
        for card in gs.hands[target]:
            gs.pile_mgr.discard(card, source)

class DrawCardsActivePlayer(Resolver):
    def __init__(self, card_cnt: int = 1):
        self.card_cnt = card_cnt

    def resolve(self, gs: GameState, source: GameCard, t: RTarget = None, context: ResContext = None):
        gs.pile_mgr.draw(gs.turn_mgr.player_turn_idx, self.card_cnt)

class DrawCards(Resolver):
    def __init__(self, card_cnt: int = 1):
        self.card_cnt = card_cnt

    def resolve(self, gs: GameState, source: GameCard, t: RTarget = None, context: ResContext = None):
        t = source.owner_id if t is None else t
        gs.pile_mgr.draw(t, self.card_cnt)

class EmptyResolver(Resolver):
    """Used by auras that have complex Listeners but no resolver"""
    def resolve(self, gs: GameState, source: GameCard, t: RTarget = None, context: ResContext = None) -> None:
        pass

class ExchangeLifeTotals(Resolver):
    def resolve(self, gs: GameState, source: GameCard, t: RTarget = None, context: ResContext = None):
        your_life = gs.life[source.owner_id]
        opp_life = gs.life[flip(source.owner_id)]
        gs.life[source.owner_id], gs.life[flip(source.owner_id)] = opp_life, your_life

class ExileAllCreatures(Resolver):
    def resolve(self, gs: GameState, source: GameCard, t: RTarget = None, context: ResContext = None) -> None:
        for c in gs.card_filter.in_play().creatures().result():
            gs.pile_mgr.exile(c)

class ExileSelf(Resolver):
    def resolve(self, gs: GameState, source: GameCard, t: RTarget = None, context: ResContext = None) -> None:
        gs.pile_mgr.exile(source)

class GainLife(Resolver):
    """Amount can be sent through the initializer or via context.x_value;
    Target can be supplied via .resolve(t) else default to source.owner_id"""
    def __init__(self, amt: int = 1):
        self.amt = amt

    def resolve(self, gs: GameState, source: GameCard, t: RTarget = None, context: ResContext = None):
        t = source.owner_id if t is None else t
        amt = context.x_value or self.amt
        gs.score_mgr.increment_life(t, amt, source, gs)

class GainLifeTargetMV(Resolver):
    @Resolver.target_required
    def resolve(self, gs: GameState, source: GameCard, t: RTarget = None, context: ResContext = None):
        gs.score_mgr.increment_life(source.owner_id, t.props.mana_value, source, gs)

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
        t = source if t is None else t
        t.modifiers.append(KWAMod(s=source, add_or_remove=self.add_or_remove, item=self.kwa,
                                  expires='EOT' if self.eot else None))

class ManaBatteriesAddMana(Resolver):
    def __init__(self, color: str):
        self.color = color

    def resolve(self, gs: GameState, source: GameCard, t: RTarget = None, context: ResContext = None) -> None:
        x = context.x_value
        source.counters.remove_counter(CHARGE, x)
        gs.mana_pools[source.owner_id].add_floating(self.color, 1 + x)

class MayPayMana(Resolver):
    def __init__(self, mana_cost: str, effect: Resolver):
        self.mana_cost = mana_cost
        self.effect = effect

    def resolve(self, gs, source, t=None, context=None):
        options = [CO(f'Pay {{{self.mana_cost}}}', lambda: self._pay_and_resolve(gs, source, t, context))]
        gs.choice_mgr.queue(ChoiceAction(options, may=True))

    def _pay_and_resolve(self, gs: GameState, source: GameCard, t: RTarget, context: ResContext):
        gs.mana_pools[source.owner_id].pay(self.mana_cost)
        self.effect.resolve(gs, source, t, context)

class Mill(Resolver):
    def __init__(self, cnt: int = 1):
        self.cnt = cnt

    @Resolver.target_required
    def resolve(self, gs: GameState, source: GameCard, t: RTarget = None, context: ResContext = None) -> None:
        gs.pile_mgr.mill(t, self.cnt)

class PayManaOr(Resolver):
    def __init__(self, mana_cost: str, effect: Resolver):
        self.mana_cost = mana_cost
        self.effect = effect

    def resolve(self, gs: GameState, source: GameCard, t=None, context=None):
        if gs.mana_pools[source.owner_id].can_pay(self.mana_cost):
            options = [CO(f'Pay {{{self.mana_cost}}}', lambda: self._pay(gs, source)),
                       CO(f'{self.effect.__repr__()}', lambda: self.effect.resolve(gs, source, t, context))]
            gs.choice_mgr.queue(ChoiceAction(options))
        else:
            self.effect.resolve(gs, source, t, context)

    def _pay(self, gs: GameState, source: GameCard):
        gs.mana_pools[source.owner_id].pay(self.mana_cost)

class Pump(Resolver):
    def __init__(self, power_adj: int, toughness_adj: int, eot: bool = False):
        self.p_adj = power_adj
        self.t_adj = toughness_adj
        self.eot = eot

    @Resolver.target_required
    def resolve(self, gs: GameState, source: GameCard, t: RTarget = None, context: ResContext = None):
        t.modifiers.append(PTMod(s=source, p_adj=self.p_adj, t_adj=self.t_adj, expires='EOT' if self.eot else None))

class PumpSelf(Resolver):
    """Doesn't require a target; using it to ease into the fluent/builder pattern; could later be replaced by:
    a generic Pump that specifies .to() method"""
    def __init__(self, power_adj: int, toughness_adj: int, eot: bool = False):
        self.p_adj = power_adj
        self.t_adj = toughness_adj
        self.eot = eot

    def resolve(self, gs: GameState, source: GameCard, t: RTarget = None, context: ResContext = None):
        s = source
        s.modifiers.append(PTMod(s=s, p_adj=self.p_adj, t_adj=self.t_adj, expires='EOT' if self.eot else None))

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

    def resolve(self, gs: GameState, source: GameCard, t: RTarget = None, context: ResContext = None):
        t = source if t is None else t
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
    def __init__(self, p_func: Callable | None = None):
        self.p_func = p_func

    def resolve(self, gs: GameState, source: GameCard, t: RTarget = None, context: ResContext = None) -> None:
        if self.p_func:
            targets = [self.p_func(gs, source)]
        elif isinstance(t, int):
            targets = [t]
        else:
            targets = [0, 1]
        for tar in targets:
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
            gs.pile_mgr.sacrifice(c)

class SacSelf(Resolver):
    def resolve(self, gs: GameState, source: GameCard, t: RTarget = None, context: ResContext = None) -> None:
        gs.pile_mgr.sacrifice(source)

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

class TapCards(Resolver):
    """Targets can be received through a func(gs, s) at init, or via a list of GameCard via .resolve()"""
    def __init__(self, t_func: Callable | None = None):
        self.t_func = t_func

    def resolve(self, gs: GameState, source: GameCard, t: RTarget = None, context: ResContext = None):
        targets = self.t_func(gs, source) if self.t_func else t
        for target in targets:
            target.tap()

class UntapCardEffect(Resolver):
    def resolve(self, gs: GameState, source: GameCard, t: RTarget = None, context: ResContext = None) -> None:
        t.untap()

class UntapCards(Resolver):
    """Targets can be received through a func(gs, s) at init, or via a list of GameCard via .resolve()"""
    def __init__(self, t_func: Callable | None = None):
        self.t_func = t_func

    def resolve(self, gs: GameState, source: GameCard, t: RTarget = None, context: ResContext = None):
        targets = self.t_func(gs, source) if self.t_func else t
        for target in targets:
            target.untap()

class XZeroOneCountersByManaValue(Resolver):
    """Put X +0/+1 counters on target creature, where X is that creature's mana value"""
    @Resolver.target_required
    def resolve(self, gs: GameState, source: GameCard, t: RTarget = None, context: ResContext = None):
        t.counters.add_counter(PLUS_ZERO_ONE, t.props.mana_value)
