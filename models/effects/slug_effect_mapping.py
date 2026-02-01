from __future__ import annotations
from typing import Callable, TYPE_CHECKING

from models.choice_actions.choice_actions_all import UntapWithManaChoice
from models.effects.damage_preventions import ArgothianPixiesPrevention, ArgothianTreefolkPrevention, \
    ArtifactWardPrevention, EnchantedBeingPrevention, MarblePriestPrevention, ScarecrowPrevention
from models.effects.damage_replacements import MartyrsOfKorlisDamageReplacement
from phase_fsm import Phase

if TYPE_CHECKING:
    from models.effects.base import Effect, EffSpec, ActivatedAbility, Activated, Static, Triggered
    from game_state import GameState
    from models.game_card import GameCard

from constants import Target, COLOR_LETTERS
from cost import SacSelfCost

from models.counter_tokens import CARRION, CORPSE, PLUS_ONE, MINUS_ONE, PIN, PLUS_ONE_ZERO, SLEEP, MINUS_ZERO_TWO
from models.effects.queries import KirdApePT, Crusade, AmrouKithkin, ArgothianPixiesCanBeBlocked, \
    ArtifactWardCanBeBlocked, BogRats, ElderSpawnCanBeBlocked, ElvenRidersCanBeBlocked, EvilEyeOfOrmsByGoreCanBeBlocked, \
    Seeker, AngelicVoices, BadMoon, SunkenCity, Castle
from models.effects.counters import (CityOfShadowsAA1, CityOfShadowsAA2, XZeroOneCountersByManaValue,
                                     RemovePlusOneZeroFromCombatant, AddCountersIfAnyCreatureDied,
                                     AddCounterPerCreatureDeath, Fasting, AddCountersYourTurnOnly,
                                     AddCountersOnHostTurn, RemoveCountersOnHostTurn, CocoonCast, RockHydraCast,
                                     AddCounter)
from models.effects.damage import DealDamage, DealDamageToTargetAndYou, \
    DealDamageOnTargetTurn, \
    ElderSpawnUpkeep, CurseArtifactUpkeep, Karma, DealDamageOnSourceTurn, LordOfThePitUpkeep, PowerSurge, StormWorld, \
    Earthquake, EternalFlame, EyeForAnEye, PreventNextDamageToCardEffect, DealDamageToAllCreaturesAndPlayers, \
    JovialEvil, Typhoon, StormSeeker, ErgRaiders, GaseousForm, PreventAllCombatDamageThisTurn, \
    LivingArtifactOnDamage, FungusaurOnDamage
from models.effects.destroy_sac_regenerate import PayManaOrSac, DestroyAll, \
    EaterOfTheDeadAA, AcidRain, ExileAllCreatures, Destroy, VoodooDollEndStep, PestilenceEndStep, \
    ErosionUpkeep, ForceOfNatureUpkeep, ManaVortexUpkeep, SeasonOfTheWitchUpkeep, SeasonOfTheWitchEndStep, SerendibDjinnNoLands
from models.effects.draw_discard import Braingeyser, CursedRackEffect, DrawCards, WheelOfFortune
from models.effects.keywords import ErhnamDjinn, KWAModEffect, EvilEyeOfOrmsByGoreCast, KoboldOverlordCast, \
    AkronLegionnaireCast
from models.effects.life import AddPoisonCounter, ElHajjaj, IvoryTower, SpiritualSanctuary, StreamOfLife, SpiritLink, \
    GainLife
from models.effects.mana import AddMana, DrainPower, EnergyTap
from models.effects.piles import BoardToHand, \
    GraveyardToHand, HandToBoard, GraveRobbersAA, GraveyardToExileInItsEntirety, GraveyardToBoard
from models.effects.pumps import DragonWhelpEndStep, BloodLust, PumpEffect, GreatDefender, HowlFromBeyond, \
    KoboldTaskmaster
from models.effects.special import CocoonUpkeep, SerendibDjinn, Shapeshifter, ActiveVolcano, \
    AnimateDead, Crumble, DivineOffering, Earthbind, Feint, FlashFlood, ForestCast, GlyphOfDestruction, GoblinKing, \
    KoboldDrillSergeant, LordOfAtlantis, MartyrsCry, ReverseDamage, RocketLauncherCast, SacrificeOnCast, Subdue, \
    SwordsToPlowshares, SyphonSoul, Web, BookOfRass, ElectricEel, ElvesOfTheDeepShadow
from models.effects.tap_untap import TapCardEffect, OptionalUntap, GiantTortoiseTap, StaysTapped, ManaShort, \
    HostStaysTapped, Riptide, Twiddle, VenarianGoldHostStaysTapped, CocoonHostStaysTapped, Reset, ForestTap, MountainTap
from models.events.events_all import EndStepEvent, CastResolvedEvent, CombatEndEvent, TapCardEvent, UpkeepEvent, \
    UntapPhaseEvent, UntapCardEvent, DamageResolvedEvent, StateBasedEvent
from utils import flip


