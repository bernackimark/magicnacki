from __future__ import annotations
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from game_state import GameState
    from models.game_card.game_card import GameCard

from models.constants import BASIC_LANDS
from models.effects.base import Listener
from models.events_all import CanBlockQueryEvent, CanAttackQueryEvent, CanCastQueryEvent, CanDamageQueryEvent, \
    CanTargetQueryEvent
from models.utils import flip


class CanBlockRule(Listener):
    listens_to = CanBlockQueryEvent

    def on_event(self, gs: GameState, source: GameCard, event: CanBlockQueryEvent) -> None:
        a = event.attacker
        b = event.blocker

        if b.is_tapped:
            event.permission = False
            return

        # blocker cannot already be blocking in another combat
        if b in {blocker for com in gs.combats for blocker in com.blockers}:
            event.permission = False
            return

        # Global land walk rule
        for walk, basic_land in zip([land.capitalize() + 'walk' for land in BASIC_LANDS], BASIC_LANDS):
            if walk in a.keyword_abilities and gs.card_filter.on_player_board(b.owner_id).by_slug(basic_land).result():
                event.permission = False
                return

        # Global Flying/Reach rule
        if ('Flying' in a.keyword_abilities and
                not any(kwa for kwa in b.keyword_abilities if kwa in ('Flying', 'Reach'))):
            event.permission = False
            return

        # Protection from color rule
        for kwa in a.keyword_abilities:
            if 'Protection From' in kwa:
                *_, color_full_word = kwa.split()
                color_map = {'Black': 'B', 'Blue': 'U', 'Green': 'G', 'Red': 'R', 'White': 'W'}
                if color_map[color_full_word] in b.colors:
                    event.permission = False
                    return


class CanAttackRule(Listener):
    listens_to = CanAttackQueryEvent

    def on_event(self, gs: GameState, source: GameCard, event: CanAttackQueryEvent) -> None:
        a = event.attacker
        if (not a.is_creature or (a.has_summoning_sickness and 'Haste' not in a.keyword_abilities)
                or a.is_tapped):
            event.permission = False
            return

        if 'Islandhome' in a.keyword_abilities:
            if not gs.card_filter.on_player_board(flip(a.owner_id)).islands().result():
                event.permission = False
                return

        adds, removes = a.modifiers.kwa_delta

        # explicit prohibition
        if 'Attack' in removes and 'Attack' not in adds:
            event.permission = False
            return

        # defender (considers animate-wall)
        if 'Defender' in a.keyword_abilities and 'Attack' not in adds:
            event.permission = False
            return

class CanCastRule(Listener):
    listens_to = CanCastQueryEvent

    def on_event(self, gs: GameState, source: GameCard, event: CanCastQueryEvent) -> None:
        c = event.card
        cost = gs.get_casting_cost(event.p_id, event.card)
        if not gs.mana_pools[event.p_id].can_pay(cost):
            event.permission = False
        elif c.props.is_land and gs.turn_mgr.has_played_land:
            event.permission = False
        elif gs.turn_mgr.player_turn_idx != event.p_id and 'Instant' not in c.props.card_types:
            event.permission = False

class CanDamageRule(Listener):
    listens_to = CanDamageQueryEvent

    def on_event(self, gs: GameState, source: GameCard, event: CanDamageQueryEvent) -> None:
        # Protection from color rule
        for kwa in event.target.keyword_abilities:
            if 'Protection From' in kwa:
                *_, color_full_word = kwa.split()
                color_map = {'Black': 'B', 'Blue': 'U', 'Green': 'G', 'Red': 'R', 'White': 'W'}
                if color_map[color_full_word] in source.colors:
                    event.permission = False
                    return

class CanTargetRule(Listener):
    listens_to = CanTargetQueryEvent

    def on_event(self, gs: GameState, source: GameCard, event: CanTargetQueryEvent) -> None:
        if isinstance(event.target, int):
            return

        # Protection from color rule
        for kwa in event.target.keyword_abilities:
            if 'Protection From' in kwa:
                *_, color_full_word = kwa.split()
                color_map = {'Black': 'B', 'Blue': 'U', 'Green': 'G', 'Red': 'R', 'White': 'W'}
                if color_map[color_full_word] in source.colors:
                    event.permission = False
                    return


BASE_RULES = [CanAttackRule(), CanBlockRule(), CanCastRule(), CanDamageRule(), CanTargetRule()]
