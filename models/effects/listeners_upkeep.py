from __future__ import annotations

from collections import defaultdict
from itertools import combinations
from typing import TYPE_CHECKING

from models.actions.base import DoNothing
from models.actions.damage import PayLife, DealDamageTo, DealDamageToYou
from models.actions.destroy_sac_regen import (DestroyAction, Sac, AllowOpponentToDestroyALand,
                                              SacToReturnAllCardsExiledBy)
from models.actions.kwa import AddKWA
from models.actions.mana import PayMana
from models.actions.piles import TutorMultipleCards
from models.actions.pump import VariablePTMod
from models.actions.special import RogahhOfKherKeepTapAndStealAction, CyclonePayManaPerCounterDealDamage, \
    SkipDrawPhaseGainLife, PayManaAndOrTakeDamage, SacTwoIslands, YawgmothDemonUnpaidUpkeep
from models.choice_actions_all import ChoiceAction
from models.counter_tokens import PUPA, PLUS_ONE, WIND, HUNGER, DREAM
from models.effects.base import Listener
from models.effects.resolvers_generic import Steal
from models.events_all import UpkeepEvent, Event
from models.modifiers import KWAMod
from models.utils import flip
from models.zone import Zone

if TYPE_CHECKING:
    from models.game_card.game_card import GameCard
    from game_state import GameState


class BlackVise(Listener):
    """As opponent's upkeep, this artifact deals X damage to that player, X is = cards in their hand minus 4"""
    listens_to = UpkeepEvent

    def on_event(self, gs: GameState, s: GameCard, event: UpkeepEvent):
        opp_id = flip(s.owner_id)
        if event.active_player != opp_id:
            return
        opp_hand_len = len(gs.pile_mgr.hands[opp_id].cards)
        if opp_hand_len > 4:
            gs.apply_damage(s, opp_hand_len - 4, opp_id)

class CocoonUpkeep(Listener):
    """At your upkeep, remove a pupa counter from this Aura.
        If you can't, sac it, put a +1/+1 counter on enchanted creature, and that creature gains flying."""
    listens_to = UpkeepEvent

    def on_event(self, gs: GameState, source: GameCard, event: UpkeepEvent) -> None:
        p_id = gs.turn_mgr.player_turn_idx
        host = source.host
        if p_id != source.owner_id:
            return
        if host.counters.get_count(PUPA):
            host.counters.remove_counter(PUPA)
            return
        gs.pile_mgr.destroy(source)
        host.counters.add_counter(PLUS_ONE)
        host.modifiers.append(KWAMod(s=source, add_or_remove='add', kwa='Flying'))

class CosmicHorror(Listener):
    """At your upkeep, destroy unless you pay {3BBB}. If destroyed this way, it deals 7 damage to you."""
    listens_to = UpkeepEvent

    def on_event(self, gs: GameState, source: GameCard, event: UpkeepEvent):
        if gs.turn_mgr.player_turn_idx != source.owner_id:
            return
        if not gs.mana_pools[source.owner_id].can_pay('3BBB'):
            gs.pile_mgr.destroy(source)
            gs.apply_damage(source, 7, source.owner_id)
            return
        options = [DestroyAction(event.active_player, gs, source, source, False),
                   PayMana(event.active_player, gs, source, '3BBB')]
        gs.pending_choice = ChoiceAction(options)

class CurseArtifact(Listener):
    """At enchanted artifact's controller's upkeep, deal 2 damage to that player unless they sacrifice that artifact"""
    listens_to = UpkeepEvent

    def on_event(self, gs: GameState, source: GameCard, event: UpkeepEvent):
        if not source.host or gs.turn_mgr.player_turn_idx != source.host.owner_id:
            return
        options = [DealDamageTo(event.active_player, gs, source, 2, source.host.owner_id),
                   Sac(event.active_player, gs, source.host)]
        gs.pending_choice = ChoiceAction(options)

