from __future__ import annotations
import random
from dataclasses import dataclass, field
from itertools import combinations, permutations
from typing import TYPE_CHECKING, Literal, Union

from models.actions.ability_pipeline import AbilityPipeline
from models.actions.combat import AssignBlocker
from models.choice_actions_all import ChoiceAction
from models.choice_options import CO
from models.constants import KW, Zone
from models.effects.listeners_mod_queries import OwnershipModQuery
from models.events_all import StateBasedEvent
from models.game_card.counter_tokens import MINUS_ZERO_ONE, STUN, PLUS_ZERO_ONE
from models.effects.base import Resolver
from models.effects.listeners_generic import PreventNextDamageBy, PreventNextDamageTo, \
    PreventAllDamageToEOT, DestroyAtEndStep, DestroyAtEndStepIfItDidntAttack
from models.game_card.modifiers import PTMod, KWAMod
from models.presentation_request import PresentationReqType
from models.systems.mana import ManaCost
from models.systems.phase import Phase
from models.utils import flip

if TYPE_CHECKING:
    from game_state import GameState
    from models.systems.combat import Combat
    from models.game_card.game_card import GameCard
    from models.effects.base import RTarget, ResContext


class FallingStar(Resolver):
    """Select an opponent's creature. If a di roll is 1-5, deal 3 damage to it"""
    @Resolver.target_required
    def resolve(self, gs: GameState, source: GameCard, t: RTarget = None, context: ResContext = None):
        result: int = gs.randomize_event(source.owner_id, [1, 2, 3, 4, 5, 6])
        print(f'The roll is a: {result}')
        if result <= 5:
            gs.apply_damage(source, 3, t)

class FalseOrders(Resolver):
    """... Remove target blocker from a combat. You may have it block in a different legal combat."""
    @Resolver.target_required
    def resolve(self, gs: GameState, source: GameCard, t: RTarget = None, context: ResContext = None):
        gs.combat_mgr.remove_from_combat(t)
        other_combats = [com for com in gs.combat_mgr.combats if t not in com.blockers]
        if other_combats:
            options = [CO(f'Reassign {source} to block {com.attacker}',
                          lambda: self._assign_blocker(t, com)) for com in other_combats]
            gs.choice_mgr.queue(ChoiceAction(options, may=True))

    @staticmethod
    def _assign_blocker(target: GameCard, com: Combat):
        com.add_blocker(target)

class Feint(Resolver):
    """Tap all creatures blocking target attacking creature.
        Prevent all combat damage that would be dealt this turn by that creature and each creature blocking it."""
    def resolve(self, gs: GameState, source: GameCard, t: RTarget = None, context: ResContext = None) -> None:
        """target = the attacker"""
        the_combat = [com for com in gs.combat_mgr.combats if com.attacker == t]
        if not the_combat:
            return
        the_combat = the_combat[0]
        gs.event_mgr.register(PreventNextDamageBy(source, combat_only=True))
        for b in the_combat.blockers:
            gs.event_mgr.register(PreventNextDamageTo(b, combat_only=True))
            b.tap()

class FeldonsCane(Resolver):
    """{T}, Exile this artifact: Shuffle your graveyard into your library."""
    def resolve(self, gs: GameState, source: GameCard, t: RTarget = None, context: ResContext = None) -> None:
        gy = gs.pile_mgr.graveyards[source.owner_id]
        lib = gs.pile_mgr.libraries[source.owner_id]
        for c in gy[:]:
            gs.pile_mgr.move_card(c, Zone.LIBRARY, cause='feldons-cane')
        random.shuffle(lib)

class FellwarStone(Resolver):
    """{T}: Add one mana of any color that a land an opponent controls could produce"""
    def resolve(self, gs: GameState, source: GameCard, t: RTarget = None, context: ResContext = None) -> None:
        produceable = {mana_produced for c in gs.card_filter.on_player_board(flip(source.owner_id)).result()
                       for mana_produced in c.mana_produced}
        options = [CO(f"Add {{{color}}}", lambda: gs.mana_pools[source.owner_id].add_floating(color))
                   for color in produceable]
        if options:
            gs.choice_mgr.queue(ChoiceAction(options))

class FireAndBrimstone(Resolver):
    """Fire and Brimstone deals 4 damage to opponent if they attacked this turn and 4 damage to you"""
    def resolve(self, gs: GameState, source: GameCard, t: RTarget = None, context: ResContext = None) -> None:
        opp = flip(source.owner_id)
        if gs.card_filter.on_player_board(opp).attackers().result():
            gs.apply_damage(source, 4, opp)
            gs.apply_damage(source, 4, source.owner_id)

