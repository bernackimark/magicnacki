from __future__ import annotations
from itertools import combinations

from .card_filter_funcs import T_FUNCS
from models.constants import COLOR_LETTERS
from models.cost import SacSelfCost, RemoveCounterCost, DiscardAtRandomCost, SacCardCost
from models.counter_tokens import PLUS_ONE_ZERO, PLUS_ONE, CHARGE
from models.effects.base import EffSpec, Activated, Triggered, Static, TargetSpec
from ..effects.resolvers_a_to_e import BarlsCage, Disharmony, CityOfShadowsAA1, CityOfShadowsAA2, CocoonCast, Banshee, \
    Earthquake, EternalFlame, EyeForAnEye, AshesToAshes, DustToDust, EaterOfTheDead, BazaarOfBaghdad, Braingeyser, \
    DemonicTutor, Clone, CopyArtifact, EvilPresence, DrainPower, EnergyTap, ArmyOfAllah, BerserkPump, BloodLust, \
    BoneFlute, AshnodsTransmogrant, ActiveVolcano, Amnesia, AnimateDead, BookOfRass, BottleOfSuleiman, ChaosOrb, \
    CocoonUpkeep, Crumble, DivineOffering, Earthbind, ElectricEel, ElvesOfTheDeepShadow, ArenaOfTheAncientsCast, \
    CocoonHostStaysTapped
from models.effects.resolvers_generic import UnblockableThisTurn, AddCounter, \
    ManaBatteriesAddMana, RemovePlusOneZeroFromCombatant, AddCountersYourTurnOnly, \
    DealDamage, DealDamageToTargetAndYou, PreventAllCombatDamageThisTurn, Destroy, DestroyAll, DestroyIfItAttacked, \
    PayManaOrSac, Regenerate, SacAll, DrawCards, Discard, SetColor, KWAModEffect, GainLife, AddMana, Bounce, Steal, \
    Pump, CreateTokenCreature, RemoveHostAuras, TapCardEffect, UntapCardEffect, UntapCardsEffect, \
    StaysTapped, PreventNextDamageToSourceOwner, PreventNextDamageBy, RemoveFromCombat
from .effect_spec_helpers import dual_land_activated_ability_specs, MANA_BATTERY_ADD_CHARGE, \
    untap_for_mana_at_owner_upkeep, is_tapped
from ..effects.listeners_card_specific import DragonWhelpEndStep, ErgRaiders, AliFromCairo, Blight, \
    CityOfBrassDamageOnTap, BlackVise, \
    CosmicHorror, CurseArtifact, Cyclone, DemonicHordesUpkeep, ElderSpawnUpkeep, EnergyFlux, ErhnamDjinn, \
    ErosionUpkeep, AnkhOfMishra, CitanulDruid, DingusEgg, DropOfHoney
from ..effects.listeners_draw_discard import CursedRackEffect
from ..effects.listeners_dies import AbuJafar, AxelrodGunnarson, CreatureBond, CyclopeanMummy
from ..effects.listeners_damage import ArgothianPixies, ArgothianTreefolkPrevention, ArtifactWardPrevention, \
    Backfire, ElHajjaj
from ..effects.listeners_combat import CavePeopleAttackPump, Abomination, \
    CockatriceAndThicketBasilisk, ElderLandWurm, AislingLeprechaun, Arboria
from ..effects.listeners_generic import OnColorSpellPayOneColorlessForOneLifeChoice, \
    UntapRemovesPumpFromAnotherCard, CardsDontUntapAtUntapPhase, OptionalUntap, \
    DealDamageOnHostUpkeep, ReturnToOwnerOnLTB, PreventCombatDamageFromEnchantedCreatures
from models.effects.listeners_permission import AmrouKithkin, ArgothianPixiesCanBeBlocked, ArtifactWardCanBeBlocked, \
    BogRats, ElderSpawnCanBeBlocked, ElvenRidersCanBeBlocked, EvilEyeOfOrmsByGoreCanBeBlocked, CityInABottle, \
    ArtifactWardCanBeTargeted, AkronLegionnaire, EvilEyeOfOrmsByGoreMyNonEyeNoAttack, CantBeTargetedByAuras, \
    HostCantBeTargetedByAuras, HostCantAttack, WalkRuleRemoved, DampingField
