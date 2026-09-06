from __future__ import annotations
import random
from itertools import combinations
from typing import TYPE_CHECKING

from models.actions.stack_accept_counter import CounterSpellAction
from models.choice_actions_all import ChoiceAction
from models.choice_options import CO, pay_mana_to_prevent_counter, copy_card
from models.constants import BASIC_LANDS, KW, Zone
from models.game_card.counter_tokens import PLUS_ONE, HATCHLING, STUN
from models.effects.base import Resolver, RTarget, ResContext
from models.effects.listeners_generic import PreventAllDamageByEOT, DestroyAtEndStep, PreventNextDamageBy, \
    BounceAtEndStep, PreventNextDamageTo, DestroyAtEndStepIfItDidntAttack, LTBTandem
from models.effects.resolvers_generic import Reveal, CreateTokenCreature
from models.events_all import DamageResolvedEvent
from models.game_card.modifiers import KWAMod, PTMod, SubTypeMod
from models.systems.mana import ManaCost
from models.utils import flip

if TYPE_CHECKING:
    from game_state import GameState
    from models.game_card.game_card import GameCard


class PhantasmalTerrain(Resolver):
    """Enchant land As this Aura enters, choose a basic land type. Enchanted land is the chosen type."""
    def resolve(self, gs: GameState, source: GameCard, t: RTarget = None, context: ResContext = None) -> None:
        options = [CO(f"Turn {t} into a {land_type}", lambda: self.sub_type_replacement(source, t, land_type))
                   for land_type in BASIC_LANDS]
        gs.choice_mgr.queue(ChoiceAction(options))

    @staticmethod
    def sub_type_replacement(s: GameCard, target: GameCard, sub_type: str):
        sub_type = sub_type.capitalize()
        s_types = target.card_sub_types.copy()
        target.modifiers.append(SubTypeMod(s=s, item=sub_type))
        for s_type in s_types:
            target.modifiers.append(SubTypeMod(s=s, add_or_remove='remove', item=s_type))

class PowerSink(Resolver):
    """Counter target spell unless its controller pays {X}.
    If opponent doesn't, they tap all lands with mana abilities they control and lose all unspent mana."""

    def resolve(self, gs: GameState, source: GameCard, t: RTarget = None, context: ResContext = None) -> None:
        from models.action_stack import StackItemType
        if not isinstance(t, StackItemType):
            raise ValueError(f"{source.props.name} needs a spell target")
        power_sink_x = source.extras.get('x')
        if not power_sink_x:
            raise ValueError(f"Power Sink's X wasn't registered yet")
        p_id = t.player_idx
        if not gs.mana_pools[p_id].can_pay(str(power_sink_x)):
            gs.action_stack.remove(t)
            gs.pile_mgr.move_card(t.source, Zone.GRAVEYARD, cause='fizzled', emit_zone_event=False)
            return
        mana_cost = str(power_sink_x)
        options = [CO(f'Pay {{{mana_cost}}} to prevent counterspell by {source}',
                      lambda: pay_mana_to_prevent_counter(gs, p_id, mana_cost, t)),
                   CounterSpellAction(p_id, gs, t)]
        gs.choice_mgr.queue(ChoiceAction(options))

class PriestOfYawgmoth(Resolver):
    """Sac an artifact: Add an amount of {B} equal to the sacrificed creature's mana value."""
    def resolve(self, gs: GameState, source: GameCard, t: RTarget = None, context: ResContext = None) -> None:
        mana_value = ManaCost(context.cost_result.paid_cards[0].casting_cost).mana_value
        gs.mana_pools[source.owner_id].add_floating('B', mana_value)

