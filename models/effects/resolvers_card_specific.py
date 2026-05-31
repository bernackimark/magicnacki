from __future__ import annotations
import math
import random
from typing import TYPE_CHECKING, Optional, Literal

from models.actions.special import SacCreatureAndAddMana
from models.actions.tap_untap import LeaveTapped
from models.effects.query_card_mods import ArmyOfAllahEOT, BoneFluteEOT, HellSwarmEOT, HolyLightEOT, MarshGasEOT, \
    MoraleEOT, PietyEOT, ShieldWallEOT, TransmutationEOT
from models.phase_manager import Phase

if TYPE_CHECKING:
    from game_state import GameState
    from models.game_card.game_card import GameCard

from models.actions.draw_discard import DiscardCard
from models.choice_actions_all import DiscardChoice, SearchLibraryChoice, NaturalSelectionChoice, ShuffleOrDontChoice, \
    CopyCardChoice, PrimalClayChoice, TriassicEggChoice, FastingChoice, HealingSalveChoice, RemoveCounterForLifeChoice, \
    SerendibDjinnUpkeepChoice, ShapeshifterChoice, DrawCardsOrDontChoice, PayLifeOrDiscardChoice
from models.counter_tokens import STORAGE, PUPA, PLUS_ONE, MINUS_ZERO_ONE, HUNGER, VITALITY, SLEEP
from models.damage import PreventNextDamage
from models.effects.base import Resolver
from models.effects.listeners_card_specific import GlyphOfDoomListener, GlyphOfLifeListener, \
    SandalsOfAbdallahIfCreatureDies
from models.effects.resolvers_generic import GraveyardToExile, CreateTokenCreature
from models.effects.queries import TowerOfCoireallEOT, NoAttacksAllowedEOT
from models.modifiers import SubTypeMod, KWAMod, PTMod
from models.utils import flip
from models.zone import Zone


class GlyphOfDoom(Resolver):
    """On cast, select a wall.  Register GlyphOfDoomListener."""
    def resolve(self, gs: GameState, source: GameCard, target: Optional[GameCard] = None):
        if not target:
            raise ValueError(f'{source.props.name} needs a target')
        temp_effect = GlyphOfDoomListener(target)
        gs.event_mgr.register_effect_until_eot((temp_effect, source))


class GlyphOfLife(Resolver):
    """On cast, select a wall.  Register GlyphOfLifeListener."""
    def resolve(self, gs: GameState, source: GameCard, target: Optional[GameCard] = None):
        if not target:
            raise ValueError(f'{source.props.name} needs a target')
        temp_effect = GlyphOfLifeListener(target)
        gs.event_mgr.register_effect_until_eot((temp_effect, source))


class TowerOfCoireall(Resolver):
    """{T}: Target creature can't be blocked by Walls this turn"""
    def resolve(self, gs: GameState, source: GameCard, target: GameCard = None):
        if not target:
            raise ValueError(f'{source.props.name} needs a target')
        temp_effect = TowerOfCoireallEOT(target)
        gs.event_mgr.register_effect_until_eot((temp_effect, source))


class CityOfShadowsAA1(Resolver):
    """{T}, Exile a creature you control: Put a storage counter on this land"""
    def resolve(self, gs: GameState, source: GameCard, target: GameCard = None):
        source.counters.add_counter(STORAGE)


class CityOfShadowsAA2(Resolver):
    """{T}: Add {C} for each storage counter on this land"""
    def resolve(self, gs: GameState, source: GameCard, target: GameCard = None):
        cnt = len(source.counters.get_count(STORAGE))
        gs.mana_pools[source.owner_id].add_floating('C', cnt)


class CocoonCast(Resolver):
    def resolve(self, gs: GameState, source: GameCard, target=None):
        target.tap(gs)
        source.counters.add_counter(PUPA, 3)


class RockHydraCast(Resolver):
    """This creature enters with X +1/+1 counters on it ..."""
    def resolve(self, gs: GameState, source: GameCard, target=None):
        if x := getattr(source, 'variable_x', 0):  # read X chosen when casting
            source.counters.add_counter(PLUS_ONE, x)


class Banshee(Resolver):
    """{X}, {T}: This creature deals half X damage, rounded down, to any target, and half X damage, rounded up to you"""
    def resolve(self, gs: GameState, s: GameCard, t: Optional[GameCard] = None):
        if not t:
            raise ValueError(f'{s.props.name} needs a target')
        damage_to_target = s.variable_x // 2
        damage_to_you = s.variable_x - damage_to_target
        gs.apply_damage(s, damage_to_target, t)
        gs.apply_damage(s, damage_to_you, s.owner_id)
        s.variable_x = None


class Earthquake(Resolver):
    """Earthquake deals X damage to each creature without flying and each player"""
    def resolve(self, gs: GameState, source: GameCard, target: Optional[GameCard] = None):
        x = getattr(source, 'variable_x', 0)  # read X chosen when casting
        for c in gs.card_filter.in_play().has('Flying', False).creatures().result():
            gs.apply_damage(source, x, c)
        for p_id in (0, 1):
            gs.apply_damage(source, x, p_id)


class EternalFlame(Resolver):
    """X = # of mountains caster controls; deal x damage to opponent and round(x/2) to caster"""
    def resolve(self, gs: GameState, source: GameCard, target: Optional[GameCard] = None):
        x = len(gs.card_filter.on_player_board(gs.turn_mgr.player_turn_idx).mountains().result())
        gs.apply_damage(source, x, flip(gs.turn_mgr.player_turn_idx))
        gs.apply_damage(source, math.ceil(x/2), gs.turn_mgr.player_turn_idx)


class EyeForAnEye(Resolver):
    """The next time a source of your choice would deal damage to you this turn, also deal damage to source's owner."""
    # Handling this in an interesting way to work within current framework:
    # Prevent all damage via gs.damage_preventions, then apply the damage here via the callback
    def resolve(self, gs: GameState, s: GameCard, t: Optional[GameCard] = None):
        """target = the GameCard doing the original damage"""
        def deal_damage(prevented: int):
            gs.apply_damage(t, prevented, s.owner_id)
            gs.apply_damage(s, prevented, t.owner_id)

        gs.damage_preventions.append(
            PreventNextDamage(s, None, target_player=s.owner_id, source_card=t, on_prevent=deal_damage))


