from __future__ import annotations

from models.cost import SacSelfCost, ExileSelfCost, RemoveCounterCost, SacCardCost, DiscardLastCardDrawnThisTurn, \
    ExileCardCost, DiscardACard
from models.game_card.counter_tokens import CARRION, PLUS_ONE
from models.effects.base import EffSpec, Activated, Triggered, Static, Spell, GenTrig
from models.target import TargetSpec
from models.effects.listeners_mod_queries import GaeasAvengerPT, GaeasLiegePT, IvoryGuardians, KormusBell, \
    LivingLands, LivingPlane, JihadPT, PumpApplies, SelfPTEqualsFuncLen, KWAApplies, BecomeBasicLand
from models.effects.listeners_permission import Moat, Meekstone, IronclawOrcs, LivonyaSilone, WalkRuleRemoved, \
    DoesntUntapAtUntap, GoblinRockSledUntap, UnblockableCondition, NoAttacksAllowedEOT, CantAttack, \
    PreventRegenerationEOT, CantBeTargetedByAuras, GoblinRockSledCanAttack, Lure, MarblePriestForcesBlock, \
    CantAttackIfAttackedLastTurn
from .amt_funcs import AmtF
from .event_conditions import EC
from .target_funcs import ET
from ..constants import KW
from ..effects.modifiers_generic import PreventDamage, RedirectToSource
from ..effects.resolvers_f_to_o import FalseOrders, JovialEvil, MindTwist, NaturalSelection, GreatDefender, \
    HowlFromBeyond, LesserWerewolf, FallingStar, Feint, FeldonsCane, HurkylsRecall, Inquisition, \
    KryShield, ManaClash, MartyrsCry, NamelessRace, ManaShort, FireAndBrimstone, LibraryOfAlexandria, FellwarStone, \
    NettlingImp, MoldDemon, ManaDrain, IfhBiffEfreet, GlyphOfDelusion, GlyphOfReincarnation, GuardianAngel, \
    Necropolis, LifeChisel, LandsEdge
from models.effects.resolvers_generic import XZeroOneCountersByManaValue, DealDamage, \
    Destroy, DestroyAll, Regenerate, SacAll, DrawCards, DestroySelfCombatants, \
    BecomeCreature, SetColor, AllWalksRemoved, KWAModEffect, GainLife, AddMana, Bounce, Reanimate, Steal, HandToBoard, \
    Pump, TapCard, UntapCardEffect, DeclareAColor, CounterSpell, RevealTopLibraryCard, EmptyResolver, \
    CounterSpellUnlessManaPaid, RemoveFromCombat, BasePT, PumpSelf, AddCounter, MayPayMana, \
    ExchangeLifeTotals, Do, GraveyardToExile, PayManaOr, SacSelf, DrawCardsActivePlayer, DiscardAtRandom, \
    AddPoisonCounter, AddCounterPerCreatureDeath, DiscardHand, RevealHands, Mill, DrawThenDiscard, Register, Exile
from models.systems.phase import Phase
from .card_filter_funcs import C_FUNCS, A_FUNCS, CF
from .effect_spec_templates import MANA_BATTERY_ADD_CHARGE, mana_battery_add_mana, mox_specs, self_pump, \
    max_x_from_printed_card, On
from ..effects.listeners_misc import IchneumonDruid, HauntingWindActivation, LeviathanAttack, InTheEyeOfChaos, \
    InvokePrejudice
from ..effects.listeners_state_change import JihadSac, OldManOfTheSeaPowerCheck, GlobalSac
from ..effects.listeners_zone_change import LandEquilibrium
from ..effects.listeners_upkeep import Fasting, GabrielAngelfire, GhazbanOgre, HazezonTamarTokenCreation, LandTax, \
    LordOfThePitUpkeep, ManaVortexUpkeep, GiantSlugUpkeep, LeviathanUpkeep, Halfdane, LivingArtifactUpkeep
from ..effects.listeners_tap_untap import Kudzu
from ..effects.listeners_end_step import InfiniteAuthorityEndStep
from ..effects.listeners_combat import MijaeDjinn, GiantShark, Johan, InfiniteAuthorityCombatEnd, FloralSpuzzem, \
    GlyphOfDoom