class GlyphOfDelusion(Resolver):
    """Put X glyph counters on target creature that target Wall blocked this turn, X = power of that blocked creature"""
    @Resolver.target_required
    def resolve(self, gs: GameState, source: GameCard, t: RTarget = None, context: ResContext = None):
        com = gs.combat_mgr.get_combat(t)
        com.declared_attacker.counters.add_counter(STUN, com.declared_attacker.power)

class GlyphOfReincarnation(Resolver):
    """Cast this spell only after combat. Destroy attacker blocked by target Wall this turn. It can't be regenerated.
    You put a different creature from the attacker's graveyard onto the battlefield under its owner's control."""
    @Resolver.target_required
    def resolve(self, gs: GameState, source: GameCard, t: RTarget = None, context: ResContext = None):
        com = gs.combat_mgr.get_combat(t)
        attacker = com.declared_attacker
        attacker_gy_creatures = list(gs.card_filter.in_player_graveyard(attacker.owner_id).creatures().result())
        gs.pile_mgr.destroy(attacker, allow_regeneration=False)
        if not attacker_gy_creatures:
            return
        elif len(attacker_gy_creatures) == 1:
            gs.pile_mgr.reanimate(attacker_gy_creatures[0])
        else:
            options = [CO(f'Reanimate {c}', lambda: gs.pile_mgr.reanimate(c)) for c in attacker_gy_creatures]
            gs.choice_mgr.queue(ChoiceAction(options))

class GreatDefender(Resolver):
    """Target creature gets +0/+X until end of turn, where X is its mana value."""
    @Resolver.target_required
    def resolve(self, gs: GameState, source: GameCard, t: RTarget = None, context: ResContext = None):
        t.modifiers.append(PTMod(s=source, t_adj=t.props.mana_value, expires='EOT'))

class GuardianAngel(Resolver):
    """Prevent the next X damage that would be dealt to any target (permanent or player) this turn.
    Until EOT, you may pay {1} at any time to prevent the next 1 damage that would be dealt to that target this turn."""
    @Resolver.target_required
    def resolve(self, gs: GameState, source: GameCard, t: RTarget = None, context: ResContext = None):
        from models.effects.listeners_generic import PreventNextDamageTo
        x = context.x_value
        gs.event_mgr.register(PreventNextDamageTo(x, protected=t), source)
        # TODO: the above only handles the FIRST next damage; need to handle subsequent damages
        #  PreventNextDamageTo needs an .on_expire callback

class HowlFromBeyond(Resolver):
    """Target creature gets +X/+0 until end of turn"""
    @Resolver.target_required
    def resolve(self, gs: GameState, source: GameCard, t: RTarget = None, context: ResContext = None):
        x = context.x_value
        t.modifiers.append(PTMod(s=source, p_adj=x, expires='EOT'))

class HurkylsRecall(Resolver):
    """Return all artifacts target player owns to their hand"""
    @Resolver.target_required
    def resolve(self, gs: GameState, source: GameCard, t: RTarget = None, context: ResContext = None):
        for artifact in gs.card_filter.on_player_board(t).artifacts().result():
            gs.pile_mgr.bounce(artifact)

class IfhBiffEfreet(Resolver):
    """{G}: IBE deals 1 damage to each creature with flying and each player. Any player may activate this ability."""
    def resolve(self, gs: GameState, source: GameCard, t: RTarget = None, context: ResContext = None) -> None:
        for i in range(2):
            gs.apply_damage(source, 1, i)
        for flier in list(gs.card_filter.in_play().creatures().has(KW.FLYING).result()):
            gs.apply_damage(source, 1, flier)

class Inquisition(Resolver):
    """Target player reveals their hand. Deal damage to that player = number of white cards in their hand."""
    @Resolver.target_required
    def resolve(self, gs: GameState, source: GameCard, t: RTarget = None, context: ResContext = None):
        opp_cards = gs.pile_mgr.hands[flip(source.owner_id)]
        for c in opp_cards:
            c.reveal()
        if white_cnt := len([c for c in opp_cards if c.is_white]):
            gs.apply_damage(source, white_cnt, flip(source.owner_id))

class JovialEvil(Resolver):
    """Deals X damage to target opponent, where X is twice the number of white creatures that player controls"""
    def resolve(self, gs: GameState, source: GameCard, t: RTarget = None, context: ResContext = None) -> None:
        opp_white_creature_cnt = len(gs.card_filter.on_player_board(t).creatures().result())
        gs.apply_damage(source, opp_white_creature_cnt * 2, t)