class Cyclone(Listener):
    """At your upkeep, add a wind counter, then pay {G} for each wind counter on it or sac.
    If you pay, Cyclone deals damage = its wind counters to each creature and each player."""
    listens_to = UpkeepEvent

    def on_event(self, gs: GameState, source: GameCard, event: UpkeepEvent):
        if gs.turn_mgr.player_turn_idx != source.owner_id:
            return
        source.counters.add_counter(WIND)
        if not gs.mana_pools[source.owner_id].can_pay('G' * source.counters.get_count(WIND)):
            gs.pile_mgr.destroy(source, False)
        options = [CyclonePayManaPerCounterDealDamage(source.owner_id, gs, source), Sac(source.owner_id, gs, source)]
        gs.pending_choice = ChoiceAction(options)

class DemonicHordesUpkeep(Listener):
    """... At your upkeep, pay {BBB} or tap this creature and sacrifice a land of an opponent's choice"""
    listens_to = UpkeepEvent

    def on_event(self, gs: GameState, source: GameCard, event: UpkeepEvent):
        if gs.turn_mgr.player_turn_idx != source.owner_id:
            return
        your_lands = gs.card_filter.on_player_board(source.owner_id).lands().result()
        if not your_lands:
            source.tap()
        elif len(your_lands) == 1:
            source.tap()
            gs.pile_mgr.destroy(your_lands[0])
        elif not gs.mana_pools[source.owner_id].can_pay('BBB'):
            source.tap()
            options = [DestroyAction(flip(source.owner_id), gs, source, land, False) for land in your_lands]
            gs.pending_choice = ChoiceAction(options)
        else:
            options = [PayMana(source.owner_id, gs, source, 'BBB'),
                       AllowOpponentToDestroyALand(source.owner_id, gs, source)]
            gs.pending_choice = ChoiceAction(options)

class DropOfHoney(Listener):
    """At your upkeep, destroy the creature with the least power. It can't be regenerated.
    If two or more creatures are tied for least power, you choose one. When there are no creatures on the battlefield,
    sac Drop of Honey."""
    listens_to = UpkeepEvent

    def on_event(self, gs: GameState, source: GameCard, event: UpkeepEvent) -> None:
        if gs.turn_mgr.player_turn_idx != source.owner_id:
            return
        creatures = gs.card_filter.creatures().in_play().result()
        if not creatures:
            gs.pile_mgr.destroy(source, allow_regeneration=False)
            return

        min_power = min([c.power for c in creatures])
        creatures_w_min_power = [c for c in creatures if c.power == min_power]

        if len(creatures_w_min_power) == 1:
            gs.pile_mgr.destroy(creatures_w_min_power[0], allow_regeneration=False)
            return

        options = [DestroyAction(source.owner_id, gs, source, c, allow_regen=False) for c in creatures_w_min_power]
        gs.pending_choice = ChoiceAction(options)

class ElderSpawnUpkeep(Listener):
    """At YOUR upkeep, sac an Island or sac this creature & it deals 6 damage to you."""
    listens_to = UpkeepEvent

    def on_event(self, gs: GameState, s: GameCard, event: UpkeepEvent):
        if event.active_player != s.owner_id:
            return
        your_islands = gs.card_filter.on_player_board(s.owner_id).islands().result()
        if not your_islands:
            gs.pile_mgr.destroy(s, allow_regeneration=False)
            gs.apply_damage(s, 6, s.owner_id)
            return

        options = [Sac(s.owner_id, gs, island) for island in your_islands] + [Sac(s.owner_id, gs, s, 6)]
        gs.pending_choice = ChoiceAction(options)

class EnergyFlux(Listener):
    """All artifacts have 'At your [the owner's] upkeep, sacrifice this artifact unless you pay {2}'"""
    listens_to = UpkeepEvent

    def on_event(self, gs: GameState, source: GameCard, event: UpkeepEvent):
        for your_artifact in gs.card_filter.on_player_board(event.active_player).artifacts().result():
            if not gs.mana_pools[event.active_player].can_pay('2'):
                gs.pile_mgr.destroy(your_artifact, allow_regeneration=False)
            options = [PayMana(event.active_player, gs, source, '2'), Sac(event.active_player, gs, source)]
            gs.action_stack.push(ChoiceAction(options), gs, False)

