from __future__ import annotations
import math
from typing import Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from game_state import GameState
    from models.game_card import GameCard

from card_filter import CardFilter
from models.choice_actions.choice_actions_all import ElderSpawnUpkeepChoice, CurseArtifactUpkeepChoice, LordOfThePitUpkeepChoice
from models.damage import DamageEvent, PreventNextDamage
from models.effects.base import Effect
from utils import flip


class PsionicEntityAA(Effect):
    """{T}: This creature deals 2 damage to any target and 3 damage to itself"""
    def resolve(self, gs: GameState, source: GameCard, target: GameCard = None):
        gs.apply_damage(source, 2, target)
        gs.apply_damage(source, 3, source)


def erg_raiders_on_end_step():
    """At YOUR end step, except for summoning sickness, if this creature didn't attack, 2 damage to you"""
    class E(Effect):
        event = 'end_step'

        def resolve(self, gs: GameState, s: GameCard, target: Optional[GameCard] = None):
            if gs.player_turn_idx != s.orig_owner_id:
                return
            if s.has_summoning_sickness:
                return
            if s not in gs.card_filter.attackers().result():
                gs.apply_damage(s, 2, s.orig_owner_id)
    return E()


def argothian_pixies_damage_prevention():
    """Prevent all damage that would be dealt to this creature by artifact creatures"""
    class E(Effect):
        def on_damage(self, gs: GameState, event: DamageEvent):
            # don't have access to GameCard due to circular import; using hasattr() to see if source is a card
            if not hasattr(event.target, 'props') or event.target.props.slug != 'argothian-pixies':
                return
            if 'Artifact' in event.source.props.card_types and 'Creature' in event.source.props.card_types:
                event.prevented += event.remaining
    return E()


def argothian_treefolk_damage_prevention():
    """Prevent all damage that would be dealt to this creature by artifact sources"""
    class E(Effect):
        def on_damage(self, gs: GameState, event: DamageEvent):
            if not hasattr(event.target, 'props') or event.target.props.slug != 'argothian-treefolk':
                return
            if 'Artifact' in event.source.props.card_types:
                event.prevented += event.remaining
    return E()


def artifact_ward_damage_prevention():
    """Prevent all damage that would be dealt to enchanted creature by artifact sources"""
    class E(Effect):
        def on_damage(self, gs: GameState, event: DamageEvent):
            if not hasattr(event.target, 'props') or not event.target.modifiers.is_enchanted_by('artifact-ward'):
                return
            if 'Artifact' in event.source.props.card_types:
                event.prevented += event.remaining
    return E()


def enchanted_being_damage_prevention():
    """Prevent all combat damage that would be dealt to this creature by enchanted creatures"""
    class E(Effect):
        def on_damage(self, gs: GameState, event: DamageEvent):
            if not hasattr(event.target, 'props') or event.target.props.slug != 'enchanted-being':
                return
            if event.is_combat and [a for a in event.source.modifiers.auras if hasattr(a, 'props')]:
                event.prevented += event.remaining
    return E()


def marble_priest_damage_prevention():
    """Prevent all combat damage that would be dealt to this creature by Walls"""
    class E(Effect):
        def on_damage(self, gs: GameState, event: DamageEvent):
            if not hasattr(event.target, 'props') or event.target.props.slug != 'marble_priest':
                return
            if event.is_combat and 'Wall' in event.source.props.card_sub_types:
                event.prevented += event.remaining
    return E()


def all_damage_prevented_to_target_card(c: GameCard):
    class E(Effect):
        def on_damage(self, gs: GameState, event: DamageEvent):
            if event.target == c:
                event.prevented += event.remaining
    return E()


def scarecrow_func():
    class E(Effect):
        def on_damage(self, gs: GameState, event: DamageEvent):
            if event.target == flip(gs.player_turn_idx):
                if event.source in gs.card_filter.in_play().creatures().has('Flying').result():
                    event.prevented += event.remaining
    return E()


def all_combat_damage_prevented():
    class E(Effect):
        def on_damage(self, gs: GameState, event: DamageEvent):
            if event.is_combat:
                event.prevented += event.remaining
    return E()


