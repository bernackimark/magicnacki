from __future__ import annotations

import random
from itertools import combinations
from typing import TYPE_CHECKING, Optional

from models.actions.base import DoNothing, Action
from models.actions.damage import DealDamageTo, PayLife
from models.actions.destroy_sac_regen import ReanimateAction
from models.actions.draw_discard import DiscardCards, DrawCard
from models.actions.piles import Tutor, Shuffle, HandToBattlefield
from models.actions.pump import VariablePTMod
from models.actions.special import CopyCard, PrimalClayA, PrimalClayB, PrimalClayC
from models.choice_actions_all import ChoiceAction
from models.counter_tokens import PLUS_ONE, SLEEP, HATCHLING, STUN
from models.effects.base import Resolver
from models.effects.listeners_dies import SandalsOfAbdallahIfCreatureDies
from models.effects.listeners_generic import PreventAllDamageByEOT, DestroyAtEndStep, PreventNextDamageBy, \
    BounceAtEndStep, PreventNextDamageTo, DestroyAtEndStepIfItDidntAttack
from models.effects.listeners_permission import TowerOfCoireallEOT, DoesntUntapAtUntapIfItAttackedLastTurn
from models.effects.resolvers_generic import Reveal
from models.modifiers import SubTypeMod, KWAMod, PTMod
from models.utils import flip
from models.zone import Zone

if TYPE_CHECKING:
    from game_state import GameState
    from models.game_card.game_card import GameCard


class PhantasmalTerrain(Resolver):
    """Enchant land As this Aura enters, choose a basic land type. Enchanted land is the chosen type"""
    def __init__(self, land_type: str):
        self.land_type = land_type

    def resolve(self, gs, source: GameCard, target: Optional[GameCard] = None):
        if target is None:
            raise ValueError(f'{source.props.name} needs a target')
        sub_types = target.card_sub_types.copy()
        target.modifiers.append(SubTypeMod(s=source, add_or_remove='add', card_sub_type=self.land_type))
        for sub_type in sub_types:
            target.modifiers.append(SubTypeMod(s=source, add_or_remove='remove', card_sub_type=sub_type))

class PrimalClay(Resolver):
    """As this creature enters, it becomes your choice of a 3/3 artifact creature, a 2/2 artifact creature with flying,
    or a 1/6 Wall artifact creature with defender in addition to its other types."""
    def resolve(self, gs: GameState, s: GameCard, t: GameCard = None):
        options = [PrimalClayA(s.owner_id, gs, s), PrimalClayB(s.owner_id, gs, s), PrimalClayC(s.owner_id, gs, s)]
        gs.pending_choice = ChoiceAction(options)

class RagMan(Resolver):
    """Opponent reveals their hand and discards a creature card at random. Activate only during your turn."""
    def resolve(self, gs: GameState, source: GameCard, target: int = None):
        if target is None:
            raise ValueError(f'{source.props.name} needs a target player')
        opp_cards = gs.pile_mgr.hands[target]
        for c in opp_cards:
            c.reveal()
        opp_creatures = [c for c in opp_cards if c.is_creature]
        if not opp_creatures:
            return
        if len(opp_creatures) == 1:
            gs.pile_mgr.discard(opp_creatures[0], source)
            return
        random_card: GameCard = gs.randomize_event(target, opp_creatures)
        gs.pile_mgr.discard(random_card, source)

class Rakalite(Resolver):
    """{2}: Prevent the next 1 damage that would be dealt to any target this turn.
    Return this artifact to its owner's hand at the beginning of the next end step."""
    def resolve(self, gs: GameState, s: GameCard, target: GameCard = None):
        """target is the card dealing damage"""
        if target is None:
            raise ValueError(f'{s.props.name} needs a target')
        gs.event_mgr.register(PreventNextDamageTo(1, protected=target), s)
        gs.event_mgr.register(BounceAtEndStep(s), s)