class ErhnamDjinn(Listener):
    """At your upkeep, target non-Wall creature an opponent controls gains forestwalk until your next upkeep"""
    listens_to = UpkeepEvent

    def on_event(self, gs: GameState, s: GameCard, event: UpkeepEvent):
        if event.active_player != s.owner_id:
            return
        eligible_targets = gs.card_filter.on_player_board(flip(s.owner_id)).non_wall_creatures().result()
        if not eligible_targets:
            return
        if len(eligible_targets) == 1:
            eligible_targets[0].modifiers.append(KWAMod('add', 'Forestwalk', s=s, expires='EOT'))
            return
        options = [AddKWA(s.owner_id, gs, s, t, 'Forestwalk') for t in eligible_targets]
        gs.pending_choice = ChoiceAction(options)

class ErosionUpkeep(Listener):
    """At upkeep of enchanted land's controller, destroy that land unless that player pays {1} or 1 life."""
    listens_to = UpkeepEvent

    def on_event(self, gs: GameState, source: GameCard, event: UpkeepEvent):
        if not source.host or event.active_player != source.host.owner_id:
            return
        options = []
        if gs.mana_pools[source.host.owner_id].can_pay('1'):
            options.append(PayMana(source.host.owner_id, gs, source, '1'))
        options.append(PayLife(source.host.owner_id, gs, source, 1))
        options.append(DestroyAction(source.host.owner_id, gs, source, source.host, allow_regen=False))
        gs.pending_choice = ChoiceAction(options)

class Fasting(Listener):
    """At your upkeep, add a hunger counter. Destroy Fasting if >=5 hunger counters.
    If you would begin your draw step, you may skip that step instead. If you do, you gain 2 life ..."""
    listens_to = UpkeepEvent

    def on_event(self, gs: GameState, source: GameCard, event: UpkeepEvent) -> None:
        if gs.turn_mgr.player_turn_idx != source.owner_id:
            return
        source.counters.add_counter(HUNGER)
        if source.counters.get_count(HUNGER) > 4:
            gs.pile_mgr.destroy(source)
        options = [SkipDrawPhaseGainLife(source.owner_id, gs, 2), DoNothing(source.owner_id, gs)]
        gs.pending_choice = ChoiceAction(options)

class ForceOfNatureUpkeep(Listener):
    """At your upkeep, this creature deals 8 damage to you unless you pay {GGGG}"""
    listens_to = UpkeepEvent

    def on_event(self, gs: GameState, s: GameCard, event: UpkeepEvent):
        if event.active_player != s.owner_id:
            return
        if not gs.mana_pools[s.owner_id].can_pay('GGGG'):
            gs.apply_damage(s, 8, s.owner_id)
            return
        options = [PayMana(s.owner_id, gs, s, 'GGGG'), DealDamageToYou(s.owner_id, gs, s, 8)]
        gs.pending_choice = ChoiceAction(options)

class GabrielAngelfire(Listener):
    """At your upkeep, choose flying, first strike, trample, rampage 3. GA gains that ability until your next upkeep."""
    listens_to = UpkeepEvent

    def on_event(self, gs: GameState, s: GameCard, event: UpkeepEvent):
        if event.active_player != s.owner_id:
            return
        kwa_options = ('Flying', 'First Strike', 'Trample', 'Rampage 3')
        options = [AddKWA(s.owner_id, gs, s, s, kwa) for kwa in kwa_options]
        gs.pending_choice = ChoiceAction(options)


class GhazbanOgre(Listener):
    """At your upkeep, if a player has more life than each other player,
    the player with the most life gains control of this creature (assuming "your" = the current controller)"""
    listens_to = UpkeepEvent

    def on_event(self, gs: GameState, source: GameCard, event: Event):
        if gs.turn_mgr.player_turn_idx != source.owner_id:
            return
        if len(set(gs.score_mgr.life)) == 1:
            return
        most_life_player_idx = max(range(len(gs.score_mgr.life)), key=lambda i: gs.score_mgr.life[i])
        if most_life_player_idx != source.owner_id:
            Steal().resolve(gs, source, source)


