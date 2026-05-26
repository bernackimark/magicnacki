from __future__ import annotations

import math
from typing import TYPE_CHECKING, Optional, Literal

from models.actions.draw_discard import DiscardCard
from models.choice_actions_all import DiscardChoice, SearchLibraryChoice, NaturalSelectionChoice, ShuffleOrDontChoice, \
    CopyCardChoice, PrimalClayChoice
from models.counter_tokens import STORAGE, PUPA, PLUS_ONE
from models.damage import PreventNextDamage
from models.effects.base import Effect
from models.effects.listens_for_block import GlyphOfDoomListener
from models.effects.listens_for_damage import GlyphOfLifeListener
from models.effects.listens_for_death import SandalsOfAbdallahIfCreatureDies
from models.effects.piles import GraveyardToExile
from models.effects.queries import TowerOfCoireallEOT
from models.modifiers import SubTypeMod, KWAMod
from models.utils import flip
from models.zone import Zone

if TYPE_CHECKING:
    from game_state import GameState
    from models.game_card.game_card import GameCard


class GlyphOfDoom(Effect):
    """On cast, select a wall.  Register GlyphOfDoomListener."""
    def resolve(self, gs: GameState, source: GameCard, target: Optional[GameCard] = None):
        if not target:
            raise ValueError(f'{source.props.name} needs a target')
        temp_effect = GlyphOfDoomListener(target)
        gs.event_mgr.register_effect_until_eot((temp_effect, source))


class GlyphOfLife(Effect):
    """On cast, select a wall.  Register GlyphOfLifeListener."""
    def resolve(self, gs: GameState, source: GameCard, target: Optional[GameCard] = None):
        if not target:
            raise ValueError(f'{source.props.name} needs a target')
        temp_effect = GlyphOfLifeListener(target)
        gs.event_mgr.register_effect_until_eot((temp_effect, source))


class TowerOfCoireall(Effect):
    """{T}: Target creature can't be blocked by Walls this turn"""
    def resolve(self, gs: GameState, source: GameCard, target: GameCard = None):
        if not target:
            raise ValueError(f'{source.props.name} needs a target')
        temp_effect = TowerOfCoireallEOT(target)
        gs.event_mgr.register_effect_until_eot((temp_effect, source))


class CityOfShadowsAA1(Effect):
    """{T}, Exile a creature you control: Put a storage counter on this land"""
    def resolve(self, gs: GameState, source: GameCard, target: GameCard = None):
        source.counters.add_counter(STORAGE)


class CityOfShadowsAA2(Effect):
    """{T}: Add {C} for each storage counter on this land"""
    def resolve(self, gs: GameState, source: GameCard, target: GameCard = None):
        cnt = len(source.counters.get_count(STORAGE))
        gs.mana_pools[source.owner_id].add_floating('C', cnt)


class CocoonCast(Effect):
    def resolve(self, gs: GameState, source: GameCard, target=None):
        target.tap(gs)
        source.counters.add_counter(PUPA, 3)


class RockHydraCast(Effect):
    """This creature enters with X +1/+1 counters on it ..."""
    def resolve(self, gs: GameState, source: GameCard, target=None):
        if x := getattr(source, 'variable_x', 0):  # read X chosen when casting
            source.counters.add_counter(PLUS_ONE, x)


class Banshee(Effect):
    """{X}, {T}: This creature deals half X damage, rounded down, to any target, and half X damage, rounded up to you"""
    def resolve(self, gs: GameState, s: GameCard, t: Optional[GameCard] = None):
        if not t:
            raise ValueError(f'{s.props.name} needs a target')
        damage_to_target = s.variable_x // 2
        damage_to_you = s.variable_x - damage_to_target
        gs.apply_damage(s, damage_to_target, t)
        gs.apply_damage(s, damage_to_you, s.owner_id)
        s.variable_x = None


class Earthquake(Effect):
    """Earthquake deals X damage to each creature without flying and each player"""
    def resolve(self, gs: GameState, source: GameCard, target: Optional[GameCard] = None):
        x = getattr(source, 'variable_x', 0)  # read X chosen when casting
        for c in gs.card_filter.in_play().has('Flying', False).creatures().result():
            gs.apply_damage(source, x, c)
        for p_id in (0, 1):
            gs.apply_damage(source, x, p_id)


class EternalFlame(Effect):
    """X = # of mountains caster controls; deal x damage to opponent and round(x/2) to caster"""
    def resolve(self, gs: GameState, source: GameCard, target: Optional[GameCard] = None):
        x = len(gs.card_filter.on_player_board(gs.turn_mgr.player_turn_idx).mountains().result())
        gs.apply_damage(source, x, flip(gs.turn_mgr.player_turn_idx))
        gs.apply_damage(source, math.ceil(x/2), gs.turn_mgr.player_turn_idx)