class RapidFire(Resolver):
    """Cast this spell only before blockers are declared. Target creature gains first strike until end of turn.
    If it doesn't have rampage, that creature gains rampage 2 until end of turn."""
    def resolve(self, gs: GameState, source: GameCard, target: Optional[GameCard] = None):
        if not target:
            raise ValueError(f'{source.props.name} needs a target')
        target.modifiers.append(KWAMod(s=source, add_or_remove='add', kwa='First Strike', expires='EOT'))
        if not target.rampage_amt:
            target.modifiers.append(KWAMod(s=source, add_or_remove='add', kwa='Rampage 2', expires='EOT'))

class Reset(Resolver):
    """Cast this spell only during an opponent's turn after their upkeep step. Untap all lands you control"""
    def resolve(self, gs: GameState, source: GameCard, target: Optional[GameCard] = None):
        for land in gs.card_filter.on_player_board(source.owner_id).lands().tapped().result():
            land.untap()

class ReversePolarity(Resolver):
    """You gain X life, where X is twice the damage dealt to you so far this turn by artifacts"""
    def resolve(self, gs: GameState, source: GameCard, target: Optional[GameCard] = None) -> None:
        from models.events_all import DamageResolvedEvent
        damage_by_artifacts = sum([e.amt for e in gs.event_mgr.get_events(gs.turn_mgr.turn_number)
                                   if isinstance(e, DamageResolvedEvent) and e.target == source.owner_id])
        if not damage_by_artifacts:
            return
        gs.score_mgr.increment_life(source.owner_id, 2 * damage_by_artifacts, source, gs)

class Riptide(Resolver):
    """Tap all blue creatures"""
    def resolve(self, gs: GameState, _: GameCard, t: Optional[GameCard] = None):
        for c in gs.card_filter.in_play().creatures().untapped().blue().result():
            c.tap()

class RockHydraCast(Resolver):
    """This creature enters with X +1/+1 counters on it ..."""
    def resolve(self, gs: GameState, source: GameCard, target=None):
        if x := source.extras.get('x', 0):  # read X chosen when casting
            source.counters.add_counter(PLUS_ONE, x)

class RocketLauncher(Resolver):
    """{2}: Deal 1 damage to any target. Destroy Rocket Launcher at next end step.
    Activate only if you've controlled continuously since the beginning of your most recent turn."""
    def can_activate(self, gs: GameState, s: GameCard) -> bool:
        print(s.turn_entered_for_owner, gs.turn_mgr.most_recent_turn_started[s.owner_id])
        if not s.turn_entered_for_owner:
            return False  # turn_entered_for_owner is getting set AFTER this check
        return s.turn_entered_for_owner < gs.turn_mgr.most_recent_turn_started[s.owner_id]

    def resolve(self, gs: GameState, s: GameCard, t: Optional[GameCard] = None):
        gs.apply_damage(s, 1, t)
        gs.event_mgr.register(DestroyAtEndStep(s), s)

class SacrificeOnCast(Resolver):
    """Sac a creature: Add an amount of {B} equal to the sacrificed creature's mana value.
    Note "sacrifice" refers to the card called sacrifice, not the game action of sacrifice"""
    def resolve(self, gs: GameState, s: GameCard, t: GameCard = None):
        mana_cnt: int = s.extras.get('mana_cnt')
        if mana_cnt is None:
            raise ValueError("The card called 'Sacrifice' didn't get the mana count attached to its extras dictionary")
        if mana_cnt:
            gs.mana_pools[s.owner_id].add_floating('B', mana_cnt)

class SafeHaven(Resolver):
    """{2}, {T}: Exile target creature you control, storing the exiled card's ID for future reference"""
    def resolve(self, gs: GameState, source: GameCard, target: Optional[GameCard] = None) -> None:
        if not target:
            raise ValueError(f"{source.props.name} needs a target")
        gs.pile_mgr.exile(target)
        if source.extras.get('cards_exiled') is None:
            source.extras['cards_exiled'] = set()
        source.extras['cards_exiled'].add(target)

class SandalsOfAbdallahIslandWalk(Resolver):
    """{T}: Target creature gains islandwalk until end of turn. When that creature dies this turn, destroy Sandals."""
    def resolve(self, gs: GameState, source: GameCard, target: Optional[GameCard] = None):
        if not target:
            raise ValueError(f'{source.props.name} needs a target')
        target.modifiers.append(KWAMod(s=source, add_or_remove='add', kwa='Islandwalk', expires='EOT'))
        gs.event_mgr.register(SandalsOfAbdallahIfCreatureDies(target_creature=target), source)