class GiantSlug(Listener):
    """At your next upkeep, this creature gains landwalk of your choice until the end of that turn."""
    listens_to = UpkeepEvent

    def on_event(self, gs: GameState, s: GameCard, event: UpkeepEvent):
        if event.active_player != s.owner_id:
            return
        kwa_options = ('Forestwalk', 'Islandwalk', 'Mountainwalk', 'Plainswalk', 'Swampwalk')
        options = [AddKWA(s.owner_id, gs, s, s, kwa) for kwa in kwa_options]
        gs.pending_choice = ChoiceAction(options)

class HazezonTamarTokenCreation(Listener):
    """Create X 1/1 Sand Warrior tokens at your next upkeep; X is the number of lands you control at that time"""
    listens_to = UpkeepEvent

    def __init__(self, owner_id: int):
        self.owner_id = owner_id

    def on_event(self, gs: GameState, source: GameCard, event: UpkeepEvent) -> None:
        if gs.turn_mgr.player_turn_idx != source.owner_id:
            return

        from .resolvers_generic import CreateTokenCreature
        for _ in gs.card_filter.lands().on_player_board(self.owner_id).result():
            CreateTokenCreature('sand-warrior').resolve(gs, source)

        gs.event_mgr.unregister_specific_effect(self)


class IvoryTower(Listener):
    """At the beginning of your upkeep, you gain X life, where X is the number of cards in your hand minus 4"""
    listens_to = UpkeepEvent

    def on_event(self, gs: GameState, source: GameCard, event: UpkeepEvent):
        p_id = source.owner_id
        if p_id != event.active_player:
            return
        if (hand_size := len(gs.pile_mgr.hands[p_id].cards)) > 4:
            gs.score_mgr.increment_life(p_id, hand_size - 4, source, gs)


class Karma(Listener):
    """At each player's upkeep, this enchantment deals damage to that player = number of Swamps they control."""
    listens_to = UpkeepEvent

    def on_event(self, gs: GameState, source: GameCard, event: UpkeepEvent):
        swamp_cnt = len(gs.card_filter.on_player_board(event.active_player).swamps().result())
        if swamp_cnt:
            gs.apply_damage(source, swamp_cnt, event.active_player)


class LandTax(Listener):
    """At your upkeep, if an opponent controls more lands than you, you may:
    search your library for up to 3 basic land cards, reveal them, put them into your hand, then shuffle"""
    listens_to = UpkeepEvent

    def on_event(self, gs: GameState, s: GameCard, event: UpkeepEvent):
        if event.active_player != s.owner_id:
            return
        your_land_cnt = len(gs.card_filter.on_player_board(s.owner_id).lands().result())
        opp_land_cnt = len(gs.card_filter.on_player_board(flip(s.owner_id)).lands().result())
        if not opp_land_cnt > your_land_cnt:
            return
        your_basic_lands = [c for c in gs.pile_mgr.libraries[s.owner_id] if c.props.is_basic_land]
        gs.add_presentation_request(s.owner_id, 'view_library', {'cards': your_basic_lands})
        basic_slug_lands = defaultdict(list)
        for c in your_basic_lands:
            if len(basic_slug_lands.get(c.props.slug)) < 3:
                basic_slug_lands[c.props.slug].append(c)
        basic_lands = [c for slug, cards in basic_slug_lands.items() for c in cards]
        combo_set = {combo for r in range(1, 4) for combo in combinations(basic_lands, r)}
        options = ([TutorMultipleCards(s.owner_id, gs, list(combo), Zone.HAND) for combo in combo_set] +
                   [DoNothing(s.owner_id, gs)])
        gs.pending_choice = ChoiceAction(options)

class LordOfThePitUpkeep(Listener):
    """At your upkeep, sacrifice a different creature. If you can't, this creature deals 7 damage to you."""
    listens_to = UpkeepEvent

    def on_event(self, gs: GameState, source: GameCard, event: UpkeepEvent):
        if event.active_player != source.owner_id:
            return
        your_other_creatures = [c for c in gs.card_filter.on_player_board(source.owner_id).creatures().result()
                                if c is not source]
        if not your_other_creatures:
            gs.apply_damage(source, 7, source.owner_id)
            return
        options = [Sac(source.owner_id, gs, c) for c in your_other_creatures]
        gs.pending_choice = ChoiceAction(options)