from models.effects.listeners_mod_queries import AddCreatureTypePTManaValue, AngelicVoices, AngryMobPT, \
    ArcadesSabbathAllCreaturePump, AspectOfWolfPT, BadMoon, BeastsOfBogardan, ConcordantCrossroads, Conversion, \
    Crusade, DakkonBlackbladePT, Castle
from models.events_all import CastResolvedEvent, UntapPhaseEvent, EndStepEvent, CombatEndEvent, UpkeepEvent, \
    DamageResolvedEvent, TapCardEvent, DiesEvent, ZoneChangeEvent, BlockEvent, AttackEvent, DamageProposedEvent, \
    CanUntapQueryEvent
from models.phase_manager import Phase

MAP: dict[str, list[EffSpec]] = {
    'abomination': [Triggered(Abomination())],
    'abu-jafar': [Triggered(AbuJafar())],
    'acid-rain': [Triggered(DestroyAll(T_FUNCS['forests']), None, CastResolvedEvent)],
    'active-volcano': [Triggered(ActiveVolcano(), T_FUNCS['active_volcano_targets'], CastResolvedEvent)],
    'adun-oakenshield': [Activated('BRGT', Bounce(), T_FUNCS['creatures_in_your_graveyard'])],
    'aisling-leprechaun': [Triggered(AislingLeprechaun())],
    'akron-legionnaire': [Static(AkronLegionnaire())],
    'aladdin': [Activated('1RRT', Steal(), T_FUNCS['opp_artifacts']), Triggered(ReturnToOwnerOnLTB())],
    'aladdins-ring': [Activated('T', DealDamage(4), T_FUNCS['all_creatures_and_players'])],
    'ali-baba': [Activated('R', TapCardEffect(), T_FUNCS['walls'])],
    'ali-from-cairo': [Static(AliFromCairo())],
    'alchors-tomb': [Activated('2T', SetColor(c), T_FUNCS['your_permanents'], text=f'Set color to {{{c}}}')
                     for c in COLOR_LETTERS],
    'amnesia': [Triggered(Amnesia(), T_FUNCS['all_players'], CastResolvedEvent)],
    'amrou-kithkin': [Static(AmrouKithkin())],
    'amulet-of-kroog': [Activated('2T', PreventNextDamageBy(1), T_FUNCS['all_creatures_and_players'])],
    'ancestral-recall': [Triggered(DrawCards(3), T_FUNCS['all_players'], CastResolvedEvent)],
    'angelic-voices': [Static(AngelicVoices())],
    'angus-mackenzie': [Activated('GWUT', PreventAllCombatDamageThisTurn(),
                                  allowed_phases=[p for p in Phase if p < Phase.COMBAT_DAMAGE])],
    'angry-mob': [Static(AngryMobPT())],
    'animate-artifact': [Triggered(None, T_FUNCS['non_creature_artifacts'], CastResolvedEvent),
                         Static(AddCreatureTypePTManaValue())],
    'animate-dead': [Triggered(AnimateDead(), T_FUNCS['creatures_in_your_graveyard'], CastResolvedEvent)],
    'animate-wall':
        [Triggered(KWAModEffect('remove', 'Defender'), T_FUNCS['walls'], CastResolvedEvent)],
    'ankh-of-mishra': [Triggered(AnkhOfMishra())],
    'anti-magic-aura': [Triggered(RemoveHostAuras(), T_FUNCS['creatures'], CastResolvedEvent),
                        Static(HostCantBeTargetedByAuras())],
    'apprentice-wizard': [Activated('UT', AddMana('C', 3), T_FUNCS['card_owner'])],
    'arboria': [Static(Arboria())],
    'arcades-sabboth': [Triggered(PayManaOrSac('GWU'), None, UpkeepEvent), Static(ArcadesSabbathAllCreaturePump()),
                        Activated('W', Pump(0, 1, True), T_FUNCS['self'])],
    'arena-of-the-ancients': [Triggered(ArenaOfTheAncientsCast(), None, CastResolvedEvent),
                              Triggered(CardsDontUntapAtUntapPhase(T_FUNCS['legendary_creatures']))],
    'argivian-archaeologist': [Activated('WWT', Bounce(), T_FUNCS['artifacts_in_your_graveyard'])],
    'argivian-blacksmith': [Activated('T', PreventNextDamageBy(2), T_FUNCS['artifact_creatures'])],
    'argothian-pixies': [Static(ArgothianPixiesCanBeBlocked()), Static(ArgothianPixies())],
    'argothian-treefolk': [Static(ArgothianTreefolkPrevention())],
    'armageddon': [Triggered(DestroyAll(lambda gs, s: gs.card_filter.in_play().by_type('Land').result()),
                   None, CastResolvedEvent)],
    'army-of-allah': [Triggered(ArmyOfAllah(), None, CastResolvedEvent)],
    'artifact-ward': [Triggered(None, T_FUNCS['creatures'], CastResolvedEvent), Static(ArtifactWardCanBeBlocked()),
                      Static(ArtifactWardPrevention()), Static(ArtifactWardCanBeTargeted())],
    'ashes-to-ashes': [Triggered(AshesToAshes(), TargetSpec(T_FUNCS['non_artifact_creatures'], 2, 2),
                                 CastResolvedEvent)],
    'ashnods-altar': [Activated('', AddMana('C', 2), extra_costs=[SacCardCost(T_FUNCS['your_creatures'])])],
    'ashnods-battle-gear': [Activated('2T', Pump(2, -2), T_FUNCS['your_creatures']),
                            Triggered(OptionalUntap()), Triggered(UntapRemovesPumpFromAnotherCard())],
    'ashnods-transmogrant': [Activated('T', AshnodsTransmogrant(), T_FUNCS['non_artifact_creatures'],
                                       extra_costs=[SacSelfCost()])],
    'aspect-of-wolf': [Static(AspectOfWolfPT())],
    'axelrod-gunnarson': [Triggered(AxelrodGunnarson())],
    'backfire': [Triggered(Backfire())],
    'bad-moon': [Static(BadMoon())],
    'badlands': dual_land_activated_ability_specs('BR'),
    'ball-lightning': [Triggered(Destroy(), T_FUNCS['self'], EndStepEvent)],
    'banshee': [Activated('XT', Banshee(), T_FUNCS['all_creatures_and_players'],
                          max_x_func=lambda gs, s: gs.mana_pools[s.owner_id].get_max_x('X'))],
    'barls-cage': [Activated('3', BarlsCage(), T_FUNCS['creatures'])],
    'bartel-runeaxe': [Static(CantBeTargetedByAuras())],
    'basalt-monolith': [Triggered(StaysTapped(), T_FUNCS['self'], UntapPhaseEvent),
                        Activated('T', AddMana('C', 3)), Activated('3', UntapCardEffect(), T_FUNCS['self'])],
    'bayou': dual_land_activated_ability_specs('BG'),
    'bazaar-of-baghdad': [Activated('2T', BazaarOfBaghdad(), text='Draw 2 cards; discard 3 cards')],
    'beasts-of-bogardan': [Static(BeastsOfBogardan())],
    'berserk': [Triggered(BerserkPump(), T_FUNCS['creatures'], CastResolvedEvent,
                          allowed_phases=[p for p in Phase if p < Phase.COMBAT_DAMAGE]),
                Triggered(DestroyIfItAttacked(), T_FUNCS['creatures'], EndStepEvent)],
    # warning: I don't think this target func is correct; it needs to know the target previously selected
    'birds-of-paradise': [Activated('T', AddMana(c), text=f'Add {{{c}}}') for c in COLOR_LETTERS],
    'black-lotus': [Activated('T', AddMana(c, 3), extra_costs=[SacSelfCost], text=f'Add {{3{c}}}')
                    for c in COLOR_LETTERS],
    'black-mana-battery': [MANA_BATTERY_ADD_CHARGE,
                           Activated('T', ManaBatteriesAddMana('B'), extra_costs=[RemoveCounterCost(CHARGE)],
                                     max_x_func=lambda gs, s:
                                     T_FUNCS['self'](gs, s).counters.get_count(CHARGE))],
    'black-vise': [Triggered(BlackVise())],
    'black-ward': [Triggered(KWAModEffect('add', 'Protection From Black'),
                             T_FUNCS['creatures'], CastResolvedEvent)],
    'blessing': [Activated('W', Pump(1, 1, True), T_FUNCS['host'])],
    'blight': [Triggered(None, T_FUNCS['lands'], CastResolvedEvent), Triggered(Blight())],
    'blood-lust': [Triggered(BloodLust(), T_FUNCS['creatures'], CastResolvedEvent)],
    'blue-mana-battery': [MANA_BATTERY_ADD_CHARGE,
                          Activated('T', ManaBatteriesAddMana('U'), extra_costs=[RemoveCounterCost(CHARGE)],
                                    max_x_func=lambda gs, s: T_FUNCS['self'](gs, s).counters.get_count(CHARGE))],
    'blue-ward': [Triggered(KWAModEffect('add', 'Protection From Blue'), T_FUNCS['creatures'], CastResolvedEvent)],
    'bog-rats': [Static(BogRats())],
    'bone-flute': [Activated('2T', BoneFlute())],
    'book-of-rass': [Activated('2', BookOfRass())],
    'boomerang': [Triggered(Bounce(), T_FUNCS['permanents'], CastResolvedEvent)],
    'boris-devilboon': [Activated('2BRTT', CreateTokenCreature('minor-demon'))],
    'bottle-of-suleiman': [Activated('1', BottleOfSuleiman(), extra_costs=[SacSelfCost()])],
    'braingeyser': [Triggered(Braingeyser(), T_FUNCS['all_players'], CastResolvedEvent)],
    'brainwash':
        # WARNING: the AA would generally be activated by the opponent normally placed on an opponent creature
        [Triggered(None, T_FUNCS['creatures'], CastResolvedEvent), Static(HostCantAttack()),
         Activated('3', KWAModEffect('add', 'Attack', True), T_FUNCS['host'])],
    'brass-man': [Triggered(StaysTapped(), T_FUNCS['self'], UntapPhaseEvent), untap_for_mana_at_owner_upkeep('1')],
    'brothers-of-fire': [Activated('T', DealDamageToTargetAndYou(1, 1), T_FUNCS['all_creatures_and_players'])],
    'burrowing':
        [Triggered(KWAModEffect('add', 'Mountainwalk'), T_FUNCS['creatures'], CastResolvedEvent)],
    'candelabra-of-tawnos': [Activated('XT', UntapCardsEffect(), TargetSpec(T_FUNCS['tapped_lands'], 1, None),
                                       max_x_func=lambda gs, s: gs.mana_pools[s.owner_id].get_max_x('X'))],
    # TODO: if candelabra's owner has 0 mana, the effect should be offered, but it's putting game in infinite loop
    'carrion-ants': [Activated('1', Pump(1, 1, True), T_FUNCS['self'])],
    'castle': [Static(Castle())],
    'cave-people': [Triggered(CavePeopleAttackPump(), T_FUNCS['self']),
                    Activated('1RRT', KWAModEffect('add', 'Mountainwalk', True), T_FUNCS['creatures'])],
    'celestial-prism': [Activated('2T', AddMana(c), T_FUNCS['card_owner'], text=f'Add 1 {c}') for c in COLOR_LETTERS],
    'chaos-orb': [Activated('1T', ChaosOrb(), T_FUNCS['opp_non_token_perms'], extra_costs=[SacSelfCost()],
                            text='If random di roll is 1-4, destroy target')],
    'chaoslace': [Triggered(SetColor('R'), T_FUNCS['cards'], CastResolvedEvent)],
    'chromium': [Triggered(PayManaOrSac('WUB'), None, UpkeepEvent)],
    'circle-of-protection-artifacts': [Activated('1', PreventNextDamageToSourceOwner(), T_FUNCS['artifacts'])],
    'circle-of-protection-black': [Activated('1', PreventNextDamageToSourceOwner(), T_FUNCS['black'])],
    'circle-of-protection-blue': [Activated('1', PreventNextDamageToSourceOwner(), T_FUNCS['blue'])],
    'circle-of-protection-green': [Activated('1', PreventNextDamageToSourceOwner(), T_FUNCS['green'])],
    'circle-of-protection-red': [Activated('1', PreventNextDamageToSourceOwner(), T_FUNCS['red'])],
    'circle-of-protection-white': [Activated('1', PreventNextDamageToSourceOwner(), T_FUNCS['white'])],
    'citanul-druid': [Triggered(CitanulDruid())],
    'city-in-a-bottle': [Triggered(SacAll(T_FUNCS['city_in_a_bottle']), None, CastResolvedEvent),
                         Triggered(SacAll(T_FUNCS['city_in_a_bottle']), None, ZoneChangeEvent),
                         Static(CityInABottle())],
    'city-of-brass': [Activated('T', AddMana(c), text=f'Add {{{c}}}') for c in COLOR_LETTERS] +
                     [Triggered(CityOfBrassDamageOnTap())],
    'city-of-shadows':
        [Activated('T', CityOfShadowsAA1()), Activated('T', CityOfShadowsAA2())],
        # TODO: needs a way to find a creature to exile in extra_costs
    'clay-statue': [Activated('2', Regenerate(), T_FUNCS['self'])],
    'cleanse': [Triggered(DestroyAll(T_FUNCS['black_creatures']), None, CastResolvedEvent)],
    'clockwork-avian':
        [Triggered(RemovePlusOneZeroFromCombatant(), T_FUNCS['self'], CombatEndEvent),
         Triggered(AddCounter(PLUS_ONE_ZERO, 4), None, CastResolvedEvent),
         Activated('XT', AddCountersYourTurnOnly(PLUS_ONE_ZERO), None, UpkeepEvent,
                   max_x_func=lambda gs, s: 4 - s.counters.get_count(PLUS_ONE_ZERO))],
    'clockwork-beast':
        [Triggered(RemovePlusOneZeroFromCombatant(), T_FUNCS['self'], CombatEndEvent),
         Triggered(AddCounter(PLUS_ONE_ZERO, 7), None, CastResolvedEvent),
         Activated('XT', AddCountersYourTurnOnly(PLUS_ONE_ZERO), None, UpkeepEvent,
                   max_x_func=lambda gs, s: 7 - s.counters.get_count(PLUS_ONE_ZERO))],
    'clone': [Triggered(Clone(), None, CastResolvedEvent)],
    'coal-golem': [Activated('3', AddMana('R', 3), T_FUNCS['card_owner'], extra_costs=[SacSelfCost()])],
    'cockatrice': [Triggered(CockatriceAndThicketBasilisk())],
    'cocoon':
        [Triggered(CocoonCast(), T_FUNCS['your_creatures'], CastResolvedEvent),
         Triggered(CocoonHostStaysTapped(), None, UntapPhaseEvent),
         Triggered(CocoonUpkeep(), None, UpkeepEvent)],
    'colossus-of-sardia': [Triggered(StaysTapped(), T_FUNCS['self'], UntapPhaseEvent),
                           untap_for_mana_at_owner_upkeep('9')],
    'concordant-crossroads': [Static(ConcordantCrossroads())],
    'consecrate-land': [Triggered(None, T_FUNCS['lands'], CastResolvedEvent),
                        Static(HostCantBeTargetedByAuras())],
    'conservator': [Activated('3T', PreventNextDamageToSourceOwner(2))],
    'control-magic': [Triggered(Steal(), T_FUNCS['opp_creatures'], CastResolvedEvent), Triggered(ReturnToOwnerOnLTB())],
    'conversion': [Triggered(PayManaOrSac('WW'), None, UpkeepEvent), Static(Conversion())],
    'copper-tablet': [Triggered(DealDamage(1), T_FUNCS['in_turn_player'], UpkeepEvent)],
    'copy-artifact': [Triggered(CopyArtifact(), None, CastResolvedEvent)],
    'coral-helm': [Activated('3', Pump(2, 2, True), T_FUNCS['creatures'],
                             extra_costs=[DiscardAtRandomCost()])],
    'cosmic-horror': [Triggered(CosmicHorror(), T_FUNCS['self'], UpkeepEvent)],
    'crevasse': [Static(WalkRuleRemoved('Mountainwalk'))],
    'creature-bond': [Triggered(CreatureBond())],
    'crimson-manticore': [Activated('RT', DealDamage(1), T_FUNCS['combatants'])],
    'crumble': [Triggered(Crumble(), T_FUNCS['artifacts'], CastResolvedEvent)],
    'crusade': [Static(Crusade())],
    'crystal-rod': [Static(OnColorSpellPayOneColorlessForOneLifeChoice('U'))],
    'curse-artifact': [Triggered(None, T_FUNCS['artifacts'], CastResolvedEvent),
                       Triggered(CurseArtifact(), T_FUNCS['self'])],
    'cursed-land': [Triggered(None, T_FUNCS['lands'], CastResolvedEvent), Triggered(DealDamageOnHostUpkeep(1))],
    'cursed-rack': [Triggered(CursedRackEffect())],
    'cyclone': [Triggered(Cyclone())],
    'cyclopean-mummy': [Triggered(CyclopeanMummy())],
    'dakkon-blackblade': [Static(DakkonBlackbladePT())],
    'damping-field': [Triggered(DampingField())],
    'dance-of-many': [Triggered(PayManaOrSac('UU'), None, UpkeepEvent)],  # the rest of the card still needs coding
    'dark-heart-of-the-wood': [Activated('', GainLife(3), extra_costs=[SacCardCost(T_FUNCS['your_forests'])])],
    'dark-ritual': [Triggered(AddMana('B', 3), None, CastResolvedEvent)],
    'dark-sphere': [Activated('T', PreventNextDamageToSourceOwner(), T_FUNCS['artifacts'],
                              extra_costs=[SacSelfCost()])],
    'darkness': [Triggered(PreventAllCombatDamageThisTurn(), None, CastResolvedEvent)],
    'davenant-archer': [Activated('T', DealDamage(1), T_FUNCS['combatants'])],
    'deadfall': [Static(WalkRuleRemoved('Forestwalk'))],
    'deathlace': [Triggered(SetColor('B'), T_FUNCS['cards'], CastResolvedEvent)],
    'death-ward': [Triggered(Regenerate(), T_FUNCS['creatures'], CastResolvedEvent)],
    'demonic-hordes': [Activated('T', Destroy(), T_FUNCS['lands']), Triggered(DemonicHordesUpkeep())],
    'demonic-torment': [Triggered(None, T_FUNCS['creatures'], CastResolvedEvent), Static(HostCantAttack())],
    'demonic-tutor': [Triggered(DemonicTutor(), None, CastResolvedEvent)],
    'desert': [Activated('T', AddMana('C')),
               Activated('T', DealDamage(1), T_FUNCS['attackers'], allowed_phases=[Phase.COMBAT_END])],
    'desert-twister': [Triggered(Destroy(), T_FUNCS['permanents'], CastResolvedEvent)],
    'diabolic-machine': [Activated('3', Regenerate(), T_FUNCS['self'])],
    'dingus-egg': [Triggered(DingusEgg())],
    'disharmony': [Triggered(Disharmony(), T_FUNCS['attackers'], CastResolvedEvent,
                             allowed_phases=[Phase.DECLARE_COMBAT, Phase.DECLARE_ATTACKERS])],
    'disrupting-scepter': [Activated('3T', Discard(), T_FUNCS['all_players'],
                                     allowed_p_id_turn=0)],  # TODO: p_id_turn needs a solution
    'disenchant':
        [Triggered(Destroy(), T_FUNCS['artifacts_and_enchantments'], CastResolvedEvent)],
    'divine-offering': [Triggered(DivineOffering(), T_FUNCS['artifacts'], CastResolvedEvent)],
    'divine-transformation':
        [Triggered(Pump(3, 3), T_FUNCS['creatures'], CastResolvedEvent)],
    'dragon-engine': [Activated('2', Pump(1, 0, True), T_FUNCS['self'])],
    'dragon-whelp': [Activated('R', Pump(1, 0, True)), Triggered(DragonWhelpEndStep(), None, EndStepEvent)],
    'drain-power': [Triggered(DrainPower(), T_FUNCS['opponent'], CastResolvedEvent)],
    'dream-coat': [Triggered(None, T_FUNCS['creatures'], CastResolvedEvent)] +
                  [Activated('', SetColor(''.join(combo)), T_FUNCS['host'], max_activations_per_turn=1,
                             text=f'{{{combo}}}')
                   for r in range(1, len(COLOR_LETTERS) + 1) for combo in combinations(COLOR_LETTERS, r)],
                  # TODO: max_activations_per_turn wasn't respected, assuming it's broke for all
    'drop-of-honey': [Triggered(DropOfHoney())],
    'drowned': [Activated('B', Regenerate(), T_FUNCS['self'])],
    'drudge-skeletons': [Activated('B', Regenerate(), T_FUNCS['self'])],
    'dust-to-dust': [Triggered(DustToDust(), TargetSpec(T_FUNCS['artifacts'], 2, 2), CastResolvedEvent)],
    'dwarven-demolition-team': [Activated('T', Destroy(), T_FUNCS['walls'])],
    'dwarven-song': [Triggered(SetColor('R', 'EOT'), TargetSpec(T_FUNCS['creatures'], 1, None),
                               CastResolvedEvent)],
    'dwarven-warriors': [Activated('T', UnblockableThisTurn(), T_FUNCS['creatures_power_two_or_less'])],
    'dwarven-weaponsmith': [Activated('T', AddCounter(PLUS_ONE), T_FUNCS['creatures'],
                                      extra_costs=[SacCardCost(T_FUNCS['your_artifacts'])],
                                      allowed_phases=[Phase.UPKEEP], allowed_p_id_turn=T_FUNCS['card_owner'])],
                    # TODO: all allowed_p_id_turn needs a better solution
    'earthbind': [Triggered(Earthbind(), T_FUNCS['creatures'], CastResolvedEvent)],
    'earthquake': [Triggered(Earthquake(), None, CastResolvedEvent)],
    'eater-of-the-dead':
        [Activated('', EaterOfTheDead(), T_FUNCS['creatures_in_all_graveyards'], conditions=[is_tapped])],
    'ebony-horse': [Activated('2T', RemoveFromCombat(), T_FUNCS['attackers'])],
    'el-hajjâj': [Triggered(ElHajjaj(), T_FUNCS['self'])],
    'elder-land-wurm': [Triggered(ElderLandWurm())],
    'elder-spawn': [Triggered(ElderSpawnUpkeep()), Static(ElderSpawnCanBeBlocked())],
    'electric-eel': [Triggered(DealDamage(1), T_FUNCS['card_owner'], CastResolvedEvent),
                     Activated('RR', ElectricEel())],
    'elephant-graveyard': [Activated('T', AddMana('C')), Activated('T', Regenerate(), T_FUNCS['elephants'])],
    'elven-riders': [Static(ElvenRidersCanBeBlocked())],
    'elves-of-deep-shadow': [Activated('T', ElvesOfTheDeepShadow())],
    'emerald-dragonfly': [Activated('GG', KWAModEffect('add', 'First Strike', True), T_FUNCS['self'])],
    'enchanted-being': [Triggered(PreventCombatDamageFromEnchantedCreatures(), T_FUNCS['self'])],
    'energy-flux': [Triggered(EnergyFlux())],
    'energy-tap': [Triggered(EnergyTap(), T_FUNCS['your_untapped_creatures'], CastResolvedEvent)],
    'erg-raiders': [Triggered(ErgRaiders())],
    'erhnam-djinn': [Triggered(ErhnamDjinn(), T_FUNCS['opp_non_wall_creatures'])],
    'erosion': [Triggered(None, T_FUNCS['lands'], CastResolvedEvent), Triggered(ErosionUpkeep())],
    'eternal-flame': [Triggered(EternalFlame(), None, CastResolvedEvent)],
    'eternal-warrior': [Triggered(KWAModEffect('add', 'Vigilance'), T_FUNCS['creatures'], CastResolvedEvent)],
    'evil-eye-of-orms-by-gore': [Static(EvilEyeOfOrmsByGoreCanBeBlocked()),
                                 Static(EvilEyeOfOrmsByGoreMyNonEyeNoAttack())],
    'evil-presence': [Triggered(EvilPresence(), T_FUNCS['lands'], CastResolvedEvent)],
    'exorcist': [Activated('1W', Destroy(), T_FUNCS['black_creatures'])],
    'eye-for-an-eye': [Triggered(EyeForAnEye(), T_FUNCS['cards'], CastResolvedEvent)],
}