class Sandstorm(Resolver):
    """Sandstorm deals 1 damage to each attacking creature.
    [from Google: it only hits creatures already attacking when it resolves.]"""
    def resolve(self, gs: GameState, source: GameCard, target: Optional[GameCard] = None):
        for attacker in gs.card_filter.attackers().result():
            gs.apply_damage(source, 1, attacker)

class ShapeshifterCast(Resolver):
    """At cast & at your upkeep, choose a number 0-7 (n). Shapeshifter's power = n, toughness = 7 - n"""
    def resolve(self, gs: GameState, source: GameCard, target: Optional[GameCard] = None):
        options = [VariablePTMod(source.owner_id, gs, source, source, i, 7 - i) for i in range(8)]
        gs.pending_choice = ChoiceAction(options)

class Simulacrum(Resolver):
    """You gain life equal to the damage already dealt to you this turn. If you control a creature,
    Simulacrum deals damage to target creature you control equal to the damage dealt to you this turn."""
    def resolve(self, gs: GameState, source: GameCard, target: Optional[GameCard] = None) -> None:
        from models.events_all import DamageResolvedEvent
        damage_taken_this_turn = sum([e.amt for e in gs.event_mgr.get_events(gs.turn_mgr.turn_number)
                                      if isinstance(e, DamageResolvedEvent) and e.target == source.owner_id])
        if not damage_taken_this_turn:
            return

        gs.score_mgr.increment_life(source.owner_id, damage_taken_this_turn, source, gs)

        your_creatures = gs.card_filter.creatures().on_player_board(source.owner_id).result()
        if your_creatures:
            options = [DealDamageTo(source.owner_id, gs, source, damage_taken_this_turn, c) for c in your_creatures]
            gs.pending_choice = ChoiceAction(options)

class Sindbad(Resolver):
    """{T}: Draw a card and reveal it. If it isn't a land, discard it."""
    def resolve(self, gs: GameState, source: GameCard, target: Optional[GameCard] = None) -> None:
        top_card = gs.pile_mgr.libraries[source.owner_id][0] if gs.pile_mgr.libraries[source.owner_id] else None
        gs.pile_mgr.draw(source.owner_id)
        Reveal().resolve(gs, source, top_card)
        if not top_card.is_land:
            gs.pile_mgr.discard(top_card, source)

class SingingTree(Resolver):
    """Target attacking creature has base power 0 until end of turn"""
    def resolve(self, gs: GameState, source: GameCard, target: Optional[GameCard] = None):
        if not target:
            raise ValueError(f'{source.props.name} needs a target')
        target.modifiers.append(PTMod(s=source, p_adj=-target.base_pt[0], expires='EOT'))

class SirensCall(Resolver):
    """... All non-Wall creatures the active player has controlled continuously since BOT must attack ..."""
    def resolve(self, gs: GameState, source: GameCard, _: Optional[GameCard | int | Action] = None) -> None:
        non_wall_creatures = gs.card_filter.on_player_board(gs.player_turn_idx).non_wall_creatures().result()
        for creature in non_wall_creatures:
            if not creature.has_summoning_sickness:
                creature.modifiers.append(KWAMod('add', 'Goad', s=source, expires='EOT'))
                gs.event_mgr.register(DestroyAtEndStepIfItDidntAttack(creature), source)

class StoneGiant(Resolver):
    """{T}: Target creature you control with toughness less than this creature's power gains flying until end of turn.
    Destroy that creature at the beginning of the next end step."""
    def resolve(self, gs: GameState, s: GameCard, t: Optional[GameCard] = None):
        t.modifiers.append(KWAMod(s=s, add_or_remove='add', kwa='Flying', expires='EOT'))
        gs.event_mgr.register(DestroyAtEndStep(t), s)

