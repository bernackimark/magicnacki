from __future__ import annotations
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from models.game_card.game_card import GameCard
    from game_state import GameState

from models.actions.destroy_sac_regen import DestroyAction, TheAbyssAction
from models.actions.special import RogahhOfKherKeepTapAndStealAction
from models.actions.tap_untap import LeaveTapped
from models.choice_actions_all import FloralSpuzzemChoice, CosmicHorrorUpkeepChoice, CurseArtifactUpkeepChoice, CycloneChoice, OpponentDestroysLandChoice, \
    DemonicHordesUpkeepChoice, ElderSpawnUpkeepChoice, PayManaOrSacUpkeepChoice, ErhnamDjinnChoice, ErosionUpkeepChoice, \
    ForceOfNatureUpkeepChoice, LandTaxChoice, LordOfThePitUpkeepChoice, SacChoice, PsychicAllergyUpkeepChoice, \
    RogahhOfKherKeepUpkeepChoice, PayLifeOrSacChoice, CopyCardChoice, YawgmothDemonChoice, MoldDemonChoice, \
    DrawCardsOrDontChoice, GabrielAngelfireChoice, GiantSlugChoice
from models.counter_tokens import PLUS_ONE, PIN, MINUS_ZERO_TWO, WIND
from models.effects.base import Listener
from models.effects.resolvers_generic import Steal
from models.events_all import EndStepEvent, LifeLossEvent, StateBasedEvent, TapCardEvent, \
    UnblockedAttackerEvent, UntapPhaseEvent, UpkeepEvent, Event, ZoneChangeEvent, CanUntapQueryEvent, AttackEvent, \
    CastResolvedEvent
from models.modifiers import PTMod
from models.utils import flip
from models.zone import Zone

# --- CAN UNTAP QUERY EVENT ---
class GoblinRockSledUntap(Listener):
    """This creature doesn't untap during your untap step if it attacked during your last turn"""
    listens_to = CanUntapQueryEvent

    def on_event(self, gs: GameState, source: GameCard, event: CanUntapQueryEvent) -> None:
        if source is not event.card:
            return
        p_last_turn_num = gs.turn_mgr.get_players_last_turn_num(source.owner_id)
        for e, turn_num in gs.event_mgr.events[::-1]:
            if turn_num == p_last_turn_num:
                if isinstance(e, AttackEvent) and e.attacker is source:
                    event.permission = False

# --- CAST RESOLVED EVENT ---
class IchneumonDruid(Listener):
    """Whenever an opponent casts their non-first instant spell that turn, ID deals 4 damage to that player."""
    listens_to = CastResolvedEvent

    def on_event(self, gs: GameState, source: GameCard, event: CastResolvedEvent) -> None:
        opp = flip(source.owner_id)
        instants_cast_in_turn = len([e for e in gs.event_mgr.get_turn_events(gs.turn_mgr.turn_number)
                                    if isinstance(e, CastResolvedEvent) and e.owner_id == opp
                                    and 'Instant' in e.card.card_types])
        if instants_cast_in_turn > 1:
            gs.apply_damage(source, 4, opp)

# --- END STEP ---
class DragonWhelpEndStep(Listener):
    """If this [pump] ability has been activated 4+ times this turn, sac at end step."""
    listens_to = EndStepEvent

    def on_event(self, gs: GameState, s: GameCard, event: EndStepEvent):
        if len([temp for temp in s.modifiers.items if temp.source is s]) >= 4:
            gs.pile_mgr.destroy(s, allow_regeneration=False)

class ErgRaiders(Listener):
    """At YOUR end step, except for summoning sickness, if this creature didn't attack, 2 damage to you"""
    listens_to = EndStepEvent

    def on_event(self, gs: GameState, s: GameCard, event: EndStepEvent):
        if gs.turn_mgr.player_turn_idx != s.owner_id or s.has_summoning_sickness:
            return
        if s not in gs.card_filter.attackers().result():
            gs.apply_damage(s, 2, s.owner_id)

