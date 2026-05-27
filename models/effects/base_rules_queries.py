from __future__ import annotations
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from game_state import GameState
    from models.game_card.game_card import GameCard

from models.constants import BASIC_LANDS
from models.effects.base import Effect, Querier
from models.utils import flip


class CanBlockRule(Querier):
    query = 'can_block'

    def on_query(self, gs: GameState, card: GameCard, **kwargs):
        """Query: card = blocker, mandatory kwarg: attacker"""
        attacker: GameCard = kwargs.get("attacker")
        if not attacker or not card:
            return None

        if card.is_tapped:
            return False

        if card in {blocker for com in gs.combats for blocker in com.blockers}:
            return False

        # Global land walk rule
        defender_idx = card.owner_id
        for walk, basic_land in zip([land.capitalize() + 'walk' for land in BASIC_LANDS], BASIC_LANDS):
            if walk in attacker.keyword_abilities and gs.card_filter.on_player_board(defender_idx).by_slug(basic_land).result():
                return False

        # Global Flying/Reach rule
        if ('Flying' in attacker.keyword_abilities and
                not any(kwa for kwa in card.keyword_abilities if kwa in ('Flying', 'Reach'))):
            return False

        # Protection from color rule
        for kwa in attacker.keyword_abilities:
            if 'Protection From' in kwa:
                *_, color_full_word = kwa.split()
                color_map = {'Black': 'B', 'Blue': 'U', 'Green': 'G', 'Red': 'R', 'White': 'W'}
                if color_map[color_full_word] in card.colors:
                    return False

        return None  # no opinion if can_block


class CanAttackRule(Querier):
    query = 'can_attack'

    def on_query(self, gs: GameState, **kwargs):
        """kwargs = includes 'card' when checking if a card can attack"""
        if not kwargs.get('card'):
            return None
        card: GameCard = kwargs.get('card')

        if (not card.is_creature or (card.has_summoning_sickness and 'Haste' not in card.keyword_abilities)
                or card.is_tapped):
            return False

        if 'Islandhome' in card.keyword_abilities:
            if not gs.card_filter.on_player_board(flip(card.owner_id)).islands().result():
                return False

        adds, removes = card.modifiers.kwa_delta

        # explicit prohibition
        if 'Attack' in removes and 'Attack' not in adds:
            return False

        # defender (considers animate-wall)
        if 'Defender' in card.keyword_abilities and 'Attack' not in adds:
            return False

        return None  # no opinion on whether the card can attack

class CanCastRule(Querier):
    query = 'can_cast'

    def on_query(self, gs: GameState, **kwargs):
        """kwargs include 'card' & 'p_id'"""
        if not kwargs.get('card'):
            return None
        card: GameCard = kwargs.get('card')
        if kwargs.get('p_id') is None:
            raise ValueError(f"I can't determine if {card.props.name} can be cast, as no player ID was supplied")
        p_id: int = kwargs.get('p_id')

        if not gs.mana_pools[p_id].can_pay(card.casting_cost):
            return False
        if card.props.is_land and gs.turn_mgr.has_played_land:
            return False
        if gs.turn_mgr.player_turn_idx != p_id and 'Instant' not in card.props.card_types:
            return False

        return None  # no opinion on whether the cast can be cast

class CanDamageRule(Querier):
    query = 'can_damage'

    def on_query(self, gs: GameState, **kwargs):
        source: GameCard = kwargs.get('source')
        target: GameCard = kwargs.get('card')
        if not source:
            return

        # Protection from color rule
        for kwa in target.keyword_abilities:
            if 'Protection From' in kwa:
                *_, color_full_word = kwa.split()
                color_map = {'Black': 'B', 'Blue': 'U', 'Green': 'G', 'Red': 'R', 'White': 'W'}
                if color_map[color_full_word] in source.colors:
                    return False

class CanTargetRule(Querier):
    query = 'can_target'

    def on_query(self, gs: GameState, **kwargs):
        source: GameCard = kwargs.get('source')
        target: GameCard | int = kwargs.get('card')
        if not source or isinstance(target, int):
            return

        # Protection from color rule
        for kwa in target.keyword_abilities:
            if 'Protection From' in kwa:
                *_, color_full_word = kwa.split()
                color_map = {'Black': 'B', 'Blue': 'U', 'Green': 'G', 'Red': 'R', 'White': 'W'}
                if color_map[color_full_word] in source.colors:
                    return False

