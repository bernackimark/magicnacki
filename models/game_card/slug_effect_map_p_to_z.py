from __future__ import annotations

from .effect_spec_helpers import dual_land_activated_ability_specs, untap_host_for_mana_at_opp_upkeep, \
    has_ge_x_counters, MANA_BATTERY_ADD_CHARGE
from .card_filter_funcs import T_FUNCS
from models.constants import COLOR_LETTERS
from models.cost import SacSelfCost, PayLifeCost, RemoveCounterCost, SacCardCost
from models.counter_tokens import PLUS_ONE, CORPSE, MINUS_ONE, SLEEP, PIN, CHARGE, DREAM, HATCHLING
from models.effects.base import EffSpec, Activated, Triggered, Static, TargetSpec
from models.effects.resolvers_card_specific import TowerOfCoireall, RockHydraCast, Sandstorm, StormSeeker, Tracker, \
    Typhoon, RagMan, Visions, WheelOfFortune, PhantasmalTerrain, PrimalClay, \
    VesuvanDoppelgangerCast, RapidFire, SandalsOfAbdallahIslandWalk, UrborgLoseFirstStrike, UrborgLoseSwampwalk, \
    StreamOfLife, UrzasTrio, TimeElementalBounce, SyphonSoul, \
    TriassicEgg, Piety, ShieldWall, SingingTree, Transmutation, Rakalite, ReverseDamage, RocketLauncherCast, \
    RocketLauncherAA, SacrificeOnCast, SerendibDjinn, Shapeshifter, StoneGiant, Subdue, SwordsToPlowshares, \
    Timetwister, UrzasAvengerFlying, UrzasAvengerFirstStrike, UrzasAvengerTrample, WallOfWonder, WandOfIth, Web, \
    WindsOfChange, WinterBlast, WormwoodTreefolkForestwalk, WormwoodTreefolkSwampwalk, Reset, Riptide, Twiddle, \
    VenarianGoldHostStaysTapped, Scarecrow, ReversePolarity, Simulacrum, Telekinesis, TangleKelp, WoodElemental, \
    SafeHaven, UntamedWilds
from models.effects.resolvers_generic import UnblockableThisTurn, AddCounter, AddCountersOnHostTurn, \
    ManaBatteriesAddMana, RemoveCountersOnHostTurn, AddCountersYourTurnOnly, AddCounterPerCreatureDeath, DealDamage, \
    DealOneDamageToTargetList, DealDamageToAllCreaturesAndPlayers, DealDamageToTargetAndSelf, \
    DealDamageToTargetAndYou, PreventNextDamageBy, TakeAnotherTurn, \
    PreventNextDamageToCardEffect, Destroy, DestroyAll, ExileAllCreatures, PayManaOrSac, Regenerate, DrawCards, \
    SetColor, KWAModEffect, AddMana, Bounce, Reanimate, Steal, GraveyardToExileInItsEntirety, Pump, \
    CreateTokenCreature, TapCardEffect, TapCardsEffect, UntapCardEffect, HostStaysTapped, StaysTapped, DeclareAColor
from ..effects.listeners_card_specific import PestilenceEndStep, SeasonOfTheWitchEndStep, \
    VoodooDollEndStep, SerendibDjinnNoLands, PsychicVenom, SpiritShackle, WildGrowth, PowerSurge, \
    PsychicAllergySac, RogahhOfKherKeepUpkeep, SeasonOfTheWitchUpkeep, SpiritualSanctuary, StormWorld, TheAbyss, \
    TheRack, TheTabernacleAtPendrellVale, VesuvanDoppelgangerUpkeep, YawgmothDemon, Revelation, StanggOnLeave, \
    VerduranEnchantress, TheWretchedUnsteal, WhirlingDervish, TimeVaultOption, TheFallen, PsychicAllergyDamage, \
    RasputinDreamweaverUntap, RasputinDreamweaverUpkeep, SafeHavenUpkeep, TawnossCoffinUntap, TawnossCoffinZoneChange
from ..effects.listeners_draw_discard import PsychicPurgeDiscard
from ..effects.listeners_dies import PersonalIncarnation, RukhEgg, SengirVampire, SuChi, SoulNet, TabletOfEpityr, \
    UrzasMiter
from ..effects.listeners_damage import RockHydraAutoDamagePrevent, UncleIstvanPrevention, \
    VeteranBodyguard, SpiritLink
from ..effects.listeners_cost import PlanarGate, PowerArtifact, StoneCalendar
from ..effects.listeners_combat import CockatriceAndThicketBasilisk, Sentinel, Venom, \
    WallOfDust, YdwenEfreet, TimeElementalAttackedOrBlocked, TheWretchedSteal