class EyeForAnEye(Effect):
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


class GaseousForm(Effect):
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


class JovialEvil(Effect):
    """deals X damage to target opponent, where X is twice the number of white creatures that player controls"""
    def resolve(self, gs: GameState, source: GameCard, target: Optional[GameCard] = None):
        # target = opponent_id
        opp_white_creature_cnt = len(gs.card_filter.on_player_board(target).creatures().result())
        gs.apply_damage(source, opp_white_creature_cnt * 2, target)


class Sandstorm(Effect):
    """Sandstorm deals 1 damage to each attacking creature.
    [from Google: it only hits creatures already attacking when it resolves.]"""
    def resolve(self, gs: GameState, source: GameCard, target: Optional[GameCard] = None):
        for attacker in gs.card_filter.attackers().result():
            gs.apply_damage(source, 1, attacker)


class StormSeeker(Effect):
    """Storm Seeker deals damage to target player equal to the number of cards in that player's hand"""
    def resolve(self, gs: GameState, source: GameCard, t: Optional[GameCard] = None):
        opp_idx = flip(source.owner_id)
        gs.apply_damage(source, len(gs.hands[opp_idx].cards), opp_idx)


class Tracker(Effect):
    """Tracker deals damage = its power to target creature. That creature deals damage = its power to this creature."""
    def resolve(self, gs: GameState, source: GameCard, target: GameCard = None):
        if not target:
            raise ValueError(f'{source.props.name} needs a target')
        gs.apply_damage(source, source.power, target)
        gs.apply_damage(target, target.power, source)


class Typhoon(Effect):
    """Typhoon deals damage to opponent = the number of Islands that player controls"""
    def resolve(self, gs: GameState, s: GameCard, t: Optional[GameCard] = None):
        opp = flip(gs.turn_mgr.player_turn_idx)
        opp_island_cnt = len(gs.card_filter.on_player_board(opp).islands().result())
        if opp_island_cnt:
            gs.apply_damage(s, opp_island_cnt, opp)


class AshesToAshes(Effect):
    """Exile two target nonartifact creatures. Ashes to Ashes deals 5 damage to you."""
    def resolve(self, gs: GameState, source: GameCard, target: list[GameCard] = None):
        if not target:
            raise ValueError(f'{source.props.name} needs a target')
        for t in target:
            gs.exile(t)
        gs.apply_damage(source, 5, source.owner_id)


class DustToDust(Effect):
    """Exile two target artifacts"""
    def resolve(self, gs: GameState, source: GameCard, target: list[GameCard] = None):
        if not target:
            raise ValueError(f'{source.props.name} needs a target')
        for t in target:
            gs.exile(t)


class EaterOfTheDead(Effect):
    """Exile target creature card from a graveyard and untap this creature"""
    def resolve(self, gs: GameState, source: GameCard, target: GameCard = None):
        if not target:
            raise RuntimeError(f'{source.props.name} needs a target')
        GraveyardToExile().resolve(gs, source, target)
        gs.untap_card(source)


class Millstone(Effect):
    """{2}, {T}: Target player mills two cards"""
    def resolve(self, gs: GameState, source: GameCard, target: int = None):
        if not target:
            raise ValueError(f'{source.props.name} needs a player to target')
        for _ in range(2):
            top_card = gs.libraries[target][0]  # Warning: if no cards, this pukes
            gs.move_card(top_card, Zone.GRAVEYARD, cause='mill')


class BazaarOfBaghdad(Effect):
    """Draw two cards, then discard three cards"""
    def resolve(self, gs: GameState, source: GameCard, target: Optional[GameCard] = None):
        gs.draw(source.owner_id, 2)
        gs.pending_choice = DiscardChoice(source.owner_id, gs, source, source.owner_id, 3, 3)


class Braingeyser(Effect):
    def resolve(self, gs: GameState, source: GameCard, target: int = None):
        if target is not None:
            x = getattr(source, 'variable_x', 0)  # read X chosen when casting
            gs.draw(target, x)


class DemonicTutor(Effect):
    """Search your library for a card, put that card into your hand, then shuffle"""
    def resolve(self, gs: GameState, source: GameCard, target=None):
        p_id = source.owner_id
        gs.pending_choice = SearchLibraryChoice(p_id, gs, source, list(gs.libraries[p_id]), Zone.HAND)