class PrimalClay(Resolver):
    """As this creature enters, it becomes your choice of a 3/3 artifact creature, a 2/2 artifact creature with flying,
    or a 1/6 Wall artifact creature with defender in addition to its other types."""
    def resolve(self, gs: GameState, source: GameCard, t: RTarget = None, context: ResContext = None) -> None:
        s = source
        options = [CO('Cast as a 3/3', lambda: self.three_three(gs, s)),
                   CO('Cast as a 2/2 flier', lambda: self.two_two_flier(gs, s)),
                   CO('Cast as a 1/6 wall', lambda: self.one_six_wall(gs, s))]
        gs.choice_mgr.queue(ChoiceAction(options))

    @staticmethod
    def three_three(gs: GameState, s: GameCard):
        s.base_pt = (3, 3)
        gs.pile_mgr.cast(s)

    @staticmethod
    def two_two_flier(gs: GameState, s: GameCard):
        s.base_pt = (2, 2)
        kwa = list(s._base_kwa)
        kwa.append(KW.FLYING)
        s._base_kwa = kwa
        gs.pile_mgr.cast(s)

    @staticmethod
    def one_six_wall(gs: GameState, s: GameCard):
        s.base_pt = (1, 6)
        kwa = list(s._base_kwa)
        kwa.append('Defender')
        s._base_kwa = kwa
        gs.pile_mgr.cast(s)

class RagMan(Resolver):
    """Opponent reveals their hand and discards a creature card at random. Activate only during your turn."""
    @Resolver.target_required
    def resolve(self, gs: GameState, source: GameCard, t: RTarget = None, context: ResContext = None):
        opp_cards = gs.pile_mgr.hands[t]
        for c in opp_cards:
            c.reveal()
        opp_creatures = [c for c in opp_cards if c.is_creature]
        if not opp_creatures:
            return
        random_creature: GameCard = gs.randomize_event(t, opp_creatures)
        gs.pile_mgr.discard(random_creature, source)

class Rakalite(Resolver):
    """{2}: Prevent the next 1 damage that would be dealt to any target this turn.
    Return this artifact to its owner's hand at the beginning of the next end step."""
    @Resolver.target_required
    def resolve(self, gs: GameState, source: GameCard, t: RTarget = None, context: ResContext = None):
        """target is the card dealing damage"""
        gs.event_mgr.register(PreventNextDamageTo(1, protected=t), source)
        gs.event_mgr.register(BounceAtEndStep(source), source)

class RapidFire(Resolver):
    """Cast this spell only before blockers are declared. Target creature gains first strike until end of turn.
    If it doesn't have rampage, that creature gains rampage 2 until end of turn."""
    @Resolver.target_required
    def resolve(self, gs: GameState, source: GameCard, t: RTarget = None, context: ResContext = None):
        t.modifiers.append(KWAMod(s=source, item=KW.FIRST_STRIKE, expires='EOT'))
        if not t.rampage_amt:
            t.modifiers.append(KWAMod(s=source, item=KW.RAMPAGE_2, expires='EOT'))

class ReversePolarity(Resolver):
    """You gain X life, where X is twice the damage dealt to you so far this turn by artifacts"""
    def resolve(self, gs: GameState, source: GameCard, t: RTarget = None, context: ResContext = None) -> None:
        damage_by_artifacts = sum([e.amt for e in gs.event_mgr.get_events(gs.turn_mgr.turn_number)
                                   if isinstance(e, DamageResolvedEvent) and e.target == source.owner_id])
        if not damage_by_artifacts:
            return
        gs.score_mgr.increment_life(source.owner_id, 2 * damage_by_artifacts, source)

class RockHydraCast(Resolver):
    """This creature enters with X +1/+1 counters on it ..."""
    def resolve(self, gs: GameState, source: GameCard, t: RTarget = None, context: ResContext = None) -> None:
        if x := context.x_value:  # read X chosen when casting
            source.counters.add_counter(PLUS_ONE, x)

class RocketLauncher(Resolver):
    """{2}: Deal 1 damage to any target. Destroy Rocket Launcher at next end step.
    Activate only if you've controlled continuously since the beginning of your most recent turn."""
    def can_activate(self, gs: GameState, s: GameCard) -> bool:
        if not s.turn_entered_for_owner:
            return False  # turn_entered_for_owner is getting set AFTER this check
        return s.turn_entered_for_owner < gs.turn_mgr.most_recent_turn_started[s.owner_id]

    def resolve(self, gs: GameState, source: GameCard, t: RTarget = None, context: ResContext = None) -> None:
        gs.apply_damage(source, 1, t)
        gs.event_mgr.register(DestroyAtEndStep(source), source)

