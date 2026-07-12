from __future__ import annotations

from models.cost import SacSelfCost, ExileSelfCost, SacTwoIslandsCost, RemoveCounterCost, \
    SacCardCost, DiscardLastCardDrawnThisTurn
from models.counter_tokens import CARRION, PLUS_ONE
from models.effects.base import EffSpec, Activated, Triggered, Static, Spell
from models.target import TargetSpec
from models.effects.listeners_mod_queries import GaeasAvengerPT, GaeasLiegePT, GiantTortoisePT, GoblinCaves, \
    GoblinShrinePump, GravitySphere, \
    HiddenPath, IvoryGuardians, JacquesLeVert, KeldonWarlordPT, KirdApePT, KoboldOverlord, KoboldTaskmaster, \
    KormusBell, LivingLands, LivingPlane, LordOfAtlantisPT, LordOfAtlantisWalk, Mightstone, NightmarePT, \
    OrcishOriflamme, JihadPT
from models.effects.listeners_permission import Moat, Meekstone, Invisibility, IronclawOrcs, Fear, \
    JuggernautUnblockableByWalls, LivonyaSilone, WalkRuleRemoved, DoesntUntapAtUntap, GoblinRockSledUntap
from ..effects.resolvers_f_to_o import FalseOrders, GlyphOfDoom, GlyphOfLife, HazezonTamar, JovialEvil, Millstone, \
    GlassesOfUrza, GwendlynDiCorci, JalumTome, MindTwist, NaturalSelection, GraveRobbersAA, GreatDefender, HellSwarm, \
    HolyLight, HowlFromBeyond, LesserWerewolf, MarshGas, Morale, FallingStar, Feint, FeldonsCane, Festival, \
    FlashFlood, GoblinKing, Greed, GlyphOfDestruction, HealingSalve, HurkylsRecall, Inquisition, KoboldDrillSergeant, \
    KryShield, LivingArtifactUpkeep, ManaClash, MartyrsCry, MazeOfIth, NamelessRace, ManaShort, Forcefield, \
    FireAndBrimstone, LibraryOfAlexandria, FellwarStone, NettlingImp, MoldDemon, ManaDrain, GiantSlug
from ..effects.resolvers_a_to_e import ExchangeLifeTotals
from models.effects.resolvers_generic import XZeroOneCountersByManaValue, DealDamage, \
    DealDamageToAllCreaturesAndPlayers, DealDamageToTargetAndYou, \
    PreventAllCombatDamageThisTurn, Destroy, DestroyAll, Regenerate, SacAll, DrawCards, \
    BecomeCreature, SetColor, AllWalksRemoved, KWAModEffect, GainLife, AddMana, Bounce, Reanimate, Steal, HandToBoard, \
    Pump, TapCardEffect, UntapCardEffect, PreventNextDamageToSourceOwner, \
    PreventAllDamageBy, PreventNextDamageBy, PreventAllDamageToThisTurn, DeclareAColor, CounterSpell, \
    RevealTopLibraryCard
from models.phase_manager import Phase
from .card_filter_funcs import T_FUNCS
from .effect_spec_templates import untap_for_mana_at_owner_upkeep, MANA_BATTERY_ADD_CHARGE, mana_battery_add_mana, \
    mox_specs, self_pump, max_x_from_printed_card
from ..effects.listeners_misc import IchneumonDruid, HauntingWindActivation, ManaDrainMainPhase
from ..effects.listeners_state_change import GoblinsOfTheFlarg, JihadSac, OldManOfTheSeaPowerCheck, ManaVortexSac
from ..effects.listeners_zone_change import FieldOfDreams, GoblinShrineOnLeave, HazezonTamarLTB, Kismet, \
    LandEquilibrium
from ..effects.listeners_upkeep import Fasting, ForceOfNatureUpkeep, GabrielAngelfire, GhazbanOgre, \
    HazezonTamarTokenCreation, IvoryTower, Karma, LandTax, LordOfThePitUpkeep, ManaVortexUpkeep
from ..effects.listeners_tap_untap import Kudzu, Lifeblood, Lifetap, HauntingWindTap
from ..effects.listeners_end_step import InfiniteAuthorityEndStep
from ..effects.listeners_combat import HasranOgress, MijaeDjinn, GiantShark, InfernalMedusa, \
    InfiniteAuthorityCombatEnd, Lure, MarblePriestForcesBlock, GoblinRockSledCanAttack, FloralSpuzzem, MerchantShip, \
    MurkDwellers