class ManaVortexUpkeep(Listener):
    """At each player's upkeep, they sac a land. If no lands on entire battlefield, sac this enchantment."""
    listens_to = UpkeepEvent

    def on_event(self, gs: GameState, source: GameCard, event: UpkeepEvent):
        if len(gs.card_filter.lands().in_play().result()) == 0:
            gs.pile_mgr.destroy(source)
            return
        your_lands = gs.card_filter.on_player_board(gs.turn_mgr.player_turn_idx).lands().result()
        options = [Sac(event.active_player, gs, land) for land in your_lands]
        gs.pending_choice = ChoiceAction(options)

class PowerLeak(Listener):
    """At host owner's upkeep, host owner may pay 0, 1, or 2 mana. PL deals 2 - the mana paid damage to host owner"""
    listens_to = UpkeepEvent

    def on_event(self, gs: GameState, source: GameCard, event: UpkeepEvent) -> None:
        host_owner = source.host.owner_id
        if event.active_player != host_owner:
            return
        available_mana_cnt = gs.mana_pools[host_owner].get_max_x('')
        if available_mana_cnt == 0:
            pay_mana_options = (0, )
        elif available_mana_cnt == 1:
            pay_mana_options = (0, 1)
        else:
            pay_mana_options = (0, 1, 2)
        options = [PayManaAndOrTakeDamage(host_owner, gs, source, mana_amt, 2 - mana_amt)
                   for mana_amt in pay_mana_options]
        gs.pending_choice = ChoiceAction(options)

class PowerSurge(Listener):
    """At the beginning of each player's upkeep, this enchantment deals X damage to that player,
        where X is the number of untapped lands they controlled at the beginning of this turn"""
    listens_to = UpkeepEvent

    def on_event(self, gs: GameState, source: GameCard, event: UpkeepEvent):
        untapped_lands = gs.card_filter.in_play().untapped().lands().result()
        if untapped_lands:
            gs.apply_damage(source, len(untapped_lands), gs.turn_mgr.player_turn_idx)


class PsychicAllergyDamage(Listener):
    """At opp's upkeep, deal X damage to that opponent. X is their number of nontoken perms of the chosen color"""
    listens_to = UpkeepEvent

    def on_event(self, gs: GameState, source: GameCard, event: UpkeepEvent) -> None:
        if gs.turn_mgr.player_turn_idx == source.owner_id:
            return
        declared_color = source.extras.get('color_declaration')
        opp = flip(source.owner_id)
        cnt = gs.card_filter.on_player_board(opp).by_color(declared_color).non_token().permanents().result()
        if cnt:
            gs.apply_damage(source, cnt, opp)


class PsychicAllergySac(Listener):
    """... At your upkeep, destroy this enchantment unless you sacrifice two Islands"""
    listens_to = UpkeepEvent

    def on_event(self, gs: GameState, source: GameCard, event: UpkeepEvent):
        if gs.turn_mgr.player_turn_idx != source.owner_id:
            return
        your_islands = gs.card_filter.on_player_board(source.owner_id).islands().result()
        if len(your_islands) < 2:
            gs.pile_mgr.destroy(source)
            return
        options = [SacTwoIslands(source.owner_id, gs, source), Sac(source.owner_id, gs, source)]
        gs.pending_choice = ChoiceAction(options)

class RasputinDreamweaverUpkeep(Listener):
    """... At your upkeep, if RD STARTED THE TURN untapped w < 7 dream counters on it, put a dream counter on it."""
    listens_to = UpkeepEvent

    def on_event(self, gs: GameState, source: GameCard, event: UpkeepEvent) -> None:
        if source.extras.get('started_this_turn_untapped') is None:
            return
        if source.extras['started_this_turn_untapped'] and source.counters.get_count(DREAM) < 7:
            source.counters.add_counter(DREAM)