class GlassesOfUrza(Effect):
    """Look at opponent's hand"""
    def resolve(self, gs: GameState, source: GameCard, target: int = None):
        for c in gs.hands[flip(source.owner_id)].cards:
            c.reveal()


class GwendlynDiCorci(Effect):
    """{T}: Target player discards a card at random. Activate only during your turn"""
    def resolve(self, gs: GameState, source: GameCard, target: int = None):
        if not target:
            raise ValueError(f'{source.props.name} needs a target')
        cards = gs.hands[target].cards
        if not cards:
            return
        if len(cards) == 1:
            gs.discard(cards[0], source)
            return
        random_card: GameCard = gs.randomize_event(target, cards)
        gs.discard(random_card, source)


class JalumTome(Effect):
    """Draw a card, then discard a card"""
    def resolve(self, gs: GameState, source: GameCard, target: Optional[GameCard] = None):
        gs.draw(source.owner_id)
        gs.pending_choice = DiscardChoice(source.owner_id, gs, source, source.owner_id)


class MindTwist(Effect):
    """Target player discards X cards at random"""
    def resolve(self, gs: GameState, source: GameCard, target: int = None):
        x = getattr(source, 'variable_x', 0)  # read X chosen when casting
        opp_id = flip(source.owner_id)
        opp_cards = gs.hands[opp_id].cards
        if not opp_cards:
            return
        if len(opp_cards) <= x:
            for c in opp_cards:
                gs.discard(c, source)
            return
        for _ in range(x):
            random_card: GameCard = gs.randomize_event(opp_id, opp_cards)
            gs.discard(random_card, source)


class NaturalSelection(Effect):
    """Look at the top 3 cards of target player's library, put them back in any order. You may shuffle."""
    def resolve(self, gs: GameState, source: GameCard, target: int = None):
        if not target:
            raise ValueError(f'{source.props.name} needs a target')
        top_3_cards = gs.libraries[target][:3]
        gs.add_presentation_request(source.owner_id, 'show_library', {'cards': top_3_cards})
        gs.pending_choice = NaturalSelectionChoice(source.owner_id, gs, source, target, top_3_cards)


class RagMan(Effect):
    """Opponent reveals their hand and discards a creature card at random. Activate only during your turn."""
    def resolve(self, gs: GameState, source: GameCard, target: int = None):
        if target is None:
            raise ValueError(f'{source.props.name} needs a target player')
        opp_cards = gs.hands[target].cards
        for c in opp_cards:
            c.reveal()
        opp_creatures = [c for c in opp_cards if c.is_creature]
        if not opp_creatures:
            return
        if len(opp_creatures) == 1:
            gs.discard(opp_creatures[0], source)
            return
        random_card: GameCard = gs.randomize_event(target, opp_creatures)
        gs.discard(random_card, source)


class Visions(Effect):
    """Look at the top five cards of target player's library. You may then have that player shuffle that library."""
    def resolve(self, gs: GameState, source: GameCard, target: int = None):
        if target is None:
            raise ValueError(f'{source.props.name} needs a target player')
        for c in gs.libraries[target][:5]:
            print('Showing you', c)
        gs.pending_choice = ShuffleOrDontChoice(target, gs, source, gs.libraries[target])


class WheelOfFortune(Effect):
    """Each player discards their hand, then draws seven cards"""
    def resolve(self, gs: GameState, source: GameCard, target: Optional[GameCard] = None):
        for i in (0, 1):
            [DiscardCard(i, gs, card).play() for card in gs.hands[i].cards]
            gs.draw(i, 7)


class Clone(Effect):
    """You may have this creature enter as a copy of any creature on the battlefield;
    pushes valid targets to the stack for user selection, which then calls an Action that copies select target attrs"""
    def resolve(self, gs: GameState, s: GameCard, t: GameCard = None):
        card_options = [c for c in gs.card_filter.in_play().creatures().result() if c is not s]
        if not card_options:
            return
        gs.pending_choice = CopyCardChoice(s.owner_id, gs, s, card_options)


class CopyArtifact(Effect):
    """You may have this enchantment enter as a copy of any artifact on the battlefield,
    except it's an enchantment in addition to its other types"""
    def resolve(self, gs: GameState, s: GameCard, t: GameCard = None):
        card_options = [c for c in gs.card_filter.in_play().artifacts().result() if c is not s]
        if not card_options:
            return
        gs.pending_choice = CopyCardChoice(s.owner_id, gs, s, card_options)