def creature_bond_on_leave():
    class E(Effect):
        event = 'leave'

        def resolve(self, gs, source: GameCard, target: Optional[GameCard] = None):
            # TODO: i think this is wrong; i think it's only if creature goes to graveyard
            # creature leaving: for every attached aura that is creature-bond, do life loss to creature's owner
            for aura in target.modifiers.auras:
                if aura.props.slug == 'creature-bond':
                    gs.decrement_life(target.orig_owner_id, target.props.toughness, aura)
                    # TODO: use apply_damage instead of directly calling decrement_life; make decrement_life private?
    return E()


def martyrs_of_korlis_on_damage():
    """As long as this creature is untapped,
    all damage that would be dealt to you by artifacts is dealt to this creature instead"""
    class E(Effect):
        event = 'on_damage'

        def resolve(self, gs: GameState, event: DamageEvent, this_card: GameCard = None):
            if this_card.is_tapped:
                return
            if event.target != this_card.orig_owner_id:
                return
            if 'Artifact' not in event.source.props.card_types:
                return
            event.target = this_card
    return E()


class DealDamage(Effect):
    def __init__(self, amount):
        self.amount = amount

    def resolve(self, gs, source: GameCard, target: GameCard = None):
        gs.apply_damage(source, self.amount, target)


def copper_tablet_on_upkeep():
    """At the beginning of each player's upkeep, this artifact deals 1 damage to that player"""
    class E(Effect):
        event = 'upkeep'

        def resolve(self, gs: GameState, source: GameCard, target: Optional[GameCard] = None):
            gs.apply_damage(source, 1, gs.player_turn_idx)
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


def curse_artifact_on_upkeep():
    """At enchanted artifact's controller's upkeep, deal 2 damage to that player unless they sacrifice that artifact"""
    class E(Effect):
        event = 'upkeep'

        def resolve(self, gs: GameState, s: GameCard, target=None):
            gs.action_stack.push(CurseArtifactUpkeepChoice(gs.player_turn_idx, gs, s), gs, False)
    return E()


def feedback_and_warp_artifact_on_upkeep():
    """At upkeep of enchanted card's controller, this Aura deals 1 damage to that player"""
    class E(Effect):
        event = 'upkeep'

        def resolve(self, gs: GameState, source: GameCard, target: Optional[GameCard] = None):
            gs.apply_damage(source, 1, target.orig_owner_id)
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


def power_surge_on_upkeep():
    """At the beginning of each player's upkeep, this enchantment deals X damage to that player,
    where X is the number of untapped lands they controlled at the beginning of this turn"""
    class E(Effect):
        event = 'upkeep'

        def resolve(self, gs: GameState, source: GameCard, target: Optional[GameCard] = None):
            untapped_lands = gs.card_filter.in_play().untapped().lands().result()
            gs.apply_damage(source, len(untapped_lands), gs.player_turn_idx)
    return E()


def serendib_efreet_on_upkeep():
    class E(Effect):
        event = 'upkeep'

        def resolve(self, gs: GameState, source: GameCard, target: Optional[GameCard] = None):
            gs.apply_damage(source, 1, source.orig_owner_id)
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


def earthquake_on_cast():
    """Earthquake deals X damage to each creature without flying and each player"""
    class E(Effect):
        event = 'cast'

        def resolve(self, gs: GameState, source: GameCard, target: Optional[GameCard] = None):
            x = getattr(source, 'variable_x', 0)  # read X chosen when casting
            for c in gs.card_filter.in_play().has('Flying', False).creatures().result():
                gs.apply_damage(source, x, c)
            for p_id in (0, 1):
                gs.apply_damage(source, x, p_id)
    return E()


def electric_eel_on_cast():
    class E(Effect):
        event = 'cast'

        def resolve(self, gs: GameState, source: GameCard, target: Optional[GameCard] = None):
            gs.decrement_life(source.orig_owner_id, 1, source)
            # TODO: decrement_life or apply_damage?
    return E()


def eternal_flame_on_cast():
    class E(Effect):
        event = 'cast'

        def resolve(self, gs: GameState, source: GameCard, target: Optional[GameCard] = None):
            """x = number of mountains caster controls; deal x damage to opponent and round(x/2) to caster"""
            x = len(CardFilter(gs).on_player_board(gs.player_turn_idx).by_slug('mountain').result())
            gs.decrement_life(flip(gs.player_turn_idx), x, source)
            gs.decrement_life(gs.player_turn_idx, math.ceil(x/2), source)
            # TODO: decrement_life or apply_damage?
    return E()