class InfiniteAuthorityEndStep(Listener):
    """At end step, if [that other] creature was destroyed [this] way, put a +1/+1 counter on host."""
    listens_to = EndStepEvent

    def on_event(self, gs: GameState, source: GameCard, event: EndStepEvent) -> None:
        from models.events_all import DiesEvent
        if not source.host:
            return
        other_combatants = gs.card_filter.combating_against(source.host).result()
        for e in gs.event_mgr.get_turn_events(gs.turn_mgr.turn_number):
            if isinstance(e, DiesEvent) and e.card in other_combatants:
                source.host.counters.add_counter(PLUS_ONE)

class PestilenceEndStep(Listener):
    """At the beginning of the end step, if no creatures are on the battlefield, sacrifice this enchantment"""
    listens_to = EndStepEvent

    def on_event(self, gs: GameState, source: GameCard, event: EndStepEvent):
        if not gs.card_filter.creatures().in_play().result():
            gs.pile_mgr.destroy(source)

class SeasonOfTheWitchEndStep(Listener):
    """At YOUR end step, destroy all untapped creatures that didn't attack this turn, except those who 'couldn't'.
    Note: I'm defining 'couldn't' = summoning sickness or has Defender"""
    listens_to = EndStepEvent

    def on_event(self, gs: GameState, s: GameCard, event: EndStepEvent):
        if gs.turn_mgr.player_turn_idx != s.owner_id:
            return
        your_untapped_creatures = gs.card_filter.on_player_board(s.owner_id).creatures().untapped().result()
        attackers = gs.card_filter.attackers().result()
        for creature in your_untapped_creatures:
            if creature in attackers:
                continue
            if creature.has_summoning_sickness or 'Defender' in creature.keyword_abilities:
                continue
            gs.pile_mgr.destroy(creature)

class VoodooDollEndStep(Listener):
    """At your end step, if untapped, destroy this card & it deals damage to you = to the # of pin counters on it"""
    listens_to = EndStepEvent

    def on_event(self, gs: GameState, source: GameCard, event: EndStepEvent):
        if gs.turn_mgr.player_turn_idx != source.owner_id:
            return
        if source.is_tapped:
            return
        if pin_cnt := source.counters.get_count(PIN) > 0:
            gs.apply_damage(source, pin_cnt, source.owner_id)
        gs.pile_mgr.destroy(source)

class WhirlingDervish(Listener):
    """At each end step, if this creature dealt damage to an opponent this turn, put a +1/+1 counter on it"""
    listens_to = EndStepEvent

    def on_event(self, gs: GameState, source: GameCard, event: EndStepEvent) -> None:
        from models.events_all import DamageResolvedEvent
        for e in gs.event_mgr.get_turn_events(gs.turn_mgr.turn_number):
            if isinstance(e, DamageResolvedEvent) and e.source is source and e.target == flip(source.owner_id):
                source.counters.add_counter(PLUS_ONE)
                return

# --- LIFE LOSS ---
class AliFromCairo(Listener):
    """Damage that would reduce your life total to less than 1 reduces it to 1 instead"""
    listens_to = LifeLossEvent

    def on_event(self, gs: GameState, s: GameCard, event: LifeLossEvent):
        if event.p_id_taking_damage != s.owner_id:
            return

        current_life = gs.score_mgr.life[event.p_id_taking_damage]

        if current_life - event.amt < 1:
            event.amt = max(current_life - 1, 0)


# --- STATE CHANGE ---
class GoblinsOfTheFlarg(Listener):
    """When you control a Dwarf, sacrifice this creature"""
    listens_to = StateBasedEvent

    def on_event(self, gs: GameState, source: GameCard, event: StateBasedEvent):
        if source.props.slug != 'goblins-of-the-flarg':
            return None

        if gs.card_filter.on_player_board(source.owner_id).by_sub_type('Dwarf').result():
            gs.pile_mgr.destroy(source, allow_regeneration=False)