class StormSeeker(Resolver):
    """Storm Seeker deals damage to target player equal to the number of cards in that player's hand"""
    def resolve(self, gs: GameState, source: GameCard, t: Optional[GameCard] = None):
        opp_idx = flip(source.owner_id)
        gs.apply_damage(source, len(gs.pile_mgr.hands[opp_idx]), opp_idx)

class StreamOfLife(Resolver):
    def resolve(self, gs: GameState, source: GameCard, target: int = None):
        x = source.extras.get('x', 0)  # read X chosen when casting
        gs.score_mgr.increment_life(target, x, source, gs)

class Subdue(Resolver):
    """Prevent all combat damage that would be dealt by target creature this turn.
    That creature gets +0/+X until end of turn, where X is its mana value."""
    def resolve(self, gs: GameState, s: GameCard, t: Optional[GameCard] = None):
        gs.event_mgr.register(PreventNextDamageBy(t, combat_only=True), s)
        t.modifiers.append(PTMod(s=s, p_adj=0, t_adj=t.props.mana_value))

class SwordsToPlowshares(Resolver):
    def resolve(self, gs, source: GameCard, target: Optional[GameCard] = None):
        if target:
            gs.pile_mgr.exile(target)  # which is correct?  exile_from_play() or exile()
            gs.score_mgr.increment_life(target.owner_id, target.power, source, gs)

class SylvanLibrary(Resolver):
    """At your draw step, you may draw two additional cards.
    If you do, choose two cards in your hand drawn this turn.
    For each of those cards, pay 4 life or put the card on top of your library."""
    # TODO: Once player opts to draw, control needs to be returned back to player to then make subsequent choices.
    def resolve(self, gs: GameState, source: GameCard, target: Optional[GameCard] = None):
        options = [DrawCard(source.owner_id, gs), DoNothing(source.owner_id, gs)]
        gs.pending_choice = ChoiceAction(options)

class SyphonSoul(Resolver):
    """Syphon Soul deals 2 damage to each other player. You gain life equal to the damage dealt this way."""
    def resolve(self, gs: GameState, source: GameCard, target: Optional[GameCard] = None):
        gs.apply_damage(source, 2, target)
        gs.score_mgr.increment_life(source.owner_id, 2, source, gs)

class TangleKelp(Resolver):
    """Tap host. Host doesn't untap during its controller's untap step if it attacked their last turn."""
    def resolve(self, gs: GameState, source: GameCard, target: Optional[GameCard] = None) -> None:
        if target is None:
            raise ValueError(f'{source.props.name} needs a target')
        target.tap()
        gs.event_mgr.register(DoesntUntapAtUntapIfItAttackedLastTurn(target), source)

class TawnossCoffin(Resolver):
    """... Exile target creature & all its auras. Note the number & kind of counters that were on that creature ..."""
    def resolve(self, gs: GameState, source: GameCard, target: Optional[GameCard] = None) -> None:
        from copy import deepcopy
        if not target:
            raise ValueError(f'{source.props.name} needs a target')
        my_deep_copy = deepcopy(target)
        source.extras['exiled_card'] = target
        source.extras['exiled_card_deep_copy'] = my_deep_copy
        gs.pile_mgr.exile(target)

class Telekinesis(Resolver):
    """Tap target creature. Prevent all combat damage that would be dealt by that creature this turn.
    It doesn't untap during its controller's next two untap steps."""
    def resolve(self, gs: GameState, source: GameCard, target: Optional[GameCard] = None) -> None:
        if target is None:
            raise ValueError(f'{source.props.name} needs a target')
        target.tap()
        gs.event_mgr.register(PreventAllDamageByEOT(target, combat_only=True), source)
        target.counters.add_counter(STUN, 2)

class TimeElementalBounce(Resolver):
    """... {2UU}, {T}: Return target unenchanted permanent to its owner's hand"""
    def resolve(self, gs: GameState, source: GameCard, target: GameCard = None):
        gs.pile_mgr.bounce(target)