from ..effects.listeners_cost import Gloom, ManaMatrix
from ..effects.listeners_damage import GaseousForm, LivingArtifactOnDamage, ForethoughtAmulet, Forcefield, GlyphOfLife
from ..effects.listeners_dies import FirestormPhoenix
from ..effects.listeners_draw_discard import IslandSanctuary
from ..effects.listeners_generic import OptionalUntap, PreventAllDamageToEOT, PreventNextDamageTo, \
    PreventAllDamageByEOT, PreventNextDamageBy, PayManaToUntapUpkeep, RedirectNextDamageFromCardToOwnerEOT, \
    PayManaOrCounterSpellListener, DestroyAtEndStep
from ..events_all import DiesEvent, UnblockedAttackerEvent, DamageResolvedEvent, DrawCardEvent, CastResolvedEvent, \
    TapCardEvent, AttackEvent, UpkeepEvent, CombatEndEvent, DamageProposedEvent, EndStepEvent, DrawStepEvent, \
    ZoneChangeEvent

MAP: dict[str: list[EffSpec]] = {
    'fallen-angel': [Activated('', Pump(2, 1, True), CF.self(),
                               extra_costs=[SacCardCost(CF.your_other_creatures())])],
    'falling-star': [Spell(FallingStar(), CF.opp_creatures(), text='If a di roll is 1-5, deal 3 damage to it')],
    'false-orders': [Spell(FalseOrders(), CF.blockers(), allowed_phases=[Phase.DECLARE_BLOCKERS])],
    'farmstead': [Spell(EmptyResolver(), CF.lands()),
                  Activated('WW', GainLife(), CF.host_owner(), allowed_phases=[Phase.UPKEEP],
                            allowed_p_turn_func=CF.host_owner(), max_activations_per_turn=1)],
    'fasting': [Triggered(Fasting(), CF.self()),
                GenTrig(On(DrawCardEvent).where(EC().you_are_drawer()).then(Destroy(CF.self())))],
    'fear': [Spell(UnblockableCondition(CF.host(), CF.non_artifact_non_black_creatures()), CF.creatures())],
    'feedback': [Spell(EmptyResolver(), CF.enchants()),
                 GenTrig(On(UpkeepEvent).where(EC().is_host_turn()).then(DealDamage(1)).t(ET.host_owner()))],
    'feint': [Spell(Feint(), CF.attackers())],
    'feldons-cane': [Activated('T', FeldonsCane(), None, extra_costs=[ExileSelfCost()])],
    'fellwar-stone': [Activated('T', FellwarStone(), is_mana_ability=True)],
    'festival': [Spell(NoAttacksAllowedEOT(), None, allowed_phases=[Phase.UPKEEP], allowed_p_turn_func=CF.opp())],
    'field-of-dreams': [GenTrig(On(ZoneChangeEvent).where(EC().zone_is_library()).then(RevealTopLibraryCard())),
                        Spell(RevealTopLibraryCard())],
    'fire-and-brimstone': [Spell(FireAndBrimstone(),)],
    'fire-drake': [Activated('R', Pump(1, 0, True), CF.self(), max_activations_per_turn=1)],
    'fire-sprites': [Activated('GT', AddMana('R'), CF.owner(), is_mana_ability=True)],
    'firebreathing': [Spell(EmptyResolver(), CF.creatures()), self_pump('R', 1, 0)],
    'firestorm-phoenix': [Triggered(FirestormPhoenix())],
    'fishliver-oil': [Spell(KWAModEffect('add', KW.ISLANDWALK), CF.creatures())],
    'fissure': [Spell(Destroy(allow_regen=False), CF.creatures_and_lands())],
    'flash-counter': [Spell(CounterSpell(), CF.instant_spells())],
    'flash-flood': [Spell(Destroy(), CF.red_permanents()), Spell(Bounce(), CF.mountains())],
    'flashfires': [Spell(DestroyAll(CF.plains()))],
    'flight': [Spell(KWAModEffect('add', KW.FLYING), CF.creatures())],
    'flood': [Activated('UU', TapCard(), CF.untapped_creatures_without_flying())],
    'floral-spuzzem': [Triggered(FloralSpuzzem())],
    'flying-carpet': [Activated('2T', KWAModEffect('add', KW.FLYING, True), CF.creatures())],
    'fog': [GenTrig(On(DamageProposedEvent, expires='EOT').where(EC().is_combat_damage()).modify(PreventDamage()))],
    'force-of-nature': [GenTrig(On(UpkeepEvent).where(EC().is_your_turn()).
                                then(PayManaOr('GGGG', DealDamage(8, CF.owner()))))],
    'force-spike': [Spell(CounterSpellUnlessManaPaid('1'), CF.spells())],
    'forcefield': [Activated('1', Forcefield(), CF.unblocked_attackers())],
    'forethought-amulet': [GenTrig(On(UpkeepEvent).where(EC().is_your_turn()).then(PayManaOr('3', SacSelf()))),
                           Static(ForethoughtAmulet())],
    'fountain-of-youth': [Activated('2T', GainLife(), CF.owner())],
    'frozen-shade': [self_pump('B', 1, 1)],
    'fungusaur': [GenTrig(On(DamageResolvedEvent).where(EC().self_is_damage_receiver()).then(AddCounter(PLUS_ONE)))],
    'gabriel-angelfire': [Triggered(GabrielAngelfire())],
    'gaeas-avenger': [Static(GaeasAvengerPT())],
    'gaeas-liege': [Static(GaeasLiegePT()), Activated('T', BecomeBasicLand('forest'), CF.lands())],
    'gaeas-touch': [Activated('', AddMana('G', 2), CF.owner(), is_mana_ability=True, extra_costs=[SacSelfCost()],
                              text='Exile for {GG}'),
                    Activated('', HandToBoard(), CF.forests_in_your_hand(), text='Play extra forest',
                              allowed_p_turn_func=CF.owner(), max_activations_per_turn=1)],
    'gaseous-form': [Spell(GaseousForm(), CF.creatures())],
    'gate-to-phyrexia': [Activated('', Destroy(), CF.artifacts(), extra_costs=[SacCardCost(CF.your_creatures())],
                                   allowed_phases=[Phase.UPKEEP], max_activations_per_turn=1,
                                   allowed_p_turn_func=CF.owner())],
    'ghazban-ogre': [Triggered(GhazbanOgre())],
    'ghost-ship': [Activated('UUU', Regenerate(), CF.self())],
    'ghosts-of-the-damned': [Activated('T', Pump(-1, 0, True), CF.creatures())],
    'giant-growth': [Spell(Pump(3, 3, True), CF.creatures())],
    'giant-shark': [Triggered(GiantShark())],
    'giant-slug': [Activated('5', GiantSlugUpkeep())],
    'giant-strength': [Spell(Pump(2, 2), CF.creatures())],
    'giant-tortoise': [Static(PumpApplies(CF.self(), (0, 3), cond=C_FUNCS['self_is_untapped']))],
    'giant-turtle': [Triggered(CantAttackIfAttackedLastTurn())],
    'glasses-of-urza': [Activated('T', RevealHands(CF.opp()))],
    'gloom': [Static(Gloom())],
    'glyph-of-delusion': [Spell(GlyphOfDelusion(), CF.walls())],
    'glyph-of-destruction': [Spell(Do(Pump(10, 0, True), Register(PreventAllDamageToEOT, target_attr='target'),
                                      Register(DestroyAtEndStep, target_attr='card_to_be_destroyed')), CF.your_walls())],
    'glyph-of-doom': [Spell(GlyphOfDoom(), CF.walls())],
    'glyph-of-life': [Spell(GlyphOfLife(), CF.walls())],
    'glyph-of-reincarnation': [Spell(GlyphOfReincarnation(), CF.walls(),
                                     allowed_phases=[p for p in Phase if p >= Phase.COMBAT_END])],
    'goblin-balloon-brigade': [Activated('R', KWAModEffect('add', KW.FLYING, True), CF.self())],
    'goblin-caves': [Static(PumpApplies(CF.goblins(), (0, 2), cond=C_FUNCS['host_is_basic_mountain']))],
    'goblin-digging-team': [Activated('T', Destroy(), CF.walls(), extra_costs=[SacSelfCost()])],
    'goblin-king': [Static(PumpApplies(CF.your_other_goblins(), (1, 1))),
                    Static(KWAApplies(CF.your_other_goblins(), 'add', KW.MOUNTAINWALK))],
    'goblin-rock-sled': [Static(GoblinRockSledUntap()), Static(GoblinRockSledCanAttack())],
    'goblin-shrine': [Static(PumpApplies(CF.goblins(), (1, 0), cond=C_FUNCS['host_is_basic_mountain'])),
                      GenTrig(On(ZoneChangeEvent).where(EC().card_is_source()).then(DealDamage(1, CF.goblins())))],
    'goblin-wizard': [Activated('T', HandToBoard(), CF.goblin_permanents_in_your_hand()),
                      Activated('T', KWAModEffect('add', KW.PROTECTION_FROM_WHITE, True), CF.goblins())],
    'goblins-of-the-flarg': [Static(GlobalSac(CF.self(), C_FUNCS['you_have_a_dwarf']))],
    'golgothian-sylex': [Activated('1T', SacAll(CF.golgothian_sylex()))],
    'gosta-dirk': [Static(WalkRuleRemoved(KW.ISLANDWALK))],
    'granite-gargoyle': [self_pump('R', 0, 1)],
    'grapeshot-catapult': [Activated('T', DealDamage(4), CF.fliers())],
    'grave-robbers': [Activated('BT', Do(GraveyardToExile(), GainLife(2)), CF.artifacts_in_graveyards())],
    'gravity-sphere': [Static(KWAApplies(CF.creatures(), 'remove', KW.FLYING))],
    'great-defender': [Spell(GreatDefender(), CF.creatures())],
    'great-wall': [Static(WalkRuleRemoved(KW.PLAINSWALK))],
    'greater-realm-of-preservation': [Activated('1W', PreventNextDamageTo(protected=CF.owner()), CF.black_and_red())],
    'greed': [Activated('B', Do(DrawCards(), DealDamage(2, CF.owner())))],
    'green-mana-battery': [MANA_BATTERY_ADD_CHARGE, mana_battery_add_mana('G')],
    'green-ward': [Spell(KWAModEffect('add', KW.PROTECTION_FROM_GREEN), CF.creatures())],
    'guardian-angel': [Spell(GuardianAngel(), CF.all_creatures_and_players())],
    'guardian-beast': [Static(KWAApplies(CF.your_non_creature_artifacts(), 'add', KW.INDESTRUCTIBLE,
                                         C_FUNCS['self_is_untapped'])),
                       Static(CantBeTargetedByAuras(CF.your_non_creature_artifacts(),
                                                    condition_func=C_FUNCS['self_is_untapped']))],
    'gwendlyn-di-corci': [Activated('T', DiscardAtRandom(), CF.all_players(), allowed_p_turn_func=CF.owner())],
    'halfdane': [Triggered(Halfdane())],
    'hammerheim': [Activated('T', AddMana('R'), CF.owner(), is_mana_ability=True),
                   Activated('T', AllWalksRemoved(), CF.creatures())],
    'hasran-ogress': [GenTrig(On(AttackEvent).where(EC().self_is_attacker()).
                              then(PayManaOr('2', DealDamage(3, CF.owner()))))],
    'haunting-wind': [Triggered(HauntingWindActivation()),
                      GenTrig(On(TapCardEvent).where(EC().card_is_artifact()).
                              then(DealDamage(1)).t(ET.event_card_owner()))],
    'hazezon-tamar': [Triggered(HazezonTamarTokenCreation()),
                      GenTrig(On(ZoneChangeEvent).where(EC().card_is_source()).then(Exile(CF.sand_warriors())))],
    'healing-salve': [Spell(GainLife(3)), Spell(PreventNextDamageTo(3), CF.all_creatures_and_players())],
    'heavens-gate': [Spell(SetColor('W', 'EOT'), TargetSpec(CF.creatures(), 1, None))],
    'hell-swarm': [Spell(PumpApplies(CF.creatures(), (-1, 0), True))],
    'hells-caretaker': [Activated('T', Reanimate(), CF.creatures_in_your_graveyard(), allowed_phases=[Phase.UPKEEP],
                                  allowed_p_turn_func=CF.owner(), extra_costs=[SacCardCost(CF.your_creatures())])],
    'hidden-path': [Static(KWAApplies(CF.green_creatures(), 'add', KW.FORESTWALK))],
    'holy-armor': [Spell(Pump(0, 2), CF.creatures()),
                   Activated('W', Pump(0, 1, True), CF.host())],
    'holy-day': [GenTrig(On(DamageProposedEvent, expires='EOT').where(EC().is_combat_damage()).modify(PreventDamage()))],
    'holy-light': [Spell(PumpApplies(CF.non_white_creatures(), (-1, -1), True))],
    'holy-strength': [Spell(Pump(1, 2), CF.creatures())],
    'horn-of-deafening': [Activated('2T', PreventNextDamageTo(protected=CF.owner(), combat_only=True), CF.creatures())],
    'horror-of-horrors': [Activated('', Regenerate(), CF.black_creatures(),
                                    extra_costs=[SacCardCost(CF.your_swamps())])],
    'howl-from-beyond': [Spell(HowlFromBeyond(), CF.creatures())],
    'howling-mine': [GenTrig(On(DrawStepEvent).where(EC().self_is_untapped()).then(DrawCardsActivePlayer()))],
    'hurkyls-recall': [Spell(HurkylsRecall(), CF.all_players())],
    'hurr-jackal': [Activated('T', PreventRegenerationEOT(), CF.creatures())],
    'hyperion-blacksmith': [Activated('T', TapCard(), CF.opp_untapped_artifacts()),
                            Activated('T', UntapCardEffect(), CF.opp_tapped_artifacts())],
    'hypnotic-specter': [GenTrig(On(DamageResolvedEvent).
                                 where(EC().self_is_damager().opp_is_damage_receiver()).then(DiscardAtRandom()))],
    'ichneumon-druid': [Triggered(IchneumonDruid())],
    'icy-manipulator': [Activated('1T', TapCard(), CF.untapped_artifacts_creatures_lands())],
    'ice-storm': [Spell(Destroy(), CF.lands())],
    'ifh-biff-efreet': [Activated('G', IfhBiffEfreet(), allowed_activators=A_FUNCS['all_players'])],
    'immolation': [Spell(Pump(2, -2), CF.creatures())],
    'in-the-eye-of-chaos': [Static(InTheEyeOfChaos())],
    'indestructible-aura': [Spell(PreventAllDamageToEOT(), CF.creatures())],
    'infernal-medusa': [GenTrig(On(CombatEndEvent).where(EC().self_is_attacker()).
                                then(DestroySelfCombatants(filter_func=CF.non_wall_creatures()))),
                        GenTrig(On(CombatEndEvent).where(EC().self_is_blocker()).then(DestroySelfCombatants()))],
    'inferno': [Spell(DealDamage(6, CF.all_creatures_and_players()))],
    'infinite-authority': [Triggered(InfiniteAuthorityCombatEnd()), Triggered(InfiniteAuthorityEndStep())],
    'instill-energy': [Spell(KWAModEffect('add', KW.HASTE), CF.creatures()),
                       Activated('', UntapCardEffect(), CF.host(), allowed_p_turn_func=CF.host_owner(),
                                 max_activations_per_turn=1)],
    'invisibility': [Spell(UnblockableCondition(CF.host(), CF.non_wall_creatures()), CF.creatures())],
    'inquisition': [Spell(Inquisition(), CF.all_players())],
    'invoke-prejudice': [Static(InvokePrejudice())],
    'iron-star': [GenTrig(On(CastResolvedEvent).where(EC().card_is_color('R')).then(MayPayMana('1', GainLife(1))))],
    'ironclaw-orcs': [Static(IronclawOrcs())],
    'island-fish-jasconius': [Triggered(DoesntUntapAtUntap(CF.self())),
                              Triggered(PayManaToUntapUpkeep('UU', CF.self()))],
    'island-of-wak-wak': [Activated('T', BasePT(base_p=0, base_t=None, eot=True), CF.fliers())],
    'island-sanctuary': [Static(IslandSanctuary())],
    'ivory-cup': [GenTrig(On(CastResolvedEvent).where(EC().card_is_color('W')).then(MayPayMana('1', GainLife(1))))],
    'ivory-guardians': [Static(IvoryGuardians())],
    'ivory-tower': [GenTrig(On(UpkeepEvent).where(EC().is_your_turn().hand_size_greater_than(CF.owner(), 4)).
                            then(GainLife(p_func=CF.owner(), amt_func=AmtF.t_hand_size(-4))))],
    'jacques-le-vert': [Static(PumpApplies(CF.your_green_creatures(), (0, 2)))],
    'jade-monolith': [Activated('1', RedirectNextDamageFromCardToOwnerEOT(), CF.creatures())],
    'jade-statue': [Activated('2', BecomeCreature(3, 6, 'Golem', True), CF.self(), allowed_phases=[Phase.MAIN])],
    'jalum-tome': [Activated('2T', DrawThenDiscard(), text='Draw one card; discard one card')],
    'jandors-ring': [Activated('2T', DrawCards(), CF.owner(), extra_costs=[DiscardLastCardDrawnThisTurn()])],
    'jandors-saddlebags': [Activated('3T', UntapCardEffect(), CF.tapped_creatures())],
    'jayemdae-tome': [Activated('4T', DrawCards(), CF.owner())],
    'jihad': [Static(JihadPT()), Static(JihadSac()), Spell(DeclareAColor())],
    'johan': [Triggered(Johan())],
    'jovial-evil': [Spell(JovialEvil(), CF.opp())],
    'juggernaut': [Static(UnblockableCondition(CF.self(), CF.walls()))],
    'jump': [Spell(KWAModEffect('add', KW.FLYING, True), CF.creatures())],
    'junun-efreet': [GenTrig(On(UpkeepEvent).where(EC().is_your_turn()).then(PayManaOr('BB', SacSelf())))],
    'juzam-djinn': [GenTrig(On(UpkeepEvent).where(EC().is_your_turn()).then(DealDamage(1)).t(ET.s_owner()))],
    'karakas': [Activated('T', AddMana('W'), is_mana_ability=True), Activated('T', Bounce(), CF.legendary_creatures())],
    'karma': [GenTrig(On(UpkeepEvent).where(EC().in_turn_p_has_swamps()).
                      then(DealDamage(to=CF.in_turn_player(), amt_func=AmtF.t_swamp_cnt())))],
    'kei-takahashi': [Activated('T', PreventNextDamageBy(preventable_amt=2), CF.creatures())],
    'keldon-warlord': [Static(SelfPTEqualsFuncLen(CF.your_non_wall_creatures()))],
    'khabal-ghoul': [GenTrig(On(EndStepEvent).where(EC().any_creature_died_this_turn()).
                             then(AddCounterPerCreatureDeath(PLUS_ONE)))],
    'killer-bees': [self_pump('G', 1, 1)],
    'king-suleiman': [Activated('T', Destroy(), CF.djinns_and_efreets())],
    'kird-ape': [Static(PumpApplies(CF.self(), (1, 2), cond=C_FUNCS['you_have_a_forest']))],
    'kismet': [GenTrig(On(ZoneChangeEvent).where(EC().card_is_opponents().card_is_artifact_crature_land()).
                       then(TapCard()).t(ET.event_card()))],
    'kobold-drill-sergeant': [Static(PumpApplies(CF.your_other_kobolds(), (0, 1))),
                              Static(KWAApplies(CF.your_other_kobolds(), 'add', KW.TRAMPLE))],
    'kobold-overlord': [Static(KWAApplies(CF.your_other_kobolds(), 'add', KW.FIRST_STRIKE))],
    'kobold-taskmaster': [Static(PumpApplies(CF.your_other_kobolds(), (0, 1)))],
    'kormus-bell': [Static(KormusBell())],
    'kry-shield': [Activated('2T', KryShield(), CF.your_creatures())],
    'kudzu': [Spell(Kudzu(), CF.lands())],
    'lady-caleria': [Activated('T', DealDamage(3), CF.combatants())],
    'lady-evangela': [Activated('WBT', PreventAllDamageByEOT(combat_only=True), CF.creatures())],
    'lance': [Spell(KWAModEffect('add', KW.FIRST_STRIKE), CF.creatures())],
    'land-equilibrium': [Static(LandEquilibrium())],
    'land-tax': [Triggered(LandTax())],
    'lands-edge': [Activated('', LandsEdge(), CF.all_players(), allowed_activators=A_FUNCS['all_players'],
                             extra_costs=[DiscardACard(CF.cards_in_your_hand())])],
    'lesser-werewolf': [Activated('B', LesserWerewolf(), CF.combating_against(),
                                  allowed_phases=[Phase.DECLARE_BLOCKERS])],
    'leviathan': [Static(DoesntUntapAtUntap(CF.self())), Static(CantAttack(CF.self())),
                  Triggered(LeviathanUpkeep()), Triggered(LeviathanAttack()), Spell(TapCard(), CF.self())],
    'ley-druid': [Activated('T', UntapCardEffect(), CF.tapped_lands())],
    'library-of-alexandria': [Activated('T', AddMana('C'), is_mana_ability=True),
                              Activated('T', LibraryOfAlexandria())],
    'life-chisel': [Spell(LifeChisel(), allowed_phases=[Phase.UPKEEP], allowed_p_turn_func=CF.owner(),
                          extra_costs=[SacCardCost(CF.your_artifacts())])],
    'lifeblood': [GenTrig(On(TapCardEvent).where(EC().card_is_mountain().card_is_opponents()).then(GainLife()))],
    'lifeforce': [Activated('GG', CounterSpell(), CF.black_spells())],
    'lifelace': [Spell(SetColor('G'), CF.cards())],
    'lifetap': [GenTrig(On(TapCardEvent).where(EC().card_is_forest().card_is_opponents()).then(GainLife()))],
    'lightning-bolt': [Spell(DealDamage(3), CF.all_creatures_and_players())],
    'living-armor': [Activated('T', XZeroOneCountersByManaValue(), CF.creatures(), extra_costs=[SacSelfCost()])],
    'living-artifact': [Spell(EmptyResolver(), CF.artifacts()), Triggered(LivingArtifactOnDamage()),
                        Triggered(LivingArtifactUpkeep())],
    'living-lands': [Static(LivingLands())],
    'living-plane': [Static(LivingPlane())],
    'living-wall': [Activated('1', Regenerate(), CF.self())],
    'livonya-silone': [Static(LivonyaSilone())],
    'llanowar-elves': [Activated('T', AddMana('G'), CF.owner(), is_mana_ability=True)],
    'lord-of-atlantis': [Static(PumpApplies(CF.other_merfolk(), (1, 1))),
                         Static(KWAApplies(CF.other_merfolk(), 'add', KW.ISLANDWALK))],
    'lord-of-the-pit': [Triggered(LordOfThePitUpkeep())],
    'lord-magnus': [Static(WalkRuleRemoved(KW.PLAINSWALK)), Static(WalkRuleRemoved(KW.FORESTWALK))],
    'lure': [Spell(Lure(), CF.creatures())],
    'magnetic-mountain': [Triggered(DoesntUntapAtUntap(CF.in_turn_player_tapped_blue_creatures())),
                          Triggered(PayManaToUntapUpkeep('4', CF.in_turn_player_tapped_blue_creatures()))],
    'mana-clash': [Spell(ManaClash())],
    'mana-drain': [Spell(ManaDrain(), CF.spells())],
    'mana-matrix': [Static(ManaMatrix())],
    'mana-short': [Spell(ManaShort(), CF.all_players())],
    'mana-vault': [Triggered(DoesntUntapAtUntap(CF.self())), Triggered(PayManaToUntapUpkeep('4', CF.self())),
                   Activated('T', AddMana('C', 3), CF.owner(), is_mana_ability=True),
                   GenTrig(On(DrawStepEvent).where(EC().is_your_turn().self_is_tapped()).
                           then(DealDamage(1, CF.owner())))],
    'mana-vortex': [Spell(Destroy(), CF.your_lands()), Static(ManaVortexUpkeep()),
                    Static(GlobalSac(CF.self(), C_FUNCS['no_lands']))],
    'marble-priest': [GenTrig(On(DamageProposedEvent).
                              where(EC().damage_target_in(CF.self()).damage_source_in(CF.walls()).is_combat_damage()).
                              modify(PreventDamage())),
                      Static(MarblePriestForcesBlock())],
    'marsh-gas': [Spell(PumpApplies(CF.creatures(), (-2, 0), True))],
    'marsh-viper': [GenTrig(On(DamageResolvedEvent).where(EC().source_damaged_opp()).then(AddPoisonCounter(2)))],
    'martyrs-cry': [Spell(MartyrsCry())],
    'martyrs-of-korlis': [GenTrig(On(DamageProposedEvent).
                                  where(EC().self_is_untapped().damage_source_in(CF.artifacts()).
                                        damage_target_in(CF.owner())).modify(RedirectToSource()))],
    'maze-of-ith': [Activated('T', RemoveFromCombat(), CF.attackers())],
    'meekstone': [Static(Meekstone())],
    'merchant-ship': [GenTrig(On(UnblockedAttackerEvent).where(EC().self_is_unblocked_attacker()).then(GainLife(2)))],
    'merfolk-assassin': [Activated('T', Destroy(), CF.islandwalkers())],
    'mightstone': [Static(PumpApplies(CF.attackers(), (1, 0)))],
    'mijae-djinn': [Triggered(MijaeDjinn())],
    'millstone': [Activated('2T', Mill(2), CF.all_players())],
    'mind-twist': [Spell(MindTwist(), CF.all_players(), max_x_func=max_x_from_printed_card)],
    'miracle-worker': [Activated('T', Destroy(), CF.auras_on_owners_creatures())],
    'mirror-universe': [Activated('T', ExchangeLifeTotals(), allowed_phases=[Phase.UPKEEP],
                                  allowed_p_turn_func=CF.owner(), extra_costs=[SacSelfCost()])],
    'mishras-factory': [Activated('T', AddMana('C'), CF.owner(), is_mana_ability=True, text='Add {C}'),
                        Activated('1', BecomeCreature(2, 2, 'Assembly-Worker', True), CF.self(), text='Become 2/2'),
                        Activated('T', Pump(1, 1, True), CF.assembly_workers(), text='Pump Assembly-Worker')],
    'moat': [Static(Moat())],
    'mold-demon': [Spell(MoldDemon())],
    'morale': [Spell(PumpApplies(CF.attackers(), (1, 1), True))],
    'mox-emerald': mox_specs('G'),
    'mox-jet': mox_specs('B'),
    'mox-pearl': mox_specs('W'),
    'mox-ruby': mox_specs('R'),
    'mox-sapphire': mox_specs('U'),
    'murk-dwellers': [GenTrig(On(UnblockedAttackerEvent).where(EC().self_is_unblocked_attacker()).then(PumpSelf(2, 0, True)))],
    'nameless-race': [Spell(NamelessRace())],
    'natural-selection': [Spell(NaturalSelection(), CF.all_players())],
    'necropolis': [Activated('', Necropolis(), extra_costs=[ExileCardCost(CF.creatures_in_your_graveyard())])],
    'nether-void': [Triggered(PayManaOrCounterSpellListener('3'))],
    'nettling-imp': [Activated('T', NettlingImp(), CF.non_wall_creatures_wo_summoning_sickness())],
    'nevinyrrals-disk': [Spell(TapCard(), CF.self()),
                         Activated('1T', DestroyAll(CF.artifacts_creatures_enchantments()))],
    'niall-silvain': [Activated('GGGGT', Regenerate(), CF.creatures())],
    'nicol-bolas': [GenTrig(On(UpkeepEvent).where(EC().is_your_turn()).then(PayManaOr('UBR', SacSelf()))),
                    GenTrig(On(DamageResolvedEvent).where(EC().damage_target_in(CF.opp()).damage_source_in(CF.self())).
                            then(DiscardHand()))],
    'nightmare': [Static(SelfPTEqualsFuncLen(CF.your_swamps()))],
    'northern-paladin': [Activated('WW', Destroy(), CF.black_permanents())],
    'oasis': [Activated('T', PreventNextDamageBy(preventable_amt=1), CF.creatures())],
    'obelisk-of-undoing': [Activated('6T', Bounce(), CF.perms_you_own_and_control())],
    'old-man-of-the-sea': [Activated('T', Steal(return_on_untap=True),
                                     CF.opp_creatures_power_not_greater_than_source()),
                           Triggered(OptionalUntap()), Static(OldManOfTheSeaPowerCheck())],
    'onulet': [GenTrig(On(DiesEvent).where(EC().card_is_source()).then(GainLife(2)))],
    'orc-general': [Activated('T', Pump(1, 1, True), CF.your_other_orcs(),
                              extra_costs=[SacCardCost(CF.another_orc_or_goblin())])],
    'orcish-artillery': [Activated('T', Do(DealDamage(2), DealDamage(3, CF.owner())), CF.all_creatures_and_players())],
    'orcish-mechanics': [Activated('T', DealDamage(2), CF.all_creatures_and_players(),
                                   extra_costs=[SacCardCost(CF.your_artifacts())])],
    'orcish-oriflamme': [Static(PumpApplies(CF.your_attackers(), (1, 0)))],
    'osai-vultures': [GenTrig(On(EndStepEvent).where(EC().any_creature_died_this_turn()).then(AddCounter(CARRION))),
                      Activated('', Pump(1, 1, True),
                                extra_costs=[RemoveCounterCost(CARRION, 2)], text='Remove 2 counters for +1/+1')],
}