class Juxtapose(Resolver):
    """You & opp exchange control of the creature you each control with the greatest MV.
    Then exchange control of artifacts the same way.
    (If 2+ cards of that type are tied for greatest, their controller chooses one of them.)
    MTG ruling: 'If one player doesn't control of the types, the other type exchange is still valid'"""

    FRESH_SELECTIONS = ['unprocessed', 'unprocessed']

    class _State:
        FRESH_SELECTIONS = ['unprocessed', 'unprocessed']

        def __init__(self, gs: GameState, source: GameCard):
            self.gs = gs
            self.source = source
            self.type_: Literal['Creature', 'Artifact'] = 'Creature'
            self.selections: list[GameCard | list[GameCard] | str | None] = self.FRESH_SELECTIONS
            self.is_done = False

        def handle(self):
            print('---')
            from models.game_card.game_card import GameCard
            if self.is_done:
                print('I am done and completely exiting the flow; the rest of this method should NOT execute')
                # self.gs.event_mgr.emit(StateBasedEvent())
                return
            if self.selections == self.FRESH_SELECTIONS:
                for p_id in (0, 1):
                    self.selections[p_id] = self.get_highest_mv_cards(p_id)
            print('Juxtapose state', self.type_, self.selections)
            if not all(self.selections):
                print('One of the values is None', self.selections)
                self.advance()  # one player doesn't have a matching card, do not swap, advance
                self.handle()
                return
            elif isinstance(self.selections[0], GameCard) and isinstance(self.selections[1], GameCard):
                print('Swapping')
                self.swap()  # each player naturally has one matching card or has selected down to a single card
                self.advance()
                self.handle()
                return
            print('self.selections', self.selections)
            for p_id, selection in enumerate(self.selections):
                if isinstance(selection, list):
                    print('Getting user selection')
                    self.get_selection(p_id, selection)  # a player must downselect to one card
                    return

        def advance(self):
            if self.type_ == 'Creature':
                self.type_ = 'Artifact'
                self.reset_selections()
                return
            else:
                print('Setting is_done = True')
                self.is_done = True
                return

        def get_selection(self, p_id: int, cards: list[GameCard]):
            if p_id != self.gs.action_on_idx:
                self.gs.action_on_idx = flip(self.gs.action_on_idx)
            options = [CO(f'Swap {c}', self._make_selection_callback(c)) for c in cards]
            self.gs.choice_mgr.queue(ChoiceAction(options))

        def _make_selection_callback(self, card: GameCard):
            return lambda: self.select_card(card)

        def reset_selections(self):
            self.selections = self.FRESH_SELECTIONS

        def select_card(self, c: GameCard):
            print('Selected', c)
            p_idx = c.owner_id
            self.selections[p_idx] = c
            self.gs.choice_mgr.complete()
            self.handle()

        def swap(self):
            """ZoneChangeEvent isn't called but OwnershipModQuery does raise an event"""
            for p_id, c in enumerate(self.selections):
                original_owner_id = int(c.owner_id)
                new_owner = flip(c.owner_id)
                self.gs.event_mgr.register(OwnershipModQuery(c, new_controller_id=new_owner), self.source)
                c.turn_entered_for_owner = self.gs.turn_mgr.turn_number
                self.gs.pile_mgr.boards[original_owner_id].remove(c)
                self.gs.pile_mgr.boards[new_owner].append(c)
                print('Swapped', c, 'to', new_owner)

        def get_highest_mv_cards(self, p_id) -> GameCard | list[GameCard] | None:
            cards = [c for c in self.gs.boards[p_id] if self.type_ in c.card_types]
            if not cards:
                return None
            max_mv_cards = [c for c in cards if c.props.mana_value == max(c.props.mana_value for c in cards)]
            return max_mv_cards[0] if len(max_mv_cards) == 1 else max_mv_cards

    def resolve(self, gs: GameState, source: GameCard, t: RTarget = None, context: ResContext = None) -> None:
        print('Entering Juxtapose state')
        state = self._State(gs, source)
        state.handle()

class KryShield(Resolver):
    """Prevent all damage that would be dealt this turn by target creature you control.
    That creature gets +0/+X until end of turn, where X is its mana value"""
    def resolve(self, gs: GameState, source: GameCard, t: RTarget = None, context: ResContext = None) -> None:
        gs.event_mgr.register(PreventNextDamageBy(t), source)
        t.modifiers.append(PTMod(s=source, t_adj=t.props.mana_value, expires='EOT'))