T_FUNCS: [str, Callable[[GameState, GameCard], list[Target]]] = {
    # --- COMMON TARGET FUNCS ---
    'active_volcano_targets': lambda gs: gs.card_filter.in_play().blue().permanents().result() +
                                 gs.card_filter.in_play().by_slug('island').result(),
    'all_creatures_and_players': lambda gs, source: gs.card_filter.in_play().creatures().result() + [0, 1],
    'all_players': lambda gs, s: [0, 1],
    'artifact_creatures_in_play': lambda gs, source: gs.card_filter.in_play().artifacts().creatures().result(),
    'artifacts_and_enchantments_in_play': lambda gs: gs.card_filter.in_play().by_type(['Artifact', 'Enchantment']).result(),
    'artifacts_creatures_lands_in_play': lambda gs, s: gs.card_filter.in_play().by_type(['Artifact', 'Creature', 'Land']).result(),
    'artifacts_in_play': lambda gs, source: gs.card_filter.in_play().artifacts().result(),
    'artifacts_in_graveyards': lambda gs, s: gs.card_filter.in_graveyards().artifacts().result(),
    'artifacts_in_your_graveyard': lambda gs, s: gs.card_filter.in_player_graveyard(s.orig_owner_id).artifacts().result(),
    'attackers': lambda gs, s: gs.card_filter.attackers().result(),
    'auras_on_lands': lambda gs, s: [a for c in gs.card_filter.in_play().lands().result()
                                     for a in c.modifiers.auras if isinstance(a, GameCard)],
    'auras_on_owners_creatures': lambda gs, s: [a for c in gs.card_filter.on_player_board(s).creatures().result()
                                                for a in c.modifiers.auras if isinstance(a, GameCard)],
    'black_in_play': lambda gs, source: gs.card_filter.in_play().black().result(),
    'black_and_red_in_play': lambda gs, source: [gs.card_filter.in_play().black().result() +
                                                 gs.card_filter.in_play().red().result()],
    'black_creatures_in_play': lambda gs, s: gs.card_filter.in_play().creatures().black().result(),
    'blue_creatures_in_play': lambda gs, s: gs.card_filter.in_play().creatures().blue().result(),
    'blue_in_play': lambda gs, source: gs.card_filter.in_play().blue().result(),
    'card_owner': lambda gs, s: s.orig_owner_id,
    'cards_in_play': lambda gs, s: gs.card_filter.in_play().result(),
    'cards_in_your_graveyard': lambda gs, s: gs.card_filter.in_player_graveyard(s.orig_owner_id).result(),
    'creatures_in_all_graveyards': lambda gs, s: gs.card_filter.in_graveyards().creatures().result(),
    'creatures_in_play': lambda gs, source: gs.card_filter.in_play().creatures().result(),
    'creatures_in_play_w_forestwalk': lambda gs, s: gs.card_filter.in_play().has('Forestwalk').result(),
    'creatures_in_play_wo_forestwalk': lambda gs, s: gs.card_filter.in_play().has('Forestwalk', False).result(),
    'creatures_in_your_graveyard': lambda gs, s: gs.card_filter.in_player_graveyard(s.orig_owner_id).creatures().result(),
    'creatures_and_enchantments_in_play': lambda gs, s: gs.card_filter.in_play().by_type(['Creature',
                                                                                          'Enchantment']).result(),
    'creatures_and_players': lambda gs, s: gs.card_filter.in_play().creatures().result() + all_player_indices(gs),
    'djinns_and_efreets': lambda gs, s: gs.card_filter.in_play().by_sub_type(['Djinn', 'Efreet']).result(),
    'enchants_in_play': lambda gs, s: gs.card_filter.in_play.enchantments().result(),
    'enchants_in_your_graveyard': lambda gs, s: gs.card_filter.in_player_graveyard(s.orig_owner_id).enchantments().result(),
    'flash_flood': lambda gs, s: gs.card_filter.in_play().red().permanents().result() +
                                 gs.card_filter.in_play().by_slug('mountain').result(),
    'fliers_in_play': lambda gs, _: gs.card_filter.in_play().creatures().has('Flying').result(),
    'forests_in_your_hand': lambda gs, s: gs.card_filter.in_player_hand(s.orig_owner_id).by_slug('forest').result(),
    'goblin_permanents_in_your_hand': lambda gs, s: gs.card_filter.in_player_hand(s.orig_owner_id).by_sub_type('Goblin').permanents().result(),
    'green_in_play': lambda gs, source: gs.card_filter.in_play().green().result(),
    'host': lambda gs, s: s.attached_to,
    'host_owner': lambda gs, s: s.attached.to.orig_owner_id,
    'in_turn_player': lambda gs, _: gs.player_turn_idx,
    'islandwalkers': lambda gs, s: gs.card_filter.in_play().has('Islandwalk').result(),
    'lands_in_play': lambda gs, source: gs.card_filter.in_play().lands().result(),
    'one_one_creatures_in_play': lambda gs, s: [c for c in gs.card_filter.in_play().creatures().result()
                                                if c.power == 1 and c.toughness == 1],
    'opp_creatures_in_play': lambda gs, s: gs.card_filter.on_player_board(flip(s.orig_owner_id)).creatures().result(),
    'opp_creatures_who_could_have_but_didnt_attack': lambda gs, s: opp_creatures_who_could_have_attacked_but_didnt(gs, s),
    'opp_non_wall_creatures_in_play': lambda gs, s: gs.card_filter.on_player_board(flip(s.orig_owner_id)).non_wall_creatures().result(),
    'opponent': lambda gs, s: flip(s.orig_owner_id),
    'permanents_in_play': lambda gs: gs.card_filter.in_play().permanents().result(),
    'red_in_play': lambda gs, source: gs.card_filter.in_play().red().result(),
    'self': lambda gs, s: s,
    'stone_giant': lambda gs, s: [c for c in gs.card_filter.on_player_board(s).creatures().result()
                                  if c.toughness < s.power],
    'tapped_creatures': lambda gs, source: gs.card_filter.in_play().creatures().tapped().result(),
    'tapped_lands': lambda gs, s: gs.card_filter.in_play().lands().tapped().result(),
    'unblocked_attackers': lambda gs, source: gs.card_filter.unblocked_attackers().result(),
    'untapped_artifacts_in_play': lambda gs, source: gs.card_filter.in_play().artifacts().untapped().result(),
    'untapped_creatures_without_flying': lambda gs, s: gs.card_filter.in_play().creatures().untapped().has('Flying', False).result(),
    'walls_in_play': lambda gs, s: gs.card_filter.in_play().walls().result(),
    'white_creatures_in_play': lambda gs, source: gs.card_filter.in_play().white().creatures().result(),
    'white_in_play': lambda gs, source: gs.card_filter.in_play().white().result(),
    'your_creatures_in_play': lambda gs, s: gs.card_filter.on_player_board(s.orig_owner_id).creatures().result(),
    'your_lands_in_play': lambda gs: gs.card_filter.on_player_board(gs.player_turn_idx).lands().result(),
    'your_untapped_creatures': lambda gs, s: gs.card_filter.on_player_board(gs.player_turn_idx).creatures().untapped().result(),
    'your_walls_in_play': lambda gs, s: gs.card_filter.on_player_board(gs.player_turn_idx).in_play().walls().result(),
}


def opp_creatures_who_could_have_attacked_but_didnt(gs: GameState, source: GameCard) -> list[GameCard | None]:
    """Returns creatures who: have 'Attack' in kwa, no summoning sickness, didn't go into combat"""
    attackers = gs.card_filter.attackers().result()
    return [c for c in gs.card_filter.on_player_board(flip(source.orig_owner_id)).creatures().result()
            if c not in attackers and not c.has_summoning_sickness and 'Attack' in c.keyword_abilities]


# --- NON-CARD-SPECIFIC PRE-CONSTRUCTED ACTIVATED ABILITY SPEC ---
def untap_at_owners_upkeep(cost_mana: str):
    return AAS(cost_mana, False, None, lambda gs, s, _: s.untap(gs), allowed_phases=[Phase.UPKEEP],
               allowed_player_turn=ActivatedAbility.AllowedPlayerTurn.CASTER, text='Untap')

def untap_host_at_owners_upkeep(cost_mana: str):
    # WARNING: allowed_player_turn = OPPONENT assumes Paralyze has been played on an opp creature !!!
    return AAS(cost_mana, False, None, lambda gs, s, _: s.attached_to.untap(gs), allowed_phases=[Phase.UPKEEP],
               allowed_player_turn=ActivatedAbility.AllowedPlayerTurn.OPPONENT, text='Untap')

# --- NON-CARD-SPECIFIC COMMON/COMPLEX EFFECT FUNCS ---
def add_mana_func(color: str, amt: int = 1):
    if color not in COLOR_LETTERS_W_COLORLESS:
        raise ValueError(f"Color must be {COLOR_LETTERS_W_COLORLESS}")

    def _effect(gs, s, t: GameCard):
        gs.mana_pools[s.orig_owner_id].add_floating(color, amt)
    return _effect

def add_remove_kwa_temp(add_or_remove: str, kwa: str):
    if add_or_remove not in {'add', 'remove'}:
        raise ValueError("add_or_remove parameter must be either 'add' or 'remove'")

    def _effect(gs, src, t: Target):
        t.modifiers.temps.append(KWATemp(add_or_remove, kwa))
    return _effect

def deal_damage_func(amt: int = None):
    def _effect(gs, source, target):
        gs.apply_damage(source, amt, target)
    return _effect

def destroy_all_non_land_perms(gs: GameState, s: GameCard, t: Target):
    for c in gs.card_filter.in_play().by_type(['Artifact', 'Creature', 'Enchantment']).result():
        gs.send_to_graveyard_from_play(c)

def dual_land_activated_ability_specs(colors: str) -> list[AAS]:
    return [AAS('', True, T_FUNCS['card_owner'], add_mana_func(color), text=f'Add {{{color}}}') for color in colors]

def prevent_next_damage_func(amt: int = None):
    def _effect(gs, src, _):
        gs.damage_preventions.append(PreventNextDamage(src, amt))
    return _effect

# --- CARD SPECIFIC COMPLEX FUNCS ---


def exchange_life_totals(gs: GameState, s: GameCard, _: Target):
    your_life = gs.life[s.orig_owner_id]
    opp_life = gs.life[flip(s.orig_owner_id)]
    gs.life[s.orig_owner_id], gs.life[flip(s.orig_owner_id)] = opp_life, your_life

