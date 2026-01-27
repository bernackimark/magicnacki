from __future__ import annotations
from typing import Optional, TYPE_CHECKING

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



def voodoo_doll_at_end_step():
    """At your end step, if untapped, destroy this card & it deals damage to you = to the # of pin counters on it"""
    class E(Effect):
        event = 'end_step'

        def resolve(self, gs: GameState, source: GameCard, target: Optional[GameCard] = None):
            if gs.player_turn_idx != source.orig_owner_id:
                return
            if source.is_tapped:
                return
            if pin_cnt := source.counters.get_count(PIN) > 0:
                gs.apply_damage(source, pin_cnt, source.orig_owner_id)
            gs.send_to_graveyard_from_play(source)
    return E()


def pestilence_on_end_step():
    """At the beginning of the end step, if no creatures are on the battlefield, sacrifice this enchantment"""
    class E(Effect):
        event = 'end_step'

        def resolve(self, gs: GameState, s: GameCard, target: Optional[GameCard] = None):
            if not gs.card_filter.creatures().in_play().result():
                gs.send_to_graveyard_from_play(s)
    return E()


def nettling_imp_on_end_step():
    """At this end step, destroy all untapped creatures that didn't attack this turn, except those who 'couldn't'."""

    class E(Effect):
        event = 'end_step'

        def resolve(self, gs: GameState, s: GameCard, target: Optional[GameCard] = None):
            """target = GameCard that needed to attack"""
            if target not in gs.card_filter.attackers().result():
                gs.send_to_graveyard_from_play(target)
    return E()


def season_of_the_witch_on_end_step():
    """At YOUR end step, destroy all untapped creatures that didn't attack this turn, except those who 'couldn't'.
    Note: I'm defining 'couldn't' = summoning sickness or has no Attack"""

    class E(Effect):
        event = 'end_step'

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
    return E()

# Convenience factory functions for common simple effects used previously
def send_to_graveyard_all_lands():
    class E(Effect):
        event = 'cast'

        def resolve(self, gs: GameState, source: "GameCard", target: Optional["GameCard"] = None):
            for land in CardFilter(gs).in_play().by_type('Land').result():
                gs.send_to_graveyard_from_play(land)
    return E()


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


def conversion_on_upkeep():
    """At the beginning of your upkeep, sacrifice this enchantment unless you pay {WW}."""
    class E(Effect):
        event = 'upkeep'

        def resolve(self, gs: GameState, source: GameCard, target=None):
            gs.action_stack.push(PayManaOrSacUpkeepChoice(source.orig_owner_id, gs, source, 'WW'), gs, False)
    return E()


def cosmic_horror_on_upkeep():
    """At the beginning of your upkeep, sacrifice this enchantment unless you pay {WW}."""
    class E(Effect):
        event = 'upkeep'

        def resolve(self, gs: GameState, source: GameCard, target=None):
            gs.action_stack.push(CosmicHorrorUpkeepChoice(source.orig_owner_id, gs, source, '3BBB'), gs, False)
    return E()


def erosion_on_upkeep():
    """At upkeep of enchanted land's controller, destroy that land unless that player pays {1} or 1 life"""
    class E(Effect):
        event = 'upkeep'

        def resolve(self, gs: GameState, source: GameCard, target: Optional[GameCard] = None):
            gs.action_stack.push(ErosionUpkeepChoice(gs.player_turn_idx, gs, source), gs, False)
    return E()


def force_of_nature_on_upkeep():
    """At your upkeep, this creature deals 8 damage to you unless you pay {GGGG}"""
    class E(Effect):
        event = 'upkeep'

        def resolve(self, gs: GameState, s: GameCard, target=None):
            gs.action_stack.push(ForceOfNatureUpkeepChoice(s.orig_owner_id, gs, s, 'GGGG', 8), gs, False)
    return E()


def forethought_amulet_on_upkeep():
    class E(Effect):
        event = 'upkeep'

        def resolve(self, gs: GameState, source: GameCard, target=None):
            gs.action_stack.push(PayManaOrSacUpkeepChoice(source.orig_owner_id, gs, source, '3'), gs, False)
    return E()