class SacrificeOnCast(Resolver):
    """Sac a creature: Add an amount of {B} equal to the sacrificed creature's mana value.
    Note "sacrifice" refers to the card called sacrifice, not the game action of sacrifice"""
    def resolve(self, gs: GameState, source: GameCard, t: RTarget = None, context: ResContext = None) -> None:
        mana_value = ManaCost(context.cost_result.paid_cards[0].casting_cost).mana_value
        gs.mana_pools[source.owner_id].add_floating('B', mana_value)

class SafeHaven(Resolver):
    """{2}, {T}: Exile target creature you control, storing the exiled card's ID for future reference"""
    @Resolver.target_required
    def resolve(self, gs: GameState, source: GameCard, t: RTarget = None, context: ResContext = None):
        gs.pile_mgr.exile(t)
        if source.extras.get('cards_exiled') is None:
            source.extras['cards_exiled'] = set()
        source.extras['cards_exiled'].add(t)

class ShapeshifterCast(Resolver):
    """At cast & at your upkeep, choose a number 0-7 (n). Shapeshifter's power = n, toughness = 7 - n"""
    def resolve(self, gs: GameState, source: GameCard, t: RTarget = None, context: ResContext = None) -> None:
        options = [CO(f"Set {source}'s power to {n} & toughness to {7 - n}",
                      lambda: self.variable_pt_mod(source, n)) for n in range(8)]
        # options = [VariablePTMod(source.owner_id, gs, source, source, i, 7 - i) for i in range(8)]
        gs.choice_mgr.queue(ChoiceAction(options))

    @staticmethod
    def variable_pt_mod(s: GameCard, n: int):
        p_adj = n - s.power
        t_adj = 7 - n - s.toughness
        s.modifiers.append(PTMod(s=s, p_adj=p_adj, t_adj=t_adj))

class Simulacrum(Resolver):
    """You gain life equal to the damage already dealt to you this turn. If you control a creature,
    Simulacrum deals damage to target creature you control equal to the damage dealt to you this turn."""
    def resolve(self, gs: GameState, s: GameCard, t: RTarget = None, context: ResContext = None) -> None:
        from models.events_all import DamageResolvedEvent
        damage_taken_this_turn = sum([e.amt for e in gs.event_mgr.get_events(gs.turn_mgr.turn_number)
                                      if isinstance(e, DamageResolvedEvent) and e.target == s.owner_id])
        if not damage_taken_this_turn:
            return

        gs.score_mgr.increment_life(s.owner_id, damage_taken_this_turn, s)

        your_creatures = gs.card_filter.creatures().on_player_board(s.owner_id).result()
        if your_creatures:
            options = [CO(f'{s} deals {damage_taken_this_turn} damage to {c}',
                          lambda: gs.apply_damage(s, damage_taken_this_turn, c)) for c in your_creatures]
            gs.choice_mgr.queue(ChoiceAction(options))

class Sindbad(Resolver):
    """{T}: Draw a card and reveal it. If it isn't a land, discard it."""
    def resolve(self, gs: GameState, source: GameCard, t: RTarget = None, context: ResContext = None) -> None:
        top_card = gs.pile_mgr.libraries[source.owner_id][0] if gs.pile_mgr.libraries[source.owner_id] else None
        gs.pile_mgr.draw(source.owner_id)
        Reveal().resolve(gs, source, top_card)
        if not top_card.is_land:
            gs.pile_mgr.discard(top_card, source)

class SingingTree(Resolver):
    """Target attacking creature has base power 0 until end of turn"""
    @Resolver.target_required
    def resolve(self, gs: GameState, source: GameCard, t: RTarget = None, context: ResContext = None):
        t.modifiers.append(PTMod(s=source, p_adj=-t.base_pt[0], expires='EOT'))

class SirensCall(Resolver):
    """... All non-Wall creatures the active player has controlled continuously since BOT must attack ..."""
    def resolve(self, gs: GameState, source: GameCard, t: RTarget = None, context: ResContext = None) -> None:
        non_wall_creatures = gs.card_filter.on_player_board(gs.player_turn_idx).non_wall_creatures().result()
        for creature in non_wall_creatures:
            if not creature.has_summoning_sickness:
                creature.modifiers.append(KWAMod(item=KW.GOAD, s=source, expires='EOT'))
                gs.event_mgr.register(DestroyAtEndStepIfItDidntAttack(creature), source)