class GaseousForm(Resolver):
    """Prevent all combat damage that would be dealt this turn by enchanted creature and each creature blocking it."""
    # TODO: THIS IS ALL DAMAGE ALWAYS.  DO I HANDLE THIS SOMEWHERE IN DAMAGE PREVENTION?
    def resolve(self, gs: GameState, s: GameCard, target: Optional[GameCard] = None):
        """target = the enchanted attacker"""
        the_combat = [com for com in gs.combats if com.attacker == target]
        if not the_combat:
            return
        gs.damage_preventions.append(PreventNextDamage(s, None, target_card=target, combat_only=True))
        for b in the_combat[0].blockers:
            gs.damage_preventions.append(PreventNextDamage(s, None, target_card=b, combat_only=True))


class JovialEvil(Resolver):
    """deals X damage to target opponent, where X is twice the number of white creatures that player controls"""
    def resolve(self, gs: GameState, source: GameCard, target: Optional[GameCard] = None):
        # target = opponent_id
        opp_white_creature_cnt = len(gs.card_filter.on_player_board(target).creatures().result())
        gs.apply_damage(source, opp_white_creature_cnt * 2, target)


class Sandstorm(Resolver):
    """Sandstorm deals 1 damage to each attacking creature.
    [from Google: it only hits creatures already attacking when it resolves.]"""
    def resolve(self, gs: GameState, source: GameCard, target: Optional[GameCard] = None):
        for attacker in gs.card_filter.attackers().result():
            gs.apply_damage(source, 1, attacker)


class StormSeeker(Resolver):
    """Storm Seeker deals damage to target player equal to the number of cards in that player's hand"""
    def resolve(self, gs: GameState, source: GameCard, t: Optional[GameCard] = None):
        opp_idx = flip(source.owner_id)
        gs.apply_damage(source, len(gs.pile_mgr.hands[opp_idx].cards), opp_idx)


class Tracker(Resolver):
    """Tracker deals damage = its power to target creature. That creature deals damage = its power to this creature."""
    def resolve(self, gs: GameState, source: GameCard, target: GameCard = None):
        if not target:
            raise ValueError(f'{source.props.name} needs a target')
        gs.apply_damage(source, source.power, target)
        gs.apply_damage(target, target.power, source)


class Typhoon(Resolver):
    """Typhoon deals damage to opponent = the number of Islands that player controls"""
    def resolve(self, gs: GameState, s: GameCard, t: Optional[GameCard] = None):
        opp = flip(gs.turn_mgr.player_turn_idx)
        opp_island_cnt = len(gs.card_filter.on_player_board(opp).islands().result())
        if opp_island_cnt:
            gs.apply_damage(s, opp_island_cnt, opp)


class AshesToAshes(Resolver):
    """Exile two target nonartifact creatures. Ashes to Ashes deals 5 damage to you."""
    def resolve(self, gs: GameState, source: GameCard, target: list[GameCard] = None):
        if not target:
            raise ValueError(f'{source.props.name} needs a target')
        for t in target:
            gs.pile_mgr.exile(t)
        gs.apply_damage(source, 5, source.owner_id)


class DustToDust(Resolver):
    """Exile two target artifacts"""
    def resolve(self, gs: GameState, source: GameCard, target: list[GameCard] = None):
        if not target:
            raise ValueError(f'{source.props.name} needs a target')
        for t in target:
            gs.pile_mgr.exile(t)


class EaterOfTheDead(Resolver):
    """Exile target creature card from a graveyard and untap this creature"""
    def resolve(self, gs: GameState, source: GameCard, target: GameCard = None):
        if not target:
            raise RuntimeError(f'{source.props.name} needs a target')
        GraveyardToExile().resolve(gs, source, target)
        gs.untap_card(source)


class Millstone(Resolver):
    """{2}, {T}: Target player mills two cards"""
    def resolve(self, gs: GameState, source: GameCard, target: int = None):
        if not target:
            raise ValueError(f'{source.props.name} needs a player to target')
        for _ in range(2):
            top_card = gs.pile_mgr.libraries[target][0]  # Warning: if no cards, this pukes
            gs.pile_mgr.move_card(top_card, Zone.GRAVEYARD, cause='mill')


class BazaarOfBaghdad(Resolver):
    """Draw two cards, then discard three cards"""
    def resolve(self, gs: GameState, source: GameCard, target: Optional[GameCard] = None):
        gs.pile_mgr.draw(source.owner_id, 2)
        gs.pending_choice = DiscardChoice(source.owner_id, gs, source, source.owner_id, 3, 3)


class Braingeyser(Resolver):
    def resolve(self, gs: GameState, source: GameCard, target: int = None):
        if target is not None:
            x = getattr(source, 'variable_x', 0)  # read X chosen when casting
            gs.pile_mgr.draw(target, x)


class DemonicTutor(Resolver):
    """Search your library for a card, put that card into your hand, then shuffle"""
    def resolve(self, gs: GameState, source: GameCard, target=None):
        p_id = source.owner_id
        gs.pending_choice = SearchLibraryChoice(p_id, gs, source, list(gs.pile_mgr.libraries[p_id]), Zone.HAND)


class GlassesOfUrza(Resolver):
    """Look at opponent's hand"""
    def resolve(self, gs: GameState, source: GameCard, target: int = None):
        for c in gs.pile_mgr.hands[flip(source.owner_id)].cards:
            c.reveal()


class GwendlynDiCorci(Resolver):
    """{T}: Target player discards a card at random. Activate only during your turn"""
    def resolve(self, gs: GameState, source: GameCard, target: int = None):
        if not target:
            raise ValueError(f'{source.props.name} needs a target')
        cards = gs.pile_mgr.hands[target].cards
        if not cards:
            return
        if len(cards) == 1:
            gs.pile_mgr.discard(cards[0], source)
            return
        random_card: GameCard = gs.randomize_event(target, cards)
        gs.pile_mgr.discard(random_card, source)


class JalumTome(Resolver):
    """Draw a card, then discard a card"""
    def resolve(self, gs: GameState, source: GameCard, target: Optional[GameCard] = None):
        gs.pile_mgr.draw(source.owner_id)
        gs.pending_choice = DiscardChoice(source.owner_id, gs, source, source.owner_id)