from ..effects.listeners_generic import OnColorSpellGainLife, OnColorSpellPayOneColorlessForOneLifeChoice, \
    AddPoisonCounter, ReturnToOwnerOnUntap, UntapRemovesPumpFromAnotherCard, OptionalUntap, \
    DealDamageToOwnerOnUpkeep, DealDamageOnHostUpkeep, ReturnToOwnerOnLTB, PreventCombatDamageFromEnchantedCreatures, \
    PreventNextDamageToCardEOT, PreventCombatDamageFromItsAttackers
from models.effects.listeners_permission import Seeker, SirensCallCanCast, CantBeTargetedByAuras, SpectralCloak, \
    WalkRuleRemoved, Smoke, WinterOrb
from models.effects.listeners_mod_queries import PeopleOfTheWoodsPT, RabidWombat, RohgahhOfKherKeepPump, SedgeTrollPT, \
    SunkenCity, WallOfTombstonesPT, WaterWurmPT, Weakstone, ZombieMasterWalk
from models.events_all import CastResolvedEvent, UntapPhaseEvent, EndStepEvent, CombatEndEvent, UpkeepEvent, \
    DamageResolvedEvent, TapCardEvent, UntapCardEvent, StateBasedEvent, DiesEvent, ZoneChangeEvent, \
    BlockEvent, DiscardEvent, DamageProposedEvent, CanUntapQueryEvent
from models.phase_manager import Phase

