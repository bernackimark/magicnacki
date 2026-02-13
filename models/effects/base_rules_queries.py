from __future__ import annotations
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from game_state import GameState
    from models.game_card import GameCard

from constants import BASIC_LANDS
from models.effects.base import Effect
from utils import flip


class CanBlockBaseRule(Effect):
    event = 'can_block'

    def on_query(self, gs: GameState, event: str, card: GameCard, **kwargs):
        """Query: card = blocker, mandatory kwarg: attacker"""
        if event != "can_block":
            return None
        attacker: GameCard = kwargs.get("attacker")
        if not attacker or not card:
            return None

        if card.is_tapped:
            return False

        if card in {blocker for com in gs.combats for blocker in com.blockers}:
            return False

        # Global land walk rule
        defender_idx = card.orig_owner_id
        for walk, basic_land in zip([land.capitalize() + 'walk' for land in BASIC_LANDS], BASIC_LANDS):
            if walk in attacker.keyword_abilities and gs.card_filter.on_player_board(defender_idx).by_slug(basic_land).result():
                return False

        # Global Flying/Reach rule
        if ('Flying' in attacker.keyword_abilities and
                not any(kwa for kwa in card.keyword_abilities if kwa in ('Flying', 'Reach'))):
            return False

        return None  # no opinion if can_block


class CanAttackBaseRule(Effect):
    event = 'can_attack'

    def on_query(self, gs: GameState, event: str, **kwargs):
        """kwargs = includes 'card' when checking if a card can attack"""
        if event != 'can_attack' or not kwargs.get('card'):
            return None
        card: GameCard = kwargs.get('card')

        if (not card.is_creature or (card.has_summoning_sickness and 'Haste' not in card.keyword_abilities)
                or card.is_tapped or 'Attack' not in card.keyword_abilities):
            return False

        if 'Islandhome' in card.keyword_abilities:
            if not gs.card_filter.on_player_board(flip(card.orig_owner_id)).by_slug('island').result():
                return False

        return None  # no opinion on whether the card can attack

class CanCastBaseRule(Effect):
    event = 'can_cast'

    def on_query(self, gs: GameState, event: str, **kwargs):
        """kwargs include 'card' & 'p_id'"""
        if event != 'can_cast' or not kwargs.get('card'):
            return None
        card: GameCard = kwargs.get('card')
        if kwargs.get('p_id') is None:
            raise ValueError(f"I can't determine if {card.props.name} can be cast, as no player ID was supplied")
        p_id: int = kwargs.get('p_id')

        if not gs.mana_pools[p_id].can_pay(card.casting_cost):
            return False
        if card.props.is_land and gs.turn.has_played_land:
            return False
        if gs.player_turn_idx != p_id and 'Instant' not in card.props.card_types:
            return False

        return None  # no opinion on whether the cast can be cast