class MindTwist(Resolver):
    """Target player discards X cards at random"""
    def resolve(self, gs: GameState, source: GameCard, target: int = None):
        x = getattr(source, 'variable_x', 0)  # read X chosen when casting
        opp_id = flip(source.owner_id)
        opp_cards = gs.pile_mgr.hands[opp_id].cards
        if not opp_cards:
            return
        if len(opp_cards) <= x:
            for c in opp_cards:
                gs.pile_mgr.discard(c, source)
            return
        for _ in range(x):
            random_card: GameCard = gs.randomize_event(opp_id, opp_cards)
            gs.pile_mgr.discard(random_card, source)


class NaturalSelection(Resolver):
    """Look at the top 3 cards of target player's library, put them back in any order. You may shuffle."""
    def resolve(self, gs: GameState, source: GameCard, target: int = None):
        if not target:
            raise ValueError(f'{source.props.name} needs a target')
        top_3_cards = gs.pile_mgr.libraries[target][:3]
        gs.add_presentation_request(source.owner_id, 'show_library', {'cards': top_3_cards})
        gs.pending_choice = NaturalSelectionChoice(source.owner_id, gs, source, target, top_3_cards)


class RagMan(Resolver):
    """Opponent reveals their hand and discards a creature card at random. Activate only during your turn."""
    def resolve(self, gs: GameState, source: GameCard, target: int = None):
        if target is None:
            raise ValueError(f'{source.props.name} needs a target player')
        opp_cards = gs.pile_mgr.hands[target].cards
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


class Visions(Resolver):
    """Look at the top five cards of target player's library. You may then have that player shuffle that library."""
    def resolve(self, gs: GameState, source: GameCard, target: int = None):
        if target is None:
            raise ValueError(f'{source.props.name} needs a target player')
        for c in gs.pile_mgr.libraries[target][:5]:
            print('Showing you', c)
        gs.pending_choice = ShuffleOrDontChoice(target, gs, source, gs.pile_mgr.libraries[target])


class WheelOfFortune(Resolver):
    """Each player discards their hand, then draws seven cards"""
    def resolve(self, gs: GameState, source: GameCard, target: Optional[GameCard] = None):
        for i in (0, 1):
            [DiscardCard(i, gs, card).play() for card in gs.pile_mgr.hands[i].cards]
            gs.pile_mgr.draw(i, 7)


class Clone(Resolver):
    """You may have this creature enter as a copy of any creature on the battlefield;
    pushes valid targets to the stack for user selection, which then calls an Action that copies select target attrs"""
    def resolve(self, gs: GameState, s: GameCard, t: GameCard = None):
        card_options = [c for c in gs.card_filter.in_play().creatures().result() if c is not s]
        if not card_options:
            return
        gs.pending_choice = CopyCardChoice(s.owner_id, gs, s, card_options)


class CopyArtifact(Resolver):
    """You may have this enchantment enter as a copy of any artifact on the battlefield,
    except it's an enchantment in addition to its other types"""
    def resolve(self, gs: GameState, s: GameCard, t: GameCard = None):
        card_options = [c for c in gs.card_filter.in_play().artifacts().result() if c is not s]
        if not card_options:
            return
        gs.pending_choice = CopyCardChoice(s.owner_id, gs, s, card_options)


class EvilPresence(Resolver):
    """Enchant land Enchanted land is a Swamp"""

    def resolve(self, gs, source: GameCard, target: Optional[GameCard] = None):
        if target is None:
            raise ValueError(f'{source.props.name} needs a target')
        sub_types = target.card_sub_types.copy()
        target.modifiers.append(SubTypeMod(s=source, add_or_remove='add', card_sub_type='Swamp'))
        for sub_type in sub_types:
            target.modifiers.append(SubTypeMod(s=source, add_or_remove='remove', card_sub_type=sub_type))


class PhantasmalTerrain(Resolver):
    """Enchant land As this Aura enters, choose a basic land type. Enchanted land is the chosen type"""
    def __init__(self, land_type: Literal['Swamp', 'Island', 'Forest', 'Mountain', 'Plains']):
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
        gs.pending_choice = PrimalClayChoice(s.owner_id, gs, s)


class VesuvanDoppelgangerCast(Resolver):
    """You may have this creature enter as a copy of any creature on the battlefield,
    except it doesn't copy that creature's color & you may select a different creature on each of your upkeeps"""
    def resolve(self, gs: GameState, s: GameCard, t: GameCard = None):
        if gs.turn_mgr.player_turn_idx != s.owner_id:
            return
        card_options = [c for c in gs.card_filter.in_play().creatures().result() if c is not s]
        if not card_options:
            return
        gs.pending_choice = CopyCardChoice(s.owner_id, gs, s, card_options, copy_color=False)


class RapidFire(Resolver):
    """Cast this spell only before blockers are declared. Target creature gains first strike until end of turn.
    If it doesn't have rampage, that creature gains rampage 2 until end of turn."""
    def resolve(self, gs: GameState, source: GameCard, target: Optional[GameCard] = None):
        if not target:
            raise ValueError(f'{source.props.name} needs a target')
        target.modifiers.append(KWAMod(s=source, add_or_remove='add', kwa='First Strike', expires='EOT'))
        if not target.rampage_amt:
            target.modifiers.append(KWAMod(s=source, add_or_remove='add', kwa='Rampage 2', expires='EOT'))


class SandalsOfAbdallahIslandWalk(Resolver):
    """{T}: Target creature gains islandwalk until end of turn. When that creature dies this turn, destroy Sandals."""
    def resolve(self, gs: GameState, source: GameCard, target: Optional[GameCard] = None):
        if not target:
            raise ValueError(f'{source.props.name} needs a target')
        target.modifiers.append(KWAMod(s=source, add_or_remove='add', kwa='Islandwalk', expires='EOT'))

        temp_effect = SandalsOfAbdallahIfCreatureDies(target_creature=target)
        gs.register_effect_until_eot((temp_effect, source))


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


class StreamOfLife(Resolver):
    def resolve(self, gs: GameState, source: GameCard, target: int = None):
        x = getattr(source, 'variable_x', 0)  # read X chosen when casting
        gs.score_mgr.increment_life(target, x, source, gs)