class JihadSac(Listener):
    """When the chosen player controls no nontoken permanents of the chosen color, sacrifice this enchantment"""
    listens_to = StateBasedEvent

    def on_event(self, gs: GameState, source: GameCard, event: StateBasedEvent) -> None:
        declared_color = source.extras.get('color_declaration')
        opp = flip(source.owner_id)
        if not gs.card_filter.on_player_board(opp).by_color(declared_color).non_token().permanents().result():
            gs.pile_mgr.destroy(source, allow_regeneration=False)

class SerendibDjinnNoLands(Listener):
    """When you control no lands, sacrifice this creature"""
    listens_to = StateBasedEvent

    def on_event(self, gs: GameState, source: GameCard, event: StateBasedEvent):
        your_lands = gs.card_filter.on_player_board(source.owner_id).lands().result()
        if not your_lands:
            print(f'Player #{source.owner_id} has no lands, so Serendib Djinn is destroyed')
            gs.pile_mgr.destroy(source, allow_regeneration=False)

# --- TAP EVENT ---
class Blight(Listener):
    """Enchant land; When enchanted land becomes tapped, destroy it."""
    listens_to = TapCardEvent

    def on_event(self, gs: GameState, source: GameCard, event: TapCardEvent):
        if not source.host or source.props.slug != 'blight' or event.card is not source.host:
            return
        gs.pile_mgr.destroy(source.host)


class CityOfBrassDamageOnTap(Listener):
    """Whenever this land becomes tapped, it deals 1 damage to you"""
    listens_to = TapCardEvent

    def on_event(self, gs: GameState, source: GameCard, event: TapCardEvent):
        if event.card is not source:
            return
        gs.apply_damage(source, 1, source.owner_id)


class Lifeblood(Listener):
    """Whenever a Mountain an opponent controls becomes tapped, you gain 1 life."""
    listens_to = TapCardEvent

    def on_event(self, gs: GameState, s: GameCard, event: TapCardEvent):
        if event.card.owner_id == s.owner_id:
            return
        if 'Mountain' in event.card.card_sub_types:
            gs.score_mgr.increment_life(s.owner_id, 1, s, gs)


class Lifetap(Listener):
    """Whenever a Forest an opponent controls becomes tapped, you gain 1 life."""
    listens_to = TapCardEvent

    def on_event(self, gs: GameState, s: GameCard, event: TapCardEvent):
        if event.card.owner_id == s.owner_id:
            return
        if 'Forest' in event.card.card_sub_types:
            gs.score_mgr.increment_life(s.owner_id, 1, s, gs)


class PsychicVenom(Listener):
    """Whenever enchanted land becomes tapped, this Aura deals 2 damage to that land's controller"""
    listens_to = TapCardEvent

    def on_event(self, gs: GameState, s: GameCard, event: TapCardEvent):
        if event.card is not s.host:
            return
        gs.apply_damage(s, 2, event.card.owner_id)


class SpiritShackle(Listener):
    """Whenever enchanted creature becomes tapped, put a -0/-2 counter on it"""
    listens_to = TapCardEvent

    def on_event(self, gs: GameState, s: GameCard, event: TapCardEvent):
        if event.card is not s.host:
            return
        s.host.counters.add_counter(MINUS_ZERO_TWO)


class WildGrowth(Listener):
    """Enchant land Whenever enchanted land is tapped for mana, its controller adds another {G}"""
    listens_to = TapCardEvent

    def on_event(self, gs: GameState, source: GameCard, event: TapCardEvent):
        if source.host is not event.card:
            return
        gs.mana_pools[event.card.owner_id].add_floating('G')