class Stangg(Resolver):
    """When S ETB, create Stangg Twin, a legendary 3/4 red & green Human Warrior creature token.
    Exile that token when S LTB. Sac S when that token LTB"""
    def resolve(self, gs: GameState, source: GameCard, t: RTarget = None, context: ResContext = None) -> None:
        existing_stangg_twins = gs.card_filter.in_play().by_slug('stangg-twin').result()
        CreateTokenCreature('stangg-twin').resolve(gs, source)
        this_stangg_twin = next(c for c in gs.card_filter.in_play().by_slug('stangg-twin').result()
                                if c not in existing_stangg_twins)
        gs.event_mgr.register(LTBTandem([source, this_stangg_twin]), source)

class StormSeeker(Resolver):
    """Storm Seeker deals damage to target player equal to the number of cards in that player's hand"""
    def resolve(self, gs: GameState, source: GameCard, t: RTarget = None, context: ResContext = None) -> None:
        opp_idx = flip(source.owner_id)
        gs.apply_damage(source, len(gs.pile_mgr.hands[opp_idx]), opp_idx)

class Subdue(Resolver):
    """Prevent all combat damage that would be dealt by target creature this turn.
    That creature gets +0/+X until end of turn, where X is its mana value."""
    def resolve(self, gs: GameState, source: GameCard, t: RTarget = None, context: ResContext = None) -> None:
        gs.event_mgr.register(PreventNextDamageBy(t, combat_only=True), source)
        t.modifiers.append(PTMod(s=source, p_adj=0, t_adj=t.props.mana_value))

class SwordsToPlowshares(Resolver):
    @Resolver.target_required
    def resolve(self, gs: GameState, source: GameCard, t: RTarget = None, context: ResContext = None):
        gs.pile_mgr.exile(t)
        gs.score_mgr.increment_life(t.owner_id, t.power, source)

class TawnossCoffin(Resolver):
    """... Exile target creature & all its auras. Note the number & kind of counters that were on that creature ..."""
    @Resolver.target_required
    def resolve(self, gs: GameState, source: GameCard, t: RTarget = None, context: ResContext = None):
        from copy import deepcopy
        my_deep_copy = deepcopy(t)
        source.extras['exiled_card'] = t
        source.extras['exiled_card_deep_copy'] = my_deep_copy
        gs.pile_mgr.exile(t)

class Telekinesis(Resolver):
    """Tap target creature. Prevent all combat damage that would be dealt by that creature this turn.
    It doesn't untap during its controller's next two untap steps."""
    @Resolver.target_required
    def resolve(self, gs: GameState, source: GameCard, t: RTarget = None, context: ResContext = None):
        t.tap()
        gs.event_mgr.register(PreventAllDamageByEOT(t, combat_only=True), source)
        t.counters.add_counter(STUN, 2)

class Timetwister(Resolver):
    """Each player shuffles their hand & graveyard into their library, then draws 7 cards.
    (Timetwister to its owner's graveyard.)"""
    def resolve(self, gs: GameState, source: GameCard, t: RTarget = None, context: ResContext = None) -> None:
        for p_id in (0, 1):
            for c in gs.pile_mgr.hands[p_id][:]:
                gs.pile_mgr.move_card(c, Zone.LIBRARY, emit_zone_event=False)
            for c in gs.pile_mgr.graveyards[p_id][:]:
                gs.pile_mgr.move_card(c, Zone.LIBRARY, emit_zone_event=False)
            random.shuffle(gs.pile_mgr.libraries[p_id])
            gs.pile_mgr.draw(p_id, 7)
            if p_id == source.owner_id:
                gs.pile_mgr.move_card(source, Zone.GRAVEYARD, emit_zone_event=False)

class Tracker(Resolver):
    """Tracker deals damage = its power to target creature. That creature deals damage = its power to this creature.
    According to Google, this is slightly different from modern term 'fight',
    since this is spelled out as two distinct successive actions."""
    @Resolver.target_required
    def resolve(self, gs: GameState, source: GameCard, t: RTarget = None, context: ResContext = None):
        gs.apply_damage(source, source.power, t)
        gs.apply_damage(t, t.power, source)