def forcefield_func(gs: GameState, s: GameCard, t: Target):
    gs.damage_preventions.append(PreventNextDamage(s, source_card=t, target_player=s.orig_owner_id, combat_only=True))
    gs.apply_damage(t, 1, s.orig_owner_id, is_combat=True)

def greed_func(gs: GameState, source: GameCard, _: Target):
    gs.decrement_life(source.orig_owner_id, 2, source)
    gs.draw(gs.hands[source.orig_owner_id], gs.decks[source.orig_owner_id].cards, 1)

def hammerheim_func(gs: GameState, source: GameCard, t: Target):
    for land in ('Island', 'Forest', 'Mountain', 'Swamps', 'Plains'):
        t.modifiers.temps.append(KWATemp('remove', f'{land}walk'))

def kry_shield_func(gs: GameState, s: GameCard, t: Target):
    """Prevent all damage that would be dealt this turn by target creature you control.
    That creature gets +0/+X until end of turn, where X is its mana value"""
    gs.damage_preventions.append(PreventNextDamage(s, source_card=t))
    t.modifiers.temps.append(PTTemp(0, t.props.casting_weight))

def jade_monolith_func(gs: GameState, s: GameCard, t: Optional[GameCard] = None):
    """target = the GameCard being protected"""

    def redirect_damage(prevented: int):
        gs.apply_damage(t, prevented, t.orig_owner_id)

    gs.damage_preventions.append(PreventNextDamage(s, None, target_card=t, on_prevent=redirect_damage))

def maze_of_ith_func(gs: GameState, s: GameCard, t: Target):
    the_combat = [com for com in gs.combats if com.attacker == t]
    if not the_combat:
        return
    gs.damage_preventions.append(PreventNextDamage(s, None, target_card=t, combat_only=True))
    for b in the_combat[0].blockers:
        gs.damage_preventions.append(PreventNextDamage(s, None, target_card=b, combat_only=True))
    t.untap(gs)

def orcish_artillery_func(gs: GameState, s: GameCard, t: Target):
    """{T}: This creature deals 2 damage to any target and 3 damage to you"""
    gs.apply_damage(s, 2, t)
    gs.apply_damage(s, 3, s.orig_owner_id)

def psionic_entity_func(gs: "GameState", source: "GameCard", t: Target):
    # {T}: This creature deals 2 damage to any target and 3 damage to itself
    gs.apply_damage(source, 2, t)
    gs.apply_damage(source, 3, source)

def rakalite_func(gs: GameState, s: GameCard, _: Target):
    prevent_next_damage_func(1)
    gs.return_to_hand(s)

def rocket_launcher_func(gs: GameState, s: GameCard, t: Target):
    """{2}: Deal 1 damage to any target. Destroy Rocket Launcher at next end step."""
    gs.apply_damage(s, 1, t)
    gs.end_step_funcs.append(lambda gs, s: gs.send_to_graveyard_from_play(s))

def shimian_nightstalker_func(gs: GameState, s: GameCard, t: Target):
    """{B}, {T}: All damage that would be dealt to you this turn by target attacking creature is dealt
    to this creature instead.  target = the GameCard doing the damage"""
    def redirect_damage(prevented: int):
        gs.apply_damage(t, prevented, t.orig_owner_id)

    gs.damage_preventions.append(PreventNextDamage(s, None, target_player=s.orig_owner_id,
                                                   source_card=t, on_prevent=redirect_damage))

def stone_giant_func(gs: GameState, s: GameCard, t: Target):
    """{T}: Target creature you control with toughness less than this creature's power gains flying until end of turn.
    Destroy that creature at the beginning of the next end step."""
    add_remove_kwa_temp('add', 'Flying')
    gs.end_step_funcs.append(lambda gs, s: gs.send_to_graveyard_from_play(t))


MANA_BATTERY_ADD_CHARGE_AAS = AAS('2', True, lambda _, s: s, lambda gs, s, t: s.counters.add_counter(CHARGE))