# --- UNBLOCKED ---
class FloralSpuzzem(Listener):
    """Whenever this creature walks, you may destroy target opp artifact instead of dealing the combat damage."""
    listens_to = UnblockedAttackerEvent

    def on_event(self, gs: GameState, s: GameCard, event: UnblockedAttackerEvent):
        if event.attacker != s or not gs.card_filter.on_player_board(flip(s.owner_id)).artifacts().result():
            return
        gs.action_stack.push(FloralSpuzzemChoice(s.owner_id, gs, s), gs, False)


class MerchantShip(Listener):
    """Whenever this creature attacks and isn't blocked, you gain 2 life"""
    listens_to = UnblockedAttackerEvent

    def on_event(self, gs: GameState, s: GameCard, event: UnblockedAttackerEvent):
        if event.attacker != s:
            return
        gs.score_mgr.increment_life(s.owner_id, 2, s, gs)


class MurkDwellers(Listener):
    """Whenever this creature attacks and isn't blocked, it gets +2/+0 until end of combat"""
    listens_to = UnblockedAttackerEvent

    def on_event(self, gs: GameState, s: GameCard, event: UnblockedAttackerEvent):
        if event.attacker != s:
            return
        s.modifiers.append(PTMod(s=s, p_adj=2, expires='EOT'))


# --- UNTAP PHASE ---
class MagneticMountainOnUntapStep(Listener):
    """Blue creatures don't untap during their controllers' untap steps"""
    listens_to = UntapPhaseEvent

    def on_event(self, gs: GameState, s: GameCard, event: UntapPhaseEvent):
        if event.active_player != s.owner_id:
            return
        if s in gs.card_filter.on_player_board(event.active_player).blue().creatures().result():
            gs.action_stack.push(LeaveTapped(s.owner_id, gs, s), gs, False)

class TimeVaultOption(Listener):
    """If you would begin your turn while this artifact is tapped, you may skip that turn instead."""
    listens_to = UntapPhaseEvent

    def on_event(self, gs: GameState, source: GameCard, event: UntapPhaseEvent) -> None:
        if source.owner_id != event.active_player or not source.is_tapped:
            return
        from models.choice_actions_all import TimeVaultChoice
        gs.action_stack.push(TimeVaultChoice(source.owner_id, gs, source), False)

# --- UPKEEP ---
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
        gs.action_stack.push(CosmicHorrorUpkeepChoice(source.owner_id, gs, source), gs, False)

class CurseArtifact(Listener):
    """At enchanted artifact's controller's upkeep, deal 2 damage to that player unless they sacrifice that artifact"""
    listens_to = UpkeepEvent

    def on_event(self, gs: GameState, source: GameCard, event: UpkeepEvent):
        if not source.host or gs.turn_mgr.player_turn_idx != source.host.owner_id:
            return
        gs.action_stack.push(CurseArtifactUpkeepChoice(gs.turn_mgr.player_turn_idx, gs, source), gs, False)

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
        gs.action_stack.push(CycloneChoice(source.owner_id, gs, source), gs, False)

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
            gs.action_stack.push(OpponentDestroysLandChoice(flip(source.owner_id), gs, source))
        else:
            gs.action_stack.push(DemonicHordesUpkeepChoice(source.owner_id, gs, source), gs, False)

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

        from models.choice_actions_all import DestroyChoice
        gs.pending_choice = DestroyChoice(source.owner_id, gs, source, creatures_w_min_power, allow_regen=False)

class ElderSpawnUpkeep(Listener):
    """At YOUR upkeep, sac an Island or sac this creature & it deals 6 damage to you."""
    listens_to = UpkeepEvent

    def on_event(self, gs: GameState, s: GameCard, event: UpkeepEvent):
        if gs.turn_mgr.player_turn_idx != s.owner_id:
            return
        gs.action_stack.push(ElderSpawnUpkeepChoice(gs.turn_mgr.player_turn_idx, gs, s), gs, False)