class Timetwister(Resolver):
    """Each player shuffles their hand & graveyard into their library, then draws 7 cards.
    (Timetwister to its owner's graveyard.)"""
    def resolve(self, gs: GameState, s: GameCard, target: Optional[GameCard] = None):
        for p_id in (0, 1):
            for c in gs.pile_mgr.hands[p_id]:
                gs.pile_mgr.move_card(c, Zone.LIBRARY, emit_zone_event=False)
            for c in gs.pile_mgr.graveyards[p_id]:
                gs.pile_mgr.move_card(c, Zone.LIBRARY, emit_zone_event=False)
            random.shuffle(gs.pile_mgr.libraries[p_id])
            gs.pile_mgr.draw(p_id, 7)
            # if p_id == s.owner_id:
            #     gs.pile_mgr.graveyards[p_id].append(time_twister)

class TowerOfCoireall(Resolver):
    """{T}: Target creature can't be blocked by Walls this turn"""
    def resolve(self, gs: GameState, source: GameCard, target: GameCard = None):
        if not target:
            raise ValueError(f'{source.props.name} needs a target')
        gs.event_mgr.register(TowerOfCoireallEOT(target), source)

class Tracker(Resolver):
    """Tracker deals damage = its power to target creature. That creature deals damage = its power to this creature."""
    def resolve(self, gs: GameState, source: GameCard, target: GameCard = None):
        if not target:
            raise ValueError(f'{source.props.name} needs a target')
        gs.apply_damage(source, source.power, target)
        gs.apply_damage(target, target.power, source)

class TriassicEgg(Resolver):
    """Choose one (activate only if there are two or more hatchling counters on this artifact.):
    * You may put a creature card from your hand onto the battlefield.
    * Return target creature card from your graveyard to the battlefield."""
    def can_activate(self, _: GameState, source: GameCard) -> bool:
        return source.counters.get_count(HATCHLING) >= 2

    def resolve(self, gs: GameState, source: GameCard, _: Optional[GameCard] = None):
        options = []
        for card_in_hand in gs.pile_mgr.hands[source.owner_id]:
            if card_in_hand.is_creature:
                options.append(HandToBattlefield(source.owner_id, gs, card_in_hand))
        for card_in_graveyard in gs.pile_mgr.graveyards[source.owner_id]:
            if card_in_graveyard.is_creature:
                options.append(ReanimateAction(source.owner_id, gs, source, card_in_graveyard))
        if not options:
            return
        gs.pending_choice = ChoiceAction(options)

class Twiddle(Resolver):
    def resolve(self, gs, source: GameCard, target: Optional[GameCard] = None):
        if target:
            target.untap() if target.is_tapped else target.tap()

class Typhoon(Resolver):
    """Typhoon deals damage to opponent = the number of Islands that player controls"""
    def resolve(self, gs: GameState, s: GameCard, t: Optional[GameCard] = None):
        opp = flip(gs.player_turn_idx)
        opp_island_cnt = len(gs.card_filter.on_player_board(opp).islands().result())
        if opp_island_cnt:
            gs.apply_damage(s, opp_island_cnt, opp)

class UntamedWilds(Resolver):
    """Search your library for a basic land card, put that card onto the battlefield, then shuffle"""
    def resolve(self, gs: GameState, source: GameCard, target=None):
        p_id = source.owner_id
        basic_lands = [c for c in gs.pile_mgr.libraries[p_id] if c.props.is_basic_land]
        gs.add_presentation_request(p_id, 'search_library', {'cards': basic_lands})
        options = [Tutor(p_id, gs, source, basic_land, Zone.BATTLEFIELD) for basic_land in basic_lands]
        gs.pending_choice = ChoiceAction(options)

class UrborgLoseFirstStrike(Resolver):
    """{T}: Target creature loses FIRST STRIKE or swampwalk until end of turn"""
    def resolve(self, gs: GameState, source: GameCard, target: Optional[GameCard] = None):
        if not target:
            raise ValueError(f'{source.props.name} needs a target')
        target.modifiers.append(KWAMod(s=source, add_or_remove='remove', kwa='First Strike', expires='EOT'))

class UrborgLoseSwampwalk(Resolver):
    """{T}: Target creature loses first strike or SWAMPWALK until end of turn"""
    def resolve(self, gs: GameState, source: GameCard, target: Optional[GameCard] = None):
        if not target:
            raise ValueError(f'{source.props.name} needs a target')
        target.modifiers.append(KWAMod(s=source, add_or_remove='remove', kwa='Swampwalk', expires='EOT'))

