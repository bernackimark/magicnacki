from __future__ import annotations
from itertools import combinations

from .card_filter_funcs import T_FUNCS
from models.constants import COLOR_LETTERS
from models.cost import SacSelfCost, RemoveCounterCost, DiscardAtRandomCost, SacCardCost
from models.counter_tokens import PLUS_ONE_ZERO, PLUS_ONE, CHARGE
from models.effects.base import EffSpec, Activated, Triggered, Static, TargetSpec, Spell
from ..effects.resolvers_a_to_e import BarlsCage, Disharmony, CityOfShadowsAA1, CityOfShadowsAA2, CocoonCast, Banshee, \
    Earthquake, EternalFlame, EyeForAnEye, AshesToAshes, DustToDust, EaterOfTheDead, BazaarOfBaghdad, Braingeyser, \
    DemonicTutor, Clone, CopyArtifact, EvilPresence, DrainPower, EnergyTap, ArmyOfAllah, Berserk, BloodLust, \
    BoneFlute, AshnodsTransmogrant, ActiveVolcano, Amnesia, AnimateDead, BookOfRass, BottleOfSuleiman, ChaosOrb, \
    Crumble, DivineOffering, Earthbind, ElectricEel, ElvesOfTheDeepShadow, ArenaOfTheAncientsCast, EnchantmentAlteration
from models.effects.resolvers_generic import UnblockableThisTurn, AddCounter, \
    ManaBatteriesAddMana, \
    DealDamage, DealDamageToTargetAndYou, PreventAllCombatDamageThisTurn, Destroy, DestroyAll, \
    Regenerate, SacAll, DrawCards, Discard, SetColor, KWAModEffect, GainLife, AddMana, Bounce, Steal, \
    Pump, CreateTokenCreature, RemoveHostAuras, TapCardEffect, UntapCardEffect, UntapCardsEffect, \
    PreventNextDamageToSourceOwner, PreventNextDamageBy, RemoveFromCombat
from .effect_spec_helpers import dual_land_activated_ability_specs, MANA_BATTERY_ADD_CHARGE, \
    untap_for_mana_at_owner_upkeep
from ..effects.listeners_card_specific import DragonWhelpEndStep, ErgRaiders, AliFromCairo, Blight, \
    CityOfBrassDamageOnTap, BlackVise, \
    CosmicHorror, CurseArtifact, Cyclone, DemonicHordesUpkeep, ElderSpawnUpkeep, EnergyFlux, ErhnamDjinn, \
    ErosionUpkeep, AnkhOfMishra, CitanulDruid, DingusEgg, DropOfHoney, CocoonUntap, CocoonUpkeep, CityInABottle
from ..effects.listeners_draw_discard import CursedRackEffect
from ..effects.listeners_dies import AbuJafar, AxelrodGunnarson, CreatureBond, CyclopeanMummy
from ..effects.listeners_damage import ArgothianPixies, ArgothianTreefolkPrevention, ArtifactWardPrevention, \
    Backfire, ElHajjaj
from ..effects.listeners_combat import CavePeopleAttackPump, Abomination, \
    CockatriceAndThicketBasilisk, ElderLandWurm, AislingLeprechaun, Arboria, ClockworkCombatEnd
from ..effects.listeners_generic import OnColorSpellPayOneColorlessForOneLifeChoice, \
    UntapRemovesPumpFromAnotherCard, CardsDontUntapAtUntapPhase, OptionalUntap, \
    DealDamageOnHostUpkeep, ReturnToOwnerOnLTB, PreventCombatDamageFromEnchantedCreatures, PayManaOrSacAtUpkeep, \
    DestroyAtEndStep, DealDamageOnEveryUpkeep
from models.effects.listeners_permission import AmrouKithkin, ArgothianPixiesCanBeBlocked, ArtifactWardCanBeBlocked, \
    BogRats, ElderSpawnCanBeBlocked, ElvenRidersCanBeBlocked, EvilEyeOfOrmsByGoreCanBeBlocked, CityInABottleCantCast, \
    ArtifactWardCanBeTargeted, AkronLegionnaire, EvilEyeOfOrmsByGoreMyNonEyeNoAttack, CantBeTargetedByAuras, \
    HostCantBeTargetedByAuras, HostCantAttack, WalkRuleRemoved, DampingField, DoesntUntapAtUntap
