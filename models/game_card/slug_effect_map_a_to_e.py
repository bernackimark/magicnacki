from __future__ import annotations
from itertools import combinations

from .amt_funcs import AmtF
from .card_filter_funcs import C_FUNCS, A_FUNCS, CF
from models.constants import COLOR_LETTERS, KW
from models.cost import SacSelfCost, DiscardAtRandomCost, SacCardCost
from models.game_card.counter_tokens import PLUS_ONE_ZERO, PLUS_ONE, DOOM, STORAGE, STUN, PUPA
from models.effects.base import EffSpec, Activated, Triggered, Static, Spell, GenTrig
from .event_conditions import EC
from .target_funcs import ET
from ..effects.modifiers_generic import PreventDamage
from ..events_all import AttackEvent, DiesEvent, BlockEvent, CombatEndEvent, UpkeepEvent, EndStepEvent, \
    CastResolvedEvent, TapCardEvent, DamageProposedEvent
from ..target import TargetSpec
from ..effects.resolvers_a_to_e import Disharmony, CityOfShadowsAddMana, Banshee, Earthquake, EternalFlame, DustToDust, EaterOfTheDead, \
    EvilPresence, DrainPower, EnergyTap, Berserk, BloodLust, Amnesia, BottleOfSuleiman, ChaosOrb, DiamondValley, ConsecrateLand, \
    Crumble, Earthbind, EnchantmentAlteration, DanceOfMany, Disintegrate, CuombajjWitches, Cleansing, DrafnasRestoration, Eureka
from models.effects.resolvers_generic import AddCounter, DealDamage, Destroy, DestroyAll, \
    Regenerate, SacAll, DrawCards, Discard, SetColor, KWAModEffect, GainLife, AddMana, Bounce, Steal, \
    Pump, CreateTokenCreature, RemoveHostAuras, TapCardEffect, UntapCardEffect, UntapCards, RemoveFromCombat, \
    CounterSpell, BecomeCreaturePTEqualsManaValue, EmptyResolver, RemoveCounter, PumpSelf, DestroySelfCombatants, \
    MayPayMana, Do, Reanimate, GainLifeTargetMV, PayManaOr, SacSelf, Exile, TapCards, AddType, DrawThenDiscard, Copy, \
    Tutor
from .effect_spec_templates import dual_land_specs, MANA_BATTERY_ADD_CHARGE, mana_battery_add_mana, self_pump, \
    clockwork_avian_x, clockwork_beast_x, max_x_from_printed_card, your_tapped_land_cnt_and_max_x, On
from ..effects.listeners_misc import AliFromCairo, ArtifactPossessionActivation
from ..effects.listeners_state_change import GlobalSac
from ..effects.listeners_zone_change import AnkhOfMishra, DingusEgg
from ..effects.listeners_upkeep import BlackVise, CocoonUpkeep, CurseArtifact, Cyclone, \
    DemonicHordesUpkeep, DropOfHoney, ElderSpawnUpkeep, EnergyFlux, ErhnamDjinn, ErosionUpkeep
from ..effects.listeners_end_step import DragonWhelpEndStep, ErgRaiders
from ..effects.listeners_draw_discard import CursedRack, ArmageddonClockDrawStep
from ..effects.listeners_dies import AxelrodGunnarson, CreatureBond, BlazingEffigy, BrineHag
from ..effects.listeners_damage import Backfire, ElHajjaj, EyeForAnEye, BloodOfTheMartyr
from ..effects.listeners_combat import AislingLeprechaun
from ..effects.listeners_generic import UntapRemovesPumpFromAnotherCard, OptionalUntap, \
    PreventNextDamageTo, PreventNextDamageBy, PayManaToUntapUpkeep