class UrzasAvengerFlying(Resolver):
    """This creature gets -1/-1 and gains your choice of FLYING, first strike, or trample until end of turn"""
    def resolve(self, gs: GameState, source: GameCard, target: Optional[GameCard] = None):
        source.modifiers.append(PTMod(s=source, p_adj=-1, t_adj=-1, expires='EOT'))
        source.modifiers.append(KWAMod(s=source, add_or_remove='add', kwa='Flying', expires='EOT'))

class UrzasAvengerFirstStrike(Resolver):
    """This creature gets -1/-1 and gains your choice of flying, FIRST STRIKE, or trample until end of turn"""
    def resolve(self, gs: GameState, source: GameCard, target: Optional[GameCard] = None):
        source.modifiers.append(PTMod(s=source, p_adj=-1, t_adj=-1, expires='EOT'))
        source.modifiers.append(KWAMod(s=source, add_or_remove='add', kwa='First Strike', expires='EOT'))

class UrzasAvengerTrample(Resolver):
    """This creature gets -1/-1 and gains your choice of flying, first strike, or TRAMPLE until end of turn"""
    def resolve(self, gs: GameState, source: GameCard, target: Optional[GameCard] = None):
        source.modifiers.append(PTMod(s=source, p_adj=-1, t_adj=-1, expires='EOT'))
        source.modifiers.append(KWAMod(s=source, add_or_remove='add', kwa='Trample', expires='EOT'))

class UrzasTrio(Resolver):
    """{T}: Add {C}.
    urzas-mine: If you control an Urza's Power-Plant and an Urza's Tower, add {CC} instead.
    urzas-power-plant: If you control an Urza's Mine and an Urza's Tower, add {CC} instead.
    urzas-tower: If you control an Urza's Mine and an Urza's Power-Plant, add {CCC} instead"""
    def resolve(self, gs: GameState, s: GameCard, _: Optional[GameCard] = None):
        mines = gs.card_filter.on_player_board(s.owner_id).by_slug('urzas-mine').result()
        power_plants = gs.card_filter.on_player_board(s.owner_id).by_slug('urzas-power-plant').result()
        towers = gs.card_filter.on_player_board(s.owner_id).by_slug('urzas-tower').result()
        if not (mines and power_plants and towers):
            gs.mana_pools[s.owner_id].add_floating('C')
        elif s.props.slug == 'urzas-tower':
            gs.mana_pools[s.owner_id].add_floating('CCC')
        else:
            gs.mana_pools[s.owner_id].add_floating('CC')

class VenarianGoldCast(Resolver):
    """When this Aura enters, tap enchanted creature and put X sleep counters on it ..."""
    def resolve(self, gs: GameState, source: GameCard, target: GameCard = None):
        if not target:
            raise RuntimeError(f"{source.props.name} needs a casting target")
        target.tap()
        if x := source.extras.get('x', 0):  # read X chosen when casting
            source.counters.add_counter(SLEEP, x)

class VesuvanDoppelgangerCast(Resolver):
    """You may have this creature enter as a copy of any creature on the battlefield,
    except it doesn't copy that creature's color & you may select a different creature on each of your upkeeps"""
    def resolve(self, gs: GameState, s: GameCard, t: GameCard = None):
        if gs.player_turn_idx != s.owner_id:
            return
        card_options = [c for c in gs.card_filter.in_play().creatures().result() if c is not s]
        if not card_options:
            return
        options = [CopyCard(s.owner_id, gs, s, card, copy_color=False) for card in card_options]
        gs.pending_choice = ChoiceAction(options)

class Visions(Resolver):
    """Look at the top five cards of target player's library. You may then have that player shuffle that library."""
    def resolve(self, gs: GameState, source: GameCard, target: int = None):
        if target is None:
            raise ValueError(f'{source.props.name} needs a target player')
        gs.add_presentation_request(source.owner_id, 'view_library', {'cards': gs.pile_mgr.libraries[target][:5]})
        options = [Shuffle(source.owner_id, gs, gs.pile_mgr.libraries[target]), DoNothing(source.owner_id, gs)]
        gs.pending_choice = ChoiceAction(options)

