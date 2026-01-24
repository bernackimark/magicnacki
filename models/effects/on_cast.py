from __future__ import annotations
import math
from typing import TYPE_CHECKING, Optional

from phase_fsm import Phase
from utils import flip
from ..actions.choices import SacYourCreatureChoice, Sac, SacCreatureAndAddMana, ShapeshifterChoice
from ..actions.draw_discard import DiscardCard
from ..damage import PreventNextDamage

if TYPE_CHECKING:
    from ..game_card import GameCard
    from game_state import GameState

from models.effects.base import Effect
from models.effects.global_ import AngelicVoicesEffect, BadMoonEffect, CastleEffect, CrusadeEffect, \
    all_combat_damage_prevented, all_damage_prevented_to_target_card, SunkenCityEffect
from models.modifiers import KWAModifier, KWATemp, PTModifier, PTTemp
from card_filter import CardFilter


def acid_rain_on_cast():
    class E(Effect):
        event = 'cast'

        def resolve(self, gs: GameState, source: "GameCard", target: Optional["GameCard"] = None):
            for forest in CardFilter(gs).in_play().by_slug('forest').result():
                gs.send_to_graveyard_from_play(forest)
    return E()

def active_volcano_on_cast():
    """Choose one - * Destroy target blue permanent. * Return target Island to its owner's hand."""
    class E(Effect):
        event = 'cast'

        def resolve(self, gs: GameState, s: GameCard, t: GameCard = None):
            gs.return_to_hand_from_board(t) if t.props.slug == 'island' else gs.send_to_graveyard_from_play(t)

    return E()

def akron_legionnaire_on_cast():
    class E(Effect):
        event = 'cast'

        def resolve(self, gs, source: GameCard, target: Optional[GameCard] = None):
            # Except for creatures named Akron Legionnaire and artifact creatures, creatures you control can't attack
            my_creatures = CardFilter(gs).creatures().on_player_board(source.orig_owner_id).result()
            artifact_creatures = CardFilter(gs).creatures().on_player_board(source.orig_owner_id).by_color('C').result()
            akron_legionnaires = CardFilter(gs).creatures().on_player_board(source.orig_owner_id).by_slug(
                'akron-legionnaire').result()
            for my_creature in my_creatures:
                if my_creature not in [artifact_creatures + akron_legionnaires]:
                    my_creature.modifiers.auras.append(KWAModifier(source, 'remove', 'Attack'))
    return E()

def ancestral_recall_on_cast():
    class E(Effect):
        event = 'cast'

        def resolve(self, gs: GameState, source: GameCard, target: Optional[int] = None):
            """target = player_id whose lands should be tapped"""
            if target is None:
                return
            gs.draw(gs.hands[target], gs.decks[target].cards, 3)
            print(f"Ancestral Recall has player #{target} draw three cards.")
    return E()


def angelic_voices_on_cast():
    class E(Effect):
        event = 'cast'

        def resolve(self, gs, source: GameCard, target: Optional[GameCard] = None):
            # TODO: Review this new approach where global effects don't directly influence GameCards
            gs.global_effects.append((source, AngelicVoicesEffect(source.orig_owner_id), False))
            # add +0/+2 mod for in-turn player's creatures that are untapped
            # for c in CardFilter(gs).creatures().on_player_board(gs.player_turn_idx).tapped(False).result():
            #     c.pt_modifiers.append(PTModifier(source, 0, 2))

    return E()

def animate_wall_on_cast():
    class E(Effect):
        event = 'cast'

        def resolve(self, gs, source: GameCard, target: Optional[GameCard] = None):
            target.modifiers.auras.append(KWAModifier(source, 'remove', 'Defender'))
    return E()


def bad_moon_on_cast():
    class E(Effect):
        event = 'cast'

        def resolve(self, gs, source: GameCard, target: Optional[GameCard] = None):
            # TODO: Review this new approach where global effects don't directly influence GameCards
            gs.global_effects.append((source, BadMoonEffect(source.orig_owner_id), False))

    return E()