class EnergyFlux(Listener):
    """All artifacts have 'At your [the owner's] upkeep, sacrifice this artifact unless you pay {2}'"""
    listens_to = UpkeepEvent

    def on_event(self, gs: GameState, source: GameCard, event: UpkeepEvent):
        for your_artifact in gs.card_filter.on_player_board(gs.turn_mgr.player_turn_idx).artifacts().result():
            gs.action_stack.push(PayManaOrSacUpkeepChoice(gs.turn_mgr.player_turn_idx, gs, your_artifact, '2'), gs, False)

class ErhnamDjinn(Listener):
    """At your upkeep, target non-Wall creature an opponent controls gains forestwalk until your next upkeep"""
    listens_to = UpkeepEvent

    def on_event(self, gs: GameState, s: GameCard, event: UpkeepEvent):
        if gs.turn_mgr.player_turn_idx != s.owner_id:
            return
        gs.pending_choice = ErhnamDjinnChoice(s.owner_id, gs, s)

class ErosionUpkeep(Listener):
    """At upkeep of enchanted land's controller, destroy that land unless that player pays {1} or 1 life."""
    listens_to = UpkeepEvent

    def on_event(self, gs: GameState, source: GameCard, event: UpkeepEvent):
        if not source.host or gs.turn_mgr.player_turn_idx != source.host.owner_id:
            return
        gs.action_stack.push(ErosionUpkeepChoice(gs.turn_mgr.player_turn_idx, gs, source), gs, False)

class ForceOfNatureUpkeep(Listener):
    """At your upkeep, this creature deals 8 damage to you unless you pay {GGGG}"""
    listens_to = UpkeepEvent

    def on_event(self, gs: GameState, s: GameCard, event: UpkeepEvent):
        if gs.turn_mgr.player_turn_idx != s.owner_id:
            return
        gs.action_stack.push(ForceOfNatureUpkeepChoice(s.owner_id, gs, s, 'GGGG', 8), gs, False)

class GabrielAngelfire(Listener):
    """At your upkeep, choose flying, first strike, trample, rampage 3. GA gains that ability until your next upkeep."""
    listens_to = UpkeepEvent

    def on_event(self, gs: GameState, s: GameCard, event: UpkeepEvent):
        if gs.turn_mgr.player_turn_idx != s.owner_id:
            return
        gs.pending_choice = GabrielAngelfireChoice(s.owner_id, gs, s)

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
        if gs.turn_mgr.player_turn_idx != s.owner_id:
            return
        gs.pending_choice = GiantSlugChoice(s.owner_id, gs, s)

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

    def on_event(self, gs: GameState, source: GameCard, event: UpkeepEvent):
        if gs.turn_mgr.player_turn_idx != source.owner_id:
            return
        your_land_cnt = len(gs.card_filter.on_player_board(source.owner_id).lands().result())
        opp_land_cnt = len(gs.card_filter.on_player_board(flip(source.owner_id)).lands().result())
        if not opp_land_cnt > your_land_cnt:
            return
        gs.pending_choice = LandTaxChoice(source.owner_id, gs, source)


class LordOfThePitUpkeep(Listener):
    """At your upkeep, sacrifice a different creature. If you can't, this creature deals 7 damage to you."""
    listens_to = UpkeepEvent

    def on_event(self, gs: GameState, source: GameCard, event: UpkeepEvent):
        if event.active_player != source.owner_id:
            return
        choice_obj = LordOfThePitUpkeepChoice(gs.turn_mgr.player_turn_idx, gs, source)
        if not choice_obj.get_actions():
            gs.apply_damage(source, 7, source.owner_id)
            return
        gs.action_stack.push(choice_obj, gs, False)