def eye_for_an_eye_on_cast():
    """The next time a source of your choice would deal damage to you this turn, also deal damage to source's owner."""
    # Handling this in an interesting way to work within current framework:
    # Prevent all damage via gs.damage_preventions, then apply the damage here via the callback

    class E(Effect):
        event = 'cast'

        def resolve(self, gs: GameState, s: GameCard, t: Optional[GameCard] = None):
            """target = the GameCard doing the original damage"""
            def deal_damage(prevented: int):
                gs.apply_damage(t, prevented, s.orig_owner_id)
                gs.apply_damage(s, prevented, t.orig_owner_id)

            gs.damage_preventions.append(
                PreventNextDamage(s, None, target_player=s.orig_owner_id, source_card=t, on_prevent=deal_damage))
    return E()


def indestructible_aura_on_cast():
    class E(Effect):
        event = 'cast'

        def resolve(self, gs: GameState, source: GameCard, target: Optional[GameCard] = None):
            """target = the GameCard being protected"""
            gs.damage_preventions.append(PreventNextDamage(source, target_card=target))
    return E()


def inferno_on_cast():
    class E(Effect):
        event = 'cast'

        def resolve(self, gs: GameState, source: GameCard, target: Optional[GameCard] = None):
            # Inferno deals 6 damage to each creature and each player
            [gs.apply_damage(source, 6, p_id, is_combat=False) for p_id in (0, 1)]
            [gs.apply_damage(source, 6, creature) for creature in gs.card_filter.in_play().creatures().result()]
    return E()


def jovial_evil_on_cast():
    class E(Effect):
        event = 'cast'

        def resolve(self, gs: GameState, source: GameCard, target: Optional[GameCard] = None):
            # deals X damage to target opponent, where X is twice the number of white creatures that player controls
            opp_white_creature_cnt = len(gs.card_filter.on_player_board(target).creatures().result())
            gs.apply_damage(source, opp_white_creature_cnt * 2, target)
    return E()


def lightning_bolt_on_cast():
    class E(Effect):
        event = 'cast'

        def resolve(self, gs: GameState, source: GameCard, target: Optional[GameCard] = None):
            gs.apply_damage(source, 3, target)
    return E()


def typhoon_on_cast():
    """Typhoon deals damage to opponent = the number of Islands that player controls"""
    class E(Effect):
        event = 'cast'

        def resolve(self, gs: GameState, s: GameCard, t: Optional[GameCard] = None):
            opp = flip(gs.player_turn_idx)
            opp_island_cnt = len(gs.card_filter.on_player_board(opp).by_slug('island').result())
            if opp_island_cnt:
                gs.apply_damage(s, opp_island_cnt, opp)
    return E()


def gaseous_form_on_cast():
    """Prevent all combat damage that would be dealt this turn by enchanted creature and each creature blocking it."""
    class E(Effect):
        event = 'cast'

        def resolve(self, gs: GameState, s: GameCard, target: Optional[GameCard] = None):
            """target = the enchanted attacker"""
            the_combat = [com for com in gs.combats if com.attacker == target]
            if not the_combat:
                return
            gs.damage_preventions.append(PreventNextDamage(s, None, target_card=target, combat_only=True))
            for b in the_combat[0].blockers:
                gs.damage_preventions.append(PreventNextDamage(s, None, target_card=b, combat_only=True))
    return E()


def psionic_blast_on_cast():
    """Psionic Blast deals 4 damage to any target and 2 damage to you"""
    class E(Effect):
        event = 'cast'

        def resolve(self, gs, source: GameCard, target: Optional[GameCard] = None):
            if not target:
                raise ValueError("Psionic Blast needs a target")
            gs.apply_damage(source, 4, target)
            gs.apply_damage(source, 2, source.orig_owner_id)


def storm_seeker_on_cast():
    """Storm Seeker deals damage to target player equal to the number of cards in that player's hand"""

    class E(Effect):
        event = 'cast'

        def resolve(self, gs: GameState, source: GameCard, t: Optional[GameCard] = None):
            opp_idx = flip(source.orig_owner_id)
            gs.apply_damage(source, len(gs.hands[opp_idx].cards), opp_idx)
    return E()