def blood_lust_on_cast():
    class E(Effect):
        event = 'cast'

        def resolve(self, gs, source: GameCard, target: Optional[GameCard] = None):
            # Target creatures gain +4/-4 until end of turn. If this reduces creature's toughness < 1, toughness = 1.
            if target:
                new_toughness = max(1, target.toughness - 4)
                toughness_mod = new_toughness - target.toughness
                target.modifiers.auras.append(PTModifier(source, 4, toughness_mod))
    return E()

def boomerang_on_cast():
    class E(Effect):
        event = 'cast'

        def resolve(self, gs, source: GameCard, target: Optional[GameCard] = None):
            if target:
                board = gs.boards[target.orig_owner_id]
                board.remove_from_board(target)
                gs.return_to_hand(target)
    return E()

def braingeyser_on_cast():
    class E(Effect):
        event = 'cast'

        def resolve(self, gs: GameState, source: GameCard, target: int = None):
            if target is not None:
                x = getattr(source, 'variable_x', 0)  # read X chosen when casting
                gs.draw(gs.hands[target], gs.decks[target].cards, x)
    return E()

def brainwash_on_cast():
    class E(Effect):
        event = 'cast'

        def resolve(self, gs, source: GameCard, target: Optional[GameCard] = None):
            target.modifiers.auras.append(KWAModifier(source, 'remove', 'Attack'))
    return E()

def burrowing_on_cast():
    class E(Effect):
        event = 'cast'

        def resolve(self, gs, source: GameCard, target: Optional[GameCard] = None):
            if target:
                target.modifiers.auras.append(KWAModifier(source, 'add', 'Mountainwalk'))

    return E()

def castle_on_cast():
    class E(Effect):
        event = 'cast'
        
        def resolve(self, gs, source: GameCard, target: Optional[GameCard] = None):
            # TODO: Review this new approach where global effects don't directly influence GameCards
            gs.global_effects.append((source, CastleEffect(source.orig_owner_id), False))
            # add +0/+2 mod for in-turn player's creatures that are untapped
            # for c in CardFilter(gs).creatures().on_player_board(gs.player_turn_idx).tapped(False).result():
            #     c.pt_modifiers.append(PTModifier(source, 0, 2))
    return E()

def cleanse_on_cast():
    class E(Effect):
        event = 'cast'

        def resolve(self, gs, source: GameCard, target: Optional[GameCard] = None):
            for c in CardFilter(gs).in_play().creatures().black().result():
                gs.send_to_graveyard_from_play(c)
    return E()


def crumble_on_cast():
    class E(Effect):
        event = 'cast'

        def resolve(self, gs, source: GameCard, target: Optional[GameCard] = None):
            if target:
                gs.send_to_graveyard_from_play(target)
                gs.increment_life(target.orig_owner_id, target.props.casting_weight)

    return E()

def crusade_on_cast():
    class E(Effect):
        event = 'cast'
        
        def resolve(self, gs, source: GameCard, target: Optional[GameCard] = None):
            # TODO: Review this new approach where global effects don't directly influence GameCards
            gs.global_effects.append((source, CrusadeEffect(source.orig_owner_id), False))
            # for c in CardFilter(gs).in_play().creatures().white().result():
            #     c.pt_modifiers.append(PTModifier(source, 1, 1))
    return E()

def dark_ritual_on_cast():
    class E(Effect):
        event = 'cast'

        def resolve(self, gs: GameState, source: GameCard, target: Optional[int] = None):
            gs.mana_pools[source.orig_owner_id].add_floating('B', 3)
    return E()

def darkness_or_fog_or_holy_day_on_cast():
    class E(Effect):
        event = 'cast'

        def resolve(self, gs: GameState, source: GameCard, target=None):
            gs.global_effects.append((source, all_combat_damage_prevented(), True))
    return E()

def demonic_torment_on_cast():
    class E(Effect):
        event = 'cast'

        def resolve(self, gs, source: GameCard, target: Optional[GameCard] = None):
            if not target:
                raise ValueError("Demonic Torment needs a target")
            target.modifiers.auras.append(KWAModifier(source, 'remove', 'Attack'))

    return E()

