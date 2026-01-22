from __future__ import annotations
from typing import TYPE_CHECKING, Optional

from utils import flip
from ..actions.choices import PayManaOrSacUpkeepChoice, ForceOfNatureUpkeepChoice, CosmicHorrorUpkeepChoice, \
    ElderSpawnUpkeepChoice, CurseArtifactUpkeepChoice, ErosionUpkeepChoice, LordOfThePitUpkeepChoice, \
    SeasonOfTheWitchUpkeepChoice, SerendibDjinnUpkeepChoice, AddKWA, SacALandChoice, ShapeshifterChoice

if TYPE_CHECKING:
    from ..game_card import GameCard
    from game_state import GameState

from models.effects.base import Effect
from card_filter import CardFilter


def conversion_on_upkeep():
    """At the beginning of your upkeep, sacrifice this enchantment unless you pay {WW}."""
    class E(Effect):
        event = 'upkeep'

        def resolve(self, gs: GameState, source: GameCard, target=None):
            gs.action_stack.push(PayManaOrSacUpkeepChoice(source.orig_owner_id, gs, source, 'WW'), gs, False)
    return E()

def copper_tablet_on_upkeep():
    """At the beginning of each player's upkeep, this artifact deals 1 damage to that player"""
    class E(Effect):
        event = 'upkeep'

        def resolve(self, gs: GameState, source: GameCard, target: Optional[GameCard] = None):
            gs.apply_damage(source, 1, gs.player_turn_idx)
    return E()

def cosmic_horror_on_upkeep():
    """At the beginning of your upkeep, sacrifice this enchantment unless you pay {WW}."""
    class E(Effect):
        event = 'upkeep'

        def resolve(self, gs: GameState, source: GameCard, target=None):
            gs.action_stack.push(CosmicHorrorUpkeepChoice(source.orig_owner_id, gs, source, '3BBB'), gs, False)
    return E()

def curse_artifact_on_upkeep():
    """At enchanted artifact's controller's upkeep, deal 2 damage to that player unless they sacrifice that artifact"""
    class E(Effect):
        event = 'upkeep'

        def resolve(self, gs: GameState, s: GameCard, target=None):
            gs.action_stack.push(CurseArtifactUpkeepChoice(gs.player_turn_idx, gs, s), gs, False)
    return E()

def cursed_land_on_upkeep():
    """Cursed Land does 1 damage to target land's controller during each upkeep"""
    class E(Effect):
        event = 'upkeep'

        def resolve(self, gs: GameState, source: GameCard, target: Optional[GameCard] = None):
            gs.apply_damage(source, 1, target.orig_owner_id)
    return E()

def elder_spawn_on_upkeep():
    """At your upkeep, sac an Island or sac this creature & it deals 6 damage to you."""
    class E(Effect):
        event = 'upkeep'

        def resolve(self, gs: GameState, s: GameCard, target=None):
            gs.action_stack.push(ElderSpawnUpkeepChoice(gs.player_turn_idx, gs, s), gs, False)
    return E()

def erhnam_djinn_on_upkeep():
    """At upkeep, target non-Wall creature an opponent controls gains forestwalk until your next upkeep"""
    class E(Effect):
        event = 'upkeep'

        def resolve(self, gs: GameState, source: GameCard, target: Optional[GameCard] = None):
            opp_id = flip(source.orig_owner_id)
            for c in gs.card_filter.on_player_board(opp_id).non_wall_creatures().result():
                gs.action_stack.push(AddKWA(opp_id, gs, source, c, 'Forestwalk'))
    return E()

def erosion_on_upkeep():
    """At upkeep of enchanted land's controller, destroy that land unless that player pays {1} or 1 life"""
    class E(Effect):
        event = 'upkeep'

        def resolve(self, gs: GameState, source: GameCard, target: Optional[GameCard] = None):
            gs.action_stack.push(ErosionUpkeepChoice(gs.player_turn_idx, gs, source), gs, False)
    return E()

def feedback_and_warp_artifact_on_upkeep():
    """At upkeep of enchanted card's controller, this Aura deals 1 damage to that player"""
    class E(Effect):
        event = 'upkeep'
        
        def resolve(self, gs: GameState, source: GameCard, target: Optional[GameCard] = None):
            gs.apply_damage(source, 1, target.orig_owner_id)
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

def ivory_tower_on_upkeep():
    class E(Effect):
        event = 'upkeep'

        def resolve(self, gs: GameState, source: GameCard, target: Optional[GameCard] = None):
            # At the beginning of your upkeep, you gain X life, where X is the number of cards in your hand minus 4
            p_id = source.orig_owner_id
            if (hand_size := len(gs.hands[p_id].cards)) > 4:
                gs.increment_life(p_id, hand_size - 4)
    return E()