from ..effects.listeners_cost import Gloom, ManaMatrix
from ..effects.listeners_damage import GaseousForm, MarblePriestPrevention, MartyrsOfKorlis, \
    FungusaurOnDamage, HypnoticSpecter, LivingArtifactOnDamage, NicolBolas, ForethoughtAmulet
from ..effects.listeners_dies import Onulet
from ..effects.listeners_draw_discard import HowlingMine, ManaVaultDamageIfTapped, FastingDestroy
from ..effects.listeners_generic import OnColorSpellPayOneColorlessForOneLifeChoice, \
    AddPoisonCounter, ReturnToOwnerOnUntap, CardsDontUntapAtUntapPhase, OptionalUntap, \
    DealDamageToOwnerOnUpkeep, DealDamageOnHostUpkeep, CantAttackIfAttackedLastTurn, PayManaOrSacAtUpkeep, \
    AddCounterPerCreatureDeathAtEndStep, AddCountersIfAnyCreatureDied

MAP: dict[str: list[EffSpec]] = {
    'fallen-angel': [Activated('', Pump(2, 1, True), T_FUNCS['self'],
                     extra_costs=[SacCardCost(T_FUNCS['your_other_creatures'])])],
    'falling-star': [Spell(FallingStar(), T_FUNCS['opp_creatures'],
                           text='If a di roll is 1-5, deal 3 damage to it')],
    'false-orders': [Spell(FalseOrders(), T_FUNCS['blockers'], allowed_phases=[Phase.DECLARE_BLOCKERS])],
    'farmstead': [Spell(None, T_FUNCS['lands']),
                  Activated('WW', GainLife(), T_FUNCS['host_owner'], allowed_phases=[Phase.UPKEEP],
                            allowed_p_id_turn=T_FUNCS['host_owner'], max_activations_per_turn=1)],
    'fasting': [Triggered(Fasting(), T_FUNCS['self']), Triggered(FastingDestroy())],
    'fear': [Spell(None, T_FUNCS['creatures']), Static(Fear())],
    'feedback': [Triggered(DealDamageOnHostUpkeep(1), T_FUNCS['host']), Spell(None, T_FUNCS['enchants'])],
    'feint': [Spell(Feint(), T_FUNCS['attackers'])],
    'feldons-cane': [Activated('T', FeldonsCane(), None, extra_costs=[ExileSelfCost()])],
    'fellwar-stone': [Activated('T', FellwarStone())],
    'festival': [Spell(Festival(), None, allowed_phases=[Phase.UPKEEP], allowed_p_id_turn=T_FUNCS['opponent'])],
    'field-of-dreams': [Triggered(FieldOfDreams()), Spell(RevealTopLibraryCard())],
    'fire-and-brimstone': [Spell(FireAndBrimstone(),)],
    'fire-drake': [Activated('R', Pump(1, 0, True), T_FUNCS['self'], max_activations_per_turn=1)],
    'fire-sprites': [Activated('GT', AddMana('R'), T_FUNCS['card_owner'])],
    'firebreathing': [Spell(None, T_FUNCS['creatures']), self_pump('R', 1, 0)],
    'fishliver-oil': [Spell(KWAModEffect('add', 'Islandwalk'), T_FUNCS['creatures'])],
    'fissure': [Spell(Destroy(False), T_FUNCS['creatures_and_lands'])],
    'flash-counter': [Spell(CounterSpell(), T_FUNCS['instant_spells'])],
    'flash-flood': [Spell(FlashFlood(), T_FUNCS['flash_flood'])],
    'flashfires': [Spell(DestroyAll(T_FUNCS['plains']))],
    'flight': [Spell(KWAModEffect('add', 'Flying'), T_FUNCS['creatures'])],
    'flood': [Activated('UU', TapCardEffect(), T_FUNCS['untapped_creatures_without_flying'])],
    'floral-spuzzem': [Triggered(FloralSpuzzem())],
    'flying-carpet': [Activated('2T', KWAModEffect('add', 'Flying', True), T_FUNCS['creatures'])],
    'fog': [Spell(PreventAllCombatDamageThisTurn())],
    'force-of-nature': [Triggered(ForceOfNatureUpkeep())],
    'forcefield': [Activated('1', Forcefield(), T_FUNCS['unblocked_attackers'])],
    'forethought-amulet': [Triggered(PayManaOrSacAtUpkeep('3')), Static(ForethoughtAmulet())],
    'fountain-of-youth': [Activated('2T', GainLife(), T_FUNCS['card_owner'])],
    'frozen-shade': [self_pump('B', 1, 1)],
    'fungusaur': [Triggered(FungusaurOnDamage())],
    'gabriel-angelfire': [Triggered(GabrielAngelfire())],
    'gaeas-avenger': [Static(GaeasAvengerPT())],
    'gaeas-liege': [Static(GaeasLiegePT())],  # more to code
    'gaeas-touch': [Activated('', AddMana('G', 2), T_FUNCS['card_owner'], extra_costs=[SacSelfCost()],
                              text='Exile for {GG}'),
                    Activated('', HandToBoard(), T_FUNCS['forests_in_your_hand'], text='Play extra forest',
                              allowed_p_id_turn=T_FUNCS['card_owner'], max_activations_per_turn=1)],
    'gaseous-form': [Static(GaseousForm()), Spell(None, T_FUNCS['creatures'])],
    'gate-to-phyrexia': [Activated('', Destroy(), T_FUNCS['artifacts'],
                                   extra_costs=[SacCardCost(T_FUNCS['your_creatures'])],
                                   allowed_phases=[Phase.UPKEEP], max_activations_per_turn=1,
                                   allowed_p_id_turn=T_FUNCS['card_owner'])],
    'ghazbán-ogre': [Triggered(GhazbanOgre())],
    'ghost-ship': [Activated('UUU', Regenerate(), T_FUNCS['self'])],
    'ghosts-of-the-damned': [Activated('T', Pump(-1, 0, True), T_FUNCS['creatures'])],
    'giant-growth': [Spell(Pump(3, 3, True), T_FUNCS['creatures'])],
    'giant-shark': [Triggered(GiantShark())],
    'giant-slug': [Activated('5', GiantSlug())],
    'giant-strength': [Spell(Pump(2, 2), T_FUNCS['creatures'])],
    'giant-tortoise': [Static(GiantTortoisePT())],
    'giant-turtle': [Triggered(CantAttackIfAttackedLastTurn())],
    'glasses-of-urza': [Activated('T', GlassesOfUrza())],
    'gloom': [Static(Gloom())],
    'glyph-of-destruction': [Spell(GlyphOfDestruction(), T_FUNCS['your_walls'])],
    'glyph-of-doom': [Spell(GlyphOfDoom(), T_FUNCS['walls'])],
    'glyph-of-life': [Spell(GlyphOfLife(), T_FUNCS['walls'])],
    'goblin-balloon-brigade': [Activated('R', KWAModEffect('add', 'Flying', True), T_FUNCS['self'])],
    'goblin-caves': [Static(GoblinCaves())],
    'goblin-digging-team': [Activated('T', Destroy(), T_FUNCS['walls'], extra_costs=[SacSelfCost()])],
    'goblin-king': [Spell(GoblinKing())],
    'goblin-rock-sled': [Static(GoblinRockSledUntap()), Static(GoblinRockSledCanAttack())],
    'goblin-shrine': [Static(GoblinShrinePump()), Triggered(GoblinShrineOnLeave())],
    'goblin-wizard': [Activated('T', HandToBoard(), T_FUNCS['goblin_permanents_in_your_hand']),
                      Activated('T', KWAModEffect('add', 'Protection From White', True), T_FUNCS['goblins'])],
    'goblins-of-the-flarg': [Static(GoblinsOfTheFlarg())],
    'golgothian-sylex': [Activated('1T', SacAll(T_FUNCS['golgothian_sylex']))],
    'gosta-dirk': [Static(WalkRuleRemoved('Islandwalk'))],
    'granite-gargoyle': [self_pump('R', 0, 1)],
    'grapeshot-catapult': [Activated('T', DealDamage(4), T_FUNCS['fliers'])],
    'grave-robbers': [Activated('BT', GraveRobbersAA(), T_FUNCS['artifacts_in_graveyards'])],
    'gravity-sphere': [Static(GravitySphere())],
    'great-defender': [Spell(GreatDefender(), T_FUNCS['creatures'])],
    'great-wall': [Static(WalkRuleRemoved('Plainswalk'))],
    'greater-realm-of-preservation': [Activated('1W', PreventNextDamageToSourceOwner(), T_FUNCS['black_and_red'])],
    'greed': [Activated('B', Greed(), T_FUNCS['card_owner'])],
    'green-mana-battery': [MANA_BATTERY_ADD_CHARGE, mana_battery_add_mana('G')],
    'green-ward': [Spell(KWAModEffect('add', 'Protection From Green'), T_FUNCS['creatures'])],
    'gwendlyn-di-corci': [Activated('T', GwendlynDiCorci(), T_FUNCS['all_players'])],
    'hammerheim': [Activated('T', AddMana('R'), T_FUNCS['card_owner']),
                   Activated('T', AllWalksRemoved(), T_FUNCS['creatures'])],
    'hasran-ogress': [Triggered(HasranOgress())],
    'haunting-wind': [Triggered(HauntingWindActivation()), Triggered(HauntingWindTap())],
    'hazezon-tamar': [Triggered(HazezonTamarTokenCreation(T_FUNCS['card_owner'])), Triggered(HazezonTamarLTB()),
                      Spell(HazezonTamar())],
    'healing-salve': [Spell(HealingSalve())],
    'heavens-gate': [Spell(SetColor('W', 'EOT'), TargetSpec(T_FUNCS['creatures'], 1, None))],
    'hell-swarm': [Spell(HellSwarm())],
    'hells-caretaker': [Activated('T', Reanimate(), T_FUNCS['creatures_in_your_graveyard'],
                                  allowed_phases=[Phase.UPKEEP], allowed_p_id_turn=T_FUNCS['card_owner'],
                                  extra_costs=SacCardCost(T_FUNCS['your_creatures']))],
    'hidden-path': [Static(HiddenPath())],
    'holy-armor': [Spell(Pump(0, 2), T_FUNCS['creatures']),
                   Activated('W', Pump(0, 1, True), T_FUNCS['host'])],
    'holy-day': [Spell(PreventAllCombatDamageThisTurn())],
    'holy-light': [Spell(HolyLight())],
    'holy-strength': [Spell(Pump(1, 2), T_FUNCS['creatures'])],
    'horn-of-deafening': [Activated('2T', PreventNextDamageToSourceOwner(combat_only=True), T_FUNCS['creatures'])],
    'horror-of-horrors': [Activated('', Regenerate(), T_FUNCS['black_creatures'],
                                    extra_costs=[SacCardCost(T_FUNCS['your_swamps'])])],
    'howl-from-beyond': [Spell(HowlFromBeyond(), T_FUNCS['creatures'])],
    'howling-mine': [Triggered(HowlingMine())],
    'hurkyls-recall': [Spell(HurkylsRecall(), T_FUNCS['all_players'])],
    'hyperion-blacksmith': [Activated('T', TapCardEffect(), T_FUNCS['opp_untapped_artifacts']),
                            Activated('T', UntapCardEffect(), T_FUNCS['opp_tapped_artifacts'])],
    'hypnotic-specter': [Triggered(HypnoticSpecter())],
    'ichneumon-druid': [Triggered(IchneumonDruid())],
    'icy-manipulator': [Activated('1T', TapCardEffect(), T_FUNCS['untapped_artifacts_creatures_lands'])],
    'ice-storm': [Spell(Destroy(), T_FUNCS['lands'])],
    'immolation': [Spell(Pump(2, -2), T_FUNCS['creatures'])],
    'indestructible-aura': [Spell(PreventAllDamageToThisTurn(), T_FUNCS['creatures'])],
    'infernal-medusa': [Triggered(InfernalMedusa())],
    'inferno': [Spell(DealDamageToAllCreaturesAndPlayers(6))],
    'infinite-authority': [Triggered(InfiniteAuthorityCombatEnd()), Triggered(InfiniteAuthorityEndStep())],
    'instill-energy': [Spell(KWAModEffect('add', 'Haste'), T_FUNCS['creatures']),
                       Activated('', UntapCardEffect(), T_FUNCS['host'], allowed_p_id_turn=T_FUNCS['host_owner'],
                                 max_activations_per_turn=1)],
    'invisibility': [Spell(None, T_FUNCS['creatures']), Static(Invisibility())],
    'inquisition': [Spell(Inquisition(), T_FUNCS['all_players'])],
    'iron-star': [Static(OnColorSpellPayOneColorlessForOneLifeChoice('R'))],
    'ironclaw-orcs': [Static(IronclawOrcs())],
    'island-fish-jasconius': [Triggered(DoesntUntapAtUntap()),
                              untap_for_mana_at_owner_upkeep('UUU', T_FUNCS['card_owner'])],
    'ivory-cup': [Static(OnColorSpellPayOneColorlessForOneLifeChoice('W'))],
    'ivory-guardians': [Static(IvoryGuardians())],
    'ivory-tower': [Triggered(IvoryTower())],
    'jacques-le-vert': [Static(JacquesLeVert())],
    # 'jade-monolith': [Activated('1', JadeMonolith(), T_FUNCS['all_creatures_and_players'])],  # needs a multi-step target selection for source & target
    'jade-statue': [Activated('2', BecomeCreature(3, 6, 'Golem', True), T_FUNCS['self'],
                              allowed_phases=[Phase.MAIN])],
    'jalum-tome': [Activated('2T', JalumTome(), text='Draw one card; discard one card')],
    'jandors-ring': [Activated('2T', DrawCards(), T_FUNCS['card_owner'], extra_costs=[DiscardLastCardDrawnThisTurn()])],
    'jandors-saddlebags': [Activated('3T', UntapCardEffect(), T_FUNCS['tapped_creatures'])],
    'jayemdae-tome': [Activated('4T', DrawCards(), T_FUNCS['card_owner'])],
    'jihad': [Static(JihadPT()), Static(JihadSac()), Spell(DeclareAColor())],
    'jovial-evil': [Spell(JovialEvil(), T_FUNCS['opponent'])],
    'juggernaut': [Static(JuggernautUnblockableByWalls())],
    'jump': [Spell(KWAModEffect('add', 'Flying', True), T_FUNCS['creatures'])],
    'junún-efreet': [Triggered(PayManaOrSacAtUpkeep('BB'))],
    'juzám-djinn': [Triggered(DealDamageToOwnerOnUpkeep(1), T_FUNCS['self'])],
    'karakas': [Activated('T', AddMana('W')), Activated('T', Bounce(), T_FUNCS['legendary_creatures'])],
    'karma': [Triggered(Karma())],
    'kei-takahashi': [Activated('T', PreventNextDamageBy(2), T_FUNCS['creatures'])],
    'keldon-warlord': [Static(KeldonWarlordPT())],
    'khabál-ghoul': [AddCounterPerCreatureDeathAtEndStep(PLUS_ONE)],
    'killer-bees': [self_pump('G', 1, 1)],
    'king-suleiman': [Activated('T', Destroy(), T_FUNCS['djinns_and_efreets'])],
    'kird-ape': [Static(KirdApePT())],
    'kismet': [Static(Kismet())],
    'kobold-drill-sergeant': [Spell(KoboldDrillSergeant())],
    'kobold-overlord': [Static(KoboldOverlord())],
    'kobold-taskmaster': [Static(KoboldTaskmaster())],
    'kormus-bell': [Static(KormusBell())],
    'kry-shield': [Activated('2T', KryShield(), T_FUNCS['your_creatures'])],
    'kudzu': [Triggered(Kudzu()), Spell(None, T_FUNCS['lands'])],
    'lady-caleria': [Activated('T', DealDamage(3), T_FUNCS['combatants'])],
    'lady-evangela': [Activated('WBT', PreventAllDamageBy(combat_only=True), T_FUNCS['creatures'])],
    'lance': [Spell(KWAModEffect('add', 'First Strike'), T_FUNCS['creatures'])],
    'land-equilibrium': [Static(LandEquilibrium())],
    'land-tax': [Triggered(LandTax())],
    'lesser-werewolf': [Activated('B', LesserWerewolf(), T_FUNCS['combating_against'],
                                  allowed_phases=[Phase.DECLARE_ATTACKERS])],  # at Declare Attackers, won't know how it's combating
    'leviathan':
        [Triggered(DoesntUntapAtUntap()),
         # TODO: this is wrong, should be a Triggered(..., ..., UpkeepEvent)
         Activated(None, UntapCardEffect(), T_FUNCS['self'], extra_costs=[SacTwoIslandsCost()],
                   allowed_phases=[Phase.UPKEEP], allowed_p_id_turn=T_FUNCS['card_owner']),
         # TODO: handle this via CanAttackQueryEvent
         Activated(None, KWAModEffect('add', 'Attack'), T_FUNCS['self'], extra_costs=[SacTwoIslandsCost()],
                   allowed_phases=[Phase.DECLARE_ATTACKERS], allowed_p_id_turn=T_FUNCS['card_owner']),
         Spell(TapCardEffect(), T_FUNCS['self'])],
    'ley-druid': [Activated('T', UntapCardEffect(), T_FUNCS['tapped_lands'])],
    'library-of-alexandria': [Activated('T', AddMana('C')), Activated('T', LibraryOfAlexandria())],
    'lifeblood': [Triggered(Lifeblood())],
    'lifeforce': [Activated('GG', CounterSpell(), T_FUNCS['black_spells'])],
    'lifelace': [Spell(SetColor('G'), T_FUNCS['cards'])],
    'lifetap': [Triggered(Lifetap())],
    'lightning-bolt': [Spell(DealDamage(3), T_FUNCS['all_creatures_and_players'])],
    'living-armor':
        [Activated('T', XZeroOneCountersByManaValue(), T_FUNCS['creatures'], extra_costs=[SacSelfCost()])],
    'living-artifact': [Spell(None, T_FUNCS['artifacts']), Triggered(LivingArtifactOnDamage()),
                        Triggered(LivingArtifactUpkeep())],
    'living-lands': [Static(LivingLands())],
    'living-plane': [Static(LivingPlane())],
    'living-wall': [Activated('1', Regenerate(), T_FUNCS['self'])],
    'livonya-silone': [Static(LivonyaSilone())],
    'llanowar-elves': [Activated('T', AddMana('G'), T_FUNCS['card_owner'])],
    'lord-of-atlantis': [Static(LordOfAtlantisPT()), Static(LordOfAtlantisWalk())],
    'lord-of-the-pit': [Triggered(LordOfThePitUpkeep())],
    'lord-magnus': [Static(WalkRuleRemoved('Plainswalk')), Static(WalkRuleRemoved('Forestwalk'))],
    'lure': [Spell(None, T_FUNCS['creatures']), Triggered(Lure())],
    'magnetic-mountain': [Triggered(CardsDontUntapAtUntapPhase(T_FUNCS['in_turn_player_tapped_blue_creatures'])),
                          Activated('4', UntapCardEffect(), T_FUNCS['your_tapped_blue_creatures'],
                                    allowed_phases=[Phase.UPKEEP])],
    'mana-clash': [Spell(ManaClash())],
    'mana-drain': [Spell(ManaDrain(), T_FUNCS['spells'])],
    'mana-matrix': [Static(ManaMatrix())],
    'mana-short': [Spell(ManaShort(), T_FUNCS['all_players'])],
    'mana-vault': [Triggered(DoesntUntapAtUntap()), untap_for_mana_at_owner_upkeep('4', T_FUNCS['card_owner']),
                   Activated('T', AddMana('C', 3), T_FUNCS['card_owner']),
                   Triggered(ManaVaultDamageIfTapped())],
    'mana-vortex': [Spell(Destroy(), T_FUNCS['your_lands']), Static(ManaVortexUpkeep()), Static(ManaVortexSac())],
    'marble-priest': [Static(MarblePriestPrevention()), Static(MarblePriestForcesBlock())],
    'marsh-gas': [Spell(MarshGas())],
    'marsh-viper': [Triggered(AddPoisonCounter(2))],
    'martyrs-cry': [Spell(MartyrsCry())],
    'martyrs-of-korlis': [Static(MartyrsOfKorlis())],
    'maze-of-ith': [Activated('T', MazeOfIth(), T_FUNCS['attackers'])],
    'meekstone': [Static(Meekstone())],
    'merchant-ship': [Triggered(MerchantShip())],
    'merfolk-assassin': [Activated('T', Destroy(), T_FUNCS['islandwalkers'])],
    'mightstone': [Static(Mightstone())],
    'mijae-djinn': [Triggered(MijaeDjinn())],
    'millstone': [Activated('2T', Millstone(), T_FUNCS['all_players'])],
    'mind-twist': [Spell(MindTwist(), T_FUNCS['all_players'], max_x_func=max_x_from_printed_card)],
    'miracle-worker': [Activated('T', Destroy(), T_FUNCS['auras_on_owners_creatures'])],
    'mirror-universe': [Activated('True', ExchangeLifeTotals(), allowed_phases=[Phase.UPKEEP],
                                  allowed_p_id_turn=T_FUNCS['card_owner'], extra_costs=[SacSelfCost()])],
    'mishras-factory': [Activated('T', AddMana('C'), T_FUNCS['card_owner'], text='Add {C}'),
                        Activated('1', BecomeCreature(2, 2, 'Assembly-Worker', True), T_FUNCS['self'], text='Become 2/2'),
                        Activated('T', Pump(1, 1, True), T_FUNCS['assembly_workers'], text='Pump Assembly-Worker')],
    'moat': [Static(Moat())],
    'mold-demon': [Spell(MoldDemon())],
    'morale': [Spell(Morale())],
    'mox-emerald': mox_specs('G'),
    'mox-jet': mox_specs('B'),
    'mox-pearl': mox_specs('W'),
    'mox-ruby': mox_specs('R'),
    'mox-sapphire': mox_specs('U'),
    'murk-dwellers': [Triggered(MurkDwellers())],
    'nameless-race': [Spell(NamelessRace())],
    'natural-selection': [Spell(NaturalSelection(), T_FUNCS['all_players'])],
    'necropolis': [Activated('', XZeroOneCountersByManaValue(), T_FUNCS['creatures_in_your_graveyard'])],
    # TODO: needs an extra cost of "Exile a creature card from your graveyard"
    'nettling-imp': [Activated('T', NettlingImp(), T_FUNCS['non_wall_creatures_wo_summoning_sickness'])],
    'nevinyrrals-disk': [Spell(TapCardEffect(), T_FUNCS['self']),
                         Activated('1T', DestroyAll(T_FUNCS['artifacts_creatures_enchantments']))],
    'niall-silvain': [Activated('GGGGT', Regenerate(), T_FUNCS['creatures'])],
    'nicol-bolas': [Triggered(PayManaOrSacAtUpkeep('UBR')), Triggered(NicolBolas())],
    'nightmare': [Static(NightmarePT())],
    'northern-paladin': [Activated('WW', Destroy(), T_FUNCS['black_permanents'])],
    'oasis': [Activated('T', PreventNextDamageBy(1), T_FUNCS['creatures'])],
    'obelisk-of-undoing': [Activated('6T', Bounce(), T_FUNCS['perms_you_own_and_control'])],
    'old-man-of-the-sea': [Activated('T', Steal(), T_FUNCS['opp_creatures_power_not_greater_than_source']),
                           Triggered(OptionalUntap()), Triggered(ReturnToOwnerOnUntap()),
                           Static(OldManOfTheSeaPowerCheck())],
    'onulet': [Triggered(Onulet())],
    'orc-general': [Activated('T', Pump(1, 1, True), T_FUNCS['your_other_orcs'],
                              extra_costs=[SacCardCost(T_FUNCS['another_orc_or_goblin'])])],
    'orcish-artillery': [Activated('T', DealDamageToTargetAndYou(2, 3), T_FUNCS['all_creatures_and_players'])],
    'orcish-mechanics': [Activated('T', DealDamage(2), T_FUNCS['all_creatures_and_players'],
                                   extra_costs=[SacCardCost(T_FUNCS['your_artifacts'])])],
    'orcish-oriflamme': [Static(OrcishOriflamme())],
    'osai-vultures': [Triggered(AddCountersIfAnyCreatureDied(CARRION)),
                      Activated('', Pump(1, 1, True),
                                extra_costs=[RemoveCounterCost(CARRION, 2)], text='Remove 2 counters for +1/+1')],
}