def desert_twister_on_cast():
    class E(Effect):
        event = 'cast'

        def resolve(self, gs, source: GameCard, target: Optional[GameCard] = None):
            if not target:
                raise ValueError("Desert Twister needs a target")
            if target:
                gs.send_to_graveyard_from_play(target)

    return E()

def disenchant_on_cast():
    class E(Effect):
        event = 'cast'
        
        def resolve(self, gs, source: GameCard, target: Optional[GameCard] = None):
            if not target:
                raise ValueError("Disenchant needs a target")
            if target:
                print(f"Disenchant's target is {target}")
                gs.send_to_graveyard_from_play(target)
    return E()

def divine_offering_on_cast():
    class E(Effect):
        event = 'cast'

        def resolve(self, gs, source: GameCard, target: Optional[GameCard] = None):
            if not target:
                raise ValueError("Divine Offering needs a target")
            if target:
                gs.increment_life(source.orig_owner_id, target.power)
                gs.send_to_graveyard_from_play(target)

    return E()

def divine_transformation_on_cast():
    class E(Effect):
        event = 'cast'

        def resolve(self, gs, source: GameCard, target: Optional[GameCard] = None):
            if target:
                target.modifiers.auras.append(PTModifier(source, 3, 3))
    return E()

def drain_power_on_cast():
    class E(Effect):
        event = 'cast'

        def resolve(self, gs: GameState, source: GameCard, target: Optional[int] = None):
            """target = player_id whose available mana will be targeted & given to the other player"""
            if target is None:
                return
            land_giver_mana = gs.mana_pools[target].available_mana.copy()
            land_taker_id = flip(target)
            for color, amt in land_giver_mana.items():
                gs.mana_pools[land_taker_id].add_floating(color, amt)
            print(f"{source} steals all of Player #{target}'s unused mana.")
    return E()

def earthbind_on_cast():
    class E(Effect):
        event = 'cast'

        def resolve(self, gs: GameState, source: GameCard, target: Optional[GameCard] = None):
            if target:
                target.modifiers.auras.append(KWAModifier(source, 'remove', 'Flying'))
            if 'Flying' in target.keyword_abilities:
                gs.decrement_life(target.orig_owner_id, 2, source)
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
    return E()

def energy_tap_on_cast():
    class E(Effect):
        event = 'cast'

        def resolve(self, gs: GameState, source: GameCard, target: Optional[GameCard] = None):
            """target = GameCard to be tapped"""
            if target is None:
                return
            target.tap(gs)
            mana_value = source.props.casting_weight
            gs.mana_pools[source.orig_owner_id].add_floating('C', mana_value)
            print(f"{source} taps to add {mana_value} colorless to your mana pool.")
    return E()

def eternal_flame_on_cast():
    class E(Effect):
        event = 'cast'

        def resolve(self, gs: GameState, source: GameCard, target: Optional[GameCard] = None):
            """x = number of mountains caster controls; deal x damage to opponent and round(x/2) to caster"""
            x = len(CardFilter(gs).on_player_board(gs.player_turn_idx).by_slug('mountain').result())
            gs.decrement_life(flip(gs.player_turn_idx), x, source)
            gs.decrement_life(gs.player_turn_idx, math.ceil(x/2), source)
    return E()

def eternal_warrior_on_cast():
    class E(Effect):
        event = 'cast'

        def resolve(self, gs, source: GameCard, target: Optional[GameCard] = None):
            if not target:
                raise ValueError("Eternal Warrior needs a target")
            target.modifiers.auras.append(KWAModifier(source, 'add', 'Vigilance'))
    return E()

def evil_eye_of_orms_by_gore_on_cast():
    class E(Effect):
        event = 'cast'

        def resolve(self, gs, source: GameCard, target: Optional[GameCard] = None):
            """Non-Eye creatures you control can't attack."""
            my_creatures = CardFilter(gs).creatures().on_player_board(source.orig_owner_id).result()
            my_eyes = CardFilter(gs).creatures().on_player_board(source.orig_owner_id).by_sub_type('Eye').result()
            for my_creature in my_creatures:
                if my_creature not in my_eyes:
                    my_creature.modifiers.auras.append(KWAModifier(source, 'remove', 'Attack'))
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

