from __future__ import annotations

from itertools import combinations
from typing import TYPE_CHECKING

from models.effects.identity import SetColor, AddCreatureTypePTManaValue, BecomeCreature, EvilPresence, PhantasmalTerrain

if TYPE_CHECKING:
    from models.game_card import GameCard

from constants import COLOR_LETTERS
from cost import SacSelfCost, ExileSelfCost, SacTwoIslandsCost, PayLifeCost, RemoveCounterCost
from models.card_attributes.card_filter_funcs import T_FUNCS
from models.counter_tokens import PLUS_ONE_ZERO, CARRION, PLUS_ONE, CORPSE, MINUS_ZERO_TWO, MINUS_ONE, SLEEP, PIN, \
    CHARGE
from models.effects.base import EffSpec, Activated, Triggered, Static
from models.effects.combat import WalkRuleRemoved, TowerOfCoireall, UnblockableThisTurn
from models.effects.counters import CityOfShadowsAA1, CityOfShadowsAA2, RemovePlusOneZeroFromCombatant, \
    AddCountersYourTurnOnly, CocoonCast, XZeroOneCountersByManaValue, AddCountersIfAnyCreatureDied, \
    RockHydraCast, AddCounterPerCreatureDeath, AddCounterToHost, AddCountersOnHostTurn, RemoveCountersOnHostTurn, \
    CitanulDruid, ManaBatteriesAddMana, AddCounter
from models.effects.damage import DealDamage, DealDamageToTargetAndYou, CurseArtifactUpkeep, DealDamageOnTargetTurn, \
    PreventAllCombatDamageThisTurn, Earthquake, ElderSpawnUpkeep, ErgRaiders, EternalFlame, EyeForAnEye, \
    FungusaurOnDamage, GaseousForm, PreventNextDamageToCardEffect, DealDamageToAllCreaturesAndPlayers, JovialEvil, \
    DealDamageOnSourceTurn, Karma, LivingArtifactOnDamage, LordOfThePitUpkeep, PowerSurge, DealDamageToTargetAndSelf, \
    StormSeeker, StormWorld, Typhoon, PersonalIncarnation, CreatureBond, Backfire, TheRack, AnkhOfMishra, BlackVise, \
    DingusEgg, GoblinShrineOnLeave, ManaVaultDamageIfTapped, Banshee, RukhEgg
from models.effects.damage_preventions import PreventNextDamageEffect, ArgothianPixiesPrevention, \
    ArgothianTreefolkPrevention, ArtifactWardPrevention, PreventNextDamageToSourceOwner, EnchantedBeingPrevention, \
    Forcefield, MarblePriestPrevention, ScarecrowPrevention, UncleIstvanPrevention
from models.effects.damage_replacements import JadeMonolith, MartyrsOfKorlisDamageReplacement
from models.effects.destroy_sac_regenerate import AcidRain, DestroyAll, Destroy, PayManaOrSac, EaterOfTheDeadAA, \
    ErosionUpkeep, ForceOfNatureUpkeep, ManaVortexUpkeep, PestilenceEndStep, SeasonOfTheWitchUpkeep, \
    SeasonOfTheWitchEndStep, SerendibDjinnNoLands, VoodooDollEndStep, ExileAllCreatures, CyclopeanMummy, \
    DestroyIfItAttacked, PsychicAllergyUpkeep, LandEquilibrium, Millstone, EnergyFlux, TheTabernacleAtPendrellVale
from models.effects.draw_discard import DrawCards, Braingeyser, CursedRackEffect, WheelOfFortune, VerduranEnchantress
from models.effects.keywords import AkronLegionnaireCast, KWAModEffect, ErhnamDjinn, EvilEyeOfOrmsByGoreCast, \
    AllWalksRemoved, KoboldOverlordCast, SandalsOfAbdallahIslandWalk
from models.effects.life import ElHajjaj, GainLife, IvoryTower, AddPoisonCounter, SpiritLink, SpiritualSanctuary, \
    StreamOfLife, Onulet, OnColorSpellPayOneColorlessForOneLifeChoice, AliFromCairo
from models.effects.mana import AddMana, DrainPower, EnergyTap, ExchangeLifeTotals, SuChi, UrzasTrio
from models.effects.piles import Bounce, HandToBoard, GraveRobbersAA, Reanimate, GraveyardToExileInItsEntirety, Steal, \
    StealCardLeaves, GhazbanOgre
from models.effects.pumps import PumpEffect, BloodLust, DragonWhelpEndStep, GreatDefender, HowlFromBeyond, \
    KoboldTaskmaster, HellSwarm, HolyLight, ArmyOfAllah, BoneFlute, MarshGas, Morale, Piety, ShieldWall, BerserkPump
from models.effects.queries import AmrouKithkin, AngelicVoices, ArgothianPixiesCanBeBlocked, ArtifactWardCanBeBlocked, \
    BadMoon, BogRats, Castle, Crusade, ElderSpawnCanBeBlocked, ElvenRidersCanBeBlocked, EvilEyeOfOrmsByGoreCanBeBlocked, \
    KirdApePT, Seeker, SunkenCity, Mightstone, OrcishOriflamme, ConcordantCrossroads, GravitySphere, HiddenPath, Moat, \
    RabidWombat, LordOfAtlantisPT, LordOfAtlantisWalk, Meekstone, GoblinCaves, GoblinShrinePump, Weakstone, WaterWurmPT, \
    AngryMobPT, AspectOfWolfPT, GaeasAvengerPT, GaeasLiegePT, KeldonWarlordPT, NightmarePT, PeopleOfTheWoodsPT, \
    WallOfTombstonesPT, GoblinsOfTheFlarg, Invisibility, IronclawOrcs, Fear, KormusBell, LivingLands, LivingPlane, \
    Conversion, JuggernautUnblockableByWalls
from models.effects.special import ActiveVolcano, AnimateDead, BookOfRass, CocoonUpkeep, Crumble, DivineOffering, \
    Earthbind, ElectricEel, ElvesOfTheDeepShadow, Feint, FlashFlood, ForestCast, GlyphOfDestruction, GoblinKing, Greed, \
    KoboldDrillSergeant, KryShield, MartyrsCry, MazeOfIth, Rakalite, ReverseDamage, RocketLauncherCast, \
    RocketLauncherAA, SacrificeOnCast, SerendibDjinn, Shapeshifter, StoneGiant, Subdue, SwordsToPlowshares, SyphonSoul, \
    Web, TabletOfEpityr, SoulNet, UrzasMiter, WormwoodTreefolkForestwalk, WormwoodTreefolkSwampwalk, Fasting, \
    FeldonsCane, Timetwister, WindsOfChange, HurkylsRecall, AshnodsTransmogrant, CreateTokenCreature, \
    LivingArtifactUpkeep
from models.effects.tap_untap import UntapForManaEffect, UntapHostForManaEffect, TapCardEffect, OptionalUntap, \
    StaysTapped, CocoonHostStaysTapped, ForestTap, GiantTortoiseTap, UntapCardEffect, ManaShort, MountainTap, \
    HostStaysTapped, Reset, Riptide, Twiddle, VenarianGoldHostStaysTapped, Kismet
from models.events.events_all import CastResolvedEvent, UntapPhaseEvent, EndStepEvent, CombatEndEvent, UpkeepEvent, \
    DamageResolvedEvent, TapCardEvent, UntapCardEvent, StateBasedEvent, DiesEvent, DrawCardEvent, ZoneChangeEvent, \
    DrawStepEvent
from phase_fsm import Phase

def dual_land_activated_ability_specs(colors: str) -> list[EffSpec]:
    return [Activated('T', AddMana(color), T_FUNCS['card_owner'], text=f'Add {{{color}}}') for color in colors]


def untap_for_mana_at_owner_upkeep(untap_cost: str) -> EffSpec:
    return Activated(untap_cost, UntapForManaEffect(untap_cost), allowed_phases=[Phase.UPKEEP],
                     allowed_player_turn=EffSpec.AllowedPlayerTurn.CASTER, text='Untap')