ACTIVATED_ABILITY: dict[str, list[AAS]] = {
    'badlands': dual_land_activated_ability_specs('BR'),
    'bayou': dual_land_activated_ability_specs('BG'),
    'black-mana-battery': [MANA_BATTERY_ADD_CHARGE_AAS],  # add discharge logic
    'blue-mana-battery': [MANA_BATTERY_ADD_CHARGE_AAS],  # add discharge logic
    'brass-man': [untap_at_owners_upkeep('1')],
    'circle-of-protection-artifacts':
        [AAS('1', False, T_FUNCS['artifacts_in_play'],  # would this include instants/sorceries?
             lambda gs, src, t: gs.damage_preventions.append(PreventNextDamage(src, source_card=t, target_player=src.orig_owner_id)))],
    'circle-of-protection-black':
        [AAS('1', False, T_FUNCS['black_in_play'],  # would this include instants/sorceries?
             lambda gs, src, t: gs.damage_preventions.append(PreventNextDamage(src, source_card=t, target_player=src.orig_owner_id)))],
    'circle-of-protection-blue':
        [AAS('1', False, T_FUNCS['blue_in_play'],  # would this include instants/sorceries?
             lambda gs, src, t: gs.damage_preventions.append(PreventNextDamage(src, source_card=t, target_player=src.orig_owner_id)))],
    'circle-of-protection-green':
        [AAS('1', False, T_FUNCS['green_in_play'],  # would this include instants/sorceries?
             lambda gs, src, t: gs.damage_preventions.append(PreventNextDamage(src, source_card=t, target_player=src.orig_owner_id)))],
    'circle-of-protection-red':
        [AAS('1', False, T_FUNCS['red_in_play'],  # would this include instants/sorceries?
             lambda gs, src, t: gs.damage_preventions.append(PreventNextDamage(src, source_card=t, target_player=src.orig_owner_id)))],
    'circle-of-protection-white':
        [AAS('1', False, T_FUNCS['white_in_play'],  # would this include instants/sorceries?
             lambda gs, src, t: gs.damage_preventions.append(PreventNextDamage(src, source_card=t, target_player=src.orig_owner_id)))],



    # 'colossus-of-sardia': [untap_at_owners_upkeep('9')],
    'colossus-of-sardia': [Activated('9', lambda gs, s, _: UntapWithManaChoice(s.orig_owner_id, gs, s, '9'),
                                     allowed_phases=[Phase.UPKEEP],
                                     allowed_player_turn=EffSpec.AllowedPlayerTurn.CASTER, text='Untap')],

    'conservator':
        [AAS('3', True, None, lambda gs, src, _: gs.damage_preventions.append(
                        PreventNextDamage(src, remaining=2, target_player=src.orig_owner_id)))],
    'farmstead':
        [AAS('WW', True, lambda gs, _: gs.player_turn_idx, lambda gs, _, t: gs.increment_life(gs.player_turn_idx, 1))],
    'forcefield':
        # Next time an unblocked creature of your choice would deal combat damage to you this turn, reduce damage to 1
        [AAS('1', False, T_FUNCS['unblocked_attackers'], forcefield_func)],
    'gaeas-touch': [AAS('', False, lambda gs, s: s.orig_owner_id, add_mana_func('G', 2),
                        extra_costs=[ExileSelfCost()])],  # gaeas-touch has one more Activated Ability left to code
    'greater-realm-of-preservation':
        [AAS('1W', False, T_FUNCS['black_and_red_in_play'],  # would this include instants/sorceries?
             lambda gs, src, t: gs.damage_preventions.append(
                            PreventNextDamage(src, source_card=t, target_player=src.orig_owner_id)))],
    'greed': [AAS('B', False, T_FUNCS['card_owner'], lambda gs, s, t: greed_func(gs, s, t))],
    'green-mana-battery': [MANA_BATTERY_ADD_CHARGE_AAS],  # add discharge logic
    'hammerheim':
        # {T}: Add {R}. {T}: Target creature loses all landwalk abilities until end of turn.
        [AAS('', True, lambda _, s: s.orig_owner_id, add_mana_func('R')),
         AAS('', True, T_FUNCS['creatures_in_play'], lambda gs, s, t: hammerheim_func(gs, s, t))],
    'holy-armor': [AAS('W', False, None, pump_func(0, 1))],
    'horn-of-deafening':
        [AAS('2', True, T_FUNCS['creatures_in_play'],
             lambda gs, s, t: gs.damage_preventions.append(PreventNextDamage(s, source_card=t,
                                                                                        combat_only=True)))],
    'hyperion-blacksmith':
        # {T}: You may tap or untap target artifact an opponent controls
        [AAS('', True, lambda gs, s: gs.card_filter.on_player_board(flip(s.orig_owner_id)).artifacts().result(),
             lambda gs, source, t: t.untap(gs) if t.is_tapped else t.tap(gs))],
    'icy-manipulator':
    # {1}, {T}: Tap target artifact, creature, or land
        [AAS('1', True, lambda gs, source: gs.card_filter.in_play().by_type(['Artifact', 'Creature', 'Land']).tapped(False).result(),
             lambda gs, source, t: t.tap(gs))],
    'instill-energy':
        # {0}: Untap enchanted creature. Activate only during your turn and only once each turn
        [AAS('', False, None, lambda gs, source, t: t.untap(gs),
             allowed_player_turn=ActivatedAbility.AllowedPlayerTurn.CASTER, max_activations_per_turn=1)],
    'island-fish-jasconius': [untap_at_owners_upkeep('UUU')],
    'jade-monolith': [AAS('1', False, T_FUNCS['all_creatures_and_players'], jade_monolith_func)],
    'jandors-saddlebags': [AAS('3', True, T_FUNCS['tapped_creatures'], lambda gs, source, t: t.untap(gs))],
    'jayemdae-tome':
        [AAS('4', True, T_FUNCS['card_owner'],
             lambda gs, s, t: gs.draw(gs.hands[s.orig_owner_id], gs.decks[s.orig_owner_id].cards, 1))],
    'killer-bees': [AAS('G', False, lambda gs, source: source, pump_func(1, 1))],
    'king-suleiman':
        [Activated('T', Destroy(), T_FUNCS['djinns_and_efreets'])],
    'kry-shield': [AAS('2', True, T_FUNCS['your_creatures_in_play'], kry_shield_func)],
    'ley-druid':
        [AAS('', True, T_FUNCS['tapped_lands'], lambda gs, source, t: t.untap(gs))],
    'llanowar-elves': [AAS('', True, T_FUNCS['card_owner'], add_mana_func('G'))],
    'mana-vault': [untap_at_owners_upkeep('4'), AAS('', True, T_FUNCS['card_owner'], add_mana_func('C', 3))],
    'maze-of-ith': [AAS('', True, lambda gs, s: gs.card_filter.attackers().result(), maze_of_ith_func)],
    'merfolk-assassin':
        [Activated('T', Destroy(), T_FUNCS['islandwalkers'])],
    'miracle-worker': [Activated('T', Destroy(), T_FUNCS['auras_on_owners_creatures'])],
    'mirror-universe': [AAS('', True, None, exchange_life_totals, allowed_phases=[Phase.UPKEEP],
                            allowed_player_turn=ActivatedAbility.AllowedPlayerTurn.CASTER, extra_costs=[SacSelfCost()])],
    'mox-emerald': [AAS('', True, T_FUNCS['card_owner'], add_mana_func('G'))],
    'mox-jet': [AAS('', True, T_FUNCS['card_owner'], add_mana_func('B'))],
    'mox-pearl': [AAS('', True, T_FUNCS['card_owner'], add_mana_func('W'))],
    'mox-ruby': [AAS('', True, T_FUNCS['card_owner'], add_mana_func('R'))],
    'mox-sapphire': [AAS('', True, T_FUNCS['card_owner'], add_mana_func('U'))],
    'nettling-imp': [AAS('', True, T_FUNCS['opp_creatures_who_could_have_but_didnt_attack'],
                         lambda gs, s, t: gs.end_step_funcs.append(nettling_imp_on_end_step),
                         allowed_player_turn=ActivatedAbility.AllowedPlayerTurn.OPPONENT,
                         allowed_phases=[phase for phase in Phase if phase < Phase.DECLARE_ATTACKERS])],
    'nevinyrrals-disk': [AAS('1', True, None, lambda gs, s, t: destroy_all_non_land_perms(gs, s, t))],
    'northern-paladin': [Activated('WW', Destroy(), T_FUNCS['creatures_and_enchantments_in_play'])],
    'oasis': [AAS('', True, T_FUNCS['creatures_in_play'], prevent_next_damage_func(1))],
    'orcish-artillery': [AAS('', True, T_FUNCS['all_creatures_and_players'], orcish_artillery_func)],
    'paralyze': [untap_host_at_owners_upkeep('4')],
    'pendelhaven':
        [AAS('', True, lambda gs, s: s.orig_owner_id, add_mana_func('G')),
         AAS('', True, T_FUNCS['one_one_creatures_in_play'], pump_func(1, 2))],
    'pirate-ship': [AAS('', True, T_FUNCS['all_creatures_and_players'], deal_damage_func(1))],
    'pixie-queen':
        [AAS('GGG', True, T_FUNCS['creatures_in_play'], add_remove_kwa_temp('add', 'Flying'))],
    'plateau': dual_land_activated_ability_specs('RW'),
    'pradesh-gypsies': [AAS('1G', True, T_FUNCS['creatures_in_play'], pump_func(-2, 0))],
    'prodigal-sorcerer': [AAS('', True, T_FUNCS['all_creatures_and_players'], deal_damage_func(1))],
    'psionic-entity':
        [AAS('', True, T_FUNCS['all_creatures_and_players'], lambda gs, s, t: psionic_entity_func(gs, s, t))],
    'radjan-spirit':
        [AAS('', True, T_FUNCS['creatures_in_play'], add_remove_kwa_temp('remove', 'Flying'))],
    'rakalite': [AAS('2', False, T_FUNCS['all_creatures_and_players'], rakalite_func)],
    'red-mana-battery': [MANA_BATTERY_ADD_CHARGE_AAS],  # add discharge logic
    'relic-barrier': [AAS('', True, T_FUNCS['untapped_artifacts_in_play'], lambda gs, s, t: t.tap(gs))],
    'rod-of-ruin': [AAS('3', True, T_FUNCS['all_creatures_and_players'], deal_damage_func(1))],
    'rocket-launcher':
        [AAS('2', False, T_FUNCS['all_creatures_and_players'], lambda gs, s, t: rocket_launcher_func(gs, s, t))],
    'royal-assassin': [Activated('T', Destroy(), T_FUNCS['tapped_creatures'])],
    'samite-healer': [AAS('', True, T_FUNCS['all_creatures_and_players'], prevent_next_damage_func(1))],
    'savannah': dual_land_activated_ability_specs('GW'),

    'savaen-elves': [Activated('GGT', Destroy(), T_FUNCS['auras_on_lands'])],
    'scarecrow': [AAS('6', True, None,
                      lambda gs, s, t: gs.global_effects.append((s, scarecrow_func)))],
    'scarwood-hag': [AAS('GGGG', True, T_FUNCS['creatures_in_play_wo_forestwalk'],
                         add_remove_kwa_temp('add', 'Forestwalk')),
                     AAS('GGGG', True, T_FUNCS['creatures_in_play_w_forestwalk'],
                         add_remove_kwa_temp('remove', 'Forestwalk'))],
    'scavenger-folk': [Activated('GT', Destroy(), T_FUNCS['artifacts_in_play'], extra_costs=[SacSelfCost()])],
    'scrubland': dual_land_activated_ability_specs('BW'),
    'shimian-night-stalker': [AAS('B', True, T_FUNCS['attackers'], shimian_nightstalker_func)],
    'shivan-dragon': [AAS('R', False, None, pump_func(1, 0))],
    'sisters-of-the-flame': [AAS('', True, lambda gs, s: s.orig_owner_id, add_mana_func('R'))],
    'sol-ring': [AAS('', True, lambda gs, s: s.orig_owner_id, add_mana_func('C', 2))],
    'sorceress-queen': [AAS('', True, lambda gs, s: [c for c in T_FUNCS['creatures_in_play'] if c != s],
                            lambda gs, s, t: t.modifiers.temps.append(PTTemp(-t.power, t.toughness - 2)))],
    'spinal-villain': [Activated('T', Destroy(), T_FUNCS['blue_creatures_in_play'])],
    'staff-of-zegon': [AAS('3', True, T_FUNCS['creatures_in_play'], pump_func(-2, 0))],
    'stone-giant': [AAS('', True, T_FUNCS['stone_giant'], stone_giant_func)],
    'strip-mine': [AAS('', True, lambda gs, s: s.orig_owner_id, add_mana_func('C')),
                   Activated('T', Destroy(), T_FUNCS['lands_in_play'], extra_costs=[SacSelfCost()])],
    'taiga': dual_land_activated_ability_specs('RG'),
    'tropical-island': dual_land_activated_ability_specs('GU'),
    'tundra': dual_land_activated_ability_specs('WU'),
    'underground-sea': dual_land_activated_ability_specs('BU'),
    'volcanic-island': dual_land_activated_ability_specs('RU'),
    'wall-of-water': [AAS('U', False, None, pump_func(1, 0))],
    'white-mana-battery': [MANA_BATTERY_ADD_CHARGE_AAS],  # add discharge logic
}