class DrainPower(Resolver):
    """Target player activates a mana ability of each land they control.
    Then that player loses all unspent mana & you add the mana lost this way."""
    def resolve(self, gs: GameState, source: GameCard, target: Optional[int] = None):
        """target = player_id whose available mana will be targeted & given to the other player"""
        if target is None:
            raise ValueError(f'{source.props.name} needs a target')
        land_giver_mana = gs.mana_pools[target].available_mana.copy()
        for color, amt in land_giver_mana.items():
            gs.mana_pools[source.owner_id].add_floating(color, amt)


class EnergyTap(Resolver):
    """Tap target untapped creature you control to add an amount of {C} equal to that creature's mana value."""
    def resolve(self, gs: GameState, source: GameCard, target: Optional[GameCard] = None):
        if target is None:
            return
        gs.tap_card(target)
        gs.mana_pools[source.owner_id].add_floating('C', source.props.mana_value)
        print(f"{source} taps to add {source.props.mana_value} colorless to your mana pool.")


class ExchangeLifeTotals(Resolver):
    def resolve(self, gs: GameState, s: GameCard, _: Optional[GameCard] = None):
        your_life = gs.score_mgr.life[s.owner_id]
        opp_life = gs.score_mgr.life[flip(s.owner_id)]
        gs.score_mgr.life[s.owner_id], gs.score_mgr.life[flip(s.owner_id)] = opp_life, your_life


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


class GraveRobbersAA(Resolver):
    """{B}, {T}: Exile target artifact card from a graveyard. You gain 2 life."""
    def resolve(self, gs: GameState, source: GameCard, target: GameCard = None):
        GraveyardToExile().resolve(gs, source, target)
        gs.score_mgr.increment_life(source.owner_id, 2, source, gs)


class TimeElementalBounce(Resolver):
    """... {2UU}, {T}: Return target unenchanted permanent to its owner's hand"""
    def resolve(self, gs: GameState, source: GameCard, target: GameCard = None):
        gs.pile_mgr.bounce(target)


class TriassicEgg(Resolver):
    """Choose one:
    * You may put a creature card from your hand onto the battlefield.
    * Return target creature card from your graveyard to the battlefield."""
    def resolve(self, gs: GameState, source: GameCard, _: Optional[GameCard] = None):
        gs.action_stack.push(TriassicEggChoice(source.owner_id, gs, source), gs, False)


class ArmyOfAllah(Resolver):
    """Attacking creatures get +2/0 until end of turn"""
    def resolve(self, gs: GameState, source: GameCard, target: Optional[GameCard] = None):
        gs.register_effect_until_eot((ArmyOfAllahEOT(), source))


class BerserkPump(Resolver):
    """Cast this spell only before the combat damage step.
    Target creature gains trample and gets +X/+0 until end of turn, where X is its power.
    At the beginning of the next end step, destroy that creature if it attacked this turn."""
    def resolve(self, gs: GameState, source: GameCard, target: Optional[GameCard] = None):
        if not target:
            raise RuntimeError(f'{source.props.name} needs a target')
        target.modifiers.append(PTMod(s=source, p_adj=int(target.power) * 2, expires='EOT'))
        target.modifiers.append(KWAMod(s=source, add_or_remove='add', kwa='Trample', expires='EOT'))


class BloodLust(Resolver):
    """Target creature gains +4/-4 until end of turn. If this reduces creature's toughness < 1, toughness = 1."""
    def resolve(self, gs, source: GameCard, target: Optional[GameCard] = None):
        if not target:
            raise RuntimeError(f'{source.props.name} needs a target')
        new_toughness = max(1, target.toughness - 4)
        toughness_mod = new_toughness - target.toughness
        target.modifiers.append(PTMod(s=source, p_adj=4, t_adj=toughness_mod, expires='EOT'))


class BoneFlute(Resolver):
    """All creatures get -1/-0 until end of turn"""
    def resolve(self, gs: GameState, source: GameCard, target: Optional[GameCard] = None):
        gs.register_effect_until_eot((BoneFluteEOT(), source))


class GreatDefender(Resolver):
    def resolve(self, gs, source: GameCard, target: Optional[GameCard] = None):
        """Target creature gets +0/+X until end of turn, where X is its mana value."""
        if target:
            target.modifiers.append(PTMod(s=source, t_adj=target.props.mana_value, expires='EOT'))


class HellSwarm(Resolver):
    """All creatures get -1/-0 until end of turn"""
    def resolve(self, gs: GameState, source: GameCard, target: Optional[GameCard] = None):
        gs.register_effect_until_eot((HellSwarmEOT(), source))


class HolyLight(Resolver):
    """Nonwhite creatures get -1/-1 until end of turn"""
    def resolve(self, gs: GameState, source: GameCard, target: Optional[GameCard] = None):
        gs.register_effect_until_eot((HolyLightEOT(), source))


class HowlFromBeyond(Resolver):
    """Target creature gets +X/+0 until end of turn"""
    def resolve(self, gs: GameState, source: GameCard, target: GameCard = None):
        if target is not None:
            x = getattr(source, 'variable_x', 0)  # read X chosen when casting
            target.modifiers.append(PTMod(s=source, p_adj=x, expires='EOT'))


class LesserWerewolf(Resolver):
    """If this creature's power is >= 1, it gets -1/-0 until EOT & put a -0/-1 counter on
    target creature blocking/blocked by this creature. Activate only during the declare blockers step."""
    def resolve(self, gs: GameState, source: GameCard, target: Optional[GameCard] = None):
        if source.power < 1:
            return
        source.modifiers.append(PTMod(s=source, p_adj=-1, expires='EOT'))
        target.counters.add_counter(MINUS_ZERO_ONE)


class MarshGas(Resolver):
    """All creatures get -2/-0 until end of turn"""
    def resolve(self, gs: GameState, source: GameCard, target: Optional[GameCard] = None):
        gs.register_effect_until_eot((MarshGasEOT(), source))


class Morale(Resolver):
    """Attacking creatures get +1/+1 until end of turn"""
    def resolve(self, gs: GameState, source: GameCard, target: Optional[GameCard] = None):
        gs.register_effect_until_eot((MoraleEOT(), source))


class Piety(Resolver):
    """Blocking creatures get 0/+3 until end of turn"""
    def resolve(self, gs: GameState, source: GameCard, target: Optional[GameCard] = None):
        gs.register_effect_until_eot((PietyEOT(), source))


