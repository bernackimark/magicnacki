from __future__ import annotations
from typing import TYPE_CHECKING

from models.choice_actions_all import ChoiceAction, ChoiceOption

if TYPE_CHECKING:
    from game_state import GameState
    from models.game_card.game_card import GameCard

from models.constants import BASIC_LANDS, KW, Zone
from models.effects.base import Listener
from models.events_all import CanBlockQueryEvent, CanAttackQueryEvent, CanCastQueryEvent, CanDamageQueryEvent, \
    CanTargetQueryEvent, StateBasedEvent
from models.utils import flip


class BaseRule(Listener):
    registry: list[type["BaseRule"]] = []

    def __init_subclass__(cls):
        super().__init_subclass__()
        BaseRule.registry.append(cls)


class CanBlockRule(BaseRule):
    listens_to = CanBlockQueryEvent

    def on_event(self, gs: GameState, source: GameCard, event: CanBlockQueryEvent) -> None:
        a = event.attacker
        b = event.blocker

        if b.is_tapped:
            event.permission = False
            return

        # blocker cannot already be blocking in another combat
        if b in gs.combat_mgr.blockers:
            event.permission = False
            return

        # Global land walk rule
        for walk, basic_land in zip([land.capitalize() + 'walk' for land in BASIC_LANDS], BASIC_LANDS):
            if walk in a.keyword_abilities and gs.card_filter.on_player_board(b.owner_id).by_slug(basic_land).result():
                event.permission = False
                return

        # Global Flying/Reach rule
        if (KW.FLYING in a.keyword_abilities and
                not any(kwa for kwa in b.keyword_abilities if kwa in (KW.FLYING, KW.REACH))):
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


class CanAttackRule(BaseRule):
    listens_to = CanAttackQueryEvent

    def on_event(self, gs: GameState, source: GameCard, event: CanAttackQueryEvent) -> None:
        a = event.attacker
        if (not a.is_creature or (a.has_summoning_sickness and KW.HASTE not in a.keyword_abilities)
                or a.is_tapped):
            event.permission = False
            return

        if KW.ISLANDHOME in a.keyword_abilities:
            if not gs.card_filter.on_player_board(flip(a.owner_id)).islands().result():
                event.permission = False
                return

        # defender (considers animate-wall)
        if 'Defender' in a.keyword_abilities:
            event.permission = False
            return

class CanCastRule(BaseRule):
    listens_to = CanCastQueryEvent

    def on_event(self, gs: GameState, source: GameCard, event: CanCastQueryEvent) -> None:
        c = event.card
        cost = gs.get_casting_cost(event.p_id, event.card)
        if not gs.mana_pools[event.p_id].can_pay(cost):
            event.permission = False
        elif c.props.is_land and gs.turn_mgr.has_played_land:
            event.permission = False
        elif gs.player_turn_idx != event.p_id and 'Instant' not in c.props.card_types:
            event.permission = False

class CanDamageRule(BaseRule):
    """If card has Protection From [color of source], event.permission = False;
    as of now, players never have Protection"""
    listens_to = CanDamageQueryEvent

    def on_event(self, gs: GameState, source: GameCard, event: CanDamageQueryEvent) -> None:
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

class CanTargetRule(BaseRule):
    listens_to = CanTargetQueryEvent

    def on_event(self, gs: GameState, source: GameCard, event: CanTargetQueryEvent) -> None:
        from models.game_card.game_card import GameCard
        if not isinstance(event.target, GameCard):
            return

        # Protection from color rule
        for kwa in event.target.keyword_abilities:
            if 'Protection From' in kwa:
                *_, color_full_word = kwa.split()
                color_map = {'Black': 'B', 'Blue': 'U', 'Green': 'G', 'Red': 'R', 'White': 'W'}
                if color_map[color_full_word] in source.colors:
                    event.permission = False
                    return

class IslandhomeCheck(BaseRule):
    listens_to = StateBasedEvent

    def on_event(self, gs: GameState, source: GameCard, event: StateBasedEvent) -> None:
        for creature in gs.card_filter.in_play().has(KW.ISLANDHOME).result():
            if not gs.card_filter.on_player_board(creature.owner_id).islands().result():
                gs.pile_mgr.destroy(creature)

class LegendarySingletonCheck(BaseRule):
    """A state-based action that immediately forces you to choose one and put the other into its owner's graveyard;
    it bypasses hexproof or indestructible; this counts as "dying" and will trigger any such abilities"""
    listens_to = StateBasedEvent

    def on_event(self, gs: GameState, source: GameCard, event: StateBasedEvent) -> None:
        for p_id in (0, 1):
            legends_seen = {}
            for c in gs.card_filter.on_player_board(p_id).legendaries().result():
                if c.props.slug not in legends_seen:
                    legends_seen[c.props.slug] = c
                else:
                    options = [ChoiceOption(f'Move legendary {c} to graveyard',
                                            lambda: gs.pile_mgr.move_card(c, Zone.BATTLEFIELD, cause='legendary_rule'))
                               for c in legends_seen.values()]
                    # options = [BattlefieldToGraveyard(p_id, gs, c) for c in legends_seen.values()]
                    gs.queue_choice(ChoiceAction(options))

class LifeAndPoisonCheck(BaseRule):
    """Check for game_over (player life <= 0 & poison >= 10); set GameState's winner = -1 draw or 0/1 for win"""
    listens_to = StateBasedEvent

    def on_event(self, gs: GameState, source: GameCard, event: StateBasedEvent) -> None:
        if gs.is_game_over:  # there could be a win condition that sets is_game_over to True elsewhere
            return

        """Returns None if game is not over;
        else -1 if a draw, 0 for player #0, 1 for player #1, updates gs.is_game_over"""
        zero_life = [idx for idx, life in enumerate(gs.life) if life <= 0]
        ten_poison = [idx for idx, poison in enumerate(gs.score_mgr.poison_counters) if poison >= 10]

        losers = tuple(set(zero_life + ten_poison))
        if not losers:
            return
        if len(losers) > 1:
            gs.winner = -1
            gs.is_game_over = True
            print('The game ends in a draw')
            return
        else:
            gs.winner = flip(losers[0])
            gs.is_game_over = True
            print(f'Player #{gs.winner} wins the game')
            return

class ZeroToughnessCheck(BaseRule):
    listens_to = StateBasedEvent

    def on_event(self, gs: GameState, source: GameCard, event: StateBasedEvent) -> None:
        for creature in gs.card_filter.in_play().creatures().result():
            if creature.damage_received_this_turn >= creature.toughness:
                print(f'ZeroToughnessSBR calls gs.pile_mgr.destroy() for {creature}')
                gs.pile_mgr.destroy(creature)


BASE_RULES = [CanAttackRule(), CanBlockRule(), CanCastRule(), CanDamageRule(), CanTargetRule(),
              IslandhomeCheck(), LegendarySingletonCheck(), LifeAndPoisonCheck(), ZeroToughnessCheck()]