def untap_host_for_mana_at_opp_upkeep(untap_cost: str) -> EffSpec:
    return Activated(untap_cost, UntapHostForManaEffect(untap_cost), allowed_phases=[Phase.UPKEEP],
                     allowed_player_turn=EffSpec.AllowedPlayerTurn.OPPONENT, text='Untap')


def is_tapped(s: GameCard) -> bool:
    return s.is_tapped


MANA_BATTERY_ADD_CHARGE = Activated('2T', AddCounter(CHARGE), T_FUNCS['self'])


INVOCATIONS: dict[str, list[EffSpec]] = {
    'acid-rain': [Triggered(AcidRain(), None, CastResolvedEvent)],
    'active-volcano': [Triggered(ActiveVolcano(), T_FUNCS['active_volcano_targets'], CastResolvedEvent)],
    'akron-legionnaire': [Triggered(AkronLegionnaireCast(), None, CastResolvedEvent)],
    'aladdin': [Activated('1RRT', Steal(), T_FUNCS['opp_artifacts_in_play'])],
    'aladdins-ring': [Activated('T', DealDamage(4), T_FUNCS['all_creatures_and_players'])],
    'ali-baba': [Activated('RT', TapCardEffect(), T_FUNCS['walls_in_play'])],
    'ali-from-cairo': [Static(AliFromCairo())],
    'alchors-tomb': [Activated('2T', SetColor(c), T_FUNCS['your_permanents_in_play'], text=f'Set color to {{{c}}}')
                     for c in COLOR_LETTERS],
    'amrou-kithkin': [Static(AmrouKithkin())],
    'amulet-of-kroog': [Activated('2T', PreventNextDamageEffect(1), T_FUNCS['all_creatures_and_players'])],
    'ancestral-recall': [Triggered(DrawCards(3), T_FUNCS['all_players'], CastResolvedEvent)],
    'angelic-voices': [Static(AngelicVoices())],
    'angry-mob': [Static(AngryMobPT())],
    'animate-artifact': [Triggered(None, T_FUNCS['non_creature_artifacts_in_play'], CastResolvedEvent),
                         Static(AddCreatureTypePTManaValue())],
    'animate-dead': [Triggered(AnimateDead(), T_FUNCS['creatures_in_your_graveyard'], CastResolvedEvent)],
    'animate-wall':
        [Triggered(KWAModEffect('remove', 'Defender'), T_FUNCS['walls_in_play'], CastResolvedEvent)],
    'ankh-of-mishra': [Triggered(AnkhOfMishra(), None, ZoneChangeEvent)],
    'apprentice-wizard': [Activated('UT', AddMana('C', 3), T_FUNCS['card_owner'])],
    'argivian-archaeologist': [Activated('WWT', Bounce(), T_FUNCS['artifacts_in_your_graveyard'])],
    'argivian-blacksmith': [Activated('T', PreventNextDamageEffect(2), T_FUNCS['artifact_creatures_in_play'])],
    'argothian-pixies': [Static(ArgothianPixiesCanBeBlocked(), Static(ArgothianPixiesPrevention()))],
    'argothian-treefolk': [Static(ArgothianTreefolkPrevention())],
    'armageddon':
        [Triggered(DestroyAll(lambda gs, s: gs.card_filter.in_play().by_type('Land').result()),
                   None, CastResolvedEvent)],
    'army-of-allah': [Triggered(ArmyOfAllah(), None, CastResolvedEvent)],
    'artifact-ward': [Triggered(None, T_FUNCS['artifacts_in_play'], CastResolvedEvent),
                      Static(ArtifactWardCanBeBlocked(), Static(ArtifactWardPrevention()))],
    'ashnods-battle-gear': [Triggered(OptionalUntap(), None, UntapPhaseEvent)],
    'ashnods-transmogrant':
        [Activated('T', AshnodsTransmogrant(), T_FUNCS['non_artifact_creatures_in_play'], extra_costs=[SacSelfCost()])],
    'aspect-of-wolf': [Static(AspectOfWolfPT())],
    'backfire': [Triggered(Backfire(), None, DamageResolvedEvent)],
    'bad-moon': [Static(BadMoon())],
    'badlands': dual_land_activated_ability_specs('BR'),
    'ball_lightning': [Triggered(Destroy(), T_FUNCS['self'], EndStepEvent)],
    'banshee': [Activated('XT', Banshee(), T_FUNCS['all_creatures_and_players'],
                          max_variable_x_func=lambda gs, s: gs.mana_pools[s.owner_id].get_max_x('X'))],
    'basalt-monolith': [Triggered(StaysTapped(), T_FUNCS['self'], UntapPhaseEvent),
                        Activated('T', AddMana('C', 3)), Activated('3', UntapCardEffect(), T_FUNCS['self'])],
    'bayou': dual_land_activated_ability_specs('BG'),
    'berserk': [Triggered(BerserkPump(), T_FUNCS['creatures_in_play'],
                          CastResolvedEvent, allowed_phases=[p for p in Phase if p < Phase.COMBAT_DAMAGE]),
                Triggered(DestroyIfItAttacked(), T_FUNCS['creatures_in_play'], EndStepEvent)],  # warning: i don't think this target func is correct; it needs to know the target previously selected
    'birds-of-paradise': [Activated('T', AddMana(c), text=f'Add {{{c}}}') for c in COLOR_LETTERS],
    'black-mana-battery': [MANA_BATTERY_ADD_CHARGE,
                           Activated('T', ManaBatteriesAddMana('B'), extra_costs=[RemoveCounterCost(CHARGE)],
                                     max_variable_x_func=lambda gs, s: T_FUNCS['self'](gs, s).counters.get_count(CHARGE))],
    'black-vise': [Triggered(BlackVise(), T_FUNCS['opponent'], UpkeepEvent)],
    'black-ward': [Triggered(KWAModEffect('add', 'Protection From Black'),
                             T_FUNCS['creatures_in_play'], CastResolvedEvent)],
    'blessing': [Activated('W', PumpEffect(1, 1, True), T_FUNCS['host'])],
    'blight': Triggered(Destroy(), T_FUNCS['host'], TapCardEvent),
    'blood-lust': [Triggered(BloodLust(), T_FUNCS['creatures_in_play'], CastResolvedEvent)],
    'blue-mana-battery': [MANA_BATTERY_ADD_CHARGE,
                           Activated('T', ManaBatteriesAddMana('U'), extra_costs=[RemoveCounterCost(CHARGE)],
                                     max_variable_x_func=lambda gs, s: T_FUNCS['self'](gs, s).counters.get_count(CHARGE))],
    'blue-ward': [Triggered(KWAModEffect('add', 'Protection From Blue'),
                            T_FUNCS['creatures_in_play'], CastResolvedEvent)],
    'bog-rats': [Static(BogRats())],
    'bone-flute': [Activated('2T', BoneFlute())],
    'book-of-rass': [Activated('2', BookOfRass())],
    'boomerang': [Triggered(Bounce(), T_FUNCS['permanents_in_play'], CastResolvedEvent)],
    'braingeyser': [Triggered(Braingeyser(), T_FUNCS['all_players'], CastResolvedEvent)],
    'brainwash':
        # WARNING: the AA would generally be activated by the opponent normally placed on an opponent creature
        [Triggered(KWAModEffect('remove', 'Attack'), T_FUNCS['creatures_in_play'], CastResolvedEvent),
         Activated('3', KWAModEffect('add', 'Attack', True), T_FUNCS['host'])],
    'brass-man': [Triggered(StaysTapped(), T_FUNCS['self'], UntapPhaseEvent), untap_for_mana_at_owner_upkeep('1')],
    'brothers-of-fire': [Activated('T', DealDamageToTargetAndYou(1, 1), T_FUNCS['all_creatures_and_players'])],
    'burrowing':
        [Triggered(KWAModEffect('add', 'Mountainwalk'), T_FUNCS['creatures_in_play'], CastResolvedEvent)],
    'carrion-ants': [Activated('1', PumpEffect(1, 1, True), T_FUNCS['self'])],
    'castle': [Static(Castle())],
    'celestial-prism': [Activated('2T', AddMana(c), T_FUNCS['card_owner'], text=f'Add 1 {c}') for c in COLOR_LETTERS],
    'chaoslace': [Triggered(SetColor('R'), T_FUNCS['cards_in_play'], CastResolvedEvent)],
    'circle-of-protection-artifacts': [Activated('1', PreventNextDamageToSourceOwner(), T_FUNCS['artifacts_in_play'])],
    'circle-of-protection-black': [Activated('1', PreventNextDamageToSourceOwner(), T_FUNCS['black_in_play'])],
    'circle-of-protection-blue': [Activated('1', PreventNextDamageToSourceOwner(), T_FUNCS['blue_in_play'])],
    'circle-of-protection-green': [Activated('1', PreventNextDamageToSourceOwner(), T_FUNCS['green_in_play'])],
    'circle-of-protection-red': [Activated('1', PreventNextDamageToSourceOwner(), T_FUNCS['red_in_play'])],
    'circle-of-protection-white': [Activated('1', PreventNextDamageToSourceOwner(), T_FUNCS['white_in_play'])],
    'citanul-druid': [Triggered(CitanulDruid(), None, ZoneChangeEvent)],
    'city-of-shadows':
        [Activated('T', CityOfShadowsAA1()), Activated('T', CityOfShadowsAA2())],  # TODO: needs a way to find a creature to exile in extra_costs
    'cleanse':
        [Triggered(DestroyAll(T_FUNCS['black_creatures_in_play']), None, CastResolvedEvent)],
    'clockwork-avian':
        [Triggered(RemovePlusOneZeroFromCombatant(), T_FUNCS['self'], CombatEndEvent),
         Triggered(AddCountersYourTurnOnly(PLUS_ONE_ZERO, 4), T_FUNCS['self'], CastResolvedEvent),
         Activated('XT', AddCountersYourTurnOnly(PLUS_ONE_ZERO), None, UpkeepEvent,
                   max_variable_x_func=lambda gs, s: 4 - s.counters.get_count(PLUS_ONE_ZERO))],
    'clockwork-beast':
        [Triggered(RemovePlusOneZeroFromCombatant(), T_FUNCS['self'], CombatEndEvent),
         Triggered(AddCountersYourTurnOnly(PLUS_ONE_ZERO, 7), T_FUNCS['self'], CastResolvedEvent),
         Activated('XT', AddCountersYourTurnOnly(PLUS_ONE_ZERO), None, UpkeepEvent,
                   max_variable_x_func=lambda gs, s: 7 - s.counters.get_count(PLUS_ONE_ZERO))],
    'coal-golem': [Activated('3', AddMana('R', 3), T_FUNCS['card_owner'], extra_costs=[SacSelfCost()])],
    'cocoon':
        [Triggered(CocoonCast(), T_FUNCS['your_creatures_in_play'], CastResolvedEvent),
         Triggered(CocoonHostStaysTapped(), None, UntapPhaseEvent),
         Triggered(CocoonUpkeep(), None, UpkeepEvent)],
    'colossus-of-sardia': [Triggered(StaysTapped(), T_FUNCS['self'], UntapPhaseEvent),
                           untap_for_mana_at_owner_upkeep('9')],
    'concordant-crossroads': [Static(ConcordantCrossroads())],
    'conservator': [Activated('3T', PreventNextDamageToSourceOwner(2))],
    'control-magic': [Triggered(Steal(), T_FUNCS['opp_creatures_in_play'], CastResolvedEvent),
                      Triggered(StealCardLeaves(), None, ZoneChangeEvent)],
    'conversion': [Triggered(PayManaOrSac('WW'), None, UpkeepEvent), Static(Conversion())],
    'copper-tablet': [Triggered(DealDamage(1), T_FUNCS['in_turn_player'], UpkeepEvent)],
    'cosmic-horror': [Triggered(PayManaOrSac('3BBB'), None, UpkeepEvent)],
    'crevasse': [Static(WalkRuleRemoved('Mountainwalk'))],
    'creature-bond': [Triggered(CreatureBond(), None, DiesEvent)],
    'crumble': [Triggered(Crumble()), T_FUNCS['artifacts_in_play'], CastResolvedEvent],
    'crusade': [Static(Crusade())],
    'crystal-rod': [Static(OnColorSpellPayOneColorlessForOneLifeChoice('U'))],
    'curse-artifact': [Triggered(CurseArtifactUpkeep(), T_FUNCS['artifacts_in_play'], UpkeepEvent)],
    'cursed-land': [Triggered(DealDamageOnTargetTurn(1), T_FUNCS['lands_in_play'], UpkeepEvent)],
    'cursed-rack': [Triggered(CursedRackEffect(), None, EndStepEvent)],
    'cyclopean-mummy': [Triggered(CyclopeanMummy(), None, DiesEvent)],
    'dark-ritual': [Triggered(AddMana('B', 3), None, CastResolvedEvent)],
    'darkness': [Triggered(PreventAllCombatDamageThisTurn(), None, CastResolvedEvent)],
    'deadfall': [Static(WalkRuleRemoved('Forestwalk'))],
    'deathlace': [Triggered(SetColor('B'), T_FUNCS['cards_in_play'], CastResolvedEvent)],
    'demonic-torment':
        [Triggered(KWAModEffect('remove', 'Attack'), T_FUNCS['creatures_in_play'], CastResolvedEvent)],
    'desert-twister': [Triggered(Destroy(), T_FUNCS['permanents_in_play'], CastResolvedEvent)],
    'dingus-egg': [Triggered(DingusEgg(), None, ZoneChangeEvent)],
    'disenchant':
        [Triggered(Destroy(), T_FUNCS['artifacts_and_enchantments_in_play'], CastResolvedEvent)],
    'divine-offering': [Triggered(DivineOffering(), T_FUNCS['artifacts_in_play'], CastResolvedEvent)],
    'divine-transformation':
        [Triggered(PumpEffect(3, 3), T_FUNCS['creatures_in_play'], CastResolvedEvent)],
    'dragon-engine': [Activated('2', PumpEffect(1, 0, True), T_FUNCS['self'])],
    'dragon-whelp': [Triggered(DragonWhelpEndStep(), None, EndStepEvent)],
    'drain-power': [Triggered(DrainPower(), T_FUNCS['opponent'], CastResolvedEvent)],
    'dream-coat': [Triggered(None, T_FUNCS['creatures_in_play'], CastResolvedEvent)] +
                  [Activated('', SetColor(''.join(combo)), T_FUNCS['host'], max_activations_per_turn=1, text=f'{{{combo}}}')
                   for r in range(1, len(COLOR_LETTERS) + 1) for combo in combinations(COLOR_LETTERS, r)],
                  # TODO: max_activations_per_turn wasn't respected, assuming it's broke for all
    'dwarven-demolition-team': [Activated('T', Destroy(), T_FUNCS['walls_in_play'])],
    'dwarven-warriors': [Activated('T', UnblockableThisTurn(), T_FUNCS['creatures_power_two_or_less'])],
    'earthbind': [Triggered(Earthbind(), T_FUNCS['creatures_in_play'], CastResolvedEvent)],
    'earthquake': [Triggered(Earthquake(), None, CastResolvedEvent)],
    'eater-of-the-dead':
        [Activated('', EaterOfTheDeadAA(), T_FUNCS['creatures_in_all_graveyards'], conditions=[is_tapped])],
    'el-hajjâj': [Triggered(ElHajjaj(), T_FUNCS['self'], DamageResolvedEvent)],
    'elder-spawn': [Triggered(ElderSpawnUpkeep(), None, UpkeepEvent), Static(ElderSpawnCanBeBlocked())],
    'electric-eel': [Triggered(DealDamage(1), T_FUNCS['self'], CastResolvedEvent), Activated('RR', ElectricEel())],
    'elven-riders': [Static(ElvenRidersCanBeBlocked())],
    'elves-of-deep-shadow': [Activated('T', ElvesOfTheDeepShadow())],
    'emerald-dragonfly': [Activated('GG', KWAModEffect('add', 'First Strike', True), T_FUNCS['self'])],
    'enchanted-being': [Static(EnchantedBeingPrevention())],
    'energy-flux': [Triggered(EnergyFlux(), None, UpkeepEvent)],
    'energy-tap': [Triggered(EnergyTap(), T_FUNCS['your_untapped_creatures'], CastResolvedEvent)],
    'erg-raiders': [Triggered(ErgRaiders(), None, EndStepEvent)],
    'erhnam-djinn': [Triggered(ErhnamDjinn(), T_FUNCS['opp_non_wall_creatures_in_play'], UpkeepEvent)],
    'erosion':
        [Triggered(None, T_FUNCS['lands_in_play'], CastResolvedEvent), Triggered(ErosionUpkeep(), None, UpkeepEvent)],
    'eternal-flame': [Triggered(EternalFlame(), None, CastResolvedEvent)],
    'eternal-warrior': [Triggered(KWAModEffect('add', 'Vigilance'), T_FUNCS, CastResolvedEvent)],
    'evil-eye-of-orms-by-gore': [Triggered(EvilEyeOfOrmsByGoreCast(), None, CastResolvedEvent),
                                 Static(EvilEyeOfOrmsByGoreCanBeBlocked())],
    'evil-presence': [Triggered(EvilPresence(), T_FUNCS['lands_in_play'], CastResolvedEvent)],
    'exorcist': [Activated('1W', Destroy(), T_FUNCS['black_creatures_in_play'])],
    'eye-for-an-eye': [Triggered(EyeForAnEye(), T_FUNCS['cards_in_play'], CastResolvedEvent)],
    'faint': [Triggered(Feint(), T_FUNCS['attackers'], CastResolvedEvent)],
    'farmstead': [Triggered(None, T_FUNCS['lands_in_play'], CastResolvedEvent),
                  Activated('WW', GainLife(), T_FUNCS['host_owner'], allowed_phases=[Phase.UPKEEP],
                            allowed_p_id_turn=T_FUNCS['host_owner'], max_activations_per_turn=1)],
    'fasting': [Triggered(Fasting(), T_FUNCS['self'], UpkeepEvent),
                Triggered(Destroy(), T_FUNCS['self'], DrawCardEvent)],
    'fear': [Triggered(None, T_FUNCS['creatures_in_play'], CastResolvedEvent), Static(Fear())],
    'feedback': [Triggered(DealDamageOnTargetTurn(1), T_FUNCS['enchants_in_play'], UpkeepEvent)],
    'feldons-cane': [Activated('T', FeldonsCane(), None, extra_costs=[ExileSelfCost()])],
    'fire-drake': [Activated('R', PumpEffect(1, 0, True), T_FUNCS['self'], max_activations_per_turn=1)],
    'fire-sprites': [Activated('GT', AddMana('R'), T_FUNCS['card_owner'])],
    'firebreathing': [Triggered(None, T_FUNCS['creatures_in_play'], CastResolvedEvent),
                      Activated('R', PumpEffect(1, 0, True), T_FUNCS['self'])],
    'flash-flood': [Triggered(FlashFlood(), T_FUNCS['flash_flood'], CastResolvedEvent)],
    'flashfires':
        [Triggered(DestroyAll(lambda gs, s: gs.card_filter.in_play().plains().result()),
                   None, CastResolvedEvent)],
    'flight': [Triggered(KWAModEffect('add', 'Flying'), T_FUNCS['creatures_in_play'], CastResolvedEvent)],
    'flood': [Activated('UU', TapCardEffect(), T_FUNCS['untapped_creatures_without_flying'])],
    'fishliver-oil':
        [Triggered(KWAModEffect('add', 'Islandwalk'), T_FUNCS['creatures_in_play'], CastResolvedEvent)],
    'flying-carpet': [Activated('2T', KWAModEffect('add', 'Flying', True), T_FUNCS['creatures_in_play'])],
    'fog': [Triggered(PreventAllCombatDamageThisTurn(), None, CastResolvedEvent)],
    'force-of-nature': [Triggered(ForceOfNatureUpkeep(), None, UpkeepEvent)],
    'forcefield': [Activated('1', Forcefield(), T_FUNCS['unblocked_attackers'])],
    'forest': [Triggered(ForestCast(), None, CastResolvedEvent), Triggered(ForestTap(), None, TapCardEvent)],
    'forethought-amulet': [Triggered(PayManaOrSac('3'), None, UpkeepEvent)],
    'fountain-of-youth': [Activated('2T', GainLife(), T_FUNCS['card_owner'])],
    'frozen-shade': [Activated('B', PumpEffect(1, 1, True), T_FUNCS['self'])],
    'fungusaur': [Triggered(FungusaurOnDamage(), None, DamageResolvedEvent)],
    'gaeas-avenger': [Static(GaeasAvengerPT())],
    'gaeas-liege': [Static(GaeasLiegePT())],
    'gaeas-touch': [Activated('', AddMana('G', 2), T_FUNCS['card_owner'], extra_costs=[ExileSelfCost()], text='Exile for {GG}'),
                    Activated('', HandToBoard(), T_FUNCS['forests_in_your_hand'], text='Play extra forest',
                              allowed_player_turn=EffSpec.AllowedPlayerTurn.CASTER, max_activations_per_turn=1)],  # TODO: activated_cnt_this_turn needs to increment
    'gaseous-form': [Triggered(GaseousForm(), T_FUNCS['creatures_in_play'], CastResolvedEvent)],
    'ghazbán-ogre': [Triggered(GhazbanOgre(), None, UpkeepEvent)],
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
    'goblin-caves': [Static(GoblinCaves())],
    'goblin-digging-team': [Activated('T', Destroy(), T_FUNCS['walls_in_play'], extra_costs=[SacSelfCost()])],
    'goblin-king': [Triggered(GoblinKing(), None, CastResolvedEvent)],
    'goblin-shrine': [Static(GoblinShrinePump()), Triggered(GoblinShrineOnLeave(), None, ZoneChangeEvent)],
    'goblin-wizard': [Activated('T', HandToBoard(), T_FUNCS['goblin_permanents_in_your_hand'])],
    'goblins-of-the-flarg': [Static(GoblinsOfTheFlarg())],
    'granite-gargoyle': [Activated('R', PumpEffect(0, 1, True), T_FUNCS['self'])],
    'grapeshot-catapult': [Activated('T', DealDamage(4), T_FUNCS['fliers_in_play'])],
    'grave-robbers': [Activated('BT', GraveRobbersAA(), T_FUNCS['artifacts_in_graveyards'])],
    'gravity-sphere': [Static(GravitySphere())],
    'great-defender': [Triggered(GreatDefender(), T_FUNCS['creatures_in_play'], CastResolvedEvent)],
    'great-wall': [Static(WalkRuleRemoved('Plainswalk'))],
    'greater-realm-of-preservation': [Activated('1W', PreventNextDamageToSourceOwner(),
                                                T_FUNCS['black_and_red_in_play'])],
    'greed': [Activated('B', Greed(), T_FUNCS['card_owner'])],
    'green-mana-battery': [MANA_BATTERY_ADD_CHARGE,
                           Activated('T', ManaBatteriesAddMana('G'), extra_costs=[RemoveCounterCost(CHARGE)],
                                     max_variable_x_func=lambda gs, s: T_FUNCS['self'](gs, s).counters.get_count(CHARGE))],
    'green-ward': [Triggered(KWAModEffect('add', 'Protection From Green'),
                             T_FUNCS['creatures_in_play'], CastResolvedEvent)],
    'hammerheim': [Activated('T', AddMana('R'), T_FUNCS['card_owner']),
                   Activated('T', AllWalksRemoved(), T_FUNCS['creatures_in_play'])],
    'hell-swarm': [Triggered(HellSwarm(), None, CastResolvedEvent)],
    'hidden-path': [Static(HiddenPath())],
    'holy-armor': [Triggered(PumpEffect(0, 2), T_FUNCS['creatures_in_play'], CastResolvedEvent),
                   Activated('W', PumpEffect(0, 1, True), T_FUNCS['host'])],
    'holy-day': [Triggered(PreventAllCombatDamageThisTurn(), None, CastResolvedEvent)],
    'holy-light': [Triggered(HolyLight(), None, CastResolvedEvent)],
    'holy-strength': [Triggered(PumpEffect(1, 2), T_FUNCS['creatures_in_play'], CastResolvedEvent)],
    'horn-of-deafening': [Activated('2T', PreventNextDamageToSourceOwner(combat_only=True),
                                    T_FUNCS['creatures_in_play'])],
    'howl-from-beyond': [Triggered(HowlFromBeyond(), T_FUNCS['creatures_in_play'], CastResolvedEvent)],
    'hurkyls-recall': [Triggered(HurkylsRecall(), T_FUNCS['all_players'], CastResolvedEvent)],
    'hyperion-blacksmith': [Activated('T', TapCardEffect(), T_FUNCS['opp_untapped_artifacts']),
                            Activated('T', UntapCardEffect(), T_FUNCS['opp_tapped_artifacts'])],
    'icy-manipulator': [Activated('1T', TapCardEffect(), T_FUNCS['untapped_artifacts_creatures_lands'])],
    'ice-storm': [Triggered(Destroy(), T_FUNCS['lands_in_play'], CastResolvedEvent)],
    'immolation': [Triggered(PumpEffect(2, -2), T_FUNCS['creatures_in_play'], CastResolvedEvent)],
    'indestructible-aura':
        [Triggered(PreventNextDamageToCardEffect(), T_FUNCS['creatures_in_play'], CastResolvedEvent)],
    'inferno': [Triggered(DealDamageToAllCreaturesAndPlayers(6), None, CastResolvedEvent)],
    'instill-energy':
        [Triggered(KWAModEffect('add', 'Haste'), T_FUNCS['creatures_in_play'], CastResolvedEvent),
         Activated('', UntapCardEffect(), T_FUNCS['host'], allowed_p_id_turn=T_FUNCS['host_owner'],
                   max_activations_per_turn=1)],
    'invisibility': [Triggered(None, T_FUNCS['creatures_in_play'], CastResolvedEvent), Static(Invisibility())],
    'iron-star': [Static(OnColorSpellPayOneColorlessForOneLifeChoice('R'))],
    'ironclaw-orcs': [Static(IronclawOrcs())],
    'island-fish-jasconius': [Triggered(StaysTapped(), T_FUNCS['self'], UntapPhaseEvent),
                              untap_for_mana_at_owner_upkeep('UUU')],
    'ivory-cup': [Static(OnColorSpellPayOneColorlessForOneLifeChoice('W'))],
    'ivory-tower': [Triggered(IvoryTower(), None, UpkeepEvent)],
    'jade-monolith': [Activated('1', JadeMonolith(), T_FUNCS['all_creatures_and_players'])],
    'jade-statue': [Activated('2', BecomeCreature(3, 6, 'Golem', True), T_FUNCS['self'],
                              allowed_phases=[Phase.CAST])],
    'jandors-saddlebags': [Activated('3T', UntapCardEffect(), T_FUNCS['tapped_creatures'])],
    'jayemdae-tome': [Activated('4T', DrawCards(), T_FUNCS['card_owner'])],
    'jovial-evil': [Triggered(JovialEvil(), T_FUNCS['opponent'], CastResolvedEvent)],
    'juggernaut': [Static(JuggernautUnblockableByWalls())],
    'jump':
        [Triggered(KWAModEffect('add', 'Flying', True), T_FUNCS['creatures_in_play'], CastResolvedEvent)],
    'junun-efreet': [Triggered(PayManaOrSac('BB'), None, UpkeepEvent)],
    'juzam-djinn': [Triggered(DealDamageOnSourceTurn(1), None, UpkeepEvent)],
    'karma': [Triggered(Karma(), None, UpkeepEvent)],
    'keldon-warlord': [Static(KeldonWarlordPT())],
    'khabál-ghoul': [AddCounterPerCreatureDeath(PLUS_ONE), None, EndStepEvent],
    'killer-bees': [Activated('G', PumpEffect(1, 1, True), T_FUNCS['self'])],
    'king-suleiman': [Activated('T', Destroy(), T_FUNCS['djinns_and_efreets'])],
    'kird-ape': [Static(KirdApePT())],
    'kismet': [Static(Kismet())],
    'kobold-drill-sergeant': [Triggered(KoboldDrillSergeant(), None, CastResolvedEvent)],
    'kobold-overlord': [Triggered(KoboldOverlordCast(), None, CastResolvedEvent)],
    'kobold-taskmaster': [Triggered(KoboldTaskmaster(), None, CastResolvedEvent)],
    'kormus-bell': [Static(KormusBell())],
    'kry-shield': [Activated('2T', KryShield(), T_FUNCS['your_creatures_in_play'])],
    'lance':
        [Triggered(KWAModEffect('add', 'First Strike'), T_FUNCS['creatures_in_play'], CastResolvedEvent)],
    'land-equilibrium': [Static(LandEquilibrium())],
    'leviathan':
        [Triggered(TapCardEffect(), T_FUNCS['self'], CastResolvedEvent),
         Triggered(StaysTapped(), T_FUNCS['self'], UntapPhaseEvent),
         Activated(None, UntapCardEffect(), T_FUNCS['self'], extra_costs=[SacTwoIslandsCost()],
                   allowed_phases=Phase.UPKEEP, allowed_player_turn=T_FUNCS['card_owner']),
         Triggered(KWAModEffect('remove', 'Attack'), T_FUNCS['self'], EndStepEvent),
         Activated(None, KWAModEffect('add', 'Attack'), T_FUNCS['self'], extra_costs=[SacTwoIslandsCost()],
                   allowed_phases=Phase.DECLARE_ATTACKERS, allowed_player_turn=T_FUNCS['card_owner'])],
    'ley-druid': [Activated('T', UntapCardEffect(), T_FUNCS['tapped_lands'])],
    'lightning-bolt': [Triggered(DealDamage(3), T_FUNCS['all_creatures_and_players'], CastResolvedEvent)],
    'lifelace': [Triggered(SetColor('G'), T_FUNCS['cards_in_play'], CastResolvedEvent)],
    'living-armor':
        [Activated('T', XZeroOneCountersByManaValue(), T_FUNCS['creatures_in_play'], extra_costs=[SacSelfCost()])],
    'living-artifact':
        [Triggered(None, T_FUNCS['artifacts_in_play'], CastResolvedEvent),
         Triggered(LivingArtifactOnDamage(), None, DamageResolvedEvent),
         Triggered(LivingArtifactUpkeep(), None, UpkeepEvent)],
    'living-lands': [Static(LivingLands())],
    'living-plane': [Static(LivingPlane())],
    'llanowar-elves': [Activated('T', AddMana('G'), T_FUNCS['card_owner'])],
    'lord-of-atlantis': [Static(LordOfAtlantisPT()), Static(LordOfAtlantisWalk())],
    'lord-of-the-pit': [Triggered(LordOfThePitUpkeep(), None, UpkeepEvent)],
    'mana-short': [Triggered(ManaShort(), T_FUNCS['all_players'], CastResolvedEvent)],
    'mana-vault': [Triggered(StaysTapped(), T_FUNCS['self'], UntapPhaseEvent), untap_for_mana_at_owner_upkeep('4'),
                   Activated('T', AddMana('C', 3), T_FUNCS['card_owner']),
                   Triggered(ManaVaultDamageIfTapped(), None, DrawStepEvent)],
    'mana-vortex':
        [Triggered(Destroy(), T_FUNCS['your_lands_in_play'], CastResolvedEvent),
         Triggered(ManaVortexUpkeep(), None, UpkeepEvent)],
    'marble-priest': [Static(MarblePriestPrevention())],  # there is some part of Marble Priest that's not yet coded !!!
    'marsh-gas': [Triggered(MarshGas(), None, CastResolvedEvent)],
    'marsh-viper': [Triggered(AddPoisonCounter(2), None, DamageResolvedEvent)],
    'martyrs-cry': [Triggered(MartyrsCry(), None, CastResolvedEvent)],
    'martyrs-of-korlis': [Static(MartyrsOfKorlisDamageReplacement())],  # note: no way this works
    'maze-of-ith': [Activated('T', MazeOfIth(), T_FUNCS['attackers'])],
    'meekstone': [Static(Meekstone())],
    'merfolk-assassin': [Activated('T', Destroy(), T_FUNCS['islandwalkers'])],
    'mightstone': [Static(Mightstone())],
    'millstone': [Activated('2T', Millstone(), T_FUNCS['all_players'])],
    'miracle-worker': [Activated('T', Destroy(), T_FUNCS['auras_on_owners_creatures'])],
    'mirror-universe': [Activated('True', ExchangeLifeTotals(), allowed_phases=[Phase.UPKEEP],
                                  allowed_p_id_turn=T_FUNCS['card_owner'], extra_costs=[SacSelfCost()])],
    'mishras-factory': [Activated('T', AddMana('C'), T_FUNCS['card_owner'], text='Add {C}'),
                        Activated('1', BecomeCreature(2, 2, 'Assembly-Worker', True), T_FUNCS['self'], text='Become 2/2'),
                        Activated('T', PumpEffect(1, 1, True), T_FUNCS['assembly_workers'], text='Pump Assembly-Worker')],
    'moat': [Static(Moat())],
    'morale': [Triggered(Morale(), None, CastResolvedEvent)],
    'mountain': [Triggered(MountainTap(), None, TapCardEvent)],
    'mox-emerald': [Activated('T', AddMana('G'), T_FUNCS['card_owner'])],
    'mox-jet': [Activated('T', AddMana('B'), T_FUNCS['card_owner'])],
    'mox-pearl': [Activated('T', AddMana('W'), T_FUNCS['card_owner'])],
    'mox-ruby': [Activated('T', AddMana('R'), T_FUNCS['card_owner'])],
    'mox-sapphire': [Activated('T', AddMana('U'), T_FUNCS['card_owner'])],
    'necropolis': [Activated('', XZeroOneCountersByManaValue(), T_FUNCS['creatures_in_your_graveyard'])],  # TODO: needs an extra cost of "Exile a creature card from your graveyard"
    'nevinyrrals-disk': [Triggered(TapCardEffect(), T_FUNCS['self'], CastResolvedEvent),
                         Activated('1T', True, DestroyAll(T_FUNCS['artifacts_creatures_enchantments_in_play']))],
    'nightmare': [Static(NightmarePT())],
    'northern-paladin': [Activated('WW', Destroy(), T_FUNCS['creatures_and_enchantments_in_play'])],
    'oasis': [Activated('T', PreventNextDamageEffect(1), T_FUNCS['creatures_in_play'])],
    'obelisk-of-undoing': [Activated('6T', Bounce(), T_FUNCS['perms_you_own_and_control'])],
    'old-man-of-the-sea': [Activated('T', Steal(), T_FUNCS['opp_creatures_power_not_greater_than_source']),
                           Triggered(OptionalUntap(), None, UntapPhaseEvent),
                           Triggered(StealCardLeaves(), None, UntapCardEvent)],  # WARNING: doubt this works;
    'onulet': [Triggered(Onulet(), None, DiesEvent)],
    'orcish-artillery': [Activated('T', DealDamageToTargetAndYou(2, 3), T_FUNCS['all_creatures_and_players'])],
    'orcish-oriflamme': [Static(OrcishOriflamme())],
    'osai-vultures': [Triggered(AddCountersIfAnyCreatureDied(CARRION), T_FUNCS['self'], EndStepEvent),
                      Activated('', PumpEffect(1, 1, True),
                                extra_costs=[RemoveCounterCost(CARRION, 2)], text='Remove 2 counters for +1/+1')],
    'paralyze': [Triggered(TapCardEffect(), T_FUNCS['host'], CastResolvedEvent),
                 Triggered(HostStaysTapped(), T_FUNCS['host'], UntapPhaseEvent),
                 untap_host_for_mana_at_opp_upkeep('4')],
    'pendelhaven': [Activated('T', AddMana('G'), T_FUNCS['card_owner']),
                    Activated('T', PumpEffect(1, 2, True), T_FUNCS['one_one_creatures_in_play'])],
    'people-of-the-woods': [Static(PeopleOfTheWoodsPT())],
    'personal-incarnation': [Triggered(PersonalIncarnation(), None, DiesEvent)],
    'pestilence': [Activated('B', DealDamageToAllCreaturesAndPlayers(1)),
                   Triggered(PestilenceEndStep(), None, EndStepEvent)],
    'phantasmal-forces': [Triggered(PayManaOrSac('U'), None, UpkeepEvent)],
    'phantasmal-terrain': [Triggered(PhantasmalTerrain(land_type), T_FUNCS['lands_in_play'], CastResolvedEvent,
                                     text=f'convert to {land_type}')
                           for land_type in {'Swamp', 'Island', 'Forest', 'Mountain', 'Plains'}],
                           # TODO: All 5 of these are getting registered, and I think that's causing problems
    'phyrexian-gremlins': [Triggered(OptionalUntap(), None, UntapPhaseEvent)],
    'piety': [Triggered(Piety(), None, CastResolvedEvent)],
    'pirate-ship': [Activated('T', DealDamage(1), T_FUNCS['all_creatures_and_players'])],
    'pit-scorpion': [Triggered(AddPoisonCounter(), None, DamageResolvedEvent)],
    'pixie-queen': [Activated('GGGT', KWAModEffect('add', 'Flying'), T_FUNCS['creatures_in_play'])],
    'plateau': dual_land_activated_ability_specs('RW'),
    'power-surge': [Triggered(PowerSurge(), None, UpkeepEvent)],
    'pradesh-gypsies': [Activated('1GT', PumpEffect(-2, 0, True), T_FUNCS['creatures_in_play'])],
    'preacher': [Triggered(OptionalUntap(), None, UntapPhaseEvent)],
    'primordial-ooze': [Triggered(AddCountersYourTurnOnly(PLUS_ONE), T_FUNCS['self'], UpkeepEvent)],
    'prodigal-sorcerer': [Activated('T', DealDamage(1), T_FUNCS['all_creatures_and_players'], text="Deal 1 Damage}")],
    'psionic-blast': [Triggered(DealDamageToTargetAndYou(4, 2),
                                T_FUNCS['all_creatures_and_players'], CastResolvedEvent)],
    'psionic-entity': [Activated('T', DealDamageToTargetAndSelf(2, 3), T_FUNCS['all_creatures_and_players'])],
    'psychic-allergy': [Triggered(PsychicAllergyUpkeep(), T_FUNCS['self'], UpkeepEvent)],
    'psychic-venom':
        [Triggered(None, T_FUNCS['lands_in_play'], CastResolvedEvent),
         Triggered(DealDamage(2), T_FUNCS['host_owner']), TapCardEvent],
    'purelace': [Triggered(SetColor('W'), T_FUNCS['cards_in_play'], CastResolvedEvent)],
    'quagmire': [Static(WalkRuleRemoved('Swampwalk'))],
    'rabid-wombat': [Static(RabidWombat())],
    'radjan-spirit': [Activated('T', KWAModEffect('remove', 'Flying', True), T_FUNCS['creatures_in_play'])],
    'raise-dead': [Triggered(Bounce(), T_FUNCS['creatures_in_your_graveyard'], CastResolvedEvent)],
    'rakalite': [Activated('2', Rakalite(), T_FUNCS['all_creatures_and_players'])],
    'reconstruction': [Triggered(Bounce(), T_FUNCS['artifacts_in_your_graveyard'], CastResolvedEvent)],
    'red-mana-battery': [MANA_BATTERY_ADD_CHARGE,
                         Activated('T', ManaBatteriesAddMana('R'), extra_costs=[RemoveCounterCost(CHARGE)],
                                   max_variable_x_func=lambda gs, s: T_FUNCS['self'](gs, s).counters.get_count(CHARGE))],
    'red-ward': [Triggered(KWAModEffect('add', 'Protection From Red'),
                           T_FUNCS['creatures_in_play'], CastResolvedEvent)],
    'regrowth': [Triggered(Bounce(), T_FUNCS['cards_in_your_graveyard'], CastResolvedEvent)],
    'relic-barrier': [Activated('T', TapCardEffect(), T_FUNCS['untapped_artifacts_in_play'])],
    'reset':
        [Triggered(Reset(), None, CastResolvedEvent, conditions=[])],  # TODO: Cast this spell only during an opponent's turn after their upkeep step
    'resurrection': [Triggered(Reanimate(), T_FUNCS['creatures_in_your_graveyard'], CastResolvedEvent)],
    'reverse-damage': [Triggered(ReverseDamage(), T_FUNCS['cards_in_play'], CastResolvedEvent)],
    'riptide': [Triggered(Riptide(), None, CastResolvedEvent)],
    'rock-hydra': [Triggered(RockHydraCast(), T_FUNCS['self'], CastResolvedEvent)],
    'rocket-launcher': [Triggered(RocketLauncherCast(), None, CastResolvedEvent),
                        Activated('2', RocketLauncherAA(), T_FUNCS['all_creatures_and_players'])],
    'rod-of-ruin': [Activated('3T', DealDamage(1), T_FUNCS['all_creatures_and_players'])],
    'royal-assassin': [Activated('T', Destroy(), T_FUNCS['tapped_creatures'])],
    'rukh-egg': [Triggered(RukhEgg(), None, DiesEvent)],
    'sacrifice': [Triggered(SacrificeOnCast(), T_FUNCS['your_creatures_in_play'], CastResolvedEvent)],
    'samite-healer': [Activated('T', PreventNextDamageEffect(1), T_FUNCS['cards_in_play'])],
    'sandals-of-abdallah': [Activated('2', SandalsOfAbdallahIslandWalk(), T_FUNCS['creatures_in_play'])],
    'savaen-elves': [Activated('GGT', Destroy(), T_FUNCS['auras_on_lands'])],
    'savannah': dual_land_activated_ability_specs('GW'),
    'scarecrow': [Activated('6T', ScarecrowPrevention())],
    'scarwood-hag':
        [Activated('GGGGT', KWAModEffect('add', 'Forestwalk', True), T_FUNCS['creatures_in_play_wo_forestwalk']),
         Activated('GGGGT', KWAModEffect('remove', 'Forestwalk', True), T_FUNCS['forestwalkers'])],
    'scavenger-folk': [Activated('GT', Destroy(), T_FUNCS['artifacts_in_play'], extra_costs=[SacSelfCost()])],
    'scavenging-ghoul': [Triggered(AddCounterPerCreatureDeath(CORPSE), T_FUNCS['self'], EndStepEvent)],
    'scrubland': dual_land_activated_ability_specs('BW'),
    'season-of-the-witch':
        [Triggered(SeasonOfTheWitchUpkeep(), None, UpkeepEvent),
         Triggered(SeasonOfTheWitchEndStep(), None, EndStepEvent)],
    'seeker': [Static(Seeker())],
    'serendib-djinn':
        [Triggered(SerendibDjinn(), None, UpkeepEvent), Triggered(SerendibDjinnNoLands(), None, StateBasedEvent)],
    'serendib-efreet': [Triggered(DealDamageOnSourceTurn(1), None, UpkeepEvent)],
    'shapeshifter': [Triggered(Shapeshifter(), None, CastResolvedEvent), Triggered(Shapeshifter(), None, UpkeepEvent)],
    'shatter': [Triggered(Destroy(), T_FUNCS['artifacts_in_play'], CastResolvedEvent)],
    'shield-wall': [Triggered(ShieldWall(), None, CastResolvedEvent)],
    'shivan-dragon': [Activated('R', PumpEffect(1, 0, True), T_FUNCS['self'])],
    'sinkhole': [Triggered(Destroy(), T_FUNCS['lands_in_play'], CastResolvedEvent)],
    'sisters-of-the-flame': [Activated('T', AddMana('R'), T_FUNCS['card_owner'])],
    'skull-of-orm': [Activated('5T', Bounce(), T_FUNCS['enchants_in_your_graveyard'])],
    'sol-ring': [Activated('T', AddMana('C', 2), T_FUNCS['card_owner'])],
    'soul-net': [Triggered(SoulNet(), None, DiesEvent)],
    'spinal-villain': [Activated('T', Destroy(), T_FUNCS['blue_creatures_in_play'])],
    'spirit-link': [Triggered(None, T_FUNCS['creatures_in_play'], CastResolvedEvent),
                    Triggered(SpiritLink(), None, DamageResolvedEvent)],
    'spirit-shackle': [Triggered(AddCounterToHost(MINUS_ZERO_TWO), T_FUNCS['host'], TapCardEvent)],
    'spiritual-sanctuary': [Triggered(SpiritualSanctuary(), None, UpkeepEvent)],
    'staff-of-zegon': [Activated('3T', PumpEffect(-2, 0, True), T_FUNCS['creatures_in_play'])],
    'standing-stones': [Activated('1T', AddMana(c), text=f'Add {{{c}}}', extra_costs=PayLifeCost())
                        for c in COLOR_LETTERS],
    'steal-artifact': [Triggered(Steal(), T_FUNCS['opp_artifacts_in_play'], CastResolvedEvent),
                       Triggered(StealCardLeaves(), None, ZoneChangeEvent)],
    'stone-giant': [Activated('T', StoneGiant(), T_FUNCS['stone_giant'])],
    'stone-rain': [Triggered(Destroy(), T_FUNCS['lands_in_play'], CastResolvedEvent)],
    'storm-seeker': [Triggered(StormSeeker(), T_FUNCS['all_players'], CastResolvedEvent)],
    'storm-world': [Triggered(StormWorld(), None, UpkeepEvent)],
    'stream-of-life': [Triggered(StreamOfLife(), T_FUNCS['all_players'], CastResolvedEvent)],
    'strip-mine': [Activated('T', AddMana('C'), T_FUNCS['card_owner']),
                   Activated('T', Destroy(), T_FUNCS['lands_in_play'], extra_costs=[SacSelfCost()])],
    'subdue': [Triggered(Subdue(), T_FUNCS['creatures_in_play'], CastResolvedEvent)],
    'su-chi': [Triggered(SuChi(), None, DiesEvent)],
    'sunken-city': [Static(SunkenCity()), Triggered(PayManaOrSac('UU'), None, UpkeepEvent)],
    'sword-to-plowshares': [Triggered(SwordsToPlowshares(), T_FUNCS['creatures_in_play'], CastResolvedEvent)],
    'syphon-soul': [Triggered(SyphonSoul(), T_FUNCS['opponent'], CastResolvedEvent)],
    'tablet-of-epityr': [Triggered(TabletOfEpityr(), None, DiesEvent)],
    'taiga': dual_land_activated_ability_specs('RG'),
    'tawnoss-coffin': [Triggered(OptionalUntap(), None, UntapPhaseEvent)],
    'tawnoss-wand': [Activated('2T', UnblockableThisTurn(), T_FUNCS['creatures_power_two_or_less'])],
    'tawnoss-weaponry': [Triggered(OptionalUntap(), None, UntapPhaseEvent)],
    'teleport': [Triggered(UnblockableThisTurn(), T_FUNCS['creatures_in_play'], CastResolvedEvent,
                           allowed_phases=[Phase.DECLARE_COMBAT])],
    'tetravus': [Triggered(AddCountersYourTurnOnly(PLUS_ONE, 3), T_FUNCS['self'], CastResolvedEvent)],
    'the-hive': [Activated('5T', CreateTokenCreature('Wasp', 1, 1, ['Flying', 'Attack'], ['Artifact'], [], 'C'))],
    'the-rack': [Triggered(TheRack(), None, UpkeepEvent)],
    'the-tabernacle-at-pendrell-vale': [Triggered(TheTabernacleAtPendrellVale(), None, UpkeepEvent)],
    'thoughtlace': [Triggered(SetColor('U'), T_FUNCS['cards_in_play'], CastResolvedEvent)],
    'throne-of-bone': [Static(OnColorSpellPayOneColorlessForOneLifeChoice('B'))],
    'time-vault':
        [Triggered(TapCardEffect(), T_FUNCS['self'], CastResolvedEvent),
         Triggered(StaysTapped(), T_FUNCS['self'], UntapPhaseEvent)],
    'timetwister': [Triggered(Timetwister(), None, CastResolvedEvent)],
    'tivadars-crusade':
        [Triggered(DestroyAll(lambda gs, s: gs.card_filter.in_play().by_sub_type('Goblin').result()),
                   None, CastResolvedEvent)],
    'tormods-crypt':
        [Activated('T', GraveyardToExileInItsEntirety(), T_FUNCS['all_players'], extra_costs=[SacSelfCost()])],
    'tower-of-coireall': [Activated('T', TowerOfCoireall(), T_FUNCS['creatures_in_play'])],
    'tranquility':
        [Triggered(DestroyAll(lambda gs, s: gs.card_filter.in_play().by_type('Enchantment').result()),
                   None, CastResolvedEvent)],
    'triskelion': [Triggered(AddCountersYourTurnOnly(PLUS_ONE, 3), T_FUNCS['self'], CastResolvedEvent),
                   Activated('', DealDamage(1), T_FUNCS['all_creatures_and_players'],
                             extra_costs=[RemoveCounterCost(PLUS_ONE)])],
    'tropical-island': dual_land_activated_ability_specs('GU'),
    'tsunami':
        [Triggered(DestroyAll(lambda gs, s: gs.card_filter.in_play().islands().result()),
                   None, CastResolvedEvent)],
    'tundra': dual_land_activated_ability_specs('WU'),
    'twiddle': [Triggered(Twiddle(), T_FUNCS['artifacts_creatures_lands_in_play'], CastResolvedEvent)],
    'typhoon': [Triggered(Typhoon(), T_FUNCS['opponent'], CastResolvedEvent)],
    'uncle-istvan': [Static(UncleIstvanPrevention())],
    'undertow': [Static(WalkRuleRemoved('Islandwalk'))],
    'underground-sea': dual_land_activated_ability_specs('BU'),
    'unholy-strength': [Triggered(PumpEffect(2, 1), T_FUNCS['creatures_in_play'], CastResolvedEvent)],
    'unstable-mutation':
        [Triggered(PumpEffect(3, 3), T_FUNCS['creatures_in_play'], CastResolvedEvent),
         Triggered(AddCountersOnHostTurn(MINUS_ONE), T_FUNCS['self'], UpkeepEvent)],
    'unsummon': [Triggered(Bounce(), T_FUNCS['creatures_in_play'], CastResolvedEvent)],
    'urzas-chalice': [Static(OnColorSpellPayOneColorlessForOneLifeChoice('C'))],  # not sure if 'C' is ever in props.colors
    'urzas-mine': [Activated('T', UrzasTrio())],
    'urzas-miter': [Triggered(UrzasMiter(), None, DiesEvent)],
    'urzas-power-plant': [Activated('T', UrzasTrio())],
    'urzas-tower': [Activated('T', UrzasTrio())],
    'vampire-bats': [Activated('B', PumpEffect(1, 0, True), T_FUNCS['self'], max_activations_per_turn=2)],
    'venarian-gold':
        [Triggered(RemoveCountersOnHostTurn(SLEEP), T_FUNCS['your_creatures_in_play'], UpkeepEvent),
         Triggered(VenarianGoldHostStaysTapped(), None, UntapPhaseEvent)],
    'verduran-enchantress': [Static(VerduranEnchantress())],
    'volcanic-island': dual_land_activated_ability_specs('RU'),
    'voodoo-doll':
        [Triggered(AddCountersYourTurnOnly(PIN), T_FUNCS['self'], UpkeepEvent),
         Triggered(VoodooDollEndStep(), None, EndStepEvent),
         Activated('XXT', DealDamage(), T_FUNCS['all_creatures_and_players'],
                   min_x=lambda gs, s: T_FUNCS['self'](gs, s).counters.get_count(PIN)//2,
                   max_variable_x_func=lambda gs, s: T_FUNCS['self'](gs, s).counters.get_count(PIN)//2)],
    'wall-of-opposition': [Activated('1', PumpEffect(1, 0, True), T_FUNCS['self'])],
    'wall-of-tombstones': [Static(WallOfTombstonesPT())],
    'wall-of-water': [Activated('U', PumpEffect(1, 0, True), T_FUNCS['self'])],
    'wanderlust': [Triggered(None, T_FUNCS['creatures_in_play'], CastResolvedEvent),
                   Triggered(DealDamageOnTargetTurn(1), T_FUNCS['host_owner'], UpkeepEvent)],
    'warp-artifact': [Triggered(DealDamageOnTargetTurn(1), T_FUNCS['artifacts_in_play'], UpkeepEvent)],
    'water-wurm': [Static(WaterWurmPT())],
    'weakness': [Triggered(PumpEffect(-2, -1), T_FUNCS['creatures_in_play'], CastResolvedEvent)],
    'weakstone': [Static(Weakstone())],
    'web': [Triggered(Web(), T_FUNCS['creatures_in_play'], CastResolvedEvent)],
    'wheel-of-fortune': [Triggered(WheelOfFortune(), None, CastResolvedEvent)],
    'white-mana-battery': [MANA_BATTERY_ADD_CHARGE,
                           Activated('T', ManaBatteriesAddMana('W'), extra_costs=[RemoveCounterCost(CHARGE)],
                                     max_variable_x_func=lambda gs, s: T_FUNCS['self'](gs, s).counters.get_count(CHARGE))],
                           # TODO: the x_value isn't making it to .resolve(); might be true of all specs w max_var_x_fun
    'white-ward': [Triggered(KWAModEffect('add', 'Protection From White'),
                             T_FUNCS['creatures_in_play'], CastResolvedEvent)],
    'winds-of-change': [Triggered(WindsOfChange(), None, CastResolvedEvent)],
    'witch-hunter': [Activated('T', DealDamage(1), T_FUNCS['all_players']),
                     Activated('1WWT', Bounce(), T_FUNCS['opp_creatures_in_play'])],
    'wooden-sphere': [Static(OnColorSpellPayOneColorlessForOneLifeChoice('G'))],
    'wormwood-treefolk': [Activated('GG', WormwoodTreefolkForestwalk()),
                          Activated('BB', WormwoodTreefolkSwampwalk())],
    'wrath-of-god': [Triggered(ExileAllCreatures(), None, CastResolvedEvent)],
    'wyuli-wolf': [Activated('T', PumpEffect(1, 1, True), T_FUNCS['creatures_in_play'])],
}