class LandsEdge(Resolver):
    """Discard a card: If the discarded card was a land, LE deals 2 damage to target player.
    Any player may activate this ability."""
    def resolve(self, gs: GameState, source: GameCard, t: RTarget = None, context: ResContext = None) -> None:
        discarded = context.cost_results[0].paid_cards[0]
        if discarded.is_land:
            gs.apply_damage(source, 2, t)

class LesserWerewolf(Resolver):
    """If this creature's power is >= 1, it gets -1/-0 until EOT & put a -0/-1 counter on
    target creature blocking/blocked by this creature. Activate only during the declare blockers step."""
    def resolve(self, gs: GameState, source: GameCard, t: RTarget = None, context: ResContext = None) -> None:
        if source.power < 1:
            return
        source.modifiers.append(PTMod(s=source, p_adj=-1, expires='EOT'))
        t.counters.add_counter(MINUS_ZERO_ONE)

class LibraryOfAlexandria(Resolver):
    """{T}: Draw a card. Activate only if you have exactly seven cards in hand."""
    def can_activate(self, gs: GameState, source: GameCard):
        return len(gs.pile_mgr.hands[source.owner_id]) == 7

    def resolve(self, gs: GameState, source: GameCard, t: RTarget = None, context: ResContext = None) -> None:
        gs.pile_mgr.draw(source.owner_id)

class LifeChisel(Resolver):
    """Sac a creature: You gain life equal to the sacrificed creature's toughness. Activate only during your upkeep."""
    def resolve(self, gs: GameState, source: GameCard, t: RTarget = None, context: ResContext = None) -> None:
        amt = context.cost_results[0].paid_cards[0].toughness
        gs.score_mgr.increment_life(source.owner_id, amt, source)

class ManaClash(Resolver):
    """You and target opponent each flip a coin. Mana Clash deals 1 damage to each player whose coin comes up tails.
    Repeat this process until both players' coins come up heads on the same flip."""
    def resolve(self, gs: GameState, source: GameCard, t: RTarget = None, context: ResContext = None) -> None:
        caster_id, opp_id = source.owner_id, flip(source.owner_id)
        seq = ['heads', 'tails']
        while True:
            caster_result = gs.randomize_event(caster_id, seq)
            opp_result = gs.randomize_event(opp_id, seq)
            print(f"Caster's result is {caster_result}; opponent's result is {opp_result}")
            if caster_result == 'heads' and opp_result == 'heads':
                print('Since both flips were heads, there are no more flips')
                break
            if caster_result == 'tails':
                gs.apply_damage(source, 1, caster_id)
            if opp_result == 'tails':
                gs.apply_damage(source, 1, opp_id)

class ManaDrain(Resolver):
    """Counter target spell. At your next main phase, add {C} = spell's mana value."""
    def resolve(self, gs: GameState, source: GameCard, t: RTarget = None, context: ResContext = None) -> None:
        from models.effects.listeners_misc import ManaDrainMainPhase
        if not isinstance(t, AbilityPipeline):
            raise TypeError(f'{source.props.name} needs to target an Action')
        gs.action_stack.remove(t)
        gs.pile_mgr.move_card(t.source, Zone.GRAVEYARD, cause='countered', emit_zone_event=False)
        gs.event_mgr.register(ManaDrainMainPhase(t.source.props.mana_value), source)

class ManaShort(Resolver):
    @Resolver.target_required
    def resolve(self, gs: GameState, source: GameCard, t: RTarget = None, context: ResContext = None):
        """target = player_id whose lands should be tapped"""
        player_lands = gs.card_filter.on_player_board(t).lands().result()
        for land in player_lands:
            land.tap()
        print(f"Mana Short taps all lands belonging to player {t}.")

class MartyrsCry(Resolver):
    """Sorcery WW [] Exile all white creatures. For each creature exiled this way, its controller draws a card."""
    def resolve(self, gs: GameState, source: GameCard, t: RTarget = None, context: ResContext = None) -> None:
        for white_creature in gs.card_filter.in_play().white().creatures().result():
            gs.pile_mgr.exile(white_creature)
            gs.pile_mgr.draw(white_creature.owner_id)

class MazeOfIth(Resolver):
    def resolve(self, gs: GameState, source: GameCard, t: RTarget = None, context: ResContext = None) -> None:
        the_combat = gs.combat_mgr.get_combat(t)
        if not the_combat:
            return
        gs.event_mgr.register(PreventNextDamageBy(the_combat.attacker, combat_only=True))
        for b in the_combat.blockers:
            gs.event_mgr.register(PreventNextDamageTo(b, combat_only=True))
        t.untap()