def junun_efreet_on_upkeep():
    class E(Effect):
        event = 'upkeep'

        def resolve(self, gs: GameState, source: GameCard, target=None):
            gs.action_stack.push(PayManaOrSacUpkeepChoice(source.orig_owner_id, gs, source, 'BB'), gs, False)
    return E()


def mana_vortex_on_upkeep():
    """At each player's upkeep, they sac a land. If no lands on entire battlefield, sac this enchantment."""
    class E(Effect):
        event = 'upkeep'

        def resolve(self, gs: GameState, source: GameCard, target: Optional[GameCard] = None):
            if len(CardFilter(gs).lands().in_play().result()) == 0:
                gs.send_to_graveyard_from_play(source)
                return
            for land in CardFilter(gs).on_player_board(gs.player_turn_idx).lands().result():
                SacALandChoice(gs.player_turn_idx, gs, land)
    return E()


def phantasmal_forces_on_upkeep():
    class E(Effect):
        event = 'upkeep'

        def resolve(self, gs: GameState, source: GameCard, target=None):
            gs.action_stack.push(PayManaOrSacUpkeepChoice(source.orig_owner_id, gs, source, 'U'), gs, False)
    return E()


def season_of_the_witch_on_upkeep():
    """At your upkeep, sacrifice this enchantment unless you pay 2 life"""
    class E(Effect):
        event = 'upkeep'

        def resolve(self, gs: GameState, source: GameCard, target=None):
            # Pause the game and force a choice
            gs.action_stack.push(SeasonOfTheWitchUpkeepChoice(source.orig_owner_id, gs, source), gs, False)
    return E()


def sunken_city_on_upkeep():
    """At the beginning of your upkeep, sacrifice this enchantment unless you pay {UU}."""
    class E(Effect):
        event = 'upkeep'

        def resolve(self, gs: GameState, source: GameCard, target=None):
            # Pause the game and force a choice
            gs.action_stack.push(PayManaOrSacUpkeepChoice(source.orig_owner_id, gs, source, 'UU'), gs, False)
    return E()


def acid_rain_on_cast():
    class E(Effect):
        event = 'cast'

        def resolve(self, gs: GameState, source: "GameCard", target: Optional["GameCard"] = None):
            for forest in CardFilter(gs).in_play().by_slug('forest').result():
                gs.send_to_graveyard_from_play(forest)
    return E()


def cleanse_on_cast():
    class E(Effect):
        event = 'cast'

        def resolve(self, gs, source: GameCard, target: Optional[GameCard] = None):
            for c in CardFilter(gs).in_play().creatures().black().result():
                gs.send_to_graveyard_from_play(c)
    return E()


def tivadars_crusade_on_cast():
    """Destroy all Goblins"""
    class E(Effect):
        event = 'cast'

        def resolve(self, gs: GameState, s: GameCard, t: Optional[GameCard] = None):
            for c in gs.card_filter.in_play().by_sub_type('Goblin').result():
                gs.send_to_graveyard_from_play(c)
    return E()


def tranquility_on_cast():
    """Destroy all Enchantments"""
    class E(Effect):
        event = 'cast'

        def resolve(self, gs: GameState, s: GameCard, t: Optional[GameCard] = None):
            for c in gs.card_filter.in_play().by_type('Enchantment').result():
                gs.send_to_graveyard_from_play(c)
    return E()


def tsunami_on_cast():
    """Destroy all islands"""
    class E(Effect):
        event = 'cast'

        def resolve(self, gs: GameState, s: GameCard, t: Optional[GameCard] = None):
            for c in gs.card_filter.in_play().by_slug('island').result():
                gs.send_to_graveyard_from_play(c)
    return E()


def flashfires_on_cast():
    class E(Effect):
        event = 'cast'

        def resolve(self, gs: GameState, source: GameCard, target: Optional[GameCard] = None):
            """Destroy all plains"""
            for plains in gs.card_filter.in_play().by_slug('plains').result():
                gs.send_to_graveyard_from_play(plains)
    return E()