MAP: dict[str, list[EffSpec]] = {
    'palladia-mors': [Triggered(PayManaOrSac('RGW'), None, UpkeepEvent)],
    'paralyze': [Triggered(TapCardEffect(), T_FUNCS['host'], CastResolvedEvent),
                 Triggered(HostStaysTapped(), T_FUNCS['host'], UntapPhaseEvent),
                 untap_host_for_mana_at_opp_upkeep('4')],
    'part-water': [Triggered(KWAModEffect('add', 'Islandwalk', True), T_FUNCS['creatures'], CastResolvedEvent,
                   max_x_func=lambda gs, s: gs.mana_pools[s.owner_id].get_max_x('XU') // 2)],
    'pavel-maliki': [Activated('BR', Pump(1, 0, True), T_FUNCS['self'])],
    'pendelhaven': [Activated('T', AddMana('G'), T_FUNCS['card_owner']),
                    Activated('T', Pump(1, 2, True), T_FUNCS['one_one_creatures'])],
    'people-of-the-woods': [Static(PeopleOfTheWoodsPT())],
    'personal-incarnation': [Triggered(PersonalIncarnation(), None, DiesEvent)],  # more to code
    'pestilence': [Activated('B', DealDamageToAllCreaturesAndPlayers(1)),
                   Triggered(PestilenceEndStep(), None, EndStepEvent)],
    'phantasmal-forces': [Triggered(PayManaOrSac('U'), None, UpkeepEvent)],
    'phantasmal-terrain': [Triggered(PhantasmalTerrain(land_type), T_FUNCS['lands'], CastResolvedEvent,
                                     text=f'convert to {land_type}')
                           for land_type in {'Swamp', 'Island', 'Forest', 'Mountain', 'Plains'}],
                           # TODO: All 5 of these are getting registered, and I think that's causing problems
    'phyrexian-gremlins': [Triggered(OptionalUntap(), None, UntapPhaseEvent)],  # more to code
    'piety': [Triggered(Piety(), None, CastResolvedEvent)],
    'pirate-ship': [Activated('T', DealDamage(1), T_FUNCS['all_creatures_and_players'])],
    'pit-scorpion': [Triggered(AddPoisonCounter(), None, DamageResolvedEvent)],
    'pixie-queen': [Activated('GGGT', KWAModEffect('add', 'Flying'), T_FUNCS['creatures'])],
    'planar-gate': [Static(PlanarGate())],
    'plateau': dual_land_activated_ability_specs('RW'),
    'power-artifact': [Triggered(None, T_FUNCS['artifacts'], CastResolvedEvent), Static(PowerArtifact())],
    'power-surge': [Triggered(PowerSurge(), None, UpkeepEvent)],
    'pradesh-gypsies': [Activated('1GT', Pump(-2, 0, True), T_FUNCS['creatures'])],
    'preacher': [Activated('T', Steal(), T_FUNCS['opp_creatures']),
                 Triggered(OptionalUntap(), None, UntapPhaseEvent),
                 Triggered(ReturnToOwnerOnUntap(), None, UntapCardEvent)],
    'primal-clay': [Triggered(PrimalClay(), None, CastResolvedEvent)],
    'primordial-ooze': [Triggered(AddCountersYourTurnOnly(PLUS_ONE), T_FUNCS['self'], UpkeepEvent)],  # more to code
    'princess-lucrezia': [Activated('T', AddMana('U'))],
    'prodigal-sorcerer': [Activated('T', DealDamage(1), T_FUNCS['all_creatures_and_players'], text="Deal 1 Damage}")],
    'psionic-blast': [Triggered(DealDamageToTargetAndYou(4, 2),
                                T_FUNCS['all_creatures_and_players'], CastResolvedEvent)],
    'psionic-entity': [Activated('T', DealDamageToTargetAndSelf(2, 3), T_FUNCS['all_creatures_and_players'])],
    'psychic-allergy': [Triggered(PsychicAllergySac(), T_FUNCS['self'], UpkeepEvent),
                        Triggered(PsychicAllergyDamage(), None, UpkeepEvent),
                        Triggered(DeclareAColor(), None, CastResolvedEvent)],
    'psychic-purge': [Triggered(DealDamage(1), T_FUNCS['all_creatures_and_players'], CastResolvedEvent),
                      Triggered(PsychicPurgeDiscard(), None, DiscardEvent)],
    'psychic-venom':
        [Triggered(None, T_FUNCS['lands'], CastResolvedEvent), Triggered(PsychicVenom(), None, TapCardEvent)],
    'purelace': [Triggered(SetColor('W'), T_FUNCS['cards'], CastResolvedEvent)],
    'pyrotechnics': [Triggered(DealOneDamageToTargetList(),
                               TargetSpec(T_FUNCS['all_creatures_and_players'], 1, 4,
                                          allow_duplicate_targets=True), CastResolvedEvent)],
    'quagmire': [Static(WalkRuleRemoved('Swampwalk'))],
    'rabid-wombat': [Static(RabidWombat())],
    'radjan-spirit': [Activated('T', KWAModEffect('remove', 'Flying', True), T_FUNCS['creatures'])],
    'rag-man': [Activated('BBBT', RagMan(), T_FUNCS['opponent'], allowed_p_id_turn=T_FUNCS['card_owner'])],
    'ragnar': [Activated('GWUT', Regenerate(), T_FUNCS['creatures'])],
    'raise-dead': [Triggered(Bounce(), T_FUNCS['creatures_in_your_graveyard'], CastResolvedEvent)],
    'rakalite': [Activated('2', Rakalite(), T_FUNCS['all_creatures_and_players'])],
    'ramses-overdark': [Activated('T', Destroy(), T_FUNCS['enchanted_creatures'])],
    'rapid-fire': [Triggered(RapidFire(), T_FUNCS['creatures'], CastResolvedEvent,
                             allowed_phases=[p for p in Phase if p < Phase.DECLARE_BLOCKERS])],
    'rasputin-dreamweaver': [Activated('', AddMana('C'), extra_costs=[RemoveCounterCost(DREAM)]),
                             Activated('', PreventNextDamageToCardEffect(1), T_FUNCS['self'],
                                       extra_costs=[RemoveCounterCost(DREAM)]),
                             Triggered(RasputinDreamweaverUntap(), None, UntapPhaseEvent),
                             Triggered(RasputinDreamweaverUpkeep(), None, UpkeepEvent),
                             Triggered(AddCounter(DREAM, 7), None, CastResolvedEvent)],  # more to code
    'reconstruction': [Triggered(Bounce(), T_FUNCS['artifacts_in_your_graveyard'], CastResolvedEvent)],
    'red-mana-battery': [MANA_BATTERY_ADD_CHARGE,
                         Activated('T', ManaBatteriesAddMana('R'), extra_costs=[RemoveCounterCost(CHARGE)],
                                   max_x_func=lambda gs, s: T_FUNCS['self'](gs, s).counters.get_count(CHARGE))],
    'red-ward': [Triggered(KWAModEffect('add', 'Protection From Red'),
                           T_FUNCS['creatures'], CastResolvedEvent)],
    'regeneration': [Activated('G', Regenerate(), T_FUNCS['host'])],
    'regrowth': [Triggered(Bounce(), T_FUNCS['cards_in_your_graveyard'], CastResolvedEvent)],
    'relic-barrier': [Activated('T', TapCardEffect(), T_FUNCS['untapped_artifacts'])],
    'reset': [Triggered(Reset(), None, CastResolvedEvent, conditions=[])],
              # TODO: Cast this spell only during an opponent's turn after their upkeep step
    'resurrection': [Triggered(Reanimate(), T_FUNCS['creatures_in_your_graveyard'], CastResolvedEvent)],
    'revelation': [Triggered(Revelation(), None, ZoneChangeEvent)],
    'reverse-damage': [Triggered(ReverseDamage(), T_FUNCS['cards'], CastResolvedEvent)],
    'reverse-polarity': [Triggered(ReversePolarity(), None, CastResolvedEvent)],
    'righteousness': [Triggered(Pump(7, 7, True), T_FUNCS['blockers'], CastResolvedEvent)],
    'riptide': [Triggered(Riptide(), None, CastResolvedEvent)],
    'riven-turnbull': [Activated('T', AddMana('B'))],
    'rock-hydra': [Triggered(RockHydraCast(), T_FUNCS['self'], CastResolvedEvent),
                   Triggered(RockHydraAutoDamagePrevent(), None, DamageProposedEvent),
                   Activated('R', PreventNextDamageToCardEOT(T_FUNCS['self'])), Activated('RRR', AddCounter(PLUS_ONE))],
    'rocket-launcher': [Triggered(RocketLauncherCast(), None, CastResolvedEvent),
                        Activated('2', RocketLauncherAA(), T_FUNCS['all_creatures_and_players'])],
    'rod-of-ruin': [Activated('3T', DealDamage(1), T_FUNCS['all_creatures_and_players'])],
    'rohgahh-of-kher-keep': [Static(RohgahhOfKherKeepPump()), Triggered(RogahhOfKherKeepUpkeep(), None, UpkeepEvent)],
    'royal-assassin': [Activated('T', Destroy(), T_FUNCS['tapped_creatures'])],
    'rubinia-soulsinger': [Activated('T', Steal(), T_FUNCS['opp_creatures']),
                           Triggered(OptionalUntap(), None, UntapPhaseEvent),
                           Triggered(ReturnToOwnerOnUntap(), None, UntapCardEvent)],
    'rukh-egg': [Triggered(RukhEgg(), None, DiesEvent)],
    'sacrifice': [Triggered(SacrificeOnCast(), T_FUNCS['your_creatures'], CastResolvedEvent)],
    'safe-haven': [Activated('2T', SafeHaven(), T_FUNCS['your_creatures']),
                   Triggered(SafeHavenUpkeep(), None, UpkeepEvent)],
    'sage-of-lat-nam': [Activated('T', DrawCards(), T_FUNCS['card_owner'],
                                  extra_costs=[SacCardCost(T_FUNCS['your_artifacts'])])],
    'samite-healer': [Activated('T', PreventNextDamageBy(1), T_FUNCS['cards'])],
    'sandals-of-abdallah': [Activated('2', SandalsOfAbdallahIslandWalk(), T_FUNCS['creatures'])],
    'sandstorm': [Triggered(Sandstorm(), None, CastResolvedEvent)],
    'savaen-elves': [Activated('GGT', Destroy(), T_FUNCS['auras_on_lands'])],
    'savannah': dual_land_activated_ability_specs('GW'),
    'scarecrow': [Activated('6T', Scarecrow())],
    'scarwood-hag':
        [Activated('GGGGT', KWAModEffect('add', 'Forestwalk', True), T_FUNCS['creatures_wo_forestwalk']),
         Activated('GGGGT', KWAModEffect('remove', 'Forestwalk', True), T_FUNCS['forestwalkers'])],
    'scavenger-folk': [Activated('GT', Destroy(), T_FUNCS['artifacts'], extra_costs=[SacSelfCost()])],
    'scavenging-ghoul': [Triggered(AddCounterPerCreatureDeath(CORPSE), T_FUNCS['self'], EndStepEvent),
                         Activated('', Regenerate(), T_FUNCS['self'], extra_costs=[RemoveCounterCost(CORPSE)])],
    'scrubland': dual_land_activated_ability_specs('BW'),
    'sea-kings-blessing': [Triggered(SetColor('U', 'EOT'), TargetSpec(T_FUNCS['creatures'], 1, None),
                           CastResolvedEvent)],
    'season-of-the-witch':
        [Triggered(SeasonOfTheWitchUpkeep(), None, UpkeepEvent),
         Triggered(SeasonOfTheWitchEndStep(), None, EndStepEvent)],
    'sedge-troll': [Static(SedgeTrollPT()), Activated('B', Regenerate(), T_FUNCS['self'])],
    'seeker': [Static(Seeker())],
    'sengir-vampire': [Triggered(SengirVampire())],
    'sentinel': [Activated('', Sentinel(), None, BlockEvent)],
    'serendib-djinn':
        [Triggered(SerendibDjinn(), None, UpkeepEvent), Triggered(SerendibDjinnNoLands(), None, StateBasedEvent)],
    'serendib-efreet': [Triggered(DealDamageToOwnerOnUpkeep(1), T_FUNCS['self'], UpkeepEvent)],
    'serpent-generator': [Activated('4T', CreateTokenCreature('snake'))],
    'shapeshifter': [Triggered(Shapeshifter(), None, CastResolvedEvent), Triggered(Shapeshifter(), None, UpkeepEvent)],
    'shatter': [Triggered(Destroy(), T_FUNCS['artifacts'], CastResolvedEvent)],
    'shatterstorm': [Triggered(DestroyAll(T_FUNCS['artifacts'], False), None, CastResolvedEvent)],
    'shield-wall': [Triggered(ShieldWall(), None, CastResolvedEvent)],
    'shivan-dragon': [Activated('R', Pump(1, 0, True), T_FUNCS['self'])],
    'simulacrum': [Triggered(Simulacrum(), None, CastResolvedEvent)],
    'singing-tree': [Activated('T', SingingTree(), T_FUNCS['attackers'])],
    'sinkhole': [Triggered(Destroy(), T_FUNCS['lands'], CastResolvedEvent)],
    'sirens-call': [Static(SirensCallCanCast()), # this doesn't feel right
                    Triggered(KWAModEffect('add', 'Goad', True), T_FUNCS['opp_creatures'], CastResolvedEvent)],
    'sisters-of-the-flame': [Activated('T', AddMana('R'), T_FUNCS['card_owner'])],
    'skull-of-orm': [Activated('5T', Bounce(), T_FUNCS['enchants_in_your_graveyard'])],
    'smoke': [Triggered(Smoke(), None, CanUntapQueryEvent)],
    'snake': [Triggered(AddPoisonCounter(), None, DamageResolvedEvent)],  # token creature created by serpent-generator
    'sol-ring': [Activated('T', AddMana('C', 2), T_FUNCS['card_owner'])],
    'solkanar-the-swamp-king': [Triggered(OnColorSpellGainLife('B'), None, CastResolvedEvent)],
    'soul-net': [Triggered(SoulNet(), None, DiesEvent)],
    'spectral-cloak': [Triggered(None, T_FUNCS['creatures'], CastResolvedEvent), Static(SpectralCloak())],
    'spinal-villain': [Activated('T', Destroy(), T_FUNCS['blue_creatures'])],
    'spirit-link': [Triggered(None, T_FUNCS['creatures'], CastResolvedEvent),
                    Triggered(SpiritLink(), None, DamageResolvedEvent)],
    'spirit-shackle': [Triggered(None, T_FUNCS['creatures'], CastResolvedEvent),
                       Triggered(SpiritShackle(), None, TapCardEvent)],
    'spiritual-sanctuary': [Triggered(SpiritualSanctuary(), None, UpkeepEvent)],
    'staff-of-zegon': [Activated('3T', Pump(-2, 0, True), T_FUNCS['creatures'])],
    'standing-stones': [Activated('1T', AddMana(c), text=f'Add {{{c}}}', extra_costs=PayLifeCost())
                        for c in COLOR_LETTERS],
    'stangg': [Triggered(CreateTokenCreature('stangg-twin'), None, CastResolvedEvent),
               Triggered(StanggOnLeave(), None, ZoneChangeEvent)],
    'steal-artifact': [Triggered(Steal(), T_FUNCS['opp_artifacts'], CastResolvedEvent),
                       Triggered(ReturnToOwnerOnLTB(), None, ZoneChangeEvent)],
    'stone-calendar': [Static(StoneCalendar())],
    'stone-giant': [Activated('T', StoneGiant(), T_FUNCS['stone_giant'])],
    'stone-rain': [Triggered(Destroy(), T_FUNCS['lands'], CastResolvedEvent)],
    'storm-seeker': [Triggered(StormSeeker(), T_FUNCS['all_players'], CastResolvedEvent)],
    'storm-world': [Triggered(StormWorld(), None, UpkeepEvent)],
    'stream-of-life': [Triggered(StreamOfLife(), T_FUNCS['all_players'], CastResolvedEvent,
                                 max_x_func=lambda gs, s: gs.mana_pools[s.owner_id].get_max_x('XG'))],
    'strip-mine': [Activated('T', AddMana('C'), T_FUNCS['card_owner']),
                   Activated('T', Destroy(), T_FUNCS['lands'], extra_costs=[SacSelfCost()])],
    'su-chi': [Triggered(SuChi(), None, DiesEvent)],
    'subdue': [Triggered(Subdue(), T_FUNCS['creatures'], CastResolvedEvent)],
    'sunastian-falconer': [Activated('T', AddMana('C', 2))],
    'sunken-city': [Static(SunkenCity()), Triggered(PayManaOrSac('UU'), None, UpkeepEvent)],
    'swords-to-plowshares': [Triggered(SwordsToPlowshares(), T_FUNCS['creatures'], CastResolvedEvent)],
    'sylvan-paradise': [Triggered(SetColor('G', 'EOT'), TargetSpec(T_FUNCS['creatures'], 1, None),
                                  CastResolvedEvent)],
    'syphon-soul': [Triggered(SyphonSoul(), T_FUNCS['opponent'], CastResolvedEvent)],
    'tablet-of-epityr': [Triggered(TabletOfEpityr(), None, DiesEvent)],
    'taiga': dual_land_activated_ability_specs('RG'),
    'tangle-kelp': [Triggered(TangleKelp(), T_FUNCS['creatures'], CastResolvedEvent)],
    'tawnoss-coffin': [Triggered(OptionalUntap(), None, UntapPhaseEvent),
                       Triggered(TawnossCoffinUntap(), None, UntapCardEvent),
                       Triggered(TawnossCoffinZoneChange(), None, ZoneChangeEvent)],
    'tawnoss-wand': [Activated('2T', UnblockableThisTurn(), T_FUNCS['creatures_power_two_or_less'])],
    'tawnoss-weaponry': [Triggered(OptionalUntap(), None, UntapPhaseEvent),
                         Activated('2T', Pump(1, 1, True), T_FUNCS['creatures']),
                         (Triggered(UntapRemovesPumpFromAnotherCard(), None, UntapCardEffect))],
    'telekinesis': [Triggered(Telekinesis(), T_FUNCS['creatures'], CastResolvedEvent)],
    'teleport': [Triggered(UnblockableThisTurn(), T_FUNCS['creatures'], CastResolvedEvent,
                           allowed_phases=[Phase.DECLARE_COMBAT])],
    'terror': [Triggered(Destroy(False), T_FUNCS['non_artifact_non_black_creatures'], CastResolvedEvent)],
    'tetravus': [Triggered(AddCountersYourTurnOnly(PLUS_ONE, 3), T_FUNCS['self'], CastResolvedEvent)],
    'tetsuo-umezawa': [Activated('UBBRT', Destroy(), T_FUNCS['tapped_or_blocking_creatures']),
                       Static(CantBeTargetedByAuras())],
    'the-abyss': [Triggered(TheAbyss(), None, UpkeepEvent)],
    'the-brute': [Triggered(Pump(1, 0), T_FUNCS['creatures'], CastResolvedEvent),
                  Activated('RRR', Regenerate(), T_FUNCS['host'])],
    'the-fallen': [Static(TheFallen())],
    'the-hive': [Activated('5T', CreateTokenCreature('wasp'))],
    'the-rack': [Triggered(TheRack(), None, UpkeepEvent)],
    'the-tabernacle-at-pendrell-vale': [Triggered(TheTabernacleAtPendrellVale(), None, UpkeepEvent)],
    'the-wretched': [Triggered(TheWretchedSteal(), None, CombatEndEvent),
                     Triggered(TheWretchedUnsteal(), None, ZoneChangeEvent)],
    'thicket-basilisk': [Triggered(CockatriceAndThicketBasilisk(), None, BlockEvent)],
    'thoughtlace': [Triggered(SetColor('U'), T_FUNCS['cards'], CastResolvedEvent)],
    'throne-of-bone': [Static(OnColorSpellPayOneColorlessForOneLifeChoice('B'))],
    'time-elemental': [Triggered(TimeElementalAttackedOrBlocked(), None, CombatEndEvent),
                       Activated('2UUT', TimeElementalBounce(), T_FUNCS['unenchanted_perms'])],
    'time-vault':
        [Triggered(TapCardEffect(), T_FUNCS['self'], CastResolvedEvent),
         Triggered(StaysTapped(), T_FUNCS['self'], UntapPhaseEvent),
         Triggered(TimeVaultOption(), None, UntapPhaseEvent),
         Activated('T', TakeAnotherTurn())],
    'time-walk': [Triggered(TakeAnotherTurn(), None, CastResolvedEvent)],
    'timetwister': [Triggered(Timetwister(), None, CastResolvedEvent)],
    'tivadars-crusade':
        [Triggered(DestroyAll(lambda gs, s: gs.card_filter.in_play().by_sub_type('Goblin').result()),
                   None, CastResolvedEvent)],
    'tor-wauki': [Activated('T', DealDamage(2), T_FUNCS['combatants'])],
    'tormods-crypt':
        [Activated('T', GraveyardToExileInItsEntirety(), T_FUNCS['all_players'], extra_costs=[SacSelfCost()])],
    'touch-of-darkness': [Triggered(SetColor('B', 'EOT'), TargetSpec(T_FUNCS['creatures'], 1, None),
                               CastResolvedEvent)],
    'tower-of-coireall': [Activated('T', TowerOfCoireall(), T_FUNCS['creatures'])],
    'tracker': [Activated('GGT', Tracker(), T_FUNCS['creatures'])],
    'tranquility':
        [Triggered(DestroyAll(lambda gs, s: gs.card_filter.in_play().by_type('Enchantment').result()),
                   None, CastResolvedEvent)],
    'transmutation': [Triggered(Transmutation(), T_FUNCS['creatures'], CastResolvedEvent)],
    'triassic-egg': [Activated('3T', AddCounter(HATCHLING)),
                     Activated('', TriassicEgg(), extra_costs=[SacSelfCost()],
                               conditions=[has_ge_x_counters(T_FUNCS['self'], HATCHLING, 2)])],  # conditions needs to know who this card is
    'triskelion': [Triggered(AddCountersYourTurnOnly(PLUS_ONE, 3), T_FUNCS['self'], CastResolvedEvent),
                   Activated('', DealDamage(1), T_FUNCS['all_creatures_and_players'],
                             extra_costs=[RemoveCounterCost(PLUS_ONE)])],
    'tropical-island': dual_land_activated_ability_specs('GU'),
    'tsunami':
        [Triggered(DestroyAll(lambda gs, s: gs.card_filter.in_play().islands().result()),
                   None, CastResolvedEvent)],
    'tuknir-deathlock': [Activated('RGT', Pump(2, 2, True), T_FUNCS['creatures'])],
    'tundra': dual_land_activated_ability_specs('WU'),
    'tunnel': [Triggered(Destroy(False), T_FUNCS['walls'], CastResolvedEvent)],
    'twiddle': [Triggered(Twiddle(), T_FUNCS['artifacts_creatures_lands'], CastResolvedEvent)],
    'typhoon': [Triggered(Typhoon(), T_FUNCS['opponent'], CastResolvedEvent)],
    'uncle-istvan': [Static(UncleIstvanPrevention())],
    'undertow': [Static(WalkRuleRemoved('Islandwalk'))],
    'underground-sea': dual_land_activated_ability_specs('BU'),
    'unholy-strength': [Triggered(Pump(2, 1), T_FUNCS['creatures'], CastResolvedEvent)],
    'unstable-mutation':
        [Triggered(Pump(3, 3), T_FUNCS['creatures'], CastResolvedEvent),
         Triggered(AddCountersOnHostTurn(MINUS_ONE), T_FUNCS['self'], UpkeepEvent)],
    'unsummon': [Triggered(Bounce(), T_FUNCS['creatures'], CastResolvedEvent)],
    'ur-drago': [Static(WalkRuleRemoved('Swampwalk'))],
    'urborg': [Activated('T', AddMana('B')),
               Activated('T', UrborgLoseFirstStrike(), T_FUNCS['creatures_with_first_strike']),
               Activated('T', UrborgLoseSwampwalk(), T_FUNCS['creatures_with_swampwalk'])],
    'untamed-wilds': [Triggered(UntamedWilds(), None, CastResolvedEvent)],
    'urzas-avenger': [Activated('', UrzasAvengerFlying()), Activated('', UrzasAvengerFirstStrike()),
                      Activated('', UrzasAvengerTrample())],
    'urzas-chalice': [Static(OnColorSpellPayOneColorlessForOneLifeChoice('C'))],
    'urzas-mine': [Activated('T', UrzasTrio())],
    'urzas-miter': [Triggered(UrzasMiter(), None, DiesEvent)],
    'urzas-power-plant': [Activated('T', UrzasTrio())],
    'urzas-tower': [Activated('T', UrzasTrio())],
    'uthden-troll': [Activated('R', Regenerate(), T_FUNCS['self'])],
    'vaevictis-asmadi': [Triggered(PayManaOrSac('BRG'), None, UpkeepEvent),
                         Activated('B', Pump(1, 0, True), T_FUNCS['self']), Activated('R', Pump(1, 0, True), T_FUNCS['self']),
                         Activated('G', Pump(1, 0, True), T_FUNCS['self'])],
    'vampire-bats': [Activated('B', Pump(1, 0, True), T_FUNCS['self'], max_activations_per_turn=2)],
    'venarian-gold':
        [Triggered(RemoveCountersOnHostTurn(SLEEP), T_FUNCS['your_creatures'], UpkeepEvent),
         Triggered(VenarianGoldHostStaysTapped(), None, UntapPhaseEvent)],
    'venom': [Triggered(None, T_FUNCS['creatures'], CastResolvedEvent), Triggered(Venom(), None, BlockEvent)],
    'verduran-enchantress': [Static(VerduranEnchantress())],
    'vesuvan-doppelganger': [Triggered(VesuvanDoppelgangerCast(), None, CastResolvedEvent),
                             Triggered(VesuvanDoppelgangerUpkeep(), None, UpkeepEvent)],
    # TODO: despite being the same code, VesuvanDoppelgangerUpkeep doesn't trigger;
    #  the card goes to the graveyard during cast as well but gets pulled out somehow;
    #  the SBA looking at 0 toughness may be the culprit
    'veteran-bodyguard': [Triggered(VeteranBodyguard(), None, DamageProposedEvent)],
    'visions': [Triggered(Visions(), T_FUNCS['all_players'], CastResolvedEvent)],
    'volcanic-island': dual_land_activated_ability_specs('RU'),
    'voodoo-doll':
        [Triggered(AddCountersYourTurnOnly(PIN), T_FUNCS['self'], UpkeepEvent),
         Triggered(VoodooDollEndStep(), None, EndStepEvent),
         Activated('XXT', DealDamage(), T_FUNCS['all_creatures_and_players'],
                   min_x=lambda gs, s: T_FUNCS['self'](gs, s).counters.get_count(PIN)//2,
                   max_x_func=lambda gs, s: T_FUNCS['self'](gs, s).counters.get_count(PIN)//2)],
    'walking-dead': [Activated('B', Regenerate(), T_FUNCS['self'])],
    'wall-of-bone': [Activated('B', Regenerate(), T_FUNCS['self'])],
    'wall-of-brambles': [Activated('G', Regenerate(), T_FUNCS['self'])],
    'wall-of-dust': [Triggered(WallOfDust(), None, BlockEvent)],
    'wall-of-opposition': [Activated('1', Pump(1, 0, True), T_FUNCS['self'])],
    'wall-of-putrid-flesh': [Triggered(PreventCombatDamageFromEnchantedCreatures(), T_FUNCS['self'], DamageProposedEvent)],
    'wall-of-tombstones': [Static(WallOfTombstonesPT())],
    'wall-of-vapor': [PreventCombatDamageFromItsAttackers(), None, DamageProposedEvent],
    'wall-of-water': [Activated('U', Pump(1, 0, True), T_FUNCS['self'])],
    'wall-of-wonder': [Activated('2UU', WallOfWonder())],
    'wand-of-ith': [Activated('3T', WandOfIth(), allowed_p_id_turn=T_FUNCS['card_owner'])],
    'wanderlust': [Triggered(None, T_FUNCS['creatures'], CastResolvedEvent),
                   Triggered(DealDamageOnHostUpkeep(1), T_FUNCS['host_owner'], UpkeepEvent)],
    'warp-artifact': [Triggered(None, T_FUNCS['artifacts'], CastResolvedEvent),
                      Triggered(DealDamageOnHostUpkeep(1), T_FUNCS['host_owner'], UpkeepEvent)],
    'water-wurm': [Static(WaterWurmPT())],
    'weakness': [Triggered(Pump(-2, -1), T_FUNCS['creatures'], CastResolvedEvent)],
    'weakstone': [Static(Weakstone())],
    'web': [Triggered(Web(), T_FUNCS['creatures'], CastResolvedEvent)],
    'wheel-of-fortune': [Triggered(WheelOfFortune(), None, CastResolvedEvent)],
    'whirling-dervish': [Triggered(WhirlingDervish(), None, EndStepEvent)],
    'white-mana-battery': [MANA_BATTERY_ADD_CHARGE,
                           Activated('T', ManaBatteriesAddMana('W'), extra_costs=[RemoveCounterCost(CHARGE)],
                                     max_x_func=lambda gs, s: T_FUNCS['self'](gs, s).counters.get_count(CHARGE))],
                           # TODO: the x_value isn't making it to .resolve(); might be true of all specs w max_var_x_fun
    'white-ward': [Triggered(KWAModEffect('add', 'Protection From White'),
                             T_FUNCS['creatures'], CastResolvedEvent)],
    'wild-growth': [Triggered(None, T_FUNCS['lands'], CastResolvedEvent),
                    Triggered(WildGrowth(), None, TapCardEvent)],
    'will-o-the-wisp': [Activated('B', Regenerate(), T_FUNCS['self'])],
    'willow-satyr': [Activated('T', Steal(), T_FUNCS['opp_legendary_creatures']),
                     Triggered(OptionalUntap(), None, UntapPhaseEvent),
                     Triggered(ReturnToOwnerOnUntap(), None, UntapCardEvent)],
    'winds-of-change': [Triggered(WindsOfChange(), None, CastResolvedEvent)],
    'winter-blast': [Triggered(WinterBlast(), TargetSpec(T_FUNCS['untapped_creatures'], 1, None),
                               CastResolvedEvent, max_x_func=lambda gs, s: gs.mana_pools[s.owner_id].get_max_x('XG'))],
    'winter-orb': [Triggered(WinterOrb(), None, CanUntapQueryEvent)],
    'witch-hunter': [Activated('T', DealDamage(1), T_FUNCS['all_players']),
                     Activated('1WWT', Bounce(), T_FUNCS['opp_creatures'])],
    'wood-elemental': [Triggered(WoodElemental(), None, CastResolvedEvent)],
    'wooden-sphere': [Static(OnColorSpellPayOneColorlessForOneLifeChoice('G'))],
    'word-of-binding': [Triggered(TapCardsEffect(), TargetSpec(T_FUNCS['untapped_creatures'], 1, None), CastResolvedEvent,
                                  max_x_func=lambda gs, s: gs.mana_pools[s.owner_id].get_max_x('XBB'))],
    'wormwood-treefolk': [Activated('GG', WormwoodTreefolkForestwalk()),
                          Activated('BB', WormwoodTreefolkSwampwalk())],
    'wrath-of-god': [Triggered(ExileAllCreatures(), None, CastResolvedEvent)],
    'wyluli-wolf': [Activated('T', Pump(1, 1, True), T_FUNCS['creatures'])],
    'xira-arien': [Activated('BRGT', DrawCards(3), T_FUNCS['all_players'])],
    'yawgmoth-demon': [Triggered(YawgmothDemon(), None, UpkeepEvent)],
    'ydwen-efreet': [Triggered(YdwenEfreet(), None, BlockEvent)],
    'zombie-master': [Static(ZombieMasterWalk())],  # TODO: giving other zombies an activated ability
}