class ManaVortexUpkeep(Listener):
    """At each player's upkeep, they sac a land. If no lands on entire battlefield, sac this enchantment."""
    listens_to = UpkeepEvent

    def on_event(self, gs: GameState, source: GameCard, event: UpkeepEvent):
        if len(gs.card_filter.lands().in_play().result()) == 0:
            gs.pile_mgr.destroy(source)
            return
        your_lands = gs.card_filter.on_player_board(gs.turn_mgr.player_turn_idx).lands().result()
        gs.action_stack.push(SacChoice(gs.turn_mgr.player_turn_idx, gs, source, your_lands), gs, False)


class PowerSurge(Listener):
    """At the beginning of each player's upkeep, this enchantment deals X damage to that player,
        where X is the number of untapped lands they controlled at the beginning of this turn"""
    listens_to = UpkeepEvent

    def on_event(self, gs: GameState, source: GameCard, event: UpkeepEvent):
        untapped_lands = gs.card_filter.in_play().untapped().lands().result()
        if untapped_lands:
            gs.apply_damage(source, len(untapped_lands), gs.turn_mgr.player_turn_idx)


class PsychicAllergyUpkeep(Listener):
    """... At your upkeep, destroy this enchantment unless you sacrifice two Islands"""
    listens_to = UpkeepEvent

    def on_event(self, gs: GameState, source: GameCard, event: UpkeepEvent):
        if gs.turn_mgr.player_turn_idx != source.owner_id:
            return
        your_island_cnt = len([i for i in gs.card_filter.on_player_board(source.owner_id).islands().result()])
        if your_island_cnt < 2:
            gs.pile_mgr.destroy(source)
            return
        possible_actions = PsychicAllergyUpkeepChoice(gs.turn_mgr.player_turn_idx, gs, source).get_actions()
        for action in possible_actions:
            gs.action_stack.push(action, gs, False)


class RogahhOfKherKeepUpkeep(Listener):
    """... At your upkeep, pay {RRR} or else ..."""
    listens_to = UpkeepEvent

    def on_event(self, gs: GameState, source: GameCard, event: UpkeepEvent):
        if gs.turn_mgr.player_turn_idx != source.owner_id or source.props.slug != 'rogahh-of-kher-keep':
            return
        owner = source.owner_id
        target_cards = [source] + gs.card_filter.on_player_board(owner).by_slug('kobolds-of-kher-keep').result()
        if gs.mana_pools[source.owner_id].can_pay('RRR'):
            gs.action_stack.push(RogahhOfKherKeepUpkeepChoice(source.owner_id, gs, source, target_cards), gs, False)
        else:
            action = RogahhOfKherKeepTapAndStealAction(source.owner_id, gs, source, targets=target_cards)
            action.play()


class SeasonOfTheWitchUpkeep(Listener):
    """At your upkeep, sacrifice this enchantment unless you pay 2 life"""
    listens_to = UpkeepEvent

    def on_event(self, gs: GameState, source: GameCard, event: UpkeepEvent):
        if event.active_player != source.owner_id:
            return
        gs.action_stack.push(PayLifeOrSacChoice(source.owner_id, gs, source, 2), gs, False)


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
            gs.action_stack.push(DestroyAction(p_id, gs, source, your_non_art_creatures[0], False), gs, False)
        gs.action_stack.push(TheAbyssAction(p_id, gs, source), gs, False)

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
        for your_creature in gs.card_filter.on_player_board(gs.turn_mgr.player_turn_idx).creatures().result():
            gs.action_stack.push(PayManaOrSacUpkeepChoice(gs.turn_mgr.player_turn_idx, gs, your_creature, '1'))


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
        gs.pending_choice = CopyCardChoice(s.owner_id, gs, s, card_options, copy_color=False)


class YawgmothDemon(Listener):
    """At your upkeep, Sac an artifact, or tap this creature, and it deals 2 damage to you"""
    listens_to = UpkeepEvent

    def on_event(self, gs: GameState, source: GameCard, event: UpkeepEvent):
        if source.owner_id != gs.turn_mgr.player_turn_idx:
            return
        if not gs.card_filter.on_player_board(source.owner_id).artifacts().result():
            source.tap()
            gs.apply_damage(source, 2, source.owner_id)
            return
        gs.action_stack.push(YawgmothDemonChoice(source.owner_id, gs, source), gs, False)