class EvilPresence(Effect):
    """Enchant land Enchanted land is a Swamp"""

    def resolve(self, gs, source: GameCard, target: Optional[GameCard] = None):
        if target is None:
            raise ValueError(f'{source.props.name} needs a target')
        sub_types = target.card_sub_types.copy()
        target.modifiers.items.append(SubTypeMod(s=source, add_or_remove='add', card_sub_type='Swamp'))
        for sub_type in sub_types:
            target.modifiers.items.append(SubTypeMod(s=source, add_or_remove='remove', card_sub_type=sub_type))


class PhantasmalTerrain(Effect):
    """Enchant land As this Aura enters, choose a basic land type. Enchanted land is the chosen type"""
    def __init__(self, land_type: Literal['Swamp', 'Island', 'Forest', 'Mountain', 'Plains']):
        self.land_type = land_type

    def resolve(self, gs, source: GameCard, target: Optional[GameCard] = None):
        if target is None:
            raise ValueError(f'{source.props.name} needs a target')
        sub_types = target.card_sub_types.copy()
        target.modifiers.items.append(SubTypeMod(s=source, add_or_remove='add', card_sub_type=self.land_type))
        for sub_type in sub_types:
            target.modifiers.items.append(SubTypeMod(s=source, add_or_remove='remove', card_sub_type=sub_type))


class PrimalClay(Effect):
    """As this creature enters, it becomes your choice of a 3/3 artifact creature, a 2/2 artifact creature with flying,
    or a 1/6 Wall artifact creature with defender in addition to its other types."""
    def resolve(self, gs: GameState, s: GameCard, t: GameCard = None):
        gs.pending_choice = PrimalClayChoice(s.owner_id, gs, s)


class VesuvanDoppelgangerCast(Effect):
    """You may have this creature enter as a copy of any creature on the battlefield,
    except it doesn't copy that creature's color & you may select a different creature on each of your upkeeps"""
    def resolve(self, gs: GameState, s: GameCard, t: GameCard = None):
        if gs.turn_mgr.player_turn_idx != s.owner_id:
            return
        card_options = [c for c in gs.card_filter.in_play().creatures().result() if c is not s]
        if not card_options:
            return
        gs.pending_choice = CopyCardChoice(s.owner_id, gs, s, card_options, copy_color=False)


class RapidFire(Effect):
    """Cast this spell only before blockers are declared. Target creature gains first strike until end of turn.
    If it doesn't have rampage, that creature gains rampage 2 until end of turn."""
    def resolve(self, gs: GameState, source: GameCard, target: Optional[GameCard] = None):
        if not target:
            raise ValueError(f'{source.props.name} needs a target')
        target.modifiers.items.append(KWAMod(s=source, add_or_remove='add', kwa='First Strike', expires='EOT'))
        if not target.rampage_amt:
            target.modifiers.items.append(KWAMod(s=source, add_or_remove='add', kwa='Rampage 2', expires='EOT'))


class SandalsOfAbdallahIslandWalk(Effect):
    """{T}: Target creature gains islandwalk until end of turn. When that creature dies this turn, destroy Sandals."""
    def resolve(self, gs: GameState, source: GameCard, target: Optional[GameCard] = None):
        if not target:
            raise ValueError(f'{source.props.name} needs a target')
        target.modifiers.items.append(KWAMod(s=source, add_or_remove='add', kwa='Islandwalk', expires='EOT'))

        temp_effect = SandalsOfAbdallahIfCreatureDies(target_creature=target)
        gs.register_effect_until_eot((temp_effect, source))


class UrborgLoseFirstStrike(Effect):
    """{T}: Target creature loses FIRST STRIKE or swampwalk until end of turn"""
    def resolve(self, gs: GameState, source: GameCard, target: Optional[GameCard] = None):
        if not target:
            raise ValueError(f'{source.props.name} needs a target')
        target.modifiers.items.append(KWAMod(s=source, add_or_remove='remove', kwa='First Strike', expires='EOT'))


class UrborgLoseSwampwalk(Effect):
    """{T}: Target creature loses first strike or SWAMPWALK until end of turn"""
    def resolve(self, gs: GameState, source: GameCard, target: Optional[GameCard] = None):
        if not target:
            raise ValueError(f'{source.props.name} needs a target')
        target.modifiers.items.append(KWAMod(s=source, add_or_remove='remove', kwa='Swampwalk', expires='EOT'))


class StreamOfLife(Effect):
    def resolve(self, gs: GameState, source: GameCard, target: int = None):
        x = getattr(source, 'variable_x', 0)  # read X chosen when casting
        gs.score_mgr.increment_life(target, x, source, gs)