def farmstead_on_cast():
    class E(Effect):
        event = 'cast'

        def resolve(self, gs, source: GameCard, target: Optional[GameCard] = None):
            target.modifiers.auras.append(source)
    return E()

def feint_on_cast():
    """Tap all creatures blocking target attacking creature.
    Prevent all combat damage that would be dealt this turn by that creature and each creature blocking it."""
    class E(Effect):
        event = 'cast'

        def resolve(self, gs: GameState, s: GameCard, target: Optional[GameCard] = None):
            """target = the attacker"""
            the_combat = [com for com in gs.combats if com.attacker == target]
            if not the_combat:
                return
            gs.damage_preventions.append(PreventNextDamage(s, None, target_card=target, combat_only=True))
            for b in the_combat[0].blockers:
                gs.damage_preventions.append(PreventNextDamage(s, None, target_card=b, combat_only=True))
                b.tap(gs)
    return E()

def flash_flood_on_cast():
    """Choose one - * Destroy target red permanent. * Return target Mountain to its owner's hand."""
    class E(Effect):
        event = 'cast'

        def resolve(self, gs: GameState, s: GameCard, t: GameCard = None):
            gs.return_to_hand_from_board(t) if t.props.slug == 'mountain' else gs.send_to_graveyard_from_play(t)
    return E()

def flight_on_cast():
    class E(Effect):
        event = 'cast'
        
        def resolve(self, gs, source: GameCard, target: Optional[GameCard] = None):
            if target:
                target.modifiers.auras.append(KWAModifier(source, 'add', 'Flying'))
    return E()

def fishliver_oil_on_cast():
    class E(Effect):
        event = 'cast'

        def resolve(self, gs, source: GameCard, target: Optional[GameCard] = None):
            if not target:
                raise ValueError("Fishliver Oil needs a target")
            target.modifiers.auras.append(KWAModifier(source, 'add', 'Islandwalk'))
    return E()

def flashfires_on_cast():
    class E(Effect):
        event = 'cast'

        def resolve(self, gs: GameState, source: GameCard, target: Optional[GameCard] = None):
            """Destroy all plains"""
            for plains in gs.card_filter.in_play().by_slug('plains').result():
                gs.send_to_graveyard_from_play(plains)
    return E()

def forest_on_cast():
    class E(Effect):
        event = 'cast'

        def resolve(self, gs: GameState, source: GameCard, target: Optional[GameCard] = None):
            for c in gs.card_filter.on_player_board(source.orig_owner_id).result():
                if c.props.slug == 'kird-ape' and PTModifier(c, 1, 2) not in c.modifiers.auras:
                    c.modifiers.auras.append(PTModifier(c, 1, 2))
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

def giant_growth_on_cast():
    class E(Effect):
        event = 'cast'

        def resolve(self, gs, source: GameCard, target: Optional[GameCard] = None):
            target.modifiers.auras.append(PTTemp(3, 3))
    return E()

def giant_strength_on_cast():
    class E(Effect):
        event = 'cast'

        def resolve(self, gs, source: GameCard, target: Optional[GameCard] = None):
            target.modifiers.auras.append(PTModifier(source, 2, 2))
    return E()

def giant_tortoise_on_cast():
    class E(Effect):
        event = 'cast'
        
        def resolve(self, gs, source: GameCard, target: Optional[GameCard] = None):
            source.modifiers.auras.append(PTModifier(source, 0, 3))
    return E()

def glyph_of_destruction_on_cast():
    """Target blocking Wall you control gets +10/+0 until end of combat.
    Prevent all damage that would be dealt to it this turn. Destroy it at the beginning of the next end step."""
    class E(Effect):
        event = 'cast'

        def resolve(self, gs: GameState, s: GameCard, t: Optional[GameCard] = None):
            t.modifiers.temps(PTTemp(10, 0))
            gs.global_effects.append((s, all_damage_prevented_to_target_card(s), True))
            gs.end_step_funcs.append(lambda gs, s, t: gs.send_to_graveyard_from_play(s))
    return E()