class TransmuteArtifact(Resolver):
    """Sac an artifact: tutor an artifact. If that card's MV <= the sacrificed artifact's MV, put on battlefield.
    If >, you may pay {X} as the difference. If you do, put on battlefield. If you don't, put it in graveyard.
    Shuffle."""
    def __init__(self):
        self.tutored_card: GameCard | None = None
        self._gs: GameState | None = None
        self._sac_mv: int | None = None
        self._lib: list[GameCard] | None = None

    def resolve(self, gs: GameState, source: GameCard, t: RTarget = None, context: ResContext = None) -> None:
        self._gs = gs
        self._sac_mv = ManaCost(context.cost_result.paid_cards[0].casting_cost).mana_value
        self._lib = gs.pile_mgr.libraries[source.owner_id]
        lib_artifacts = [c for c in self._lib if c.is_artifact]
        gs.add_presentation_request(source.owner_id, 'search_library', {'cards': lib_artifacts})
        options = [CO(f'Tutor {c}', lambda c=c: self._select_card(c)) for c in lib_artifacts]
        gs.choice_mgr.queue(ChoiceAction(options))
        return

    def coordinate(self):
        if not self.tutored_card:
            raise ValueError("Transmute Artifact should have a selected card by here")

        mv_diff = ManaCost(self.tutored_card.casting_cost).mana_value - self._sac_mv

        if mv_diff <= 0:
            self._tutor()
            return

        if not self._gs.mana_pools[self.tutored_card.owner_id].can_pay(str(mv_diff)):
            self._to_gy()
            return

        options = [CO(f'{{{str(mv_diff)}}}: {self.tutored_card} to battlefield', lambda: self._tutor()),
                   CO(f'Place {self.tutored_card} in your graveyard', lambda: self._to_gy())]
        self._gs.choice_mgr.queue(ChoiceAction(options))

    def _select_card(self, c: GameCard):
        self.tutored_card = c
        self.coordinate()

    def _tutor(self):
        self._gs.pile_mgr.move_card(self.tutored_card, Zone.BATTLEFIELD)
        random.shuffle(self._lib)

    def _to_gy(self):
        self._gs.pile_mgr.move_card(self.tutored_card, Zone.GRAVEYARD)
        random.shuffle(self._lib)


class TriassicEggA(Resolver):
    """Choose one (activate only if there are two or more hatchling counters on this artifact.):
    * You may put a creature card from your hand onto the battlefield ... """
    def can_activate(self, gs: GameState, s: GameCard) -> bool:
        ctr_cnt_condition = s.counters.get_count(HATCHLING) >= 2
        has_creature_in_hand = len([c for c in gs.pile_mgr.hands[s.owner_id] if c.is_creature]) > 0
        return ctr_cnt_condition and has_creature_in_hand

    @Resolver.target_required
    def resolve(self, gs: GameState, source: GameCard, t: RTarget = None, context: ResContext = None):
        gs.pile_mgr.move_card(t, Zone.BATTLEFIELD)

class TriassicEggB(Resolver):
    """Choose one (activate only if there are two or more hatchling counters on this artifact.):
    ... * Return target creature card from your graveyard to the battlefield."""
    def can_activate(self, gs: GameState, s: GameCard) -> bool:
        ctr_cnt_condition = s.counters.get_count(HATCHLING) >= 2
        creatures_in_your_gy = len([c for c in gs.graveyards[s.owner_id] if c.is_creature]) > 0
        return ctr_cnt_condition and creatures_in_your_gy

    @Resolver.target_required
    def resolve(self, gs: GameState, source: GameCard, t: RTarget = None, context: ResContext = None):
        gs.pile_mgr.move_card(t, Zone.BATTLEFIELD)

class Twiddle(Resolver):
    @Resolver.target_required
    def resolve(self, gs: GameState, source: GameCard, t: RTarget = None, context: ResContext = None):
        t.untap() if t.is_tapped else t.tap()

class Typhoon(Resolver):
    """Typhoon deals damage to opponent = the number of Islands that player controls"""
    def resolve(self, gs: GameState, source: GameCard, t: RTarget = None, context: ResContext = None) -> None:
        opp = flip(gs.player_turn_idx)
        opp_island_cnt = len(gs.card_filter.on_player_board(opp).islands().result())
        if opp_island_cnt:
            gs.apply_damage(source, opp_island_cnt, opp)