def is_tapped(s: GameCard) -> bool:
    return s.is_tapped

def all_player_indices(gs):
    return list(range(gs.player_cnt))


INVOCATIONS: dict[str, list[EffSpec]] = {
    'acid-rain': [Triggered(AcidRain(), None, CastResolvedEvent)],
    'active-volcano': [Triggered(ActiveVolcano(), T_FUNCS['active_volcano_targets'], CastResolvedEvent)],
    'akron-legionnaire': [Triggered(AkronLegionnaireCast(), None, CastResolvedEvent)],
    'aladdins-ring': [Activated('T', DealDamage(4), T_FUNCS['all_creatures_and_players'])],
    'ali-baba': [Activated('RT', TapCardEffect(), T_FUNCS['walls_in_play'])],
    'amrou-kithkin': [Static(AmrouKithkin())],
    'amulet-of-kroog': [Activated('2T', prevent_next_damage_func(1), T_FUNCS['all_creatures_and_players'])],
    'ancestral-recall': [Triggered(DrawCards(3), T_FUNCS['all_players'], CastResolvedEvent)],
    'angelic-voices': [Static(AngelicVoices())],
    'animate-dead': [Triggered(AnimateDead(), T_FUNCS['creatures_in_your_graveyard'], CastResolvedEvent)],
    'animate-wall':
        [Triggered(KWAModEffect('remove', 'Defender'), T_FUNCS['walls_in_play'], CastResolvedEvent)],
    'apprentice-wizard': [Activated('UT', AddMana('C', 3), T_FUNCS['card_owner'])],
    'argivian-archaeologist': [Activated('WWT', GraveyardToHand(), T_FUNCS['artifacts_in_your_graveyard'])],
    'argivian-blacksmith': [Activated('T',  prevent_next_damage_func(2), T_FUNCS['artifact_creatures_in_play'])],
    'argothian-pixies': [Static(ArgothianPixiesCanBeBlocked(), Static(ArgothianPixiesPrevention()))],
    'argothian-treefolk': [Static(ArgothianTreefolkPrevention())],
    'armageddon':
        [Triggered(DestroyAll(lambda gs, s: gs.card_filter.in_play().by_type('Land').result()),
                   None, CastResolvedEvent)],
    'artifact-ward': [Triggered(None, T_FUNCS['artifacts_in_play'], CastResolvedEvent),
                      Static(ArtifactWardCanBeBlocked(), Static(ArtifactWardPrevention()))],
    'ashnods-battle-gear': [Triggered(OptionalUntap(), None, UntapPhaseEvent)],
    'bad-moon': [Static(BadMoon())],
    'ball_lightning': [Triggered(Destroy(), T_FUNCS['self'], EndStepEvent)],
    'basalt-monolith': [Triggered(StaysTapped(), T_FUNCS['self'], UntapPhaseEvent)],
    'birds-of-paradise': [Activated('T', AddMana(c), text=f'Add {{{c}}}') for c in COLOR_LETTERS],
    'blessing': [Activated('W', PumpEffect(1, 1, True), T_FUNCS['host'])],
    'blood-lust': [Triggered(BloodLust(), T_FUNCS['creatures_in_play'], CastResolvedEvent)],
    'bog-rats': [Static(BogRats())],
    'book-of-rass': [Activated('2', BookOfRass())],
    'boomerang': [Triggered(BoardToHand(), T_FUNCS['permanents_in_play'], CastResolvedEvent)],
    'braingeyser': [Triggered(Braingeyser(), T_FUNCS['all_players'], CastResolvedEvent)],
    'brainwash':
        # WARNING: the AA would generally be activated by the opponent normally placed on an opponent creature
        [Triggered(KWAModEffect('remove', 'Attack'), T_FUNCS['creatures_in_play'], CastResolvedEvent),
         Activated('3', KWAModEffect('add', 'Attack', True), T_FUNCS['host'])],
    'brass-man': [Triggered(StaysTapped(), T_FUNCS['self'], UntapPhaseEvent)],
    'brothers-of-fire': [Activated('T', DealDamageToTargetAndYou(1, 1), T_FUNCS['all_creatures_and_players'])],
    'burrowing':
        [Triggered(KWAModEffect('add', 'Mountainwalk'), T_FUNCS['creatures_in_play'], CastResolvedEvent)],
    'carrion-ants': [Activated('1', PumpEffect(1, 1, True), T_FUNCS['self'])],
    'castle': [Static(Castle())],
    'celestial-prism': [Activated('2T', AddMana(c), T_FUNCS['card_owner'], text=f'Add 1 {c}') for c in COLOR_LETTERS],
    'city-of-shadows':
        [Activated('T', CityOfShadowsAA1()), Activated('T', CityOfShadowsAA2())],  # TODO: needs a way to find a creature to exile in extra_costs
    'cleanse':
        [Triggered(DestroyAll(T_FUNCS['black_creatures_in_play']), None, CastResolvedEvent)],
    'clockwork-avian':
        [Triggered(RemovePlusOneZeroFromCombatant(), T_FUNCS['self'], CombatEndEvent),
         Triggered(AddCountersYourTurnOnly(PLUS_ONE_ZERO, 4), T_FUNCS['self'], CastResolvedEvent)],
    'clockwork-beast':
        [Triggered(RemovePlusOneZeroFromCombatant(), T_FUNCS['self'], CombatEndEvent),
         Triggered(AddCountersYourTurnOnly(PLUS_ONE_ZERO, 7), T_FUNCS['self'], CastResolvedEvent)],
    'coal-golem': [Activated('3', AddMana('R', 3), T_FUNCS['card_owner'], extra_costs=[SacSelfCost()])],
    'cocoon':
        [Triggered(CocoonCast(), T_FUNCS['your_creatures_in_play'], CastResolvedEvent),
         Triggered(CocoonHostStaysTapped(), None, UntapPhaseEvent),
         Triggered(CocoonUpkeep(), None, UpkeepEvent)],
    'colossus-of-sardia': [Triggered(StaysTapped(), T_FUNCS['self'], UntapPhaseEvent)],
    'conversion': [Triggered(PayManaOrSac('WW'), None, UpkeepEvent)],
    'copper-tablet': [Triggered(DealDamage(1), T_FUNCS['in_turn_player'], UpkeepEvent)],
    'cosmic-horror': [Triggered(PayManaOrSac('3BBB'), None, UpkeepEvent)],
    'crumble': [Triggered(Crumble()), T_FUNCS['artifacts_in_play'], CastResolvedEvent],
    'crusade': [Static(Crusade())],
    'curse-artifact': [Triggered(CurseArtifactUpkeep(), T_FUNCS['artifacts_in_play'], UpkeepEvent)],
    'cursed-land': [Triggered(DealDamageOnTargetTurn(1), T_FUNCS['lands_in_play'], UpkeepEvent)],
    'cursed-rack': [Triggered(CursedRackEffect(), None, EndStepEvent)],
    'dark-ritual': [Triggered(AddMana('B', 3), None, CastResolvedEvent)],
    'darkness': [Triggered(PreventAllCombatDamageThisTurn(), None, CastResolvedEvent)],
    'demonic-torment':
        [Triggered(KWAModEffect('remove', 'Attack'), T_FUNCS['creatures_in_play'], CastResolvedEvent)],
    'desert-twister': [Triggered(Destroy(), T_FUNCS['permanents_in_play'], CastResolvedEvent)],
    'disenchant':
        [Triggered(Destroy(), T_FUNCS['artifacts_and_enchantments_in_play'], CastResolvedEvent)],
    'divine-offering': [Triggered(DivineOffering(), T_FUNCS['artifacts_in_play'], CastResolvedEvent)],
    'divine-transformation':
        [Triggered(PumpEffect(3, 3), T_FUNCS['creatures_in_play'], CastResolvedEvent)],
    'dragon-engine': [Activated('2', PumpEffect(1, 0, True), T_FUNCS['self'])],
    'dragon-whelp': [Triggered(DragonWhelpEndStep(), None, EndStepEvent)],
    'drain-power': [Triggered(DrainPower(), T_FUNCS['opponent'], CastResolvedEvent)],
    'dwarven-demolition-team': [Activated('T', Destroy(), T_FUNCS['walls_in_play'])],
    'earthbind': [Triggered(Earthbind(), T_FUNCS['creatures_in_play'], CastResolvedEvent)],
    'earthquake': [Triggered(Earthquake(), None, CastResolvedEvent)],
    'eater-of-the-dead':
        [Activated('', EaterOfTheDeadAA(), T_FUNCS['creatures_in_all_graveyards'], conditions=[is_tapped])],
    'el-hajjaj': [Triggered(ElHajjaj(), T_FUNCS['self'], DamageResolvedEvent)],
    'elder-spawn': [Triggered(ElderSpawnUpkeep(), None, UpkeepEvent), Static(ElderSpawnCanBeBlocked())],
    'electric-eel': [Triggered(DealDamage(1), T_FUNCS['self'], CastResolvedEvent), Activated('RR', ElectricEel())],
    'elven-riders': [Static(ElvenRidersCanBeBlocked())],
    'elves-of-deep-shadow': [Activated('T', ElvesOfTheDeepShadow())],
    'emerald-dragonfly': [Activated('GG', KWAModEffect('add', 'First Strike', True), T_FUNCS['self'])],
    'enchanted-being': [Static(EnchantedBeingPrevention())],
    'energy-tap': [Triggered(EnergyTap(), T_FUNCS['your_untapped_creatures'], CastResolvedEvent)],
    'erg-raiders': [Triggered(ErgRaiders(), None, EndStepEvent)],
    'erhnam-djinn': [Triggered(ErhnamDjinn(), T_FUNCS['opp_non_wall_creatures_in_play'], UpkeepEvent)],
    'erosion':
        [Triggered(None, T_FUNCS['lands_in_play'], CastResolvedEvent), Triggered(ErosionUpkeep(), None, UpkeepEvent)],
    'eternal-flame': [Triggered(EternalFlame(), None, CastResolvedEvent)],
    'eternal-warrior': [Triggered(KWAModEffect('add', 'Vigilance'), T_FUNCS, CastResolvedEvent)],
    'evil-eye-of-orms-by-gore': [Triggered(EvilEyeOfOrmsByGoreCast(), None, CastResolvedEvent),
                                 Static(EvilEyeOfOrmsByGoreCanBeBlocked())],
    'exorcist': [Activated('1W', Destroy(), T_FUNCS['black_creatures_in_play'])],
    'eye-for-an-eye': [Triggered(EyeForAnEye(), T_FUNCS['cards_in_play'], CastResolvedEvent)],
    'faint': [Triggered(Feint(), T_FUNCS['attackers'], CastResolvedEvent)],
    'fasting': [Activated(Fasting(), T_FUNCS['self'], UpkeepEvent)],
    'feedback': [Triggered(DealDamageOnTargetTurn(1), T_FUNCS['enchants_in_play'], UpkeepEvent)],
    'fire-drake': [Activated('R', PumpEffect(1, 0, True), T_FUNCS['self'], max_activations_per_turn=1)],
    'fire-sprites': [Activated('GT', AddMana('R'), T_FUNCS['card_owner'])],
    'firebreathing': [Triggered(None, T_FUNCS['creatures_in_play'], CastResolvedEvent),
                      Activated('R', PumpEffect(1, 0, True), T_FUNCS['self'])],
    'flash-flood': [Triggered(FlashFlood(), T_FUNCS['flash_flood'], CastResolvedEvent)],
    'flashfires':
        [Triggered(DestroyAll(lambda gs, s: gs.card_filter.in_play().by_slug('plains').result()),
                   None, CastResolvedEvent)],
    'flight': [Triggered(KWAModEffect('add', 'Flying'), T_FUNCS['creatures_in_play'], CastResolvedEvent)],
    'flood': [Activated('UU', TapCardEffect(), T_FUNCS['untapped_creatures_without_flying'])],
    'fishliver-oil':
        [Triggered(KWAModEffect('add', 'Islandwalk'), T_FUNCS['creatures_in_play'], CastResolvedEvent)],
    'flying-carpet': [Activated('2T', KWAModEffect('add', 'Flying', True), T_FUNCS['creatures_in_play'])],
    'fog': [Triggered(PreventAllCombatDamageThisTurn(), None, CastResolvedEvent)],
    'force-of-nature': [Triggered(ForceOfNatureUpkeep(), None, UpkeepEvent)],
    'forest': [Triggered(ForestCast(), None, CastResolvedEvent), Triggered(ForestTap(), None, TapCardEvent)],
    'forethought-amulet': [Triggered(PayManaOrSac('3'), None, UpkeepEvent)],
    'fountain-of-youth': [Activated('2T', GainLife(), T_FUNCS['card_owner'])],
    'frozen-shade': [Activated('B', PumpEffect(1, 1, True), T_FUNCS['self'])],
    'fungusaur': [Triggered(FungusaurOnDamage(), None, DamageResolvedEvent)],
    'gaeas-touch':
        [Activated('', HandToBoard(), T_FUNCS['forests_in_your_hand'],
                   allowed_player_turn=EffSpec.AllowedPlayerTurn.CASTER, max_activations_per_turn=1)],  # TODO: activated_cnt_this_turn needs to increment
    'gaseous-form': [Triggered(GaseousForm(), T_FUNCS['creatures_in_play'], CastResolvedEvent)],
    'ghosts-of-the-damned': [Activated('T', PumpEffect(-1, 0, True), T_FUNCS['creatures_in_play'])],
    'giant-growth':
        [Triggered(PumpEffect(3, 3, True), T_FUNCS['creatures_in_play'], CastResolvedEvent)],
    'giant-strength':
        [Triggered(PumpEffect(2, 2), T_FUNCS['creatures_in_play'], CastResolvedEvent)],
    'giant-tortoise':
        [Triggered(PumpEffect(0, 3), None, CastResolvedEvent),
         Triggered(GiantTortoiseTap(), None, TapCardEvent),
         Triggered(PumpEffect(0, 3), None, UntapCardEvent)],
    'glyph-of-destruction': [Triggered(GlyphOfDestruction(), T_FUNCS['your_walls_in_play'], CastResolvedEvent)],
    'goblin-balloon-brigade': [Activated('R', KWAModEffect('add', 'Flying', True), T_FUNCS['self'])],
    'goblin-digging-team': [Activated('T', Destroy(), T_FUNCS['walls_in_play'], extra_costs=[SacSelfCost()])],
    'goblin-king': [Triggered(GoblinKing(), None, CastResolvedEvent)],
    'goblin-wizard': [Activated('T', HandToBoard(), T_FUNCS['goblin_permanents_in_your_hand'])],
    'granite-gargoyle': [Activated('R', PumpEffect(0, 1, True), T_FUNCS['self'])],
    'grapeshot-catapult': [Activated('T', DealDamage(4), T_FUNCS['fliers_in_play'])],
    'grave-robbers': [Activated('BT', GraveRobbersAA(), T_FUNCS['artifacts_in_graveyards'])],
    'great-defender': [Triggered(GreatDefender(), T_FUNCS['creatures_in_play'], CastResolvedEvent)],
    'holy-armor': [Triggered(PumpEffect(0, 2), T_FUNCS['creatures_in_play'], CastResolvedEvent)],
    'holy-day': [Triggered(PreventAllCombatDamageThisTurn(), None, CastResolvedEvent)],
    'holy-strength': [Triggered(PumpEffect(1, 2), T_FUNCS['creatures_in_play'], CastResolvedEvent)],
    'howl-from-beyond': [Triggered(HowlFromBeyond(), T_FUNCS['creatures_in_play'], CastResolvedEvent)],
    'ice-storm': [Triggered(Destroy(), T_FUNCS['lands_in_play'], CastResolvedEvent)],
    'immolation': [Triggered(PumpEffect(2, -2), T_FUNCS['creatures_in_play'], CastResolvedEvent)],
    'indestructible-aura':
        [Triggered(PreventNextDamageToCardEffect(), T_FUNCS['creatures_in_play'], CastResolvedEvent)],
    'inferno': [Triggered(DealDamageToAllCreaturesAndPlayers(6), None, CastResolvedEvent)],
    'instill-energy':
        [Triggered(KWAModEffect('add', 'Haste'), T_FUNCS['creatures_in_play'], CastResolvedEvent)],
        # TODO: instill-energy also has '0: Untap host (only during your turn and only once each turn)'
    'island-fish-jasconius': [Triggered(StaysTapped(), T_FUNCS['self'], UntapPhaseEvent)],
    'ivory-tower': [Triggered(IvoryTower(), None, UpkeepEvent)],
    'jovial-evil': [Triggered(JovialEvil(), T_FUNCS['opponent'], CastResolvedEvent)],
    'jump':
        [Triggered(KWAModEffect('add', 'Flying', True), T_FUNCS['creatures_in_play'], CastResolvedEvent)],
    'junun-efreet': [Triggered(PayManaOrSac('BB'), None, UpkeepEvent)],
    'juzam-djinn': [Triggered(DealDamageOnSourceTurn(1), None, UpkeepEvent)],
    'karma': [Triggered(Karma(), None, UpkeepEvent)],
    'kird-ape': [Static(KirdApePT())],
    'kobold-drill-sergeant': [Triggered(KoboldDrillSergeant(), None, CastResolvedEvent)],
    'kobold-overlord': [Triggered(KoboldOverlordCast(), None, CastResolvedEvent)],
    'kobold-taskmaster': [Triggered(KoboldTaskmaster(), None, CastResolvedEvent)],
    'lance':
        [Triggered(KWAModEffect('add', 'First Strike'), T_FUNCS['creatures_in_play'], CastResolvedEvent)],
    'leviathan':
        [Triggered(TapCardEffect(), T_FUNCS['self'], CastResolvedEvent),
         Triggered(StaysTapped(), T_FUNCS['self'], UntapPhaseEvent)],
    'lightning-bolt': [Triggered(DealDamage(3), T_FUNCS['all_creatures_and_players'], CastResolvedEvent)],
    'living-armor':
        [Activated('T', XZeroOneCountersByManaValue(), T_FUNCS['creatures_in_play'], extra_costs=[SacSelfCost()])],
    'living-artifact':
        [Triggered(None, T_FUNCS['artifacts_in_play'], CastResolvedEvent),
         Triggered(LivingArtifactOnDamage(), None, DamageResolvedEvent)],
    'lord-of-atlantis': [Activated(LordOfAtlantis(), None, CastResolvedEvent)],
    'lord-of-the-pit': [Triggered(LordOfThePitUpkeep(), None, UpkeepEvent)],
    'mana-short': [Triggered(ManaShort(), T_FUNCS['all_players'], CastResolvedEvent)],
    'mana-vault': [Triggered(StaysTapped(), T_FUNCS['self'], UntapPhaseEvent)],
    'mana-vortex':
        [Triggered(Destroy(), T_FUNCS['your_lands_in_play'], CastResolvedEvent),
         Triggered(ManaVortexUpkeep(), None, UpkeepEvent)],
    'marble-priest': [Static(MarblePriestPrevention())],  # there is some part of Marble Priest that's not yet coded !!!
    'marsh-viper': [Triggered(AddPoisonCounter(2), None, DamageResolvedEvent)],
    'martyrs-cry': [Triggered(MartyrsCry(), None, CastResolvedEvent)],
    'martyrs-of-korlis': [Static(MartyrsOfKorlisDamageReplacement())],  # note: no way this works
    'mountain': [Triggered(MountainTap(), None, TapCardEvent)],
    'necropolis':
        [Activated('', XZeroOneCountersByManaValue(), T_FUNCS['creatures_in_your_graveyard'])],  # TODO: needs an extra cost of "Exile a creature card from your graveyard"
    'nevinyrrals-disk': [Triggered(TapCardEffect(), T_FUNCS['self'], CastResolvedEvent)],
    'old-man-of-the-sea': [Triggered(OptionalUntap(), None, UntapPhaseEvent)],
    'osai-vultures': [Triggered(AddCountersIfAnyCreatureDied(CARRION), T_FUNCS['self'], EndStepEvent)],
    'paralyze':
        [Triggered(TapCardEffect(), T_FUNCS['host'], CastResolvedEvent),
         Triggered(HostStaysTapped(), T_FUNCS['host'], UntapPhaseEvent)],  # TODO: should there be an AttachToHost(Effect) ???
    'pestilence': [Triggered(PestilenceEndStep(), None, EndStepEvent)],
    'phantasmal-forces': [Triggered(PayManaOrSac('U'), None, UpkeepEvent)],
    'phyrexian-gremlins': [Triggered(OptionalUntap(), None, UntapPhaseEvent)],
    'pit-scorpion': [Triggered(AddPoisonCounter(), None, DamageResolvedEvent)],
    'power-surge': [Triggered(PowerSurge(), None, UpkeepEvent)],
    'preacher': [Triggered(OptionalUntap(), None, UntapPhaseEvent)],
    'primordial-ooze': [Triggered(AddCountersYourTurnOnly(PLUS_ONE), T_FUNCS['self'], UpkeepEvent)],
    'psionic-blast': [Triggered(DealDamageToTargetAndYou(4, 2),
                                T_FUNCS['all_creatures_and_players'], CastResolvedEvent)],
    'psychic-venom':
        [Triggered(None, T_FUNCS['lands_in_play'], CastResolvedEvent),
         Triggered(DealDamage(2), T_FUNCS['host_owner']), TapCardEvent],
    'raise-dead': [Triggered(GraveyardToHand(), T_FUNCS['creatures_in_your_graveyard'], CastResolvedEvent)],
    'reconstruction': [Triggered(GraveyardToHand(), T_FUNCS['artifacts_in_your_graveyard'], CastResolvedEvent)],
    'regrowth': [Triggered(GraveyardToHand(), T_FUNCS['cards_in_your_graveyard'], CastResolvedEvent)],
    'reset':
        [Triggered(Reset(), None, CastResolvedEvent, conditions=[])],  # TODO: Cast this spell only during an opponent's turn after their upkeep step
    'resurrection': [Triggered(GraveyardToBoard(), T_FUNCS['creatures_in_your_graveyard'], CastResolvedEvent)],
    'reverse-damage': [Triggered(ReverseDamage(), T_FUNCS['cards_in_play'], CastResolvedEvent)],
    'riptide': [Triggered(Riptide(), None, CastResolvedEvent)],
    'rock-hydra': [Triggered(RockHydraCast(), T_FUNCS['self'], CastResolvedEvent)],
    'rocket-launcher': [Triggered(RocketLauncherCast(), None, CastResolvedEvent)],
    'sacrifice': [Triggered(SacrificeOnCast(), T_FUNCS['your_creatures_in_play'], CastResolvedEvent)],
    'scarecrow': [Static(ScarecrowPrevention())],
    'scavenging-ghoul': [Triggered(AddCounterPerCreatureDeath(CORPSE), T_FUNCS['self'], EndStepEvent)],
    'season-of-the-witch':
        [Triggered(SeasonOfTheWitchUpkeep(), None, UpkeepEvent),
         Triggered(SeasonOfTheWitchEndStep(), None, EndStepEvent)],
    'seeker': [Static(Seeker())],
    'serendib-djinn':
        [Triggered(SerendibDjinn(), None, UpkeepEvent), Triggered(SerendibDjinnNoLands(), None, StateBasedEvent)],
    'serendib-efreet': [Triggered(DealDamageOnSourceTurn(1), None, UpkeepEvent)],
    'shapeshifter': [Triggered(Shapeshifter(), None, CastResolvedEvent), Triggered(Shapeshifter(), None, UpkeepEvent)],
    'shatter': [Triggered(Destroy(), T_FUNCS['artifacts_in_play'], CastResolvedEvent)],
    'sinkhole': [Triggered(Destroy(), T_FUNCS['lands_in_play'], CastResolvedEvent)],
    'skull-of-orm': [Activated('5T', GraveyardToHand(), T_FUNCS['enchants_in_your_graveyard'])],
    'spirit-link': [Triggered(None, T_FUNCS['creatures_in_play'], CastResolvedEvent),
                    Triggered(SpiritLink(), None, DamageResolvedEvent)],
    'spirit-shackle': [Triggered(AddCounter(MINUS_ZERO_TWO), T_FUNCS['host'], TapCardEvent)],
    'spritual-sanctuary': [Triggered(SpiritualSanctuary(), None, UpkeepEvent)],
    'stone-rain': [Triggered(Destroy(), T_FUNCS['lands_in_play'], CastResolvedEvent)],
    'storm-seeker': [Triggered(StormSeeker(), T_FUNCS['all_players'], CastResolvedEvent)],
    'storm-world': [Triggered(StormWorld(), None, UpkeepEvent)],
    'stream-of-life': [Triggered(StreamOfLife(), T_FUNCS['all_players'], CastResolvedEvent)],
    'subdue': [Triggered(Subdue(), T_FUNCS['creatures_in_play'], CastResolvedEvent)],
    'sunken-city': [Static(SunkenCity()), Triggered(PayManaOrSac('UU'), None, UpkeepEvent)],
    'sword-to-plowshares': [Triggered(SwordsToPlowshares(), T_FUNCS['creatures_in_play'], CastResolvedEvent)],
    'syphon-soul': [Triggered(SyphonSoul(), T_FUNCS['opponent'], CastResolvedEvent)],
    'tawnoss-coffin': [Triggered(OptionalUntap(), None, UntapPhaseEvent)],
    'tawnoss-weaponry': [Triggered(OptionalUntap(), None, UntapPhaseEvent)],
    'tetravus': [Triggered(AddCountersYourTurnOnly(PLUS_ONE, 3), T_FUNCS['self'], CastResolvedEvent)],
    'time-vault':
        [Triggered(TapCardEffect(), T_FUNCS['self'], CastResolvedEvent),
         Triggered(StaysTapped(), T_FUNCS['self'], UntapPhaseEvent)],
    'tivadars-crusade':
        [Triggered(DestroyAll(lambda gs, s: gs.card_filter.in_play().by_sub_type('Goblin').result()),
                   None, CastResolvedEvent)],
    'tormods-crypt':
        [Activated('T', GraveyardToExileInItsEntirety(), T_FUNCS['all_players'], extra_costs=[SacSelfCost()])],
    'tranquility':
        [Triggered(DestroyAll(lambda gs, s: gs.card_filter.in_play().by_type('Enchantment').result()),
                   None, CastResolvedEvent)],
    'triskelion': [Triggered(AddCountersYourTurnOnly(PLUS_ONE, 3), T_FUNCS['self'], CastResolvedEvent)],
    'tsunami':
        [Triggered(DestroyAll(lambda gs, s: gs.card_filter.in_play().by_slug('island').result()),
                   None, CastResolvedEvent)],
    'twiddle': [Triggered(Twiddle(), T_FUNCS['artifacts_creatures_lands_in_play'], CastResolvedEvent)],
    'typhoon': [Triggered(Typhoon(), T_FUNCS['opponent'], CastResolvedEvent)],
    'unholy-strength': [Triggered(PumpEffect(2, 1), T_FUNCS['creatures_in_play'], CastResolvedEvent)],
    'unstable-mutation':
        [Triggered(PumpEffect(3, 3), T_FUNCS['creatures_in_play'], CastResolvedEvent),
         Triggered(AddCountersOnHostTurn(MINUS_ONE), T_FUNCS['self'], UpkeepEvent)],
    'unsummon': [Triggered(BoardToHand(), T_FUNCS['creatures_in_play'], CastResolvedEvent)],
    'venarian-gold':
        [Triggered(RemoveCountersOnHostTurn(SLEEP), T_FUNCS['your_creatures_in_play'], UpkeepEvent),
         Triggered(VenarianGoldHostStaysTapped(), None, UntapPhaseEvent)],
    'voodoo-doll':
        [Triggered(AddCountersYourTurnOnly(PIN), T_FUNCS['self'], UpkeepEvent),
         Triggered(VoodooDollEndStep(), None, EndStepEvent)],
    'warp-artifact': [Triggered(DealDamageOnTargetTurn(1), T_FUNCS['artifacts_in_play'], UpkeepEvent)],
    'weakness': [Triggered(PumpEffect(-2, -1), T_FUNCS['creatures_in_play'], CastResolvedEvent)],
    'web': [Triggered(Web(), T_FUNCS['creatures_in_play'], CastResolvedEvent)],
    'wheel-of-fortune': [Triggered(WheelOfFortune(), trigger_event=CastResolvedEvent)],
    'wrath-of-god': [Triggered(ExileAllCreatures(), trigger_event=CastResolvedEvent)]
}

def get_activated_abilities(c: GameCard) -> list[ActivatedAbility | None]:
    eff_invocations = INVOCATIONS.get(c.props.slug)
    return [ActivatedAbility(c, inv) for inv in eff_invocations if inv.activation_type == 'activated'] if eff_invocations else []