def goblin_king_on_cast():
    class E(Effect):
        event = 'cast'

        def resolve(self, gs: GameState, source: GameCard, target: Optional[GameCard] = None):
            """All of your other Goblins gain +1+/+1 and Mountainwalk"""
            targets = gs.card_filter.on_player_board(source.orig_owner_id).creatures().by_sub_type('Goblin').result()
            for t in targets:
                if source != t:
                    t.modifiers.auras.append(KWAModifier(source, 'add', 'Mountainwalk'))
                    t.modifiers.auras.append(PTModifier(source, 1, 1))
    return E()

def great_defender_on_cast():
    class E(Effect):
        event = 'cast'

        def resolve(self, gs, source: GameCard, target: Optional[GameCard] = None):
            """Target creature gets +0/+X until end of turn, where X is its mana value."""
            if target:
                target.modifiers.auras.append(PTTemp(0, target.props.casting_weight))
    return E()

def holy_armor_on_cast():
    class E(Effect):
        event = 'cast'
        
        def resolve(self, gs, source: GameCard, target: Optional[GameCard] = None):
            if not target:
                raise ValueError("Holy armor didn't get a target!")
            if target:
                target.modifiers.auras.append(PTModifier(source, 0, 2))
    return E()

def holy_strength_on_cast():
    class E(Effect):
        event = 'cast'
        
        def resolve(self, gs, source: GameCard, target: Optional[GameCard] = None):
            if target:
                target.modifiers.auras.append(PTModifier(source, 1, 2))
    return E()

def howl_from_beyond_on_cast():
    """Target creature gets +X/+0 until end of turn"""
    class E(Effect):
        event = 'cast'

        def resolve(self, gs: GameState, source: GameCard, target: GameCard = None):
            if target is not None:
                x = getattr(source, 'variable_x', 0)  # read X chosen when casting
                target.modifiers.temps.append(PTTemp(x, 0))
    return E()


def ice_storm_on_cast():
    class E(Effect):
        event = 'cast'

        def resolve(self, gs: GameState, source: GameCard, target: Optional[GameCard] = None):
            """Destroy one land"""
            gs.send_to_graveyard_from_play(target)
    return E()

def immolation_on_cast():
    class E(Effect):
        event = 'cast'

        def resolve(self, gs: GameState, source: GameCard, target: Optional[GameCard] = None):
            if target:
                target.modifiers.auras.append(PTModifier(source, 2, -2))
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

def instill_energy_on_cast():
    class E(Effect):
        event = 'cast'

        def resolve(self, gs, source: GameCard, target: Optional[GameCard] = None):
            if not target:
                raise ValueError("Instill Energy needs a target")
            target.modifiers.auras.append(KWAModifier(source, 'add', 'Haste'))
    return E()

def jovial_evil_on_cast():
    class E(Effect):
        event = 'cast'

        def resolve(self, gs: GameState, source: GameCard, target: Optional[GameCard] = None):
            # deals X damage to target opponent, where X is twice the number of white creatures that player controls
            opp_white_creature_cnt = len(gs.card_filter.on_player_board(target).creatures().result())
            gs.apply_damage(source, opp_white_creature_cnt * 2, target)
    return E()

def jump_on_cast():
    class E(Effect):
        event = 'cast'
        
        def resolve(self, gs, source: GameCard, target: Optional[GameCard] = None):
            if target:
                target.modifiers.temps.append(KWATemp('add', 'Flying'))
    return E()

def kobold_drill_sergeant_on_cast():
    class E(Effect):
        event = 'cast'

        def resolve(self, gs: GameState, source: GameCard, target: Optional[GameCard] = None):
            """Other Kobold creatures you control get +0/+1 and have trample"""
            kobolds = gs.card_filter.on_player_board(source.orig_owner_id).creatures().by_sub_type('Kobold').result()
            for k in kobolds:
                if source != k:
                    k.modifiers.auras.append(KWAModifier(source, 'add', 'Trample'))
                    k.modifiers.auras.append(PTModifier(source, 0, 1))
    return E()