# --- ZONE CHANGE ---
class AnkhOfMishra(Listener):
    """Whenever a land enters, this artifact deals 2 damage to that land's controller"""
    listens_to = ZoneChangeEvent

    def on_event(self, gs: GameState, source: GameCard, event: ZoneChangeEvent):
        if event.to_zone != Zone.BATTLEFIELD or not event.card.props.is_land:
            return
        gs.apply_damage(source, 2, event.card.owner_id)


class CitanulDruid(Listener):
    """Whenever an opponent casts an artifact spell, put a +1/+1 counter on this creature"""
    listens_to = ZoneChangeEvent

    def on_event(self, gs: GameState, source: GameCard, event: ZoneChangeEvent):
        if event.to_zone != Zone.BATTLEFIELD or 'Artifact' not in event.card.props.card_types:
            return
        source.counters.add_counter(PLUS_ONE)

class DingusEgg(Listener):
    """Whenever a land is put into a graveyard from battlefield, deal 2 damage to that land's controller."""
    listens_to = ZoneChangeEvent

    def on_event(self, gs: GameState, source: GameCard, event: ZoneChangeEvent):
        if event.to_zone != Zone.GRAVEYARD or event.from_zone != Zone.BATTLEFIELD or not event.card.props.is_land:
            return
        gs.apply_damage(source, 2, event.card.owner_id)

class FieldOfDreams(Listener):
    """Players play with the top card of their libraries revealed"""
    listens_to = ZoneChangeEvent

    def on_event(self, gs: GameState, source: GameCard, event: ZoneChangeEvent):
        if Zone.LIBRARY not in (event.to_zone, event.from_zone):
            return
        player_idx = event.card.owner_id
        if gs.pile_mgr.libraries[player_idx]:
            gs.pile_mgr.libraries[player_idx][0].reveal()

class GoblinShrineOnLeave(Listener):
    """... When this Aura leaves the battlefield, it deals 1 damage to each Goblin creature"""
    listens_to = ZoneChangeEvent

    def on_event(self, gs: GameState, source: GameCard, event: ZoneChangeEvent):
        if event.from_zone != Zone.BATTLEFIELD or event.card.props.slug != 'goblin-shrine':
            return
        for goblin in gs.card_filter.in_play().by_sub_type('Goblin').creatures().result():
            gs.apply_damage(event.card, 1, goblin)

class HazezonTamarLTB(Listener):
    """When HT LTB, ALL permanents with BOTH the Sand AND Warrior types are exiled, not just those it created"""
    listens_to = ZoneChangeEvent

    def on_event(self, gs: GameState, source: GameCard, event: ZoneChangeEvent) -> None:
        if event.from_zone != Zone.BATTLEFIELD or event.card is not source:
            return
        for sand_warrior in gs.card_filter.in_play().by_sub_type('Sand').by_sub_type('Warrior').result():
            gs.pile_mgr.destroy(sand_warrior, allow_regeneration=False)

class Kismet(Listener):
    """Artifacts, creatures, and lands your opponents control enter tapped"""
    listens_to = ZoneChangeEvent

    def on_event(self, gs: GameState, s: GameCard, event: ZoneChangeEvent):
        if event.card.owner_id != flip(s.owner_id) or event.to_zone != Zone.BATTLEFIELD:
            return
        artifacts = gs.card_filter.on_player_board(flip(s.owner_id)).artifacts().result()
        creatures = gs.card_filter.on_player_board(flip(s.owner_id)).creatures().result()
        lands = gs.card_filter.on_player_board(flip(s.owner_id)).lands().result()
        if event.card not in artifacts + creatures + lands:
            return
        event.card.tap()