class MindTwist(Resolver):
    """Target player discards X cards at random"""
    def resolve(self, gs: GameState, source: GameCard, t: RTarget = None, context: ResContext = None) -> None:
        from models.effects.resolvers_generic import DiscardAtRandom
        x = context.x_value
        DiscardAtRandom(x).resolve(gs, source, t)

class MoldDemon(Resolver):
    """When this creature enters, sacrifice this creature unless you sacrifice two Swamps"""
    def resolve(self, gs: GameState, source: GameCard, t: RTarget = None, context: ResContext = None) -> None:
        your_swamps = gs.card_filter.on_player_board(source.owner_id).swamps().result()
        if len(your_swamps) < 2:
            gs.pile_mgr.destroy(source, False)
        combos = list(combinations(your_swamps, 2))
        options = [CO(f"Sac 2 swamps", lambda: self.sac_two_swamps(gs, combo)) for combo in combos] + \
                  [CO(f'Sac {source}', lambda: gs.pile_mgr.sacrifice(source))]
        gs.choice_mgr.queue(ChoiceAction(options))

    @staticmethod
    def sac_two_swamps(gs: GameState, two_swamps: list[GameCard]):
        for swamp in two_swamps:
            gs.pile_mgr.sacrifice(swamp)

class NamelessRace(Resolver):
    """Upon ETB, pay any amount of life (max = # of white nontoken permanents your opponents control +
    the total number of white cards in their graveyards). NR's PT are each = life paid as it entered."""
    def resolve(self, gs: GameState, source: GameCard, t: RTarget = None, context: ResContext = None) -> None:
        opp = flip(source.owner_id)
        max_amt = (len(gs.card_filter.on_player_board(opp).non_token().white().permanents().result()) +
                   len(gs.card_filter.in_player_graveyard(opp).white().result()))
        options = [CO(f'Pay {amt} life to make {source} a {amt}/{amt} creature',
                      lambda: self.etb_action(gs, source, amt)) for amt in range(max_amt + 1)]
        gs.choice_mgr.queue(ChoiceAction(options))

    @staticmethod
    def etb_action(gs: GameState, s: GameCard, amt: int):
        s.base_pt = (amt, amt)
        gs.score_mgr.decrement_life(s.owner_id, amt, s)

class NaturalSelection(Resolver):
    """Look at the top 3 cards of target player's library, put them back in any order. You may shuffle."""
    @Resolver.target_required
    def resolve(self, gs: GameState, source: GameCard, t: RTarget = None, context: ResContext = None):
        lib = gs.pile_mgr.libraries[t]
        top_3_cards = lib[:3]
        gs.add_presentation_request(source.owner_id, PresentationReqType.VIEW_LIBRARY, {'cards': top_3_cards})
        options = [CO(f"Order top of library top -> bottom: {', '.join(list(perm))}",
                      lambda: self.order_lib(lib, list(perm))) for perm in permutations(top_3_cards, r=3)] + \
                  [CO(f"Shuffle", lambda: random.shuffle(lib))]
        gs.choice_mgr.queue(ChoiceAction(options))

    @staticmethod
    def order_lib(lib: list[GameCard], ordered_cards: list[GameCard]):
        del lib[:len(ordered_cards)]
        for c in ordered_cards[::-1]:
            lib.insert(0, c)

class Necropolis(Resolver):
    """Exile a creature card from your graveyard: Put X +0/+1 counters on this creature, X = the exiled card's MV"""
    def resolve(self, gs: GameState, source: GameCard, t: RTarget = None, context: ResContext = None) -> None:
        mv = ManaCost(context.cost_results[0].paid_cards[0].casting_cost).mana_value
        source.counters.add_counter(PLUS_ZERO_ONE, mv)

class NettlingImp(Resolver):
    """Give target non-Wall creature w/o summoning sickness Goad until EOT.
    Destroy it at end step if it didn't attack this turn ...
    Activate only during an opponent's turn, before attackers are declared."""
    def can_activate(self, gs: GameState, source: GameCard) -> bool:
        return source.owner_id != gs.player_turn_idx and gs.phase_mgr.phase < Phase.DECLARE_ATTACKERS

    @Resolver.target_required
    def resolve(self, gs: GameState, source: GameCard, t: RTarget = None, context: ResContext = None):
        t.modifiers.append(KWAMod(item=KW.GOAD, s=source, expires='EOT'))
        gs.event_mgr.register(DestroyAtEndStepIfItDidntAttack(t), source)