class WallOfWonder(Resolver):
    """{2UU}: This creature gets +4/-4 until end of turn and can attack this turn as though it didn't have defender"""
    def resolve(self, gs: GameState, source: GameCard, _: Optional[GameCard] = None):
        source.modifiers.append(PTMod(s=source, p_adj=4, t_adj=-4, expires='EOT'))
        source.modifiers.append(KWAMod(s=source, add_or_remove='remove', kwa='Defender', expires='EOT'))


class WandOfIth(Resolver):
    """Opponent reveals a card at random from their hand. If it's a land, that player pays 1 lift or discards.
    If a non-land, the player pays life = to its mana value else discards it.  Activate only during your turn."""
    def resolve(self, gs: GameState, source: GameCard, target: Optional[GameCard] = None):
        opp = flip(source.owner_id)
        opp_cards = gs.pile_mgr.hands[opp]
        if not opp_cards:
            return
        the_card = gs.randomize_event(opp, opp_cards) if len(opp_cards) > 1 else opp_cards[0]
        life_payment_amt = the_card.props.mana_value if 'Land' not in the_card.card_types else 1
        options = [PayLife(opp, gs, source, life_payment_amt), DiscardCards(opp, gs, the_card)]
        gs.pending_choice = ChoiceAction(options)

class Web(Resolver):
    def resolve(self, _: GameState, source: GameCard, target: Optional[GameCard] = None):
        if target:
            target.modifiers.append(PTMod(s=source, p_adj=0, t_adj=2))
            target.modifiers.append(KWAMod(s=source, add_or_remove='add', kwa='Reach'))

class WheelOfFortune(Resolver):
    """Each player discards their hand, then draws seven cards"""
    def resolve(self, gs: GameState, source: GameCard, _: Optional[GameCard] = None):
        for i in (0, 1):
            for c in gs.pile_mgr.hands[i][::]:
                gs.pile_mgr.discard(c)
            gs.pile_mgr.draw(i, 7)

class WindsOfChange(Resolver):
    """Each player shuffles the cards from their hand into their library, then draws that many cards"""
    def resolve(self, gs: GameState, s: GameCard, target: Optional[GameCard] = None):
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
    def resolve(self, gs: GameState, source: GameCard, target: list[GameCard] = None):
        if not target:
            raise ValueError(f'{source.props.name} needs a list of targets')
        for t in target:
            t.tap()
            if 'Flying' in t.keyword_abilities:
                gs.apply_damage(source, 2, t)

class WoodElemental(Resolver):
    """As this creature enters, sac any number of untapped Forests. WE's PT are each = # of Forests sacrificed."""
    def resolve(self, gs: GameState, source: GameCard, target: Optional[GameCard] = None):
        from models.actions.special import WoodElementalETBAction
        your_untapped_forests = gs.card_filter.on_player_board(source.owner_id).forests().untapped().result()
        options = [WoodElementalETBAction(source.owner_id, gs, source, combo)
                   for r in range(len(your_untapped_forests)) for combo in combinations(your_untapped_forests, r=r)]
        gs.pending_choice = ChoiceAction(options)

class WormwoodTreefolkForestwalk(Resolver):
    """{GG}: This creature gains forestwalk until end of turn and deals 2 damage to you"""
    def resolve(self, gs: GameState, source: GameCard, target: GameCard = None):
        target.modifiers.append(KWAMod(s=source, add_or_remove='add', kwa='Forestwalk', expires='EOT'))
        gs.apply_damage(source, 2, source.owner_id)

class WormwoodTreefolkSwampwalk(Resolver):
    """{BB}: This creature gains swampwalk until end of turn and deals 2 damage to you"""
    def resolve(self, gs: GameState, source: GameCard, target: GameCard = None):
        target.modifiers.append(KWAMod(s=source, add_or_remove='add', kwa='Swampwalk', expires='EOT'))
        gs.apply_damage(source, 2, source.owner_id)