class LandEquilibrium(Listener):
    """If an opponent who controls at least as many lands as you do would put a land onto the battlefield,
    that player instead puts that land onto the battlefield then sacrifices a land of their choice"""
    listens_to = ZoneChangeEvent

    def on_event(self, gs: GameState, source: GameCard, event: ZoneChangeEvent):
        if source.owner_id == event.card.owner_id or event.card not in gs.card_filter.land().result():
            return
        your_land_cnt = len(gs.card_filter.on_player_board(source.owner_id).lands().result())
        opp_lands = gs.card_filter.on_player_board(event.card.owner_id).lands().result()
        if len(opp_lands) < your_land_cnt:
            return
        gs.action_stack.push(SacChoice(event.card.owner_id, gs, source, opp_lands), gs, False)

class MoldDemonETB(Listener):
    """When this creature enters, sacrifice this creature unless you sacrifice two Swamps"""
    listens_to = ZoneChangeEvent

    def on_event(self, gs: GameState, source: GameCard, event: ZoneChangeEvent):
        if source is not event.card or event.to_zone != Zone.BATTLEFIELD:
            return
        your_swamps = gs.card_filter.on_player_board(source.owner_id).swamps().result()
        if len(your_swamps) < 2:
            gs.pile_mgr.destroy(event.card, False)
        gs.action_stack.push(MoldDemonChoice(gs.turn_mgr.player_turn_idx, gs, source, your_swamps), gs, False)


class Revelation(Listener):
    """Players play with their hands revealed"""
    listens_to = ZoneChangeEvent

    def on_event(self, gs: GameState, source: GameCard, event: ZoneChangeEvent):
        if event.to_zone != Zone.HAND:
            return
        event.card.reveal()


class StanggOnLeave(Listener):
    """Exile that Stangg Twin token when Stangg leaves the battlefield; sacrific Stangg when Stangg Twin LTB"""
    listens_to = ZoneChangeEvent

    def on_event(self, gs: GameState, source: GameCard, event: ZoneChangeEvent):
        if event.card.props.slug not in ('stangg', 'stangg-twin') or event.card.owner_id != source.owner_id:
            return
        if event.from_zone != Zone.BATTLEFIELD:
            return
        other_slug = 'stangg-twin' if event.card.props.slug == 'stangg' else 'stangg'
        other_card = gs.card_filter.on_player_board(event.card.owner_id).by_slug(other_slug).result()[0]
        gs.pile_mgr.destroy(other_card)

class TheWretchedUnsteal(Listener):
    """... gain control of creatures UNTIL Wretched LTB or you don't control Wretched."""
    listens_to = ZoneChangeEvent

    def on_event(self, gs: GameState, source: GameCard, event: ZoneChangeEvent) -> None:
        # TODO: Since a ZoneChangeEvent doesn't capture steals ...
        #  if The Wretched itself is stolen, I still need to return the stolen creatures
        if event.card is not source or event.from_zone is not Zone.BATTLEFIELD:
            return

        from models.modifiers import OwnershipMod
        for c in gs.pile_mgr.boards[source.owner_id]:
            for mod in c.auras:
                if isinstance(mod, OwnershipMod) and mod.s is source:
                    c.modifiers.remove(mod)
                    gs.pile_mgr.boards[source.owner_id].remove(c)
                    gs.pile_mgr.boards[flip(source.owner_id)].append(c)
                    break

class VerduranEnchantress(Listener):
    """Whenever you cast an enchantment spell, you may draw a card"""
    listens_to = ZoneChangeEvent

    def on_event(self, gs: GameState, source: GameCard, event: ZoneChangeEvent):
        if source.owner_id != event.card.owner_id or event.card not in gs.card_filter.enchantments().result():
            return
        gs.action_stack.push(DrawCardsOrDontChoice(source.owner_id, gs, source), gs, False)