class RogahhOfKherKeepUpkeep(Listener):
    """... At your upkeep, pay {RRR}, else tap Rohgahh & all Kobolds of Kher Keep. Opponent gains control of them."""
    listens_to = UpkeepEvent

    def on_event(self, gs: GameState, source: GameCard, event: UpkeepEvent):
        if gs.turn_mgr.player_turn_idx != source.owner_id or source.props.slug != 'rogahh-of-kher-keep':
            return
        owner = source.owner_id
        target_cards = [source] + gs.card_filter.on_player_board(owner).by_slug('kobolds-of-kher-keep').result()
        action = RogahhOfKherKeepTapAndStealAction(source.owner_id, gs, source, target_cards)
        if not gs.mana_pools[source.owner_id].can_pay('RRR'):
            action.play()
            return
        options = [action, PayMana(source.owner_id, gs, source, 'RRR')]
        gs.pending_choice = ChoiceAction(options)

class SafeHavenUpkeep(Listener):
    """At your upkeep, you may sacrifice SH to return all cards it exiled to the battlefield under owner's control"""
    listens_to = UpkeepEvent

    def on_event(self, gs: GameState, source: GameCard, event: UpkeepEvent) -> None:
        if event.active_player != source.owner_id:
            return
        options = [SacToReturnAllCardsExiledBy(source.owner_id, gs, source, source), DoNothing(source.owner_id, gs)]
        gs.pending_choice = ChoiceAction(options)

class SeasonOfTheWitchUpkeep(Listener):
    """At your upkeep, sacrifice this enchantment unless you pay 2 life"""
    listens_to = UpkeepEvent

    def on_event(self, gs: GameState, source: GameCard, event: UpkeepEvent):
        if event.active_player != source.owner_id:
            return
        options = [PayLife(source.owner_id, gs, source, 2), Sac(source.owner_id, gs, source)]
        gs.pending_choice = ChoiceAction(options)

class SerendibDjinn(Listener):
    """At your upkeep, sac a land. If it's an Island, 3 damage to you. When you control no lands, sac this creature."""
    listens_to = UpkeepEvent

    def on_event(self, gs: GameState, source: GameCard, event: UpkeepEvent):
        if event.active_player != source.owner_id:
            return
        options = [Sac(source.owner_id, gs, land, w_damage_amt=3 if land.props.slug == 'island' else 0)
                   for land in gs.card_filter.on_player_board(source.owner_id).lands().result()]
        gs.pending_choice = ChoiceAction(options)

class ShapeshifterUpkeep(Listener):
    """At cast & at your upkeep, choose a number 0-7 (n). Shapeshifter's power = n, toughness = 7 - n"""
    listens_to = UpkeepEvent

    def on_event(self, gs: GameState, source: GameCard, event: UpkeepEvent):
        if event.active_player != source.owner_id:
            return
        options = [VariablePTMod(source.owner_id, gs, source, source, i, 7 - i) for i in range(8)]
        gs.pending_choice = ChoiceAction(options)

class SpiritualSanctuary(Listener):
    """At each player's upkeep, if that player controls a Plains, they gain 1 life"""
    listens_to = UpkeepEvent

    def on_event(self, gs: GameState, source: GameCard, event: UpkeepEvent):
        if 'plains' in gs.card_filter.on_player_board(event.active_player).plains().result():
            gs.score_mgr.increment_life(event.active_player, 1, source, gs)

class StormWorld(Listener):
    """At the beginning of each player's upkeep, this enchantment deals X damage to that player,
        where X is 4 minus the number of cards in their hand"""
    listens_to = UpkeepEvent

    def on_event(self, gs: GameState, source: GameCard, event: UpkeepEvent):
        card_cnt = len(gs.pile_mgr.hands[gs.turn_mgr.player_turn_idx].cards)
        if card_cnt > 4:
            gs.apply_damage(source, card_cnt - 4, gs.turn_mgr.player_turn_idx)


class TheAbyss(Listener):
    """At each upkeep, destroy target nonartifact creature that player controls of their choice. No regeneration."""
    listens_to = UpkeepEvent

    def on_event(self, gs: GameState, source: GameCard, event: UpkeepEvent):
        p_id = event.active_player
        your_non_art_creatures = gs.card_filter.on_player_board(p_id).non_artifact_creatures().result()
        if not your_non_art_creatures:
            return
        if len(your_non_art_creatures) == 1:
            options = [DestroyAction(p_id, gs, source, your_non_art_creatures[0], False)]
        else:
            options = [DestroyAction(p_id, gs, source, c, False) for c in your_non_art_creatures]
        gs.pending_choice = ChoiceAction(options)