def kobold_overlord_on_cast():
    """Other Kobold creatures you control have first strike"""
    class E(Effect):
        event = 'cast'

        def resolve(self, gs: GameState, source: GameCard, target: Optional[GameCard] = None):
            targets = gs.card_filter.on_player_board(source.orig_owner_id).creatures().by_sub_type('Kobold').result()
            for t in targets:
                if source != t:
                    t.modifiers.auras.append(KWAModifier(source, 'add', 'First Strike'))
    return E()

def kobold_taskmaster_on_cast():
    """Other Kobold creatures you control get +1/+0"""
    class E(Effect):
        event = 'cast'

        def resolve(self, gs: GameState, source: GameCard, target: Optional[GameCard] = None):
            for t in gs.card_filter.on_player_board(source.orig_owner_id).creatures().by_sub_type('Kobold').result():
                if source != t:
                    t.modifiers.auras.append(PTModifier(source, 1, 0))
    return E()

def lance_on_cast():
    class E(Effect):
        event = 'cast'
        
        def resolve(self, gs, source: GameCard, target: Optional[GameCard] = None):
            if target:
                target.modifiers.auras.append(KWAModifier(source, 'add', 'First Strike'))
    return E()

def leviathan_on_cast():
    class E(Effect):
        event = 'cast'

        def resolve(self, gs, source: GameCard, _: Optional[GameCard] = None):
            source.tap(gs)
    return E()

def lightning_bolt_on_cast():
    class E(Effect):
        event = 'cast'

        def resolve(self, gs: GameState, source: GameCard, target: Optional[GameCard] = None):
            gs.apply_damage(source, 3, target)
    return E()

def lord_of_atlantis_on_cast():
    class E(Effect):
        event = 'cast'

        def resolve(self, gs: GameState, source: GameCard, target: Optional[GameCard] = None):
            """All of your other Merfolk gain +1/+1 and Islandwalk"""
            targets = gs.card_filter.on_player_board(source.orig_owner_id).creatures().by_sub_type('Merfolk').result()
            for t in targets:
                if source != t:
                    t.modifiers.auras.append(KWAModifier(source, 'add', 'Islandwalk'))
                    t.modifiers.auras.append(PTModifier(source, 1, 1))
    return E()

def mana_short_on_cast():
    class E(Effect):
        event = 'cast'

        def resolve(self, gs: GameState, source: GameCard, target: Optional[int] = None):
            """target = player_id whose lands should be tapped"""
            if target is None:
                return
            player_lands = (CardFilter(gs).on_player_board(target).lands().result())
            for land in player_lands:
                land.tap(gs)
            print(f"Mana Short taps {len(player_lands)} lands belonging to player {target}.")
    return E()

def mana_vortex_on_cast():
    """When you cast this spell, sacrifice a land"""
    class E(Effect):
        event = 'cast'

        def resolve(self, gs: GameState, source: GameCard, target: GameCard = None):
            """target = player_id whose lands should be tapped"""
            if target is None:
                raise ValueError(f"{source.props.name} needs a land to sacrifice")
            gs.send_to_graveyard_from_play(target)
    return E()

def martyrs_cry_on_cast():
    """Sorcery WW [] Exile all white creatures. For each creature exiled this way, its controller draws a card."""
    class E(Effect):
        event = 'cast'

        def resolve(self, gs: GameState, source: GameCard, target: Optional[GameCard] = None):
            for white_creature in gs.card_filter.in_play().white().creatures().result():
                owner_id = white_creature.orig_owner_id
                gs.send_to_exile_from_play(white_creature)  # which is correct?  exile_from_play() or exile()
                gs.draw(gs.hands[owner_id], gs.decks[owner_id].cards, 1)
    return E()

def nevinyrrals_disk_on_cast():
    """This artifact enters tapped"""
    class E(Effect):
        event = 'cast'

        def resolve(self, gs: GameState, source: GameCard, target: Optional[GameCard] = None):
            source.tap(gs)  # what is the correct way to handle tapping a card: gs.apply_tap_effects() or c.tap()?
            gs.apply_tap_effects(source)
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