class UrborgLoseFirstStrike(Resolver):
    """{T}: Target creature loses First Strike or Swampwalk until end of turn"""

    @Resolver.target_required
    def resolve(self, gs: GameState, source: GameCard, t: RTarget = None, context: ResContext = None):
        t.modifiers.append(KWAMod(s=source, add_or_remove='remove', item=KW.FIRST_STRIKE, expires='EOT'))

class UrborgLoseSwampwalk(Resolver):
    """{T}: Target creature loses first strike or SWAMPWALK until end of turn"""
    @Resolver.target_required
    def resolve(self, gs: GameState, source: GameCard, t: RTarget = None, context: ResContext = None):
        t.modifiers.append(KWAMod(s=source, add_or_remove='remove', item=KW.SWAMPWALK, expires='EOT'))

class UrzasAvenger(Resolver):
    """This creature gets -1/-1 and gains your choice of flying, first strike, or trample until end of turn"""
    def resolve(self, gs: GameState, source: GameCard, t: RTarget = None, context: ResContext = None) -> None:
        s = source
        s.modifiers.append(PTMod(s=s, p_adj=-1, t_adj=-1, expires='EOT'))
        options = [CO(f'{source} gains {kwa}', lambda: s.modifiers.append(KWAMod(s=s, item=KW.FLYING, expires='EOT')))
                   for kwa in (KW.FLYING, KW.FIRST_STRIKE, KW.TRAMPLE)]
        gs.choice_mgr.queue(ChoiceAction(options))

class UrzasTrio(Resolver):
    """{T}: Add {C}.
    urzas-mine: If you control an Urza's Power-Plant and an Urza's Tower, add {CC} instead.
    urzas-power-plant: If you control an Urza's Mine and an Urza's Tower, add {CC} instead.
    urzas-tower: If you control an Urza's Mine and an Urza's Power-Plant, add {CCC} instead"""
    def resolve(self, gs: GameState, source: GameCard, t: RTarget = None, context: ResContext = None) -> None:
        mines = gs.card_filter.on_player_board(source.owner_id).by_slug('urzas-mine').result()
        power_plants = gs.card_filter.on_player_board(source.owner_id).by_slug('urzas-power-plant').result()
        towers = gs.card_filter.on_player_board(source.owner_id).by_slug('urzas-tower').result()
        if not (mines and power_plants and towers):
            gs.mana_pools[source.owner_id].add_floating('C')
        elif source.props.slug == 'urzas-tower':
            gs.mana_pools[source.owner_id].add_floating('CCC')
        else:
            gs.mana_pools[source.owner_id].add_floating('CC')

class VenarianGold(Resolver):
    """When this Aura enters, tap enchanted creature and put X stun counters on it ..."""
    @Resolver.target_required
    def resolve(self, gs: GameState, source: GameCard, t: RTarget = None, context: ResContext = None):
        t.tap()
        if x := context.x_value:
            t.counters.add_counter(STUN, x)

class VesuvanDoppelgangerCast(Resolver):
    """You may have this creature enter as a copy of any creature on the battlefield,
    except it doesn't copy that creature's color & you may select a different creature on each of your upkeeps"""
    def resolve(self, gs: GameState, s: GameCard, t: RTarget = None, context: ResContext = None) -> None:
        if gs.player_turn_idx != s.owner_id:
            return
        card_options = [c for c in gs.card_filter.in_play().creatures().result() if c is not s]
        if not card_options:
            return
        options = [CO(f'{s} copies {t}', lambda: copy_card(gs, s, t, copy_color=False)) for t in card_options]
        gs.choice_mgr.queue(ChoiceAction(options))

class Visions(Resolver):
    """Look at the top five cards of target player's library. You may then have that player shuffle that library."""
    @Resolver.target_required
    def resolve(self, gs: GameState, source: GameCard, t: RTarget = None, context: ResContext = None):
        gs.add_presentation_request(source.owner_id, 'view_library', {'cards': gs.pile_mgr.libraries[t][:5]})
        options = [CO(f'Shuffle', lambda: random.shuffle(gs.pile_mgr.libraries[t]))]
        gs.choice_mgr.queue(ChoiceAction(options, may=True))