class ShieldWall(Resolver):
    """Creatures you control get +0/+2 until end of turn"""
    def resolve(self, gs: GameState, source: GameCard, target: Optional[GameCard] = None):
        gs.register_effect_until_eot((ShieldWallEOT(), source))


class SingingTree(Resolver):
    """Target attacking creature has base power 0 until end of turn"""
    def resolve(self, gs: GameState, source: GameCard, target: Optional[GameCard] = None):
        if not target:
            raise ValueError(f'{source.props.name} needs a target')
        target.modifiers.append(PTMod(s=source, p_adj=-target.base_pt[0], expires='EOT'))


class Transmutation(Resolver):
    """Switch target creature's power and toughness until end of turn"""
    def resolve(self, gs: GameState, source: GameCard, target: GameCard = None):
        if not target:
            raise ValueError(f'{source.props.name} needs a target')
        gs.register_effect_until_eot((TransmutationEOT(), source))


class AshnodsTransmogrant(Resolver):
    """{T}, Sacrifice this artifact: Put a +1/+1 counter on target nonartifact creature.
    That creature becomes an artifact in addition to its other types."""
    def resolve(self, gs: GameState, s: GameCard, t: GameCard = None):
        if not t:
            raise RuntimeError(f'{s.props.name} needs a target')
        t.counters.add_counter(PLUS_ONE)
        t.card_types.append('Artifact')


class ActiveVolcano(Resolver):
    """Choose one - * Destroy target blue permanent. * Return target Island to its owner's hand."""
    def resolve(self, gs: GameState, s: GameCard, t: GameCard = None):
        gs.pile_mgr.bounce(t) if t.props.slug == 'island' else gs.pile_mgr.destroy(t)


class Amnesia(Resolver):
    """Target player reveals their hand and discards all nonland cards"""
    def resolve(self, gs: GameState, source: GameCard, target: int = None):
        if not target:
            raise ValueError(f'{source.props.name} needs a target')
        for c in gs.pile_mgr.hands[target].cards[:]:
            c.reveal()
            if 'Land' not in c.card_types:
                gs.pile_mgr.discard(c, source)


class AnimateDead(Resolver):
    def resolve(self, gs: GameState, source: GameCard, target: GameCard = None):
        if not target:
            raise ValueError(f'{source.props.name} needs a target')
        gs.pile_mgr.reanimate(target)
        target.modifiers.append(PTMod(s=source, p_adj=-1, t_adj=0))


class BookOfRass(Resolver):
    def resolve(self, gs: GameState, source: GameCard, target: GameCard = None):
        gs.apply_damage(source, 2, source.owner_id)
        gs.pile_mgr.draw(source.owner_id)


class BottleOfSuleiman(Resolver):
    """{1}, Sac: Flip a coin. If you win the flip, create a 5/5 colorless Djinn artifact creature token with flying.
    If you lose the flip, this artifact deals 5 damage to you."""
    def resolve(self, gs: GameState, s: GameCard, _: GameCard = None):
        result: str = gs.randomize_event(s.owner_id, ['heads', 'tails'])
        if result == 'heads':
            obj = CreateTokenCreature('djinn')
            obj.resolve(gs, s)
            # gs.create_token_creature(s.owner_id, 'Djinn', 5, 5, ['Flying', 'Attack'],
            #                          other_types=[], sub_types=['Djinn'], colors='C')
        else:
            gs.apply_damage(s, 5, s.owner_id)


class ChaosOrb(Resolver):
    """{1}, {T}, Sac: Choose an opponent's non-token permanent. If random di roll is 1-4, destroy target."""
    def resolve(self, gs: GameState, s: GameCard, t: GameCard = None):
        if not t:
            raise ValueError(f'{s.props.name} needs a target')
        result: int = gs.randomize_event(s.owner_id, [1, 2, 3, 4, 5, 6])
        if result <= 4:
            gs.pile_mgr.destroy(t)


class CocoonUpkeep(Resolver):
    """At your upkeep, remove a pupa counter from this Aura.
        If you can't, sac it, put a +1/+1 counter on enchanted creature, and that creature gains flying."""
    def resolve(self, gs: GameState, source: GameCard, target=None):
        p_id = gs.turn_mgr.player_turn_idx
        host = source.host
        if p_id != source.owner_id:
            return
        if not host.counters.get_count(PUPA):
            gs.pile_mgr.destroy(source)
            host.counters.add_counter(PLUS_ONE)
            host.modifiers.append(KWAMod(s=source, add_or_remove='add', kwa='Flying'))
            return
        host.counters.remove_counter(PUPA)


class Crumble(Resolver):
    def resolve(self, gs: GameState, source: GameCard, target: Optional[GameCard] = None):
        if target:
            gs.pile_mgr.destroy(target, allow_regeneration=False)
            gs.score_mgr.increment_life(target.owner_id, target.props.mana_value, source, gs)


class DivineOffering(Resolver):
    def resolve(self, gs, source: GameCard, target: Optional[GameCard] = None):
        if not target:
            raise ValueError(f"{source.props.name} needs a target")
        gs.pile_mgr.destroy(target)
        gs.score_mgr.increment_life(source.owner_id, target.props.mana_value, source, gs)


class Earthbind(Resolver):
    def resolve(self, gs: GameState, source: GameCard, target: Optional[GameCard] = None):
        if target:
            target.modifiers.append(KWAMod(s=source, add_or_remove='remove', kwa='Flying'))
        if 'Flying' in target.keyword_abilities:
            gs.apply_damage(source, 2, target.owner_id)


class ElectricEel(Resolver):
    def resolve(self, gs: GameState, source: GameCard, target: Optional[GameCard] = None):
        source.modifiers.append(PTMod(s=source, p_adj=2, expires='EOT'))
        gs.apply_damage(source, 1, source.owner_id)


class ElvesOfTheDeepShadow(Resolver):
    def resolve(self, gs: GameState, source: GameCard, target: Optional[GameCard] = None):
        gs.mana_pools[source.owner_id].add_floating('B')
        gs.apply_damage(source, 1, source.owner_id)


class FallingStar(Resolver):
    """Select an opponent's creature. If a di roll is 1-5, deal 3 damage to it"""
    def resolve(self, gs: GameState, s: GameCard, t: GameCard = None):
        if not t:
            raise ValueError(f'{s.props.name} needs a target')
        result: int = gs.randomize_event(s.owner_id, [1, 2, 3, 4, 5, 6])
        print(f'The roll is a: {result}')
        if result <= 5:
            gs.apply_damage(s, 3, t)