def reset_on_cast():
    """Cast this spell only during an opponent's turn after their upkeep step. Untap all lands you control"""
    class E(Effect):
        event = 'cast'

        def resolve(self, gs: GameState, source: GameCard, target: Optional[GameCard] = None):
            if gs.phase == Phase.UPKEEP or gs.player_turn_idx == source.orig_owner_id:
                raise ValueError("Reset must be played on opponent's turn after their upkeep phase")
            for land in gs.card_filter.on_player_board(source.orig_owner_id).lands().untapped().result():
                land.untap(gs)
    return E()

def reverse_damage_on_cast():
    """The next time a source of your choice would deal damage to you this turn, prevent that damage.
    You gain life equal to the damage prevented this way.
    Since amount prevented isn't known upon cast, use PreventNextDamage.on_prevent() callback to later call gain_life"""
    class E(Effect):
        event = 'cast'

        def resolve(self, gs: GameState, s: GameCard, target: Optional[GameCard] = None):
            """target = the GameCard doing the damage"""
            def gain_life(prevented: int):
                gs.increment_life(s.orig_owner_id, prevented)

            gs.damage_preventions.append(
                PreventNextDamage(s, None, target_player=s.orig_owner_id, source_card=target, on_prevent=gain_life))
    return E()

def riptide_on_cast():
    """Tap all blue creatures"""

    class E(Effect):
        event = 'cast'

        def resolve(self, gs: GameState, _: GameCard, t: Optional[GameCard] = None):
            for c in gs.card_filter.in_play().creatures().untapped().blue().result():
                c.tap(gs)
    return E()

def rocket_launcher_on_cast():
    """To support '{2}: Activate only if card it's been in play the entire turn...'"""
    class E(Effect):
        event = 'cast'

        def resolve(self, gs: GameState, s: GameCard, t: Optional[GameCard] = None):
            s.has_summoning_sickness = True
    return E()

def sacrifice_on_cast():
    """Sac a creature: Add an amount of {B} equal to the sacrificed creature's mana value"""
    class E(Effect):
        event = 'cast'

        def resolve(self, gs: GameState, s: GameCard, t: GameCard = None):
            if not t:
                raise ValueError(f"{s.props.name} needs a target to ... sacrifice")
            gs.action_stack.push(SacCreatureAndAddMana(s.orig_owner_id, gs, s, t, 'B', t.props.casting_weight), gs, False)
    return E()

def shapeshifter_on_cast():
    """As this creature enters, choose a number (n) between 0 and 7. Power = n, Toughness = 7-n ..."""
    class E(Effect):
        event = 'cast'

        def resolve(self, gs: GameState, source: GameCard, target: GameCard = None):
            gs.action_stack.push(ShapeshifterChoice(source.orig_owner_id, gs, source), gs, False)
    return E()

def shatter_on_cast():
    """Destroy target artifact"""
    class E(Effect):
        event = 'cast'

        def resolve(self, gs: GameState, _: GameCard, t: Optional[GameCard] = None):
            gs.send_to_graveyard_from_play(t)
    return E()

def sinkhole_and_stone_rain_on_cast():
    """Destroy target land"""

    class E(Effect):
        event = 'cast'

        def resolve(self, gs: GameState, s: GameCard, target: Optional[GameCard] = None):
            if not target:
                raise ValueError(f"{s.props.name} needs a target")
            gs.send_to_graveyard_from_play(target)
    return E()

def storm_seeker_on_cast():
    """Storm Seeker deals damage to target player equal to the number of cards in that player's hand"""

    class E(Effect):
        event = 'cast'

        def resolve(self, gs: GameState, source: GameCard, t: Optional[GameCard] = None):
            opp_idx = flip(source.orig_owner_id)
            gs.apply_damage(source, len(gs.hands[opp_idx].cards), opp_idx)
    return E()

def stream_of_life_on_cast():
    class E(Effect):
        event = 'cast'

        def resolve(self, gs: GameState, source: GameCard, target: int = None):
            x = getattr(source, 'variable_x', 0)  # read X chosen when casting
            gs.increment_life(target, x)
    return E()

