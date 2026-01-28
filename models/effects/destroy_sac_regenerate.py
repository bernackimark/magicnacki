from __future__ import annotations
from typing import Optional, TYPE_CHECKING, Callable

if TYPE_CHECKING:
    from game_state import GameState
    from models.game_card import GameCard

from card_filter import CardFilter
from models.choice_actions.choice_actions_all import PayManaOrSacUpkeepChoice, CosmicHorrorUpkeepChoice, ErosionUpkeepChoice, \
    ForceOfNatureUpkeepChoice, SacALandChoice, SeasonOfTheWitchUpkeepChoice
from models.counter_tokens import PIN
from models.effects.base import Effect
from models.effects.piles import GraveyardToExile

# --- new Class format --
class AcidRain(Effect):
    def resolve(self, gs: GameState, source: GameCard, target: GameCard = None):
        for forest in CardFilter(gs).in_play().by_slug('forest').result():
            gs.send_to_graveyard_from_play(forest)

class BoardToGraveyard(Effect):
    def resolve(self, gs: GameState, source: GameCard, target: Optional[GameCard] = None):
        gs.send_to_graveyard_from_play(target)

class EaterOfTheDeadAA(Effect):
    """Exile target creature card from a graveyard and untap this creature"""
    def resolve(self, gs: GameState, source: GameCard, target: GameCard = None):
        if not target:
            raise RuntimeError(f'{source.props.name} needs a target')
        GraveyardToExile().resolve(gs, source, target)
        source.untap(gs)

class ExileAllCreatures(Effect):
    def resolve(self, gs, source: GameCard, target: Optional[GameCard] = None):
        for c in CardFilter(gs).in_play().creatures().result():
            gs.send_to_exile(c)


# --- old function format ---

class VoodooDollEndStep(Effect):
    """At your end step, if untapped, destroy this card & it deals damage to you = to the # of pin counters on it"""
    def resolve(self, gs: GameState, source: GameCard, target: Optional[GameCard] = None):
        if gs.player_turn_idx != source.orig_owner_id:
            return
        if source.is_tapped:
            return
        if pin_cnt := source.counters.get_count(PIN) > 0:
            gs.apply_damage(source, pin_cnt, source.orig_owner_id)
        gs.send_to_graveyard_from_play(source)


class PestilenceEndStep(Effect):
    """At the beginning of the end step, if no creatures are on the battlefield, sacrifice this enchantment"""
    def resolve(self, gs: GameState, s: GameCard, target: Optional[GameCard] = None):
        if not gs.card_filter.creatures().in_play().result():
            gs.send_to_graveyard_from_play(s)

class SeasonOfTheWitchEndStep(Effect):
    """At YOUR end step, destroy all untapped creatures that didn't attack this turn, except those who 'couldn't'.
    Note: I'm defining 'couldn't' = summoning sickness or has no Attack"""
    def resolve(self, gs: GameState, s: GameCard, target: Optional[GameCard] = None):
        if gs.player_turn_idx != s.orig_owner_id:
            return
        your_untapped_creatures = gs.card_filter.on_player_board(s.orig_owner_id).creatures().untapped().result()
        attackers = gs.card_filter.attackers().result()
        for creature in your_untapped_creatures:
            if creature in attackers:
                continue
            if creature.has_summoning_sickness or 'Attack' not in creature.keyword_abilities:
                continue
            gs.send_to_graveyard_from_play(creature)


# Convenience factory functions for common simple effects used previously
class PayManaOrSac(Effect):
    def __init__(self, mana_cost: str):
        self.mana_cost = mana_cost

    def resolve(self, gs: GameState, source: GameCard, target=None):
        gs.action_stack.push(PayManaOrSacUpkeepChoice(source.orig_owner_id, gs, source, self.mana_cost), gs, False)


class ErosionUpkeep(Effect):
    def resolve(self, gs: GameState, source: GameCard, target: Optional[GameCard] = None):
        gs.action_stack.push(ErosionUpkeepChoice(gs.player_turn_idx, gs, source), gs, False)

class ForceOfNatureUpkeep(Effect):
    """At your upkeep, this creature deals 8 damage to you unless you pay {GGGG}"""
    def resolve(self, gs: GameState, s: GameCard, target=None):
        gs.action_stack.push(ForceOfNatureUpkeepChoice(s.orig_owner_id, gs, s, 'GGGG', 8), gs, False)

class ManaVortexUpkeep(Effect):
    """At each player's upkeep, they sac a land. If no lands on entire battlefield, sac this enchantment."""
    def resolve(self, gs: GameState, source: GameCard, target: Optional[GameCard] = None):
        if len(CardFilter(gs).lands().in_play().result()) == 0:
            gs.send_to_graveyard_from_play(source)
            return
        for land in CardFilter(gs).on_player_board(gs.player_turn_idx).lands().result():
            SacALandChoice(gs.player_turn_idx, gs, land)

class SeasonOfTheWitchUpkeep(Effect):
    """At your upkeep, sacrifice this enchantment unless you pay 2 life"""
    def resolve(self, gs: GameState, source: GameCard, target=None):
        # Pause the game and force a choice
        gs.action_stack.push(SeasonOfTheWitchUpkeepChoice(source.orig_owner_id, gs, source), gs, False)

class DestroyAll(Effect):
    def __init__(self, card_filter_func: Callable[[GameState, GameCard], list[GameCard]]):
        self.card_filter_func = card_filter_func

    def resolve(self, gs: GameState, s: GameCard, t: Optional[GameCard] = None):
        for c in self.card_filter_func(gs, s):
            gs.send_to_graveyard_from_play(c)

# TODO: i'm not sure I can handle this yet;
#  it happens at the end step when its activated ability was triggered at all that turn
# def nettling_imp_on_end_step():
#     """At this end step, destroy all untapped creatures that didn't attack this turn, except those who 'couldn't'."""
#
#     class E(Effect):
#         event = 'end_step'
#
#         def resolve(self, gs: GameState, s: GameCard, target: Optional[GameCard] = None):
#             """target = GameCard that needed to attack"""
#             if target not in gs.card_filter.attackers().result():
#                 gs.send_to_graveyard_from_play(target)
#     return E()

def land_on_leave():
    """serendib-djinn: When you control no lands, sacrifice this creature"""
    class E(Effect):
        event = 'leave'

        def resolve(self, gs: GameState, s: GameCard, target: Optional[GameCard] = None):
            for p_id in (0, 1):
                if gs.card_filter.on_player_board(p_id).lands().result():
                    continue
                for c in gs.card_filter.on_player_board(p_id).by_slug('serendib-djinns').result():
                    print(f'Player #{p_id} has no lands, so Serendib Djinn is destroyed')
                    gs.send_to_graveyard_from_play(c)
    return E()


def island_on_leave():
    class E(Effect):
        event = 'leave'

        def resolve(self, gs: GameState, source: GameCard, target: Optional[GameCard] = None):
            """If out of islands, send all of your creatures with Islandhome to the graveyard"""
            p_id = source.orig_owner_id
            my_islands = CardFilter(gs).on_player_board(p_id).by_slug('island').result()
            if len(my_islands) > 1:
                return
            my_island_home_creatures = CardFilter(gs).on_player_board(p_id).has('Islandhome').result()
            for creature in my_island_home_creatures:
                gs.send_to_graveyard_from_play(creature)
    return E()