from models.effects.listeners_permission import ArtifactWardCanBeTargeted, AkronLegionnaire, \
    EvilEyeOfOrmsByGoreMyNonEyeNoAttack, CantBeTargetedByAuras, HostCantAttack, \
    WalkRuleRemoved, DampingField, DoesntUntapAtUntap, CocoonUntap, HostCanAttack, UnblockableCondition, \
    UnblockableEOT, PreventRegenerationEOT, RegenerateSelf, AttackerCountMax, BlockerCountMax, CantCastAppliesTo, \
    HostCantBeTargetedBySpells, Arboria
from models.effects.listeners_mod_queries import AngelicVoices, AngryMobPT, \
    AspectOfWolfPT, Conversion, PumpApplies, SelfPTEqualsFuncLen, KWAApplies, BloodMoon, ManaProdAlter
from models.systems.phase import Phase

MAP: dict[str, list[EffSpec]] = {
    'abomination': [GenTrig(On(CombatEndEvent).where(EC.self_is_combatant()).
                            then(DestroySelfCombatants(filter_func=CF.green_and_white_creatures())))],
    'abu-jafar': [GenTrig(On(DiesEvent).where(EC.card_is_source()).then(DestroySelfCombatants(allow_regen=False)))],
    'acid-rain': [Spell(DestroyAll(CF.forests()))],
    'active-volcano': [Spell(Destroy(), CF.blue_permanents()), Spell(Bounce(), CF.islands())],
    'adun-oakenshield': [Activated('BRGT', Bounce(), CF.creatures_in_your_graveyard())],
    'aisling-leprechaun': [Triggered(AislingLeprechaun())],
    'akron-legionnaire': [Static(AkronLegionnaire())],
    'al-abaras-carpet': [Activated('5T', On(DamageProposedEvent, 'EOT').
                                   where(EC.damage_target_in(CF.owner()), EC.damage_source_in(CF.non_fliers())).
                                   modify(PreventDamage()).build())],
    'alabaster-potion': [Spell(GainLife(), CF.all_players(), max_x_func=max_x_from_printed_card,
                               text="Target player gains X life"),
                         Spell(PreventNextDamageTo(), CF.all_creatures_and_players(),
                               max_x_func=max_x_from_printed_card,
                               text="Prevent the next X damage that would be dealt to any target this turn")],
    'aladdin': [Activated('1RRT', Steal(), CF.opp_artifacts())],
    'aladdins-ring': [Activated('8T', DealDamage(4), CF.all_creatures_and_players())],
    'ali-baba': [Activated('R', TapCardEffect(), CF.walls())],
    'ali-from-cairo': [Static(AliFromCairo())],
    'alchors-tomb': [Activated('2T', SetColor(c), CF.your_permanents(), text=f'Set color to {{{c}}}')
                     for c in COLOR_LETTERS],
    'amnesia': [Spell(Amnesia(), CF.all_players())],
    'amrou-kithkin': [Static(UnblockableCondition(CF.self(), CF.creatures_power_three_or_more()))],
    'amulet-of-kroog': [Activated('2T', PreventNextDamageBy(preventable_amt=1), CF.all_creatures_and_players())],
    'ancestral-recall': [Spell(DrawCards(3), CF.all_players())],
    'angelic-voices': [Static(AngelicVoices())],
    'angus-mackenzie': [Activated('GWUT', On(DamageProposedEvent, 'EOT').where(EC.is_combat_damage()).
                                  modify(PreventDamage()).build(),
                                  allowed_phases=[p for p in Phase if p < Phase.COMBAT_DAMAGE])],
    'angry-mob': [Static(AngryMobPT())],
    'animate-artifact': [Spell(BecomeCreaturePTEqualsManaValue(), CF.non_creature_artifacts())],
    'animate-dead': [Spell(Do(Reanimate(), Pump(-1, 0)), CF.creatures_in_your_graveyard())],
    'animate-wall': [Spell(HostCanAttack(), CF.walls())],
    'ankh-of-mishra': [Triggered(AnkhOfMishra())],
    'anti-magic-aura': [Static(CantBeTargetedByAuras(CF.host())), Static(HostCantBeTargetedBySpells()),
                        Spell(RemoveHostAuras(), CF.creatures())],
    'apprentice-wizard': [Activated('UT', AddMana('C', 3), CF.owner(), is_mana_ability=True)],
    'arboria': [Static(Arboria())],
    'arcades-sabboth': [GenTrig(On(UpkeepEvent).where(EC.is_your_turn()).then(PayManaOr('GWU', SacSelf()))),
                        self_pump('W', 0, 1),
                        Static(PumpApplies(CF.your_untapped_non_attacking_creatures(), (0, 2)))],
    'arena-of-the-ancients': [Static(DoesntUntapAtUntap(CF.legendary_creatures())),
                              Spell(TapCards(CF.legendary_creatures()))],
    'argivian-archaeologist': [Activated('WWT', Bounce(), CF.artifacts_in_your_graveyard())],
    'argivian-blacksmith': [Activated('T', PreventNextDamageBy(preventable_amt=2), CF.artifact_creatures())],
    'argothian-pixies': [Static(UnblockableCondition(CF.self(), CF.artifact_creatures())),
                         GenTrig(On(DamageProposedEvent).
                                 where(EC.damage_target_in(CF.self()), EC.damage_source_in(CF.artifact_creatures())).
                                 modify(PreventDamage()))],
    'argothian-treefolk': [GenTrig(On(DamageProposedEvent).
                                   where(EC.damage_target_in(CF.self()), EC.damage_source_in(CF.artifact_creatures())).
                                   modify(PreventDamage()))],
    'armageddon': [Spell(DestroyAll(CF.lands()))],
    'armageddon-clock': [Activated('4', RemoveCounter(DOOM),
                                   allowed_phases=[Phase.UPKEEP], allowed_activators=A_FUNCS['all_players']),
                         GenTrig(On(UpkeepEvent).where(EC.is_your_turn()).then(AddCounter(DOOM))),
                         Triggered(ArmageddonClockDrawStep())],
    'army-of-allah': [Spell(PumpApplies(CF.attackers(), (2, 0), True))],
    'artifact-blast': [Spell(CounterSpell(), CF.artifact_spells())],
    'artifact-possession': [Triggered(ArtifactPossessionActivation()),
                            GenTrig(On(TapCardEvent).where(EC.card_is_host()).then(DealDamage(2)).t(ET.host_owner())),
                            Spell(EmptyResolver(), CF.artifacts())],
    'artifact-ward': [Spell(EmptyResolver(), CF.creatures()), Static(ArtifactWardCanBeTargeted()),
                      Static(UnblockableCondition(CF.host(), CF.artifact_creatures())),
                      GenTrig(On(DamageProposedEvent).
                              where(EC.damage_target_in(CF.host()), EC.damage_source_in(CF.artifacts())).
                              modify(PreventDamage()))],
    'ashes-to-ashes': [Spell(Do(Exile(), DealDamage(5, CF.owner())), TargetSpec(CF.non_artifact_creatures(), 2, 2))],
    'ashnods-altar': [Activated('', AddMana('C', 2), is_mana_ability=True
                                , extra_costs=[SacCardCost(CF.your_creatures())])],
    'ashnods-battle-gear': [Activated('2T', Pump(2, -2), CF.your_creatures()),
                            Triggered(OptionalUntap()), Triggered(UntapRemovesPumpFromAnotherCard())],
    'ashnods-transmogrant': [Activated('T', Do(AddCounter(PLUS_ONE), AddType('Artifact')), CF.non_artifact_creatures(),
                                       extra_costs=[SacSelfCost()])],
    'aspect-of-wolf': [Static(AspectOfWolfPT())],
    'atog': [Activated('', Pump(2, 2), CF.self(), extra_costs=[SacCardCost(CF.your_artifacts())])],
    'avoid-fate': [Spell(CounterSpell(), CF.spells_aura_or_instant_targeting_your_perm())],
    'axelrod-gunnarson': [Triggered(AxelrodGunnarson())],
    'backfire': [Triggered(Backfire())],
    'bad-moon': [Static(PumpApplies(CF.black_creatures(), (1, 1)))],
    'badlands': dual_land_specs('BR'),
    'ball-lightning': [GenTrig(On(EndStepEvent).then(Destroy(CF.self())))],
    'banshee': [Activated('XT', Banshee(), CF.all_creatures_and_players(), max_x_func=max_x_from_printed_card)],
    'barls-cage': [Activated('3', Do(TapCardEffect(), AddCounter(STUN)), CF.creatures())],
    'bartel-runeaxe': [Static(CantBeTargetedByAuras(CF.self()))],
    'basalt-monolith': [Triggered(DoesntUntapAtUntap(CF.self())),
                        Activated('T', AddMana('C', 3), is_mana_ability=True),
                        Activated('3', UntapCardEffect(), CF.self())],
    'bayou': dual_land_specs('BG'),
    'bazaar-of-baghdad': [Activated('2T', DrawThenDiscard(2, 3), text='Draw 2 cards; discard 3 cards')],
    'beasts-of-bogardan': [Static(PumpApplies(CF.self(), (1, 1), cond=C_FUNCS['opp_has_non_token_white_perm']))],
    'berserk': [Spell(Berserk(), CF.creatures(), allowed_phases=[p for p in Phase if p < Phase.COMBAT_DAMAGE])],
    'birds-of-paradise': [Activated('T', AddMana(c), is_mana_ability=True, text=f'Add {{{c}}}') for c in COLOR_LETTERS],
    'black-lotus': [Activated('T', AddMana(c, 3), is_mana_ability=True, extra_costs=[SacSelfCost()],
                              text=f'Add {{3{c}}}') for c in COLOR_LETTERS],
    'black-mana-battery': [MANA_BATTERY_ADD_CHARGE, mana_battery_add_mana('B')],
    'black-vise': [Triggered(BlackVise())],
    'black-ward': [Spell(KWAModEffect('add', KW.PROTECTION_FROM_BLACK), CF.creatures())],
    'blazing-effigy': [Triggered(BlazingEffigy())],
    'blessing': [Activated('W', Pump(1, 1, True), CF.host())],
    'blight': [Spell(EmptyResolver(), CF.lands()),
               GenTrig(On(TapCardEvent).where(EC.card_is_host()).then(Destroy(CF.host())))],
    'blood-lust': [Spell(BloodLust(), CF.creatures())],
    'blood-moon': [Static(BloodMoon())],
    'blood-of-the-martyr': [Triggered(BloodOfTheMartyr())],
    'blue-elemental-blast': [Spell(CounterSpell(), CF.red_spells()), Spell(Destroy(), CF.red_permanents())],
    'blue-mana-battery': [MANA_BATTERY_ADD_CHARGE, mana_battery_add_mana('U')],
    'blue-ward': [Spell(KWAModEffect('add', KW.PROTECTION_FROM_BLUE), CF.creatures())],
    'bog-rats': [Static(UnblockableCondition(CF.self(), CF.walls()))],
    'bone-flute': [Activated('2T', PumpApplies(CF.creatures(), (-1, 0), True))],
    'book-of-rass': [Activated('2', Do(DrawCards(), DealDamage(2, CF.owner())))],
    'boomerang': [Spell(Bounce(), CF.permanents())],
    'boris-devilboon': [Activated('2BRTT', CreateTokenCreature('minor-demon'))],
    'bottle-of-suleiman': [Activated('1', BottleOfSuleiman(), extra_costs=[SacSelfCost()])],
    'braingeyser': [Spell(DrawCards(), CF.all_players())],
    'brainwash': [Spell(HostCantAttack(), CF.creatures()),
                  Activated('3', HostCanAttack(CF.host()), allowed_activators=A_FUNCS['host_owner'])],
    'brass-man': [Triggered(DoesntUntapAtUntap(CF.self())),
                  Triggered(PayManaToUntapUpkeep('1', CF.self()))],
    'brine-hag': [Triggered(BrineHag())],
    'brothers-of-fire': [Activated('T', Do(DealDamage(1), DealDamage(1, CF.owner())), CF.all_creatures_and_players())],
    'burrowing': [Spell(KWAModEffect('add', KW.ISLANDWALK), CF.creatures())],
    'candelabra-of-tawnos': [Activated('XT', UntapCards(), TargetSpec(CF.your_tapped_lands(), 1, None),
                                       max_x_func=your_tapped_land_cnt_and_max_x)],
    'carrion-ants': [self_pump('1', 1, 1)],
    'castle': [Static(PumpApplies(CF.your_untapped_white_creatures(), (0, 2)))],
    'cave-people': [GenTrig(On(AttackEvent).where(EC.self_is_attacker()).then(PumpSelf(1, -2, True))),
                    Activated('1RRT', KWAModEffect('add', KW.ISLANDWALK, True), CF.creatures())],
    'caverns-of-despair': [Static(AttackerCountMax(2)), Static(BlockerCountMax(2))],
    'celestial-prism': [Activated('2T', AddMana(c), CF.owner(), is_mana_ability=True, text=f'Add 1 {c}')
                        for c in COLOR_LETTERS],
    'chaos-orb': [Activated('1T', ChaosOrb(), CF.opp_non_token_perms(), extra_costs=[SacSelfCost()],
                            text='If random di roll is 1-4, destroy target')],
    'chaoslace': [Spell(SetColor('R'), CF.cards())],
    'chromium': [GenTrig(On(UpkeepEvent).where(EC.is_your_turn()).then(PayManaOr('WUB', SacSelf())))],
    'circle-of-protection-artifacts': [Activated('1', PreventNextDamageTo(protected=CF.owner()), CF.artifacts())],
    'circle-of-protection-black': [Activated('1', PreventNextDamageTo(protected=CF.owner()), CF.black())],
    'circle-of-protection-blue': [Activated('1', PreventNextDamageTo(protected=CF.owner()), CF.blue())],
    'circle-of-protection-green': [Activated('1', PreventNextDamageTo(protected=CF.owner()), CF.green())],
    'circle-of-protection-red': [Activated('1', PreventNextDamageTo(protected=CF.owner()), CF.red())],
    'circle-of-protection-white': [Activated('1', PreventNextDamageTo(protected=CF.owner()), CF.white())],
    'citanul-druid': [GenTrig(On(CastResolvedEvent).where(EC.caster_is_opp(), EC.card_is_artifact()).then(AddCounter(PLUS_ONE)))],
    'city-in-a-bottle': [Static(GlobalSac(CF.city_in_a_bottle())), Static(CantCastAppliesTo(CF.city_in_a_bottle())),
                         Spell(SacAll(CF.city_in_a_bottle()))],
    'city-of-brass': [Activated('T', AddMana(c), is_mana_ability=True, text=f'Add {{{c}}}') for c in COLOR_LETTERS] +
                     [GenTrig(On(TapCardEvent).where(EC.card_is_source()).then(DealDamage(1)).t(ET.s_owner()))],
    'city-of-shadows': [Activated('T', AddCounter(STORAGE), extra_costs=[SacCardCost(CF.your_creatures())]),
                        Activated('T', CityOfShadowsAddMana(), is_mana_ability=True)],
    'clay-statue': [Activated('2', Regenerate(), CF.self())],
    'cleanse': [Spell(DestroyAll(CF.black_creatures()))],
    'cleansing': [Spell(Cleansing())],
    'clergy-of-the-holy-nimbus': [Static(RegenerateSelf()), Activated('1', PreventRegenerationEOT(), CF.self(),
                                                                      allowed_activators=A_FUNCS['opponent'])],
    'clockwork-avian': [GenTrig(On(CombatEndEvent).where(EC.self_is_combatant()).then(RemoveCounter(PLUS_ONE_ZERO))),
                        Activated('XT', AddCounter(PLUS_ONE_ZERO), CF.self(), allowed_phases=[Phase.UPKEEP],
                                  allowed_p_turn_func=CF.owner(), max_x_func=clockwork_avian_x),
                        Spell(AddCounter(PLUS_ONE_ZERO, 4))],
    'clockwork-beast': [GenTrig(On(CombatEndEvent).where(EC.self_is_combatant()).then(RemoveCounter(PLUS_ONE_ZERO))),
                        Activated('XT', AddCounter(PLUS_ONE_ZERO), CF.self(), allowed_phases=[Phase.UPKEEP],
                                  allowed_p_turn_func=CF.owner(), max_x_func=clockwork_beast_x),
                        Spell(AddCounter(PLUS_ONE_ZERO, 7))],
    'clone': [Spell(Copy(CF.creatures()))],
    'coal-golem': [Activated('3', AddMana('R', 3), CF.owner(), is_mana_ability=True,
                             extra_costs=[SacSelfCost()])],
    'cockatrice': [GenTrig(On(CombatEndEvent).where(EC.self_is_combatant()).
                           then(DestroySelfCombatants(filter_func=CF.non_wall_creatures())))],
    'cocoon': [Spell(Do(TapCards(), AddCounter(PUPA, 3, CF.self())), CF.your_creatures()),
               Static(CocoonUntap()), Static(CocoonUpkeep())],
    'colossus-of-sardia': [Triggered(DoesntUntapAtUntap(CF.self())), Triggered(PayManaToUntapUpkeep('9', CF.self()))],
    'concordant-crossroads': [Static(KWAApplies(CF.creatures(), 'add', KW.HASTE))],
    'consecrate-land': [Spell(ConsecrateLand(), CF.lands())],
    'conservator': [Activated('3T', PreventNextDamageTo(protected=CF.owner()))],
    'control-magic': [Spell(Steal(), CF.opp_creatures())],
    'conversion': [GenTrig(On(UpkeepEvent).where(EC.is_your_turn()).then(PayManaOr('WW', SacSelf()))), Static(Conversion())],
    'copper-tablet': [GenTrig(On(UpkeepEvent).then(DealDamage(1)).t(ET.in_turn_p()))],
    'copy-artifact': [Spell(Copy(CF.artifacts()))],
    'coral-helm': [Activated('3', Pump(2, 2, True), CF.creatures(), extra_costs=[DiscardAtRandomCost()])],
    'cosmic-horror': [GenTrig(On(UpkeepEvent).where(EC.is_your_turn()).
                              then(PayManaOr('3BBB', Do(Destroy(CF.self()), DealDamage(7, CF.owner())))))],
    'counterspell': [Spell(CounterSpell(), CF.spells())],
    'crevasse': [Static(WalkRuleRemoved(KW.ISLANDWALK))],
    'creature-bond': [Triggered(CreatureBond())],
    'crimson-manticore': [Activated('RT', DealDamage(1), CF.combatants())],
    'crumble': [Spell(Crumble(), CF.artifacts())],
    'crusade': [Static(PumpApplies(CF.white_creatures(), (1, 1)))],
    'crystal-rod': [GenTrig(On(CastResolvedEvent).where(EC.card_is_color('U')).then(MayPayMana('1', GainLife(1))))],
    'cuombajj-witches': [Activated('T', CuombajjWitches(), CF.all_creatures_and_players())],
    'curse-artifact': [Spell(CurseArtifact(), CF.artifacts())],
    'cursed-land': [Spell(EmptyResolver(), CF.lands()),
                    GenTrig(On(UpkeepEvent).where(EC.is_host_turn()).then(DealDamage(1)).t(ET.host_owner()))],
    'cursed-rack': [Static(CursedRack())],
    'cyclone': [Triggered(Cyclone())],
    'cyclopean-mummy': [GenTrig(On(DiesEvent).where(EC.card_is_source()).then(Exile(CF.self())))],
    'dakkon-blackblade': [Static(SelfPTEqualsFuncLen(CF.your_lands()))],
    'damping-field': [Triggered(DampingField())],
    'dance-of-many': [GenTrig(On(UpkeepEvent).where(EC.is_your_turn()).then(PayManaOr('UU', SacSelf()))),
                      Spell(DanceOfMany(), CF.non_token_creatures())],
    'dark-heart-of-the-wood': [Activated('', GainLife(3), extra_costs=[SacCardCost(CF.your_forests())])],
    'dark-ritual': [Spell(AddMana('B', 3))],
    'dark-sphere': [Activated('T', PreventNextDamageTo(protected=CF.owner()), CF.artifacts(),
                              extra_costs=[SacSelfCost()])],
    'darkness': [GenTrig(On(DamageProposedEvent, expires='EOT').where(EC.is_combat_damage()).modify(PreventDamage()))],
    'davenant-archer': [Activated('T', DealDamage(1), CF.combatants())],
    'deadfall': [Static(WalkRuleRemoved(KW.FORESTWALK))],
    'deathgrip': [Activated('BB', CounterSpell(), CF.green_spells())],
    'deathlace': [Spell(SetColor('B'), CF.cards())],
    'death-ward': [Spell(Regenerate(), CF.creatures())],
    'deep-water': [Activated('T', ManaProdAlter('U', CF.your_lands(), eot=True))],
    'demonic-hordes': [Activated('T', Destroy(), CF.lands()), Triggered(DemonicHordesUpkeep())],
    'demonic-torment': [Spell(HostCantAttack(), CF.creatures()),
                        GenTrig(On(DamageProposedEvent, expires='EOT').
                                where(EC.is_combat_damage(), EC.damage_source_in(CF.host())).modify(PreventDamage()))],
    'demonic-tutor': [Spell(Tutor())],
    'desert': [Activated('T', AddMana('C'), is_mana_ability=True),
               Activated('T', DealDamage(1), CF.attackers(), allowed_phases=[Phase.COMBAT_END])],
    'desert-twister': [Spell(Destroy(), CF.permanents())],
    'diabolic-machine': [Activated('3', Regenerate(), CF.self())],
    'diamond-valley': [Activated('T', DiamondValley(), extra_costs=[SacCardCost(CF.your_creatures())])],
    'dingus-egg': [Triggered(DingusEgg())],
    'disharmony': [Spell(Disharmony(), CF.attackers(), allowed_phases=[Phase.DECLARE_COMBAT, Phase.DECLARE_ATTACKERS])],
    'disintegrate': [Spell(Disintegrate(), CF.all_creatures_and_players())],
    'disrupting-scepter': [Activated('3T', Discard(), CF.all_players(), allowed_p_turn_func=CF.owner())],
    'disenchant': [Spell(Destroy(), CF.artifacts_and_enchantments())],
    'divine-offering': [Spell(Do(Destroy(allow_regen=False), GainLifeTargetMV()), CF.artifacts())],
    'divine-transformation': [Spell(Pump(3, 3), CF.creatures())],
    'drafnas-restoration': [Spell(DrafnasRestoration(), CF.all_players())],
    'dragon-engine': [self_pump('2', 1, 0)],
    'dragon-whelp': [self_pump('R', 1, 0), Triggered(DragonWhelpEndStep())],
    'drain-power': [Spell(DrainPower(), CF.opp())],
    'dream-coat': [Spell(EmptyResolver(), CF.creatures())] +
                  [Activated('', SetColor(''.join(combo)), CF.host(), max_activations_per_turn=1, text=f'{{{combo}}}')
                   for r in range(1, len(COLOR_LETTERS) + 1) for combo in combinations(COLOR_LETTERS, r)],
    'drop-of-honey': [Triggered(DropOfHoney())],
    'drowned': [Activated('B', Regenerate(), CF.self())],
    'drudge-skeletons': [Activated('B', Regenerate(), CF.self())],
    'dust-to-dust': [Spell(DustToDust(), TargetSpec(CF.artifacts(), 2, 2))],
    'dwarven-demolition-team': [Activated('T', Destroy(), CF.walls())],
    'dwarven-song': [Spell(SetColor('R', 'EOT'), TargetSpec(CF.creatures(), 1, None))],
    'dwarven-warriors': [Activated('T', UnblockableEOT(), CF.creatures_power_two_or_less())],
    'dwarven-weaponsmith': [Activated('T', AddCounter(PLUS_ONE), CF.creatures(),
                                      extra_costs=[SacCardCost(CF.your_artifacts())],
                                      allowed_phases=[Phase.UPKEEP], allowed_p_turn_func=CF.owner())],
    'earthbind': [Spell(Earthbind(), CF.creatures())],
    'earthquake': [Spell(Earthquake())],
    'eater-of-the-dead': [Activated('', EaterOfTheDead(), CF.creatures_in_all_graveyards())],
    'ebony-horse': [Activated('2T', RemoveFromCombat(), CF.attackers())],
    'el-hajjaj': [Triggered(ElHajjaj(), CF.self())],
    'elder-land-wurm': [GenTrig(On(BlockEvent).where(EC.self_is_blocker()).then(KWAModEffect('remove', 'Defender')))],
    'elder-spawn': [Triggered(ElderSpawnUpkeep()), Static(UnblockableCondition(CF.self(), CF.red()))],
    'electric-eel': [Spell(DealDamage(1), CF.owner()),
                     Activated('RR', Do(PumpSelf(0, 2, True), DealDamage(1, CF.owner())))],
    'elephant-graveyard': [Activated('T', AddMana('C'), is_mana_ability=True),
                           Activated('T', Regenerate(), CF.elephants())],
    'elven-riders': [Static(UnblockableCondition(CF.self(), CF.non_wall_non_fliers()))],
    'elves-of-deep-shadow': [Activated('T', Do(AddMana('B'), DealDamage(1, CF.owner())), is_mana_ability=True)],
    'emerald-dragonfly': [Activated('GG', KWAModEffect('add', KW.FIRST_STRIKE, True), CF.self())],
    'enchanted-being': [GenTrig(On(DamageProposedEvent).
                                where(EC.damage_target_in(CF.self()), EC.damage_source_in(CF.enchanted_creatures()),
                                      EC.is_combat_damage()).modify(PreventDamage()))],
    'enchantment-alteration': [Spell(EnchantmentAlteration(), CF.auras_on_creatures_or_lands())],
    'energy-flux': [Triggered(EnergyFlux())],
    'energy-tap': [Spell(EnergyTap(), CF.your_untapped_creatures())],
    'erg-raiders': [Triggered(ErgRaiders())],
    'erhnam-djinn': [Triggered(ErhnamDjinn(), CF.opp_non_wall_creatures())],
    'erosion': [Spell(ErosionUpkeep(), CF.lands())],
    'eternal-flame': [Spell(EternalFlame())],
    'eternal-warrior': [Spell(KWAModEffect('add', KW.VIGILANCE), CF.creatures())],
    'eureka': [Spell(Eureka())],
    'evil-eye-of-orms-by-gore': [Static(UnblockableCondition(CF.self(), CF.non_wall_creatures())),
                                 Static(EvilEyeOfOrmsByGoreMyNonEyeNoAttack())],
    'evil-presence': [Spell(EvilPresence(), CF.lands())],
    'exorcist': [Activated('1W', Destroy(), CF.black_creatures())],
    'eye-for-an-eye': [Spell(EyeForAnEye(), CF.cards())],
}