class Fasting(Resolver):
    def resolve(self, gs: GameState, source: GameCard, target=None):
        if gs.turn_mgr.player_turn_idx != source.owner_id:
            return
        source.counters.add_counter(HUNGER)
        if source.counters.get_count(HUNGER) > 4:
            gs.pile_mgr.destroy(source)
        gs.action_stack.push(FastingChoice(source.owner_id, gs, source), gs, False)


class Feint(Resolver):
    """Tap all creatures blocking target attacking creature.
        Prevent all combat damage that would be dealt this turn by that creature and each creature blocking it."""
    def resolve(self, gs: GameState, s: GameCard, target: Optional[GameCard] = None):
        """target = the attacker"""
        the_combat = [com for com in gs.combats if com.attacker == target]
        if not the_combat:
            return
        gs.damage_preventions.append(PreventNextDamage(s, None, target_card=target, combat_only=True))
        for b in the_combat[0].blockers:
            gs.damage_preventions.append(PreventNextDamage(s, None, target_card=b, combat_only=True))
            b.tap(gs)


class FeldonsCane(Resolver):
    """{T}, Exile this artifact: Shuffle your graveyard into your library."""
    def resolve(self, gs: GameState, s: GameCard, target: Optional[GameCard] = None):
        gy = gs.pile_mgr.graveyards[s.owner_id]
        lib = gs.pile_mgr.libraries[s.owner_id]
        lib.extend(gy)
        gy.clear()
        random.shuffle(lib)


class Festival(Resolver):
    """... Creatures can't attack this turn"""
    def resolve(self, gs: GameState, source: GameCard, target: Optional[GameCard] = None):
        gs.register_effect_until_eot((NoAttacksAllowedEOT(), source))


class FlashFlood(Resolver):
    """Choose one - * Destroy target red permanent. * Return target Mountain to its owner's hand."""
    def resolve(self, gs: GameState, s: GameCard, t: GameCard = None):
        gs.pile_mgr.bounce(t) if t.props.slug == 'mountain' else gs.pile_mgr.destroy(t)


class GoblinKing(Resolver):
    """All of your other Goblins gain +1+/+1 and Mountainwalk"""
    def resolve(self, gs: GameState, source: GameCard, target: Optional[GameCard] = None):
        targets = gs.card_filter.on_player_board(source.owner_id).creatures().by_sub_type('Goblin').result()
        for t in targets:
            if source != t:
                t.modifiers.append(KWAMod(s=source, add_or_remove='add', kwa='Mountainwalk'))
                t.modifiers.append(PTMod(s=source, p_adj=1, t_adj=1))


class Greed(Resolver):
    def resolve(self, gs: GameState, source: GameCard, target: Optional[GameCard] = None):
        gs.apply_damage(source, 2, source.owner_id)
        gs.pile_mgr.draw(source.owner_id)


class GlyphOfDestruction(Resolver):
    """Target blocking Wall you control gets +10/+0 until end of combat.
    Prevent all damage that would be dealt to it this turn. Destroy it at the beginning of the next end step."""
    def resolve(self, gs: GameState, s: GameCard, t: Optional[GameCard] = None):
        t.modifiers.append(PTMod(s=s, p_adj=10, expires='EOT'))
        # gs.damage_preventions.append(PreventAllDamage())  # Will this prevent all damage to everyone?
        # TODO: the above line needs to be updated, since I remove PreventAllDamage
        gs.end_step_funcs.append(lambda gs_, s_, t_: gs.pile_mgr.destroy(s))


class HealingSalve(Resolver):
    """Choose one - * You gain 3 life. * Prevent the next 3 damage that would be dealt to any target this turn."""
    def resolve(self, gs: GameState, s: GameCard, t: GameCard = None):
        gs.pending_choice = HealingSalveChoice(s.owner_id, gs, s)


class HurkylsRecall(Resolver):
    """Return all artifacts target player owns to their hand"""
    def resolve(self, gs: GameState, source: GameCard, target: int = None):
        if not target:
            raise ValueError(f"{source.props.name} needs a target player")
        for artifact in gs.card_filter.on_player_board(target).artifacts().result():
            gs.pile_mgr.bounce(artifact)


class Inquisition(Resolver):
    """Target player reveals their hand. Deal damage to that player = number of white cards in their hand."""
    def resolve(self, gs: GameState, source: GameCard, target: int = None):
        if not target:
            raise ValueError(f"{source.props.name} needs a target player")
        opp_cards = gs.pile_mgr.hands[flip(source.owner_id)].cards
        for c in opp_cards:
            c.reveal()
        if white_cnt := len([c for c in opp_cards if c.is_white]):
            gs.apply_damage(source, white_cnt, flip(source.owner_id))


class KoboldDrillSergeant(Resolver):
    """Other Kobold creatures you control get +0/+1 and have trample"""
    def resolve(self, gs: GameState, source: GameCard, target: Optional[GameCard] = None):
        kobolds = gs.card_filter.on_player_board(source.owner_id).creatures().by_sub_type('Kobold').result()
        for k in kobolds:
            if source != k:
                k.modifiers.append(KWAMod(s=source, add_or_remove='add', kwa='Trample'))
                k.modifiers.append(PTMod(s=source, p_adj=0, t_adj=1))


class KryShield(Resolver):
    """Prevent all damage that would be dealt this turn by target creature you control.
    That creature gets +0/+X until end of turn, where X is its mana value"""
    def resolve(self, gs: GameState, s: GameCard, t: Optional[GameCard] = None):
        gs.damage_preventions.append(PreventNextDamage(s, source_card=t))
        t.modifiers.append(PTMod(s=s, t_adj=t.props.mana_value, expires='EOT'))


class LivingArtifactUpkeep(Resolver):
    """... At your upkeep, you may remove a vitality counter from this Aura to gain 1 life"""
    def resolve(self, gs: GameState, s: GameCard, target=None):
        if gs.turn_mgr.player_turn_idx != s.owner_id:
            return
        gs.action_stack.push(RemoveCounterForLifeChoice(s.owner_id, gs, s, VITALITY), gs, False)