def karma_on_upkeep():
    class E(Effect):
        event = 'upkeep'
        
        def resolve(self, gs: GameState, source: GameCard, target: Optional[GameCard] = None):
            """At the beginning of each player's upkeep,
            this enchantment deals damage to that player equal to the number of Swamps they control."""
            p_id = gs.player_turn_idx
            swamp_cnt = len(CardFilter(gs).on_player_board(p_id).by_slug('swamp').result())
            if swamp_cnt:
                gs.apply_damage(source, swamp_cnt, source.orig_owner_id)
    return E()

def junun_efreet_on_upkeep():
    class E(Effect):
        event = 'upkeep'

        def resolve(self, gs: GameState, source: GameCard, target=None):
            gs.action_stack.push(PayManaOrSacUpkeepChoice(source.orig_owner_id, gs, source, 'BB'), gs, False)
    return E()

def juzam_djinn_on_upkeep():
    class E(Effect):
        event = 'upkeep'

        def resolve(self, gs: GameState, source: GameCard, target: Optional[GameCard] = None):
            gs.apply_damage(source, 1, source.orig_owner_id)
    return E()

def lord_of_the_pit_on_upkeep():
    """At your upkeep, sacrifice a different creature. If you can't, this creature deals 7 damage to you."""
    class E(Effect):
        event = 'upkeep'

        def resolve(self, gs: GameState, source: GameCard, target: Optional[GameCard] = None):
            possible_sacrifice_actions = LordOfThePitUpkeepChoice(gs.player_turn_idx, gs, source).get_actions()
            if not possible_sacrifice_actions:
                gs.apply_damage(source, 7, source.orig_owner_id)
                return
            for action in possible_sacrifice_actions:
                gs.action_stack.push(action, gs, False)
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

def power_surge_on_upkeep():
    """At the beginning of each player's upkeep, this enchantment deals X damage to that player,
    where X is the number of untapped lands they controlled at the beginning of this turn"""
    class E(Effect):
        event = 'upkeep'

        def resolve(self, gs: GameState, source: GameCard, target: Optional[GameCard] = None):
            untapped_lands = gs.card_filter.in_play().untapped().lands().result()
            gs.apply_damage(source, len(untapped_lands), gs.player_turn_idx)
    return E()

def season_of_the_witch_on_upkeep():
    """At your upkeep, sacrifice this enchantment unless you pay 2 life"""
    class E(Effect):
        event = 'upkeep'

        def resolve(self, gs: GameState, source: GameCard, target=None):
            # Pause the game and force a choice
            gs.action_stack.push(SeasonOfTheWitchUpkeepChoice(source.orig_owner_id, gs, source), gs, False)
    return E()

def serendib_djinn_on_upkeep():
    """At your upkeep, sac a land. If it's an Island, 3 damage to you. When you control no lands, sac this creature."""
    class E(Effect):
        event = 'upkeep'

        def resolve(self, gs: GameState, source: GameCard, target=None):
            gs.action_stack.push(SerendibDjinnUpkeepChoice(gs.player_turn_idx, gs, source), gs, False)
    return E()

def serendib_efreet_on_upkeep():
    class E(Effect):
        event = 'upkeep'
        
        def resolve(self, gs: GameState, source: GameCard, target: Optional[GameCard] = None):
            gs.apply_damage(source, 1, source.orig_owner_id)
    return E()

def shapeshifter_on_upkeep():
    """At your upkeep, choose a number 0-7 (n). Shapeshifter's power = n, toughness = 7 - n"""
    class E(Effect):
        event = 'upkeep'

        def resolve(self, gs: GameState, source: GameCard, target: Optional[GameCard] = None):
            gs.action_stack.push(ShapeshifterChoice(source.orig_owner_id, gs, source), gs, False)
    return E()

def spiritual_sanctuary_on_upkeep():
    """At the beginning of each player's upkeep, if that player controls a Plains, they gain 1 life"""
    class E(Effect):
        event = 'upkeep'

        def resolve(self, gs: GameState, source: GameCard, target: Optional[GameCard] = None):
            if 'plains' in gs.card_filter.on_player_board(gs.player_turn_idx).by_slug('plains').result():
                gs.increment_life(gs.player_turn_idx, 1)
    return E()

def storm_world_on_upkeep():
    """At the beginning of each player's upkeep, this enchantment deals X damage to that player,
    where X is 4 minus the number of cards in their hand"""

    class E(Effect):
        event = 'upkeep'

        def resolve(self, gs: GameState, source: GameCard, target: Optional[GameCard] = None):
            card_cnt = len(gs.hands[gs.player_turn_idx].cards)
            if card_cnt > 4:
                gs.apply_damage(source, card_cnt - 4, gs.player_turn_idx)
    return E()

def sunken_city_on_upkeep():
    """At the beginning of your upkeep, sacrifice this enchantment unless you pay {UU}."""
    class E(Effect):
        event = 'upkeep'

        def resolve(self, gs: GameState, source: GameCard, target=None):
            # Pause the game and force a choice
            gs.action_stack.push(PayManaOrSacUpkeepChoice(source.orig_owner_id, gs, source, 'UU'), gs, False)
    return E()