class TheFallen(Listener):
    """At your upkeep, this creature deals 1 damage to your opponent if it has previously damaged him/her this game"""
    listens_to = UpkeepEvent

    def on_event(self, gs: GameState, source: GameCard, event: UpkeepEvent) -> None:
        if event.active_player != source.owner_id:
            return

        from .listeners_damage import DamageResolvedEvent
        for e in gs.event_mgr.events:
            if isinstance(e, DamageResolvedEvent) and e.source is source and e.target == flip(source.owner_id):
                gs.apply_damage(source, 1, flip(source.owner_id))


class TheRack(Listener):
    """At opponent's upkeep, this artifact deals X damage to that player, X = 3 - len(hand) [X can't be negative]"""
    listens_to = UpkeepEvent

    def on_event(self, gs: GameState, s: GameCard, event: UpkeepEvent):
        opp_id = flip(s.owner_id)
        if event.active_player != opp_id:
            return
        opp_hand_len = len(gs.pile_mgr.hands[opp_id].cards)
        if opp_hand_len < 3:
            gs.apply_damage(s, 3 - opp_hand_len, opp_id)


class TheTabernacleAtPendrellVale(Listener):
    """All creatures have 'At your upkeep, destroy this creature unless you pay {1}.'"""
    listens_to = UpkeepEvent

    def on_event(self, gs: GameState, source: GameCard, event: UpkeepEvent):
        for your_creature in gs.card_filter.on_player_board(event.active_player).creatures().result():
            if not gs.mana_pools[event.active_player].can_pay('1'):
                gs.pile_mgr.destroy(your_creature, allow_regeneration=False)
            options = [PayMana(event.active_player, gs, source, '1'), Sac(event.active_player, gs, source)]
            gs.action_stack.push(ChoiceAction(options), gs, False)


class VesuvanDoppelgangerUpkeep(Listener):
    """You may have this creature enter as a copy of any creature on the battlefield,
    except it doesn't copy that creature's color & you may select a different creature on each of your upkeeps"""
    listens_to = UpkeepEvent

    def on_event(self, gs: GameState, s: GameCard, event: UpkeepEvent):
        if gs.turn_mgr.player_turn_idx != s.owner_id:
            return
        card_options = [c for c in gs.card_filter.in_play().creatures().result() if c is not s]
        if not card_options:
            return
        from models.actions.special import CopyCard
        options = [CopyCard(s.owner_id, gs, s, card, copy_color=False) for card in card_options]
        gs.pending_choice = ChoiceAction(options)


class XenicPoltergeistRelease(Listener):
    """{T}: Until your NEXT upkeep, target noncreature artifact becomes an artifact creature with PT each = its MV.
    This effect removes the registered listener at the next upkeep"""
    # TODO: This effect unregisterer should persist even if Xenic Poltergeist leaves battlefield
    listens_to = UpkeepEvent

    def on_event(self, gs: GameState, source: GameCard, event: UpkeepEvent) -> None:
        if gs.turn_mgr.player_turn_idx != source.owner_id:
            return
        gs.event_mgr.unregister_effects(source)


class YawgmothDemon(Listener):
    """At your upkeep, Sac an artifact, or tap this creature & it deals 2 damage to you"""
    listens_to = UpkeepEvent

    def on_event(self, gs: GameState, s: GameCard, event: UpkeepEvent):
        if event.active_player != s.owner_id:
            return
        your_artifacts = gs.card_filter.on_player_board(s.owner_id).artifacts().result()
        if not your_artifacts:
            s.tap()
            gs.apply_damage(s, 2, s.owner_id)
            return
        options = [Sac(s.owner_id, gs, a) for a in your_artifacts] + [YawgmothDemonUnpaidUpkeep(s.owner_id, gs, s)]
        gs.pending_choice = ChoiceAction(options)