class ManaClash(Resolver):
    """You and target opponent each flip a coin. Mana Clash deals 1 damage to each player whose coin comes up tails.
    Repeat this process until both players' coins come up heads on the same flip."""
    def resolve(self, gs: GameState, source: GameCard, target: Optional[GameCard] = None):
        caster_id, opp_id = source.owner_id, flip(source.owner_id)
        while True:
            caster_result = gs.randomize_event(caster_id, ['heads', 'tails'])
            opp_result = gs.randomize_event(opp_id, ['heads', 'tails'])
            print(f"Caster's result is {caster_result}; opponent's result is {opp_result}")
            if caster_result == 'heads' and opp_result == 'heads':
                print('Since both flips were heads, there are no more flips')
                break
            if caster_result == 'tails':
                gs.apply_damage(source, 1, caster_id)
            if opp_result == 'tails':
                gs.apply_damage(source, 1, opp_id)


class MartyrsCry(Resolver):
    """Sorcery WW [] Exile all white creatures. For each creature exiled this way, its controller draws a card."""
    def resolve(self, gs: GameState, source: GameCard, target: Optional[GameCard] = None):
        for white_creature in gs.card_filter.in_play().white().creatures().result():
            gs.pile_mgr.exile(white_creature)
            gs.pile_mgr.draw(white_creature.owner_id)


class MazeOfIth(Resolver):
    def resolve(self, gs: GameState, s: GameCard, t: Optional[GameCard] = None):
        the_combat = next((com for com in gs.combats if com.attacker is t), None)
        if not the_combat:
            return
        gs.damage_preventions.append(PreventNextDamage(s, None, target_card=t, combat_only=True))
        for b in the_combat.blockers:
            gs.damage_preventions.append(PreventNextDamage(s, None, target_card=b, combat_only=True))
        t.untap(gs)


class Rakalite(Resolver):
    def resolve(self, gs: GameState, s: GameCard, target: GameCard = None):
        """target is the card dealing damage"""
        if not target:
            raise RuntimeError(f'{s.props.name} needs a target')
        prevention = PreventNextDamage(s, None, source_card=target)
        gs.damage_preventions.append(prevention)
        gs.pile_mgr.bounce(s)


class ReverseDamage(Resolver):
    """The next time a source of your choice would deal damage to you this turn, prevent that damage.
    You gain life equal to the damage prevented this way.
    Since amount prevented isn't known upon cast, use PreventNextDamage.on_prevent() callback to later call gain_life"""
    def resolve(self, gs: GameState, s: GameCard, target: Optional[GameCard] = None):
        """target = the GameCard doing the damage"""
        def gain_life(prevented: int):
            gs.score_mgr.increment_life(s.owner_id, prevented, s, gs)

        gs.damage_preventions.append(
            PreventNextDamage(s, None, target_player=s.owner_id, source_card=target, on_prevent=gain_life))


class RocketLauncherCast(Resolver):
    """To support 'Activate only if you've controlled continuously since the beginning of your most recent turn."""
    def resolve(self, gs: GameState, s: GameCard, t: Optional[GameCard] = None):
        s.has_summoning_sickness = True


class RocketLauncherAA(Resolver):
    """{2}: Deal 1 damage to any target. Destroy Rocket Launcher at next end step."""
    def resolve(self, gs: GameState, s: GameCard, t: Optional[GameCard] = None):
        gs.apply_damage(s, 1, t)
        gs.end_step_funcs.append(lambda gs_, s_: gs.pile_mgr.destroy(s))


class SacrificeOnCast(Resolver):
    """Sac a creature: Add an amount of {B} equal to the sacrificed creature's mana value.
    Note "sacrifice" refers to the card called sacrifice, not the game action of sacrifice"""
    def resolve(self, gs: GameState, s: GameCard, t: GameCard = None):
        if not t:
            raise ValueError(f"{s.props.name} needs a target to ... sacrifice")
        gs.action_stack.push(SacCreatureAndAddMana(s.owner_id, gs, s, t, 'B', t.props.mana_value), gs, False)


class SerendibDjinn(Resolver):
    """At your upkeep, sac a land. If it's an Island, 3 damage to you. When you control no lands, sac this creature."""
    def resolve(self, gs: GameState, source: GameCard, target=None):
        if gs.turn_mgr.player_turn_idx != source.owner_id:
            return
        gs.action_stack.push(SerendibDjinnUpkeepChoice(gs.turn_mgr.player_turn_idx, gs, source), gs, False)


class Shapeshifter(Resolver):
    """At cast & at your upkeep, choose a number 0-7 (n). Shapeshifter's power = n, toughness = 7 - n"""
    def resolve(self, gs: GameState, source: GameCard, target: Optional[GameCard] = None):
        if gs.turn_mgr.player_turn_idx != source.owner_id:
            return
        gs.action_stack.push(ShapeshifterChoice(source.owner_id, gs, source), gs, False)


class StoneGiant(Resolver):
    """{T}: Target creature you control with toughness less than this creature's power gains flying until end of turn.
    Destroy that creature at the beginning of the next end step."""
    def resolve(self, gs: GameState, s: GameCard, t: Optional[GameCard] = None):
        t.modifiers.append(KWAMod(s=s, add_or_remove='add', kwa='Flying', expires='EOT'))
        gs.end_step_funcs.append(lambda gs_, s_: gs.pile_mgr.destroy(t))


class Subdue(Resolver):
    """Prevent all combat damage that would be dealt by target creature this turn.
    That creature gets +0/+X until end of turn, where X is its mana value."""
    def resolve(self, gs: GameState, s: GameCard, t: Optional[GameCard] = None):
        gs.damage_preventions.append(PreventNextDamage(s, None, source_card=t, combat_only=True))
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
        gs.action_stack.push(DrawCardsOrDontChoice(gs.turn_mgr.player_turn_idx, gs, source, 2))


class SyphonSoul(Resolver):
    """Syphon Soul deals 2 damage to each other player. You gain life equal to the damage dealt this way."""
    def resolve(self, gs: GameState, source: GameCard, target: Optional[GameCard] = None):
        gs.apply_damage(source, 2, target)
        gs.score_mgr.increment_life(source.owner_id, 2, source, gs)