from models.effects.listeners_mod_queries import AddCreatureTypePTManaValue, AngelicVoices, AngryMobPT, \
    ArcadesSabbathAllCreaturePump, AspectOfWolfPT, BadMoon, BeastsOfBogardan, ConcordantCrossroads, Conversion, \
    Crusade, DakkonBlackbladePT, Castle
from models.phase_manager import Phase

MAP: dict[str, list[EffSpec]] = {
    'abomination': [Triggered(Abomination())],
    'abu-jafar': [Triggered(AbuJafar())],
    'acid-rain': [Spell(DestroyAll(T_FUNCS['forests']))],
    'active-volcano': [Spell(ActiveVolcano(), T_FUNCS['active_volcano_targets'])],
    'adun-oakenshield': [Activated('BRGT', Bounce(), T_FUNCS['creatures_in_your_graveyard'])],
    'aisling-leprechaun': [Triggered(AislingLeprechaun())],
    'akron-legionnaire': [Static(AkronLegionnaire())],
    'aladdin': [Activated('1RRT', Steal(), T_FUNCS['opp_artifacts']), Triggered(ReturnToOwnerOnLTB())],
    'aladdins-ring': [Activated('8T', DealDamage(4), T_FUNCS['all_creatures_and_players'])],
    'ali-baba': [Activated('R', TapCardEffect(), T_FUNCS['walls'])],
    'ali-from-cairo': [Static(AliFromCairo())],
    'alchors-tomb': [Activated('2T', SetColor(c), T_FUNCS['your_permanents'], text=f'Set color to {{{c}}}')
                     for c in COLOR_LETTERS],
    'amnesia': [Spell(Amnesia(), T_FUNCS['all_players'])],
    'amrou-kithkin': [Static(AmrouKithkin())],
    'amulet-of-kroog': [Activated('2T', PreventNextDamageBy(1), T_FUNCS['all_creatures_and_players'])],
    'ancestral-recall': [Spell(DrawCards(3), T_FUNCS['all_players'])],
    'angelic-voices': [Static(AngelicVoices())],
    'angus-mackenzie': [Activated('GWUT', PreventAllCombatDamageThisTurn(),
                                  allowed_phases=[p for p in Phase if p < Phase.COMBAT_DAMAGE])],
    'angry-mob': [Static(AngryMobPT())],
    'animate-artifact': [Spell(None, T_FUNCS['non_creature_artifacts']), Static(AddCreatureTypePTManaValue())],
    'animate-dead': [Spell(AnimateDead(), T_FUNCS['creatures_in_your_graveyard'])],
    'animate-wall': [Spell(KWAModEffect('remove', 'Defender'), T_FUNCS['walls'])],
    'ankh-of-mishra': [Triggered(AnkhOfMishra())],
    'anti-magic-aura': [Spell(RemoveHostAuras(), T_FUNCS['creatures']),
                        Static(HostCantBeTargetedByAuras())],
    'apprentice-wizard': [Activated('UT', AddMana('C', 3), T_FUNCS['card_owner'])],
    'arboria': [Static(Arboria())],
    'arcades-sabboth': [Triggered(PayManaOrSacAtUpkeep('GWU')), Static(ArcadesSabbathAllCreaturePump()),
                        Activated('W', Pump(0, 1, True), T_FUNCS['self'])],
    'arena-of-the-ancients': [Spell(ArenaOfTheAncientsCast()),
                              Triggered(CardsDontUntapAtUntapPhase(T_FUNCS['legendary_creatures']))],
    'argivian-archaeologist': [Activated('WWT', Bounce(), T_FUNCS['artifacts_in_your_graveyard'])],
    'argivian-blacksmith': [Activated('T', PreventNextDamageBy(2), T_FUNCS['artifact_creatures'])],
    'argothian-pixies': [Static(ArgothianPixiesCanBeBlocked()), Static(ArgothianPixies())],
    'argothian-treefolk': [Static(ArgothianTreefolkPrevention())],
    'armageddon': [Spell(DestroyAll(lambda gs, s: gs.card_filter.in_play().by_type('Land').result()))],
    'army-of-allah': [Spell(ArmyOfAllah())],
    'artifact-ward': [Spell(None, T_FUNCS['creatures']), Static(ArtifactWardCanBeBlocked()),
                      Static(ArtifactWardPrevention()), Static(ArtifactWardCanBeTargeted())],
    'ashes-to-ashes': [Spell(AshesToAshes(), TargetSpec(T_FUNCS['non_artifact_creatures'], 2, 2))],
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
    'ball-lightning': [Triggered(DestroyAtEndStep(T_FUNCS['self']))],
    'banshee': [Activated('XT', Banshee(), T_FUNCS['all_creatures_and_players'],
                          max_x_func=lambda gs, s: gs.mana_pools[s.owner_id].get_max_x('X'))],
    'barls-cage': [Activated('3', BarlsCage(), T_FUNCS['creatures'])],
    'bartel-runeaxe': [Static(CantBeTargetedByAuras())],
    'basalt-monolith': [Triggered(DoesntUntapAtUntap()),
                        Activated('T', AddMana('C', 3)), Activated('3', UntapCardEffect(), T_FUNCS['self'])],
    'bayou': dual_land_activated_ability_specs('BG'),
    'bazaar-of-baghdad': [Activated('2T', BazaarOfBaghdad(), text='Draw 2 cards; discard 3 cards')],
    'beasts-of-bogardan': [Static(BeastsOfBogardan())],
    'berserk': [Triggered(Berserk(), T_FUNCS['creatures'])],
    'birds-of-paradise': [Activated('T', AddMana(c), text=f'Add {{{c}}}') for c in COLOR_LETTERS],
    'black-lotus': [Activated('T', AddMana(c, 3), extra_costs=[SacSelfCost], text=f'Add {{3{c}}}')
                    for c in COLOR_LETTERS],
    'black-mana-battery': [MANA_BATTERY_ADD_CHARGE,
                           Activated('T', ManaBatteriesAddMana('B'), extra_costs=[RemoveCounterCost(CHARGE)],
                                     max_x_func=lambda gs, s: T_FUNCS['self'](gs, s).counters.get_count(CHARGE))],
    'black-vise': [Triggered(BlackVise())],
    'black-ward': [Spell(KWAModEffect('add', 'Protection From Black'), T_FUNCS['creatures'])],
    'blessing': [Activated('W', Pump(1, 1, True), T_FUNCS['host'])],
    'blight': [Spell(None, T_FUNCS['lands']), Triggered(Blight())],
    'blood-lust': [Spell(BloodLust(), T_FUNCS['creatures'])],
    'blue-mana-battery': [MANA_BATTERY_ADD_CHARGE,
                          Activated('T', ManaBatteriesAddMana('U'), extra_costs=[RemoveCounterCost(CHARGE)],
                                    max_x_func=lambda gs, s: T_FUNCS['self'](gs, s).counters.get_count(CHARGE))],
    'blue-ward': [Spell(KWAModEffect('add', 'Protection From Blue'), T_FUNCS['creatures'])],
    'bog-rats': [Static(BogRats())],
    'bone-flute': [Activated('2T', BoneFlute())],
    'book-of-rass': [Activated('2', BookOfRass())],
    'boomerang': [Spell(Bounce(), T_FUNCS['permanents'])],
    'boris-devilboon': [Activated('2BRTT', CreateTokenCreature('minor-demon'))],
    'bottle-of-suleiman': [Activated('1', BottleOfSuleiman(), extra_costs=[SacSelfCost()])],
    'braingeyser': [Spell(Braingeyser(), T_FUNCS['all_players'])],
    'brainwash':
        # WARNING: the AA would generally be activated by the opponent normally placed on an opponent creature
        [Spell(None, T_FUNCS['creatures']), Static(HostCantAttack()),
         Activated('3', KWAModEffect('add', 'Attack', True), T_FUNCS['host'])],
    'brass-man': [Triggered(DoesntUntapAtUntap()), untap_for_mana_at_owner_upkeep('1', T_FUNCS['card_owner'])],
    'brothers-of-fire': [Activated('T', DealDamageToTargetAndYou(1, 1), T_FUNCS['all_creatures_and_players'])],
    'burrowing': [Spell(KWAModEffect('add', 'Mountainwalk'), T_FUNCS['creatures'])],
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
    'chaoslace': [Spell(SetColor('R'), T_FUNCS['cards'])],
    'chromium': [Triggered(PayManaOrSacAtUpkeep('WUB'))],
    'circle-of-protection-artifacts': [Activated('1', PreventNextDamageToSourceOwner(), T_FUNCS['artifacts'])],
    'circle-of-protection-black': [Activated('1', PreventNextDamageToSourceOwner(), T_FUNCS['black'])],
    'circle-of-protection-blue': [Activated('1', PreventNextDamageToSourceOwner(), T_FUNCS['blue'])],
    'circle-of-protection-green': [Activated('1', PreventNextDamageToSourceOwner(), T_FUNCS['green'])],
    'circle-of-protection-red': [Activated('1', PreventNextDamageToSourceOwner(), T_FUNCS['red'])],
    'circle-of-protection-white': [Activated('1', PreventNextDamageToSourceOwner(), T_FUNCS['white'])],
    'citanul-druid': [Triggered(CitanulDruid())],
    'city-in-a-bottle': [Spell(SacAll(T_FUNCS['city_in_a_bottle'])),
                         Static(CityInABottle()), Static(CityInABottleCantCast())],
    'city-of-brass': [Activated('T', AddMana(c), text=f'Add {{{c}}}') for c in COLOR_LETTERS] +
                     [Triggered(CityOfBrassDamageOnTap())],
    'city-of-shadows':
        [Activated('T', CityOfShadowsAA1()), Activated('T', CityOfShadowsAA2())],
        # TODO: needs a way to find a creature to exile in extra_costs
    'clay-statue': [Activated('2', Regenerate(), T_FUNCS['self'])],
    'cleanse': [Spell(DestroyAll(T_FUNCS['black_creatures']))],
    'clockwork-avian': [Static(ClockworkCombatEnd()),
                        Activated('XT', AddCounter(PLUS_ONE_ZERO), None, allowed_phases=[Phase.UPKEEP],
                                  allowed_p_id_turn=T_FUNCS['card_owner'],
                                  max_x_func=lambda gs, s: 4 - s.counters.get_count(PLUS_ONE_ZERO)),
                        Spell(AddCounter(PLUS_ONE_ZERO, 4))],
    'clockwork-beast': [Static(ClockworkCombatEnd()),
                        Activated('XT', AddCounter(PLUS_ONE_ZERO), None, allowed_phases=[Phase.UPKEEP],
                                  allowed_p_id_turn=T_FUNCS['card_owner'],
                                  max_x_func=lambda gs, s: 7 - s.counters.get_count(PLUS_ONE_ZERO)),
                        Spell(AddCounter(PLUS_ONE_ZERO, 7)),],
    'clone': [Spell(Clone())],
    'coal-golem': [Activated('3', AddMana('R', 3), T_FUNCS['card_owner'], extra_costs=[SacSelfCost()])],
    'cockatrice': [Triggered(CockatriceAndThicketBasilisk())],
    'cocoon': [Spell(CocoonCast(), T_FUNCS['your_creatures']), Static(CocoonUntap()), Static(CocoonUpkeep())],
    'colossus-of-sardia': [Triggered(DoesntUntapAtUntap()), untap_for_mana_at_owner_upkeep('9', T_FUNCS['card_owner'])],
    'concordant-crossroads': [Static(ConcordantCrossroads())],
    'consecrate-land': [Spell(None, T_FUNCS['lands']), Static(HostCantBeTargetedByAuras())],
    'conservator': [Activated('3T', PreventNextDamageToSourceOwner(2))],
    'control-magic': [Spell(Steal(), T_FUNCS['opp_creatures']), Triggered(ReturnToOwnerOnLTB())],
    'conversion': [Triggered(PayManaOrSacAtUpkeep('WW')), Static(Conversion())],
    'copper-tablet': [Static(DealDamageOnEveryUpkeep(T_FUNCS['in_turn_player'], 1))],
    'copy-artifact': [Spell(CopyArtifact())],
    'coral-helm': [Activated('3', Pump(2, 2, True), T_FUNCS['creatures'],
                             extra_costs=[DiscardAtRandomCost()])],
    'cosmic-horror': [Static(CosmicHorror())],
    'crevasse': [Static(WalkRuleRemoved('Mountainwalk'))],
    'creature-bond': [Triggered(CreatureBond())],
    'crimson-manticore': [Activated('RT', DealDamage(1), T_FUNCS['combatants'])],
    'crumble': [Spell(Crumble(), T_FUNCS['artifacts'])],
    'crusade': [Static(Crusade())],
    'crystal-rod': [Static(OnColorSpellPayOneColorlessForOneLifeChoice('U'))],
    'curse-artifact': [Spell(None, T_FUNCS['artifacts']),
                       Triggered(CurseArtifact(), T_FUNCS['self'])],
    'cursed-land': [Spell(None, T_FUNCS['lands']), Triggered(DealDamageOnHostUpkeep(1))],
    'cursed-rack': [Triggered(CursedRackEffect())],
    'cyclone': [Triggered(Cyclone())],
    'cyclopean-mummy': [Triggered(CyclopeanMummy())],
    'dakkon-blackblade': [Static(DakkonBlackbladePT())],
    'damping-field': [Triggered(DampingField())],
    'dance-of-many': [Triggered(PayManaOrSacAtUpkeep('UU'))],  # the rest of the card still needs coding
    'dark-heart-of-the-wood': [Activated('', GainLife(3), extra_costs=[SacCardCost(T_FUNCS['your_forests'])])],
    'dark-ritual': [Spell(AddMana('B', 3))],
    'dark-sphere': [Activated('T', PreventNextDamageToSourceOwner(), T_FUNCS['artifacts'],
                              extra_costs=[SacSelfCost()])],
    'darkness': [Spell(PreventAllCombatDamageThisTurn())],
    'davenant-archer': [Activated('T', DealDamage(1), T_FUNCS['combatants'])],
    'deadfall': [Static(WalkRuleRemoved('Forestwalk'))],
    'deathlace': [Spell(SetColor('B'), T_FUNCS['cards'])],
    'death-ward': [Spell(Regenerate(), T_FUNCS['creatures'])],
    'demonic-hordes': [Activated('T', Destroy(), T_FUNCS['lands']), Triggered(DemonicHordesUpkeep())],
    'demonic-torment': [Spell(None, T_FUNCS['creatures']), Static(HostCantAttack())],
    'demonic-tutor': [Spell(DemonicTutor())],
    'desert': [Activated('T', AddMana('C')),
               Activated('T', DealDamage(1), T_FUNCS['attackers'], allowed_phases=[Phase.COMBAT_END])],
    'desert-twister': [Spell(Destroy(), T_FUNCS['permanents'])],
    'diabolic-machine': [Activated('3', Regenerate(), T_FUNCS['self'])],
    'dingus-egg': [Triggered(DingusEgg())],
    'disharmony': [Spell(Disharmony(), T_FUNCS['attackers'],
                         allowed_phases=[Phase.DECLARE_COMBAT, Phase.DECLARE_ATTACKERS])],
    'disrupting-scepter': [Activated('3T', Discard(), T_FUNCS['all_players'],
                                     allowed_p_id_turn=0)],  # TODO: p_id_turn needs a solution
    'disenchant': [Spell(Destroy(), T_FUNCS['artifacts_and_enchantments'])],
    'divine-offering': [Spell(DivineOffering(), T_FUNCS['artifacts'])],
    'divine-transformation': [Spell(Pump(3, 3), T_FUNCS['creatures'])],
    'dragon-engine': [Activated('2', Pump(1, 0, True), T_FUNCS['self'])],
    'dragon-whelp': [Activated('R', Pump(1, 0, True)), Triggered(DragonWhelpEndStep())],
    'drain-power': [Spell(DrainPower(), T_FUNCS['opponent'])],
    'dream-coat': [Spell(None, T_FUNCS['creatures'])] +
                  [Activated('', SetColor(''.join(combo)), T_FUNCS['host'], max_activations_per_turn=1,
                             text=f'{{{combo}}}')
                   for r in range(1, len(COLOR_LETTERS) + 1) for combo in combinations(COLOR_LETTERS, r)],
                  # TODO: max_activations_per_turn wasn't respected, assuming it's broke for all
    'drop-of-honey': [Triggered(DropOfHoney())],
    'drowned': [Activated('B', Regenerate(), T_FUNCS['self'])],
    'drudge-skeletons': [Activated('B', Regenerate(), T_FUNCS['self'])],
    'dust-to-dust': [Spell(DustToDust(), TargetSpec(T_FUNCS['artifacts'], 2, 2))],
    'dwarven-demolition-team': [Activated('T', Destroy(), T_FUNCS['walls'])],
    'dwarven-song': [Spell(SetColor('R', 'EOT'), TargetSpec(T_FUNCS['creatures'], 1, None))],
    'dwarven-warriors': [Activated('T', UnblockableThisTurn(), T_FUNCS['creatures_power_two_or_less'])],
    'dwarven-weaponsmith': [Activated('T', AddCounter(PLUS_ONE), T_FUNCS['creatures'],
                                      extra_costs=[SacCardCost(T_FUNCS['your_artifacts'])],
                                      allowed_phases=[Phase.UPKEEP], allowed_p_id_turn=T_FUNCS['card_owner'])],
                    # TODO: all allowed_p_id_turn needs a better solution
    'earthbind': [Spell(Earthbind(), T_FUNCS['creatures'])],
    'earthquake': [Spell(Earthquake())],
    'eater-of-the-dead': [Activated('', EaterOfTheDead(), T_FUNCS['creatures_in_all_graveyards'])],
    'ebony-horse': [Activated('2T', RemoveFromCombat(), T_FUNCS['attackers'])],
    'el-hajjâj': [Triggered(ElHajjaj(), T_FUNCS['self'])],
    'elder-land-wurm': [Triggered(ElderLandWurm())],
    'elder-spawn': [Triggered(ElderSpawnUpkeep()), Static(ElderSpawnCanBeBlocked())],
    'electric-eel': [Spell(DealDamage(1), T_FUNCS['card_owner']), Activated('RR', ElectricEel())],
    'elephant-graveyard': [Activated('T', AddMana('C')), Activated('T', Regenerate(), T_FUNCS['elephants'])],
    'elven-riders': [Static(ElvenRidersCanBeBlocked())],
    'elves-of-deep-shadow': [Activated('T', ElvesOfTheDeepShadow())],
    'emerald-dragonfly': [Activated('GG', KWAModEffect('add', 'First Strike', True), T_FUNCS['self'])],
    'enchanted-being': [Triggered(PreventCombatDamageFromEnchantedCreatures(), T_FUNCS['self'])],
    'enchantment-alteration': [Spell(EnchantmentAlteration(), T_FUNCS['auras_on_creatures_or_lands'])],
    'energy-flux': [Triggered(EnergyFlux())],
    'energy-tap': [Spell(EnergyTap(), T_FUNCS['your_untapped_creatures'])],
    'erg-raiders': [Triggered(ErgRaiders())],
    'erhnam-djinn': [Triggered(ErhnamDjinn(), T_FUNCS['opp_non_wall_creatures'])],
    'erosion': [Spell(None, T_FUNCS['lands']), Triggered(ErosionUpkeep())],
    'eternal-flame': [Spell(EternalFlame())],
    'eternal-warrior': [Spell(KWAModEffect('add', 'Vigilance'), T_FUNCS['creatures'])],
    'evil-eye-of-orms-by-gore': [Static(EvilEyeOfOrmsByGoreCanBeBlocked()),
                                 Static(EvilEyeOfOrmsByGoreMyNonEyeNoAttack())],
    'evil-presence': [Spell(EvilPresence(), T_FUNCS['lands'])],
    'exorcist': [Activated('1W', Destroy(), T_FUNCS['black_creatures'])],
    'eye-for-an-eye': [Spell(EyeForAnEye(), T_FUNCS['cards'])],
}