class WallOfWonder(Resolver):
    """{2UU}: This creature gets +4/-4 until end of turn and can attack this turn as though it didn't have defender"""
    def resolve(self, gs: GameState, source: GameCard, t: RTarget = None, context: ResContext = None) -> None:
        source.modifiers.append(PTMod(s=source, p_adj=4, t_adj=-4, expires='EOT'))
        source.modifiers.append(KWAMod(s=source, add_or_remove='remove', item='Defender', expires='EOT'))

class WandOfIth(Resolver):
    """Opponent reveals a card at random from their hand. If it's a land, that player pays 1 lift or discards.
    If a non-land, the player pays life = to its mana value else discards it.  Activate only during your turn."""
    def resolve(self, gs: GameState, source: GameCard, t: RTarget = None, context: ResContext = None) -> None:
        opp = flip(source.owner_id)
        opp_cards = gs.pile_mgr.hands[opp]
        if not opp_cards:
            return
        the_card = gs.randomize_event(opp, opp_cards) if len(opp_cards) > 1 else opp_cards[0]
        life_amt = the_card.props.mana_value if 'Land' not in the_card.card_types else 1
        options = [CO(f'Pay {life_amt} life', lambda: gs.score_mgr.decrement_life(opp, life_amt, source)),
                   CO(f'Discard {the_card}', lambda: gs.pile_mgr.discard(the_card, source))]
        gs.choice_mgr.queue(ChoiceAction(options))

class WarBarge(Resolver):
    """{3}: Target creature gains islandwalk EOT. When WB LTB this turn, destroy that creature, no regen allowed"""
    @Resolver.target_required
    def resolve(self, gs: GameState, source: GameCard, t: RTarget = None, context: ResContext = None):
        t.modifiers.append(KWAMod(item=KW.ISLANDWALK, s=source, expires='EOT'))
        gs.event_mgr.register(LTBTandem([source, t], until_eot=True), source)

class WheelOfFortune(Resolver):
    """Each player discards their hand, then draws seven cards"""
    def resolve(self, gs: GameState, source: GameCard, t: RTarget = None, context: ResContext = None) -> None:
        for i in (0, 1):
            for c in gs.pile_mgr.hands[i][::]:
                gs.pile_mgr.discard(c)
            gs.pile_mgr.draw(i, 7)

class WindsOfChange(Resolver):
    """Each player shuffles the cards from their hand into their library, then draws that many cards"""
    def resolve(self, gs: GameState, source: GameCard, t: RTarget = None, context: ResContext = None) -> None:
        for p_id in range(2):
            if not gs.pile_mgr.hands[p_id]:
                continue
            hand_cards = gs.pile_mgr.hands[p_id][:]
            gs.pile_mgr.hands[p_id].clear()
            gs.pile_mgr.libraries[p_id].extend(hand_cards)
            random.shuffle(gs.pile_mgr.libraries[p_id])
            gs.pile_mgr.draw(p_id, len(hand_cards))

class WinterBlast(Resolver):
    """Tap X target creatures. Winter Blast deals 2 damage to each of those creatures with flying."""
    @Resolver.target_required
    def resolve(self, gs: GameState, source: GameCard, t: RTarget = None, context: ResContext = None):
        for target in t:
            target.tap()
            if KW.FLYING in t.keyword_abilities:
                gs.apply_damage(source, 2, target)

class WoodElemental(Resolver):
    """As this creature enters, sac any number of untapped Forests. WE's PT are each = # of Forests sacrificed."""
    def resolve(self, gs: GameState, source: GameCard, t: RTarget = None, context: ResContext = None) -> None:
        your_untapped_forests = gs.card_filter.on_player_board(source.owner_id).forests().untapped().result()
        options = [CO(f"Sac {len(combo)} to make {source} a {len(combo)}/{len(combo)} creature",
                      lambda: self.etb_action(gs, source, combo))
                   for r in range(len(your_untapped_forests)) for combo in combinations(your_untapped_forests, r=r)]
        gs.choice_mgr.queue(ChoiceAction(options))

    @staticmethod
    def etb_action(gs: GameState, s: GameCard, forest_combo: list[GameCard]):
        amt = len(forest_combo)
        s.base_pt = (amt, amt)
        for card in forest_combo:
            gs.pile_mgr.sacrifice(card)