def subdue_on_cast():
    """Prevent all combat damage that would be dealt by target creature this turn.
    That creature gets +0/+X until end of turn, where X is its mana value."""
    class E(Effect):
        event = 'cast'

        def resolve(self, gs: GameState, s: GameCard, t: Optional[GameCard] = None):
            gs.damage_preventions.append(PreventNextDamage(s, None, source_card=t, combat_only=True))
            t.modifiers.temps.append(PTModifier(s, 0, t.props.casting_weight))
    return E()


def sunken_city_on_cast():
    class E(Effect):
        event = 'cast'

        def resolve(self, gs, source: GameCard, target: Optional[GameCard] = None):
            # TODO: Review this new approach where global effects don't directly influence GameCards
            gs.global_effects.append((source, SunkenCityEffect(source.orig_owner_id), False))
    return E()

def swords_to_plowshares_on_cast():
    class E(Effect):
        event = 'cast'
        
        def resolve(self, gs, source: GameCard, target: Optional[GameCard] = None):
            if target:
                gs.send_to_exile(target)  # which is correct?  exile_from_play() or exile()
                gs.increment_life(target.orig_owner_id, target.power)
    return E()

def syphon_soul_on_cast():
    """Syphon Soul deals 2 damage to each other player. You gain life equal to the damage dealt this way."""
    class E(Effect):
        event = 'cast'

        def resolve(self, gs: GameState, source: GameCard, _: Optional[GameCard] = None):
            gs.apply_damage(source, 2, flip(source.orig_owner_id))
            gs.increment_life(source.orig_owner_id, 2)
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

def twiddle_on_cast():
    class E(Effect):
        event = 'cast'
        
        def resolve(self, gs, source: GameCard, target: Optional[GameCard] = None):
            if target:
                # toggle tapped state
                target.untap(gs) if target.is_tapped else target.tap(gs)
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

def unholy_strength_on_cast():
    class E(Effect):
        event = 'cast'

        def resolve(self, gs, source: GameCard, target: Optional[GameCard] = None):
            if target:
                target.modifiers.auras.append(PTModifier(source, 2, 1))
    return E()

def unstable_mutation_on_cast():
    class E(Effect):
        event = 'cast'

        def resolve(self, gs, source: GameCard, target: Optional[GameCard] = None):
            if target:
                target.modifiers.auras.append(PTModifier(source, 3, 3))
    return E()

def unsummon_on_cast():
    class E(Effect):
        event = 'cast'
        
        def resolve(self, gs, source: GameCard, target: Optional[GameCard] = None):
            if target:
                board = gs.boards[target.orig_owner_id]
                board.remove_from_board(target)
                gs.return_to_hand(target)
    return E()

def wheel_of_fortune_on_cast():
    """Each player discards their hand, then draws seven cards"""
    class E(Effect):
        event = 'cast'

        def resolve(self, gs: GameState, source: GameCard, target: Optional[GameCard] = None):
            for i in (0, 1):
                [DiscardCard(i, gs, card).play() for card in gs.hands[i].cards]
                gs.draw(gs.hands[i], gs.decks[i].cards, 7)
    return E()

def weakness_on_cast():
    class E(Effect):
        event = 'cast'

        def resolve(self, gs, source: GameCard, target: Optional[GameCard] = None):
            if target:
                target.modifiers.auras.append(PTModifier(source, -2, -1))
    return E()

def web_on_cast():
    class E(Effect):
        event = 'cast'

        def resolve(self, gs, source: GameCard, target: Optional[GameCard] = None):
            if target:
                target.modifiers.auras.append(PTModifier(source, 0, 2))
                target.modifiers.auras.append(KWAModifier(source, 'add', 'Reach'))
    return E()

def wrath_of_god_on_cast():
    class E(Effect):
        event = 'cast'
        
        def resolve(self, gs, source: GameCard, target: Optional[GameCard] = None):
            for c in CardFilter(gs).in_play().creatures().result():
                gs.send_to_exile(c)
    return E()