class Timetwister(Resolver):
    """Each player shuffles their hand & graveyard into their library, then draws 7 cards.
    (Timetwister to its owner's graveyard.)"""
    def resolve(self, gs: GameState, s: GameCard, target: Optional[GameCard] = None):
        time_twister = next(c for c in gs.pile_mgr.graveyards[s.owner_id] if c is s)
        for p_id in range(2):
            hand_cards = gs.pile_mgr.hands[p_id][:]
            gs.pile_mgr.hands[p_id].cards.clear()
            graveyard_cards = gs.pile_mgr.graveyards[p_id][:]
            gs.pile_mgr.graveyards.clear()
            gs.pile_mgr.libraries[p_id].extend(hand_cards)
            gs.pile_mgr.libraries[p_id].extend(graveyard_cards)
            random.shuffle(gs.pile_mgr.libraries[p_id])
            gs.pile_mgr.draw(p_id, 7)
            if p_id == s.owner_id:
                gs.pile_mgr.graveyards[p_id].append(time_twister)


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


class VenarianGoldCast(Resolver):
    """When this Aura enters, tap enchanted creature and put X sleep counters on it ..."""
    def resolve(self, gs: GameState, source: GameCard, target: GameCard = None):
        if not target:
            raise RuntimeError(f"{source.props.name} needs a casting target")
        gs.tap_card(target)
        if x := getattr(source, 'variable_x', 0):  # read X chosen when casting
            source.counters.add_counter(SLEEP, x)


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
        opp_cards = gs.pile_mgr.hands[opp].cards
        if not opp_cards:
            return
        the_card = gs.randomize_event(opp, opp_cards) if len(opp_cards) > 1 else opp_cards[0]
        life_payment_amt = the_card.props.mana_value if 'Land' not in the_card.card_types else 1
        gs.pending_choice = PayLifeOrDiscardChoice(opp, gs, source, life_payment_amt, the_card)


class Web(Resolver):
    def resolve(self, _: GameState, source: GameCard, target: Optional[GameCard] = None):
        if target:
            target.modifiers.append(PTMod(s=source, p_adj=0, t_adj=2))
            target.modifiers.append(KWAMod(s=source, add_or_remove='add', kwa='Reach'))


class WindsOfChange(Resolver):
    """Each player shuffles the cards from their hand into their library, then draws that many cards"""
    def resolve(self, gs: GameState, s: GameCard, target: Optional[GameCard] = None):
        for p_id in range(2):
            if not gs.pile_mgr.hands[p_id].cards:
                continue
            hand_cards = gs.pile_mgr.hands[p_id][:]
            gs.pile_mgr.hands[p_id].cards.clear()
            gs.pile_mgr.libraries[p_id].extend(hand_cards)
            random.shuffle(gs.pile_mgr.libraries[p_id])
            gs.pile_mgr.draw(p_id, len(hand_cards))


class WinterBlast(Resolver):
    """Tap X target creatures. Winter Blast deals 2 damage to each of those creatures with flying."""
    def resolve(self, gs: GameState, source: GameCard, target: list[GameCard] = None):
        if not target:
            raise ValueError(f'{source.props.name} needs a list of targets')
        for t in target:
            gs.tap_card(t)
            if 'Flying' in t.keyword_abilities:
                gs.apply_damage(source, 2, t)


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


class ArenaOfTheAncientsCast(Resolver):
    """When this artifact enters, tap all legendary creatures"""
    def resolve(self, gs: GameState, _: GameCard, t: Optional[GameCard] = None):
        for c in gs.card_filter.in_play().creatures().untapped().legendary().result():
            c.tap(gs)


class CocoonHostStaysTapped(Resolver):
    """Enchanted creature doesn't untap during your untap step if this Aura has a pupa counter on it"""
    def resolve(self, gs: GameState, source: GameCard, _: GameCard = None):
        if source.host.counters.get_count(PUPA):
            gs.action_stack.push(LeaveTapped(source.owner_id, gs, source.host), gs, False)


class ManaShort(Resolver):
    def resolve(self, gs: GameState, source: GameCard, target: Optional[int] = None):
        """target = player_id whose lands should be tapped"""
        if target is None:
            return
        player_lands = gs.card_filter.on_player_board(target).lands().result()
        for land in player_lands:
            land.tap(gs)
        print(f"Mana Short taps {len(player_lands)} lands belonging to player {target}.")


class Reset(Resolver):
    """Cast this spell only during an opponent's turn after their upkeep step. Untap all lands you control"""
    def resolve(self, gs: GameState, source: GameCard, target: Optional[GameCard] = None):
        if gs.phase_mgr.phase == Phase.UPKEEP or gs.turn_mgr.player_turn_idx == source.owner_id:
            return
        for land in gs.card_filter.on_player_board(source.owner_id).lands().untapped().result():
            land.untap(gs)


class Riptide(Resolver):
    """Tap all blue creatures"""
    def resolve(self, gs: GameState, _: GameCard, t: Optional[GameCard] = None):
        for c in gs.card_filter.in_play().creatures().untapped().blue().result():
            c.tap(gs)


class Twiddle(Resolver):
    def resolve(self, gs, source: GameCard, target: Optional[GameCard] = None):
        if target:
            target.untap(gs) if target.is_tapped else target.tap(gs)


class VenarianGoldHostStaysTapped(Resolver):
    """Enchanted creature doesn't untap during its controller's untap step if it has a sleep counter on it."""
    def resolve(self, gs: GameState, source: GameCard, _: GameCard = None):
        if source.host.counters.get_count(SLEEP):
            gs.action_stack.push(LeaveTapped(source.owner_id, gs, source.host), gs, False)


class Scarecrow(Resolver):
    """(Activated Ability): Prevent all damage that would be dealt to you this turn by creatures with flying"""
    def resolve(self, gs: GameState, source: GameCard, target: Optional[GameCard] = None) -> None:
        from models.effects.listeners_card_specific import ScarecrowPrevention
        gs.until_eot_effects_and_cards.append((ScarecrowPrevention(protected_player=source.owner_id), source))


class Forcefield(Resolver):
    """(1): Next time an unblocked creature of your choice would deal you combat damage this turn, reduce damage to 1"""
    def resolve(self, gs, s: GameCard, t: Optional[GameCard] = None):
        from models.effects.listeners_card_specific import ForcefieldPrevention
        gs.until_eot_effects_and_cards.append((ForcefieldPrevention(creature=t, protected_player=s.owner_id), s))
