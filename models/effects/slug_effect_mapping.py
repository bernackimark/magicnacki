from __future__ import annotations
from dataclasses import dataclass, field
from enum import Enum, auto
from functools import partial
from typing import Callable, Literal, Union, TYPE_CHECKING

from models.counter_tokens import CARRION, CORPSE, PLUS_ONE, MINUS_ONE, PIN, PLUS_ONE_ZERO
from models.effects.legacy_funcs_w_odd_events import giant_tortoise_on_untap, islandhome_can_attack_effect, \
    amrou_kithkin_can_be_blocked, artifact_ward_can_be_blocked, argothian_pixies_can_be_blocked, \
    bog_rats_can_be_blocked, elder_spawn_can_be_blocked, elven_riders_can_be_blocked, \
    evil_eye_of_orms_by_gore_can_be_blocked, seeker_enchanted_creature_can_be_blocked, gaseous_form_on_cast, \
    reset_on_cast

if TYPE_CHECKING:
    from models.events.base import Event
    from game_state import GameState
    from models.game_card import GameCard

from constants import Target, COLOR_LETTERS
from cost import Cost, TapCost, ManaCost, SacSelfCost

from models.effects.counters import (spirit_shackle_on_tap, CityOfShadowsAA1, CityOfShadowsAA2, XZeroOneCountersByManaValue,
                                     RemovePlusOneZeroFromCombatant, AddCountersIfAnyCreatureDied,
                                     AddCounterPerCreatureDeath, Fasting, AddCountersYourTurnOnly,
                                     AddCountersOnHostTurn, RemoveCountersOnHostTurn, CocoonCast, RockHydraCast)
from models.effects.damage import argothian_pixies_damage_prevention, \
    argothian_treefolk_damage_prevention, artifact_ward_damage_prevention, enchanted_being_damage_prevention, \
    marble_priest_damage_prevention, creature_bond_on_leave, martyrs_of_korlis_on_damage, DealDamage, \
    living_artifact_on_damage, fungusaur_on_damage, DealDamageOnTargetTurn, \
    ElderSpawnUpkeep, CurseArtifactUpkeep, Karma, DealDamageOnSourceTurn, LordOfThePitUpkeep, PowerSurge, StormWorld, \
    Earthquake, EternalFlame, EyeForAnEye, PreventNextDamageToCardEffect, DealDamageToAllCreaturesAndPlayers, \
    JovialEvil, Typhoon, PsionicBlast, StormSeeker, ErgRaiders
from models.effects.destroy_sac_regenerate import land_on_leave, island_on_leave, PayManaOrSac, DestroyAll, \
    EaterOfTheDeadAA, AcidRain, ExileAllCreatures, BoardToGraveyard, VoodooDollEndStep, PestilenceEndStep, \
    ErosionUpkeep, ForceOfNatureUpkeep, ManaVortexUpkeep, SeasonOfTheWitchUpkeep, SeasonOfTheWitchEndStep
from models.effects.draw_discard import Braingeyser, CursedRackEffect, DrawCards, WheelOfFortune
from models.effects.global_ import global_on_leave, angelic_voices_on_cast, bad_moon_on_cast, castle_on_cast, \
        crusade_on_cast, darkness_or_fog_or_holy_day_on_cast, sunken_city_on_cast
from models.effects.keywords import ErhnamDjinn, KWAModEffect, EvilEyeOfOrmsByGoreCast, KoboldOverlordCast, \
    AkronLegionnaireCast
from models.effects.life import spirit_link_on_damage, add_poison_counter_on_damage, add_two_poison_counters_on_damage, \
        el_hajjaj_on_damage, ivory_tower_on_upkeep, spiritual_sanctuary_on_upkeep, stream_of_life_on_cast
from models.effects.mana import dark_ritual_on_cast, drain_power_on_cast, energy_tap_on_cast, AddMana
from models.effects.piles import BoardToHand, \
    GraveyardToHand, HandToBoard, GraveRobbersAA, GraveyardToExileInItsEntirety, GraveyardToBoard
from models.effects.pumps import DragonWhelpEndStep, BloodLust, PumpEffect, GreatDefender, HowlFromBeyond, \
    KoboldTaskmaster
from models.effects.special import cocoon_on_upkeep, serendib_djinn_on_upkeep, shapeshifter_on_upkeep, \
        active_volcano_on_cast, animate_dead_on_cast, crumble_on_cast, divine_offering_on_cast, earthbind_on_cast, \
        feint_on_cast, flash_flood_on_cast, forest_on_cast, goblin_king_on_cast, glyph_of_destruction_on_cast, \
        kobold_drill_sergeant_on_cast, lord_of_atlantis_on_cast, martyrs_cry_on_cast, reverse_damage_on_cast, \
        rocket_launcher_on_cast, shapeshifter_on_cast, subdue_on_cast, syphon_soul_on_cast, web_on_cast, \
        venarian_gold_on_cast, swords_to_plowshares_on_cast, farmstead_on_cast
from models.effects.tap_untap import *
from models.effects.tap_untap import host_stays_tapped_at_untap_phase, stays_tapped_at_untap_phase, \
        untap_option_at_untap_phase, cocoon_at_untap_phase, venarian_gold_at_untap_phase, TapCardEffect
from models.events.events_all import EndStepEvent, CastResolvedEvent, CombatEndEvent, UpkeepEvent
from phase_fsm import Phase
from utils import flip


T_FUNCS: [str, Callable[[GameState, GameCard], list[Target]]] = {
    # --- COMMON TARGET FUNCS ---
    'all_creatures_and_players': lambda gs, source: gs.card_filter.in_play().creatures().result() + [0, 1],
    'all_players': lambda gs, s: [0, 1],
    'artifact_creatures_in_play': lambda gs, source: gs.card_filter.in_play().artifacts().creatures().result(),
    'artifacts_and_enchantments_in_play': lambda gs: gs.card_filter.in_play().by_type(['Artifact', 'Enchantment']).result(),
    'artifacts_creatures_lands_in_play': lambda gs, s: CardFilter(gs).in_play().by_type(['Artifact', 'Creature', 'Land']).result(),
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
    'enchants_in_play': lambda gs, s: gs.card_filter.in_play.enchantments().result(),
    'enchants_in_your_graveyard': lambda gs, s: gs.card_filter.in_player_graveyard(s.orig_owner_id).enchantments().result(),
    'fliers_in_play': lambda gs, _: gs.card_filter.in_play().creatures().has('Flying').result(),
    'forests_in_your_hand': lambda gs, s: gs.card_filter.in_player_hand(s.orig_owner_id).by_slug('forest').result(),
    'goblin_permanents_in_your_hand': lambda gs, s: gs.card_filter.in_player_hand(s.orig_owner_id).by_sub_type('Goblin').permanents().result(),
    'green_in_play': lambda gs, source: gs.card_filter.in_play().green().result(),
    'host': lambda gs, s: s.attached_to,
    'in_turn_player': lambda gs, _: gs.player_turn_idx,
    'lands_in_play': lambda gs, source: gs.card_filter.in_play().lands().result(),
    'one_one_creatures_in_play': lambda gs, s: [c for c in gs.card_filter.in_play().creatures().result()
                                                if c.power == 1 and c.toughness == 1],
    'opp_creatures_in_play': lambda gs, s: gs.card_filter.on_player_board(flip(s.orig_owner_id)).creatures().result(),
    'opp_creatures_who_could_have_but_didnt_attack': lambda gs, s: opp_creatures_who_could_have_attacked_but_didnt(gs, s),
    'opp_non_wall_creatures_in_play': lambda gs, s: gs.card_filter.on_player_board(flip(s.orig_owner_id)).non_wall_creatures().result(),
    'opponent': lambda gs, s: flip(s.orig_owner_id),
    'permanents_in_play': lambda gs: CardFilter(gs).in_play().permanents().result(),
    'red_in_play': lambda gs, source: gs.card_filter.in_play().red().result(),
    'self': lambda gs, s: s,
    'stone_giant': lambda gs, s: [c for c in gs.card_filter.on_player_board(s).creatures().result()
                                  if c.toughness < s.power],
    'tapped_creatures': lambda gs, source: gs.card_filter.in_play().creatures().tapped().result(),
    'tapped_lands': lambda gs, s: gs.card_filter.in_play().lands().tapped().result(),
    'unblocked_attackers': lambda gs, source: gs.card_filter.unblocked_attackers().result(),
    'untapped_artifacts_in_play': lambda gs, source: gs.card_filter.in_play().artifacts().untapped().result(),
    'walls_in_play': lambda gs, s: gs.card_filter.in_play().walls().result(),
    'white_in_play': lambda gs, source: gs.card_filter.in_play().white().result(),
    'your_creatures_in_play': lambda gs, s: gs.card_filter.on_player_board(s.orig_owner_id).creatures().result(),
    'your_lands_in_play': lambda gs: gs.card_filter.on_player_board(gs.player_turn_idx).lands().result(),
}


@dataclass
class EffSpec:
    """Effect Specification"""

    class AllowedPlayerTurn(Enum):
        CASTER = auto()
        OPPONENT = auto()

    activation_type: Literal["cast", "upkeep", "activated", "untap", "static"]
    cost: str
    effect: Effect
    target_filter: Union[Callable, None] = None
    trigger_event: type[Event] | None = None
    conditions: list[Callable[[], bool], None] = field(default_factory=list)
    extra_costs: list[Cost | None] = None
    allowed_phases: list[Phase | None] = field(default_factory=list)
    allowed_player_turn: AllowedPlayerTurn | None = field(default_factory=list)
    allowed_p_id_turn: int | None = None
    activated_cnt_this_turn: int = 0
    max_activations_per_turn: int = 999
    text: str = ''

    @property
    def costs(self) -> list[Cost | None]:
        the_costs = []
        if not self.cost:
            pass
        elif 'T' in self.cost:
            the_costs.append(TapCost())
            the_costs.append(ManaCost(self.cost[:-1]))
        else:
            the_costs.append(ManaCost(self.cost))
        if self.extra_costs:
            for extra_cost in self.extra_costs:
                the_costs.append(extra_cost)
        return the_costs


@dataclass
class ActivatedAbility:
    source: GameCard
    eff_spec: EffSpec

    def __post_init__(self):
        """from InitVars 'cost_mana', 'cost_tap', and 'extra_costs', build attribute 'costs'
        allowed_p_id_turns need knowledge of the card's owner and is assigned here;
        if allowed_player_turn is None, then the ability should be permitted on both turns"""
        if self.eff_spec.allowed_player_turn == self.eff_spec.AllowedPlayerTurn.CASTER:
            self.eff_spec.allowed_p_id_turn = self.source.orig_owner_id
        if self.eff_spec.allowed_player_turn == self.eff_spec.AllowedPlayerTurn.OPPONENT:
            self.eff_spec.allowed_p_id_turn = flip(self.source.orig_owner_id)

    def can_activate(self, gs: GameState) -> bool:
        if self.eff_spec.allowed_phases and gs.phase not in self.eff_spec.allowed_phases:
            print("C")
            return False
        if self.eff_spec.allowed_player_turn and gs.player_turn_idx != self.eff_spec.allowed_p_id_turn:
            print("F")
            return False
        if self.eff_spec.allowed_p_id_turn and self.source.orig_owner_id != self.eff_spec.allowed_p_id_turn:
            print("D")
            return False
        if self.eff_spec.activated_cnt_this_turn >= self.eff_spec.max_activations_per_turn:
            print("E")
            return False
        if self.eff_spec.conditions:
            for cond in self.eff_spec.conditions:
                if not cond(self.source):
                    print('G')
                    return False
        return all(cost.can_pay(gs, self.source) for cost in self.eff_spec.costs)

    def pay_costs(self, gs):
        for cost in self.eff_spec.costs:
            cost.pay(gs, self.source)


def opp_creatures_who_could_have_attacked_but_didnt(gs: GameState, source: GameCard) -> list[GameCard | None]:
    """Returns creatures who: have 'Attack' in kwa, no summoning sickness, didn't go into combat"""
    attackers = gs.card_filter.attackers().result()
    return [c for c in gs.card_filter.on_player_board(flip(source.orig_owner_id)).creatures().result()
            if c not in attackers and not c.has_summoning_sickness and 'Attack' in c.keyword_abilities]


def is_tapped(s: GameCard) -> bool:
    return s.is_tapped

def all_player_indices(gs):
    return list(range(gs.player_cnt))


CAST_TARGETS = {
    'active-volcano': lambda gs: CardFilter(gs).in_play().blue().permanents().result() +
                                 CardFilter(gs).in_play().by_slug('island').result(),
    'animate-dead': lambda gs: CardFilter(gs).in_player_graveyard(gs.player_turn_idx).creatures().result(),
    'artifact-ward': lambda gs: CardFilter(gs).in_play().creatures().result(),
    'cocoon': lambda gs: CardFilter(gs).on_player_board(gs.player_turn_idx).creatures().result(),
    'crumble': lambda gs: CardFilter(gs).in_play().artifacts().result(),
    'divine-offering': lambda gs: CardFilter(gs).in_play().artifacts().result(),
    'drain-power': lambda gs: all_player_indices(gs),
    'earthbind': lambda gs: CardFilter(gs).in_play().creatures().result(),
    'energy-tap': lambda gs: CardFilter(gs).on_player_board(gs.player_turn_idx).creatures().untapped().result(),
    'erosion': lambda gs: CardFilter(gs).in_play().lands().result(),
    'farmstead': lambda gs: CardFilter(gs).on_player_board(gs.player_turn_idx).lands.result(),
    'feint': lambda gs: CardFilter(gs).attackers().result(),
    'firebreathing': lambda gs: CardFilter(gs).in_play().creatures().result(),
    'flash-flood': lambda gs: CardFilter(gs).in_play().red().permanents().result() +
                                 CardFilter(gs).in_play().by_slug('mountain').result(),
    'gaseous-form': lambda gs: CardFilter(gs).in_play().creatures().result(),
    'instill-energy': lambda gs: CardFilter(gs).in_play().creatures().result(),
    'living-artifact': lambda gs: CardFilter(gs).in_play().artifacts().result(),
    'martyrs-cry': lambda gs: CardFilter(gs).in_play().creatures().white().result(),
    'psychic-venom': lambda gs: CardFilter(gs).in_play().lands().result(),
    'sacrifice': lambda gs: CardFilter(gs).on_player_board(gs.player_turn_idx).creatures().result(),
    'shatter': lambda gs: CardFilter(gs).in_play().artifacts().result(),
    'spirit-link': lambda gs: CardFilter(gs).in_play().creatures().result(),
    'spirit-shackle': lambda gs: CardFilter(gs).in_play().creatures().result(),
    'stream-of-life': lambda gs: all_player_indices(gs),
    'subdue': lambda gs: CardFilter(gs).in_play().creatures().result(),
    'venarian-gold': lambda gs: CardFilter(gs).in_play().creatures().result(),
    'weakness': lambda gs: CardFilter(gs).in_play().creatures().result(),
    'web': lambda gs: CardFilter(gs).in_play().creatures().result(),
    'winter-blast': lambda gs: CardFilter(gs).in_play().creatures().untapped().result(),
}

SLUG_EFFECTS: dict[str, list[Effect]] = {
        'active-volcano': [active_volcano_on_cast()],
        'angelic-voices': [angelic_voices_on_cast(), global_on_leave()],
        'animate-dead': [animate_dead_on_cast()],
        'amrou-kithkin': [amrou_kithkin_can_be_blocked()],
        'argothian-pixies': [argothian_pixies_can_be_blocked(), argothian_pixies_damage_prevention()],
        'argothian-treefolk': [argothian_treefolk_damage_prevention()],
        'artifact-ward': [artifact_ward_can_be_blocked(), artifact_ward_damage_prevention()],
        'ashnods-battle-gear': [untap_option_at_untap_phase()],
        'bad-moon': [bad_moon_on_cast(), global_on_leave()],
        'basalt-monolith': [stays_tapped_at_untap_phase()],
        'bog-rats': [bog_rats_can_be_blocked()],
        'brass-man': [stays_tapped_at_untap_phase()],
        'castle': [castle_on_cast(), global_on_leave()],
        'cocoon': [cocoon_on_upkeep(), cocoon_at_untap_phase()],
        'colossus-of-sardia': [stays_tapped_at_untap_phase()],
        'creature-bond': [creature_bond_on_leave()],
        'crumble': [crumble_on_cast()],
        'crusade': [crusade_on_cast(), global_on_leave()],
        'dark-ritual': [dark_ritual_on_cast()],
        'darkness': [darkness_or_fog_or_holy_day_on_cast()],
        'divine-offering': [divine_offering_on_cast()],
        'drain-power': [drain_power_on_cast()],
        'earthbind': [earthbind_on_cast()],
        'el-hajjâj': [el_hajjaj_on_damage()],
        'elder-spawn': [elder_spawn_can_be_blocked()],
        'elven-riders': [elven_riders_can_be_blocked()],
        'enchanted-being': [enchanted_being_damage_prevention()],
        'energy-tap': [energy_tap_on_cast()],
        'evil-eye-of-orms-by-gore': [evil_eye_of_orms_by_gore_can_be_blocked()],
        'farmstead': [farmstead_on_cast()],
        'feint': [feint_on_cast()],
        'flash-flood': [flash_flood_on_cast()],
        'fog': [darkness_or_fog_or_holy_day_on_cast()],
        'forest': [forest_on_cast(), forest_on_tap(), land_on_leave()],
        'fungusaur': [fungusaur_on_damage()],
        'gaseous-form': [gaseous_form_on_cast()],
        'giant-tortoise': [giant_tortoise_on_tap(), giant_tortoise_on_untap()],
        'glyph-of-destruction': [glyph_of_destruction_on_cast()],
        'goblin-king': [goblin_king_on_cast()],
        'holy-day': [darkness_or_fog_or_holy_day_on_cast()],
        'island': [island_on_leave(), land_on_leave()],
        'island-fish-jasconius': [stays_tapped_at_untap_phase()],
        'ivory-tower': [ivory_tower_on_upkeep()],
        'kobold-drill-sergeant': [kobold_drill_sergeant_on_cast(),],
        'leviathan': [stays_tapped_at_untap_phase()],  # lots of other things to code
        'living-artifact': [living_artifact_on_damage()],
        'lord-of-atlantis': [lord_of_atlantis_on_cast()],
        'mana-vault': [stays_tapped_at_untap_phase()],
        'marble-priest': [marble_priest_damage_prevention()],  # NOT CODED: All Walls able to block this creature do so
        'marsh-viper': [add_two_poison_counters_on_damage()],
        'martyrs-cry': [martyrs_cry_on_cast()],
        'martyrs-on-korlis': [martyrs_of_korlis_on_damage()],
        'mountain': [mountain_on_tap(), land_on_leave()],
        'old-man-of-the-sea': [untap_option_at_untap_phase()],
        'paralyze': [host_stays_tapped_at_untap_phase()],
        'phyrexian-gremlins': [untap_option_at_untap_phase()],
        'pirate-ship': [islandhome_can_attack_effect()],
        'pit-scorpion': [add_poison_counter_on_damage()],
        'plains': [land_on_leave()],
        'preacher': [untap_option_at_untap_phase()],
        'reset': [reset_on_cast()],
        'reverse-damage': [reverse_damage_on_cast()],
        'rocket-launcher': [rocket_launcher_on_cast()],
        'sea-serpent': [islandhome_can_attack_effect()],
        'seeker': [seeker_enchanted_creature_can_be_blocked()],
        'serendib-djinn': [serendib_djinn_on_upkeep()],
        'shapeshifter': [shapeshifter_on_cast(), shapeshifter_on_upkeep()],
        'swamp': [land_on_leave()],
        'spirit-link': [spirit_link_on_damage()],
        'spirit-shackle': [spirit_shackle_on_tap()],
        'spiritual-sanctuary': [spiritual_sanctuary_on_upkeep()],
        'stream-of-life': [stream_of_life_on_cast()],
        'subdue': [subdue_on_cast()],
        'sunken-city': [sunken_city_on_cast(), global_on_leave()],
        'swords-to-plowshares': [swords_to_plowshares_on_cast()],
        'syphon-soul': [syphon_soul_on_cast()],
        'tawnoss-coffin': [untap_option_at_untap_phase()],
        'tawnoss-weaponry': [untap_option_at_untap_phase()],
        'time-vault': [stays_tapped_at_untap_phase()],
        'venarian-gold': [venarian_gold_on_cast(), venarian_gold_at_untap_phase()],
        'web': [web_on_cast()],
    }

Activated = partial(EffSpec, 'activated')
Triggered = partial(EffSpec, 'triggered', '')

# TODO: NEXT: Continue converting from old system to new system

INVOCATIONS: dict[str, list[EffSpec]] = {
    'acid-rain':
        [Triggered(AcidRain(), None, CastResolvedEvent)],
    'akron-legionnaire':
        [Triggered(AkronLegionnaireCast(), None, CastResolvedEvent)],
    'aladdins-ring':
        [Activated('T', DealDamage(4), T_FUNCS['all_creatures_and_players'])],
    'ali-baba':
        [Activated('RT', TapCardEffect(), T_FUNCS['walls_in_play'])],
    'ancestral-recall':
        [Triggered(DrawCards(3), T_FUNCS['all_players'], CastResolvedEvent)],
    'animate-wall':
        [Triggered(KWAModEffect('remove', 'Defender'), T_FUNCS['walls_in_play'], CastResolvedEvent)],
    'apprentice-wizard':
        [Activated('UT', AddMana('C', 3), T_FUNCS['card_owner'])],
    'argivian-archaeologist':
        [Activated('WWT', GraveyardToHand(), T_FUNCS['artifacts_in_your_graveyard'])],
    'armageddon':
        [Triggered(DestroyAll(lambda gs, s: gs.card_filter.in_play().by_type('Land').result()),
                   None, CastResolvedEvent)],
    'ball_lightning':
        [Triggered(BoardToGraveyard(), T_FUNCS['self'], EndStepEvent)],
    'birds-of-paradise':
        [Activated('T', AddMana(c), text=f'Add {{{c}}}') for c in COLOR_LETTERS],
    'blood-lust':
        [Triggered(BloodLust(), T_FUNCS['creatures_in_play'], CastResolvedEvent)],
    'boomerang':
        [Triggered(BoardToHand(), T_FUNCS['permanents_in_play'], CastResolvedEvent)],
    'braingeyser':
        [Triggered(Braingeyser(), T_FUNCS['all_players'], CastResolvedEvent)],
    'brainwash':
        [Triggered(KWAModEffect('remove', 'Attack'), T_FUNCS['creatures_in_play'], CastResolvedEvent)],
    'burrowing':
        [Triggered(KWAModEffect('add', 'Mountainwalk'), T_FUNCS['creatures_in_play'], CastResolvedEvent)],
    'city-of-shadows':
        [Activated('T', CityOfShadowsAA1()),  # TODO: needs a way to find a creature to exile in extra_costs
         Activated('T', CityOfShadowsAA2())],
    'cleanse':
        [Triggered(DestroyAll(lambda gs, s: gs.card_filter.in_play().creatures().black().result()),
                   None, CastResolvedEvent)],
    'clockwork-avian':
        [Triggered(RemovePlusOneZeroFromCombatant(), T_FUNCS['self'], CombatEndEvent),
         Triggered(AddCountersYourTurnOnly(PLUS_ONE_ZERO, 4), T_FUNCS['self'], CastResolvedEvent)],
    'clockwork-beast':
        [Triggered(RemovePlusOneZeroFromCombatant(), T_FUNCS['self'], CombatEndEvent),
         Triggered(AddCountersYourTurnOnly(PLUS_ONE_ZERO, 7), T_FUNCS['self'], CastResolvedEvent)],
    'cocoon':
        [Triggered(CocoonCast(), T_FUNCS['self'], CastResolvedEvent)],
    'conversion':
        [Triggered(PayManaOrSac('WW'), None, UpkeepEvent)],
    'copper-tablet':
        [Triggered(DealDamage(1), T_FUNCS['in_turn_player'], UpkeepEvent)],
    'cosmic-horror':
        [Triggered(PayManaOrSac('3BBB'), None, UpkeepEvent)],
    'curse-artifact':
        [Triggered(CurseArtifactUpkeep(), T_FUNCS['artifacts_in_play'], UpkeepEvent)],
    'cursed-land':
        [Triggered(DealDamageOnTargetTurn(1), T_FUNCS['lands_in_play'], UpkeepEvent)],
    'cursed-rack':
        [Triggered(CursedRackEffect(), trigger_event=EndStepEvent)],
    'demonic-torment':
        [Triggered(KWAModEffect('remove', 'Attack'), T_FUNCS['creatures_in_play'], CastResolvedEvent)],
    'desert-twister':
        [Triggered(BoardToGraveyard(), T_FUNCS['permanents_in_play'], CastResolvedEvent)],
    'disenchant':
        [Triggered(BoardToGraveyard(), T_FUNCS['artifacts_and_enchantments_in_play'], CastResolvedEvent)],
    'divine-transformation':
        [Triggered(PumpEffect(3, 3), T_FUNCS['creatures_in_play'], CastResolvedEvent)],
    'dragon-whelp':
        [Triggered(DragonWhelpEndStep(), None, EndStepEvent)],
    'earthquake':
        [Triggered(Earthquake(), None, CastResolvedEvent)],
    'eater-of-the-dead':
        [Activated('', EaterOfTheDeadAA(), T_FUNCS['creatures_in_all_graveyards'], conditions=[is_tapped])],
    'elder-spawn':
        [Triggered(ElderSpawnUpkeep(), None, UpkeepEvent)],
    'electric-eel':
        [Triggered(DealDamage(1), T_FUNCS['self'], CastResolvedEvent)],
    'erg-raiders':
        [Triggered(ErgRaiders(), None, EndStepEvent)],
    'erhnam-djinn':
        [Triggered(ErhnamDjinn(), T_FUNCS['opp_non_wall_creatures_in_play'], UpkeepEvent)],
    'erosion':
        [Triggered(ErosionUpkeep(), None, UpkeepEvent)],
    'eternal-flame':
        [Triggered(EternalFlame(), None, CastResolvedEvent)],
    'eternal-warrior':
        [Triggered(KWAModEffect('add', 'Vigilance'), T_FUNCS, CastResolvedEvent)],
    'evil-eye-of-orms-by-gore':
        [Triggered(EvilEyeOfOrmsByGoreCast(), None, CastResolvedEvent)],
    'eye-for-an-eye':
        [Triggered(EyeForAnEye(), T_FUNCS['cards_in_play'], CastResolvedEvent)],
    'fasting':
        [Activated(Fasting(), T_FUNCS['self'], UpkeepEvent)],
    'feedback':
        [Triggered(DealDamageOnTargetTurn(1), T_FUNCS['enchants_in_play'], UpkeepEvent)],
    'flashfires':
        [Triggered(DestroyAll(lambda gs, s: gs.card_filter.in_play().by_slug('plains').result()),
                   None, CastResolvedEvent)],
    'flight':
        [Triggered(KWAModEffect('add', 'Flying'), T_FUNCS['creatures_in_play'], CastResolvedEvent)],
    'fishliver-oil':
        [Triggered(KWAModEffect('add', 'Islandwalk'), T_FUNCS['creatures_in_play'], CastResolvedEvent)],
    'force-of-nature':
        [Triggered(ForceOfNatureUpkeep(), None, UpkeepEvent)],
    'forethought-amulet':
        [Triggered(PayManaOrSac('3'), None, UpkeepEvent)],
    'gaeas-touch':
        [Activated('', HandToBoard(), T_FUNCS['forests_in_your_hand'],
                   allowed_player_turn=EffSpec.AllowedPlayerTurn.CASTER, max_activations_per_turn=1)],  # TODO: activated_cnt_this_turn needs to increment
    'giant-growth':
        [Triggered(PumpEffect(3, 3, True), T_FUNCS['creatures_in_play'], CastResolvedEvent)],
    'giant-strength':
        [Triggered(PumpEffect(2, 2), T_FUNCS['creatures_in_play'], CastResolvedEvent)],
    'giant-tortoise':
        [Triggered(PumpEffect(0, 3), None, CastResolvedEvent)],
    'goblin-wizard':
        [Activated('T', HandToBoard(), T_FUNCS['goblin_permanents_in_your_hand'])],
    'grave-robbers':
        [Activated('BT', GraveRobbersAA(), T_FUNCS['artifacts_in_graveyards'])],
    'great-defender':
        [Triggered(GreatDefender(), T_FUNCS['creatures_in_play'], CastResolvedEvent)],
    'holy-armor':
        [Triggered(PumpEffect(0, 2), T_FUNCS['creatures_in_play'], CastResolvedEvent)],
    'holy-strength':
        [Triggered(PumpEffect(1, 2), T_FUNCS['creatures_in_play'], CastResolvedEvent)],
    'howl-from-beyond':
        [Triggered(HowlFromBeyond(), T_FUNCS['creatures_in_play'], CastResolvedEvent)],
    'ice-storm':
        [Triggered(BoardToGraveyard(), T_FUNCS['lands_in_play'], CastResolvedEvent)],
    'immolation':
        [Triggered(PumpEffect(2, -2), T_FUNCS['creatures_in_play'], CastResolvedEvent)],
    'indestructible-aura':
        [Triggered(PreventNextDamageToCardEffect(), T_FUNCS['creatures_in_play'], CastResolvedEvent)],
    'inferno':
        [Triggered(DealDamageToAllCreaturesAndPlayers(6), None, CastResolvedEvent)],
    'instill-energy':
        [Triggered(KWAModEffect('add', 'Haste'), T_FUNCS['creatures_in_play'], CastResolvedEvent)],
    'jovial-evil':
        [Triggered(JovialEvil(), T_FUNCS['opponent'], CastResolvedEvent)],
    'jump':
        [Triggered(KWAModEffect('add', 'Flying', True), T_FUNCS['creatures_in_play'], CastResolvedEvent)],
    'junun-efreet':
        [Triggered(PayManaOrSac('BB'), None, UpkeepEvent)],
    'juzam-djinn':
        [Triggered(DealDamageOnSourceTurn(1), None, UpkeepEvent)],
    'karma':
        [Triggered(Karma(), None, UpkeepEvent)],
    'kobold-overlord':
        [Triggered(KoboldOverlordCast(), None, CastResolvedEvent)],
    'kobold-taskmaster':
        [Triggered(KoboldTaskmaster(), None, CastResolvedEvent)],
    'lance':
        [Triggered(KWAModEffect('add', 'First Strike'), T_FUNCS['creatures_in_play'], CastResolvedEvent)],
    'leviathan':
        [Triggered(TapCardEffect(), T_FUNCS['self'], CastResolvedEvent)],
    'lightning-bolt':
        [Triggered(DealDamage(3), T_FUNCS['all_creatures_and_players'], CastResolvedEvent)],
    'living-armor':
        [Activated('T', XZeroOneCountersByManaValue(), T_FUNCS['creatures_in_play'], extra_costs=[SacSelfCost()])],
    'lord-of-the-pit':
        [Triggered(LordOfThePitUpkeep(), None, UpkeepEvent)],
    'mana-short':
        [Triggered(ManaShort(), T_FUNCS['all_players'], CastResolvedEvent)],
    'mana-vortex':
        [Triggered(BoardToGraveyard(), T_FUNCS['your_lands_in_play'], CastResolvedEvent),
         Triggered(ManaVortexUpkeep(), None, UpkeepEvent)],
    'necropolis':
        [Activated('', XZeroOneCountersByManaValue(), T_FUNCS['creatures_in_your_graveyard'])],  # TODO: needs an extra cost of "Exile a creature card from your graveyard"
    'nevinyrrals-disk':
        [Triggered(TapCardEffect(), T_FUNCS['self'], CastResolvedEvent)],
    'osai-vultures':
        [Triggered(AddCountersIfAnyCreatureDied(CARRION), T_FUNCS['self'], EndStepEvent)],
    'paralyze':
        [Triggered(TapCardEffect(), T_FUNCS['host'], CastResolvedEvent)],  # TODO: should there be an AttachToHost(Effect) ???
    'pestilence':
        [Triggered(PestilenceEndStep(), None, EndStepEvent)],
    'phantasmal-forces':
        [Triggered(PayManaOrSac('U'), None, UpkeepEvent)],
    'power-surge':
        [Triggered(PowerSurge(), None, UpkeepEvent)],
    'primordial-ooze':
        [Triggered(AddCountersYourTurnOnly(PLUS_ONE), T_FUNCS['self'], UpkeepEvent)],
    'psionic-blast':
        [Triggered(PsionicBlast(), T_FUNCS['all_creatures_and_players'], CastResolvedEvent)],
    'raise-dead':
        [Triggered(GraveyardToHand(), T_FUNCS['creatures_in_your_graveyard'], CastResolvedEvent)],
    'reconstruction':
        [Triggered(GraveyardToHand(), T_FUNCS['artifacts_in_your_graveyard'], CastResolvedEvent)],
    'regrowth':
        [Triggered(GraveyardToHand(), T_FUNCS['cards_in_your_graveyard'], CastResolvedEvent)],
    'resurrection':
        [Triggered(GraveyardToBoard(), T_FUNCS['creatures_in_your_graveyard', CastResolvedEvent])],
    'riptide':
        [Triggered(Riptide(), None, CastResolvedEvent)],
    'rock-hydra':
        [Triggered(RockHydraCast(), T_FUNCS['self'], CastResolvedEvent)],
    'scavenging-ghoul':
        [Triggered(AddCounterPerCreatureDeath(CORPSE), T_FUNCS['self'], EndStepEvent)],
    'season-of-the-witch':
        [Triggered(SeasonOfTheWitchUpkeep(), None, UpkeepEvent),
         Triggered(SeasonOfTheWitchEndStep(), None, EndStepEvent)],
    'serendib-djinn':
        [Triggered(DealDamageOnSourceTurn(1), None, UpkeepEvent)],
    'sinkhole':
        [Triggered(BoardToGraveyard(), T_FUNCS['lands_in_play'], CastResolvedEvent)],
    'skull-of-orm':
        [Activated('5T', GraveyardToHand(), T_FUNCS['enchants_in_your_graveyard'])],
    'stone-rain':
        [Triggered(BoardToGraveyard(), T_FUNCS['lands_in_play'], CastResolvedEvent)],
    'storm-seeker':
        [Triggered(StormSeeker(), T_FUNCS['all_players'], CastResolvedEvent)],
    'storm-world':
        [Triggered(StormWorld(), None, UpkeepEvent)],
    'sunken-city':
        [Triggered(PayManaOrSac('UU'), None, UpkeepEvent)],
    'tetravus':
        [Triggered(AddCountersYourTurnOnly(PLUS_ONE, 3), T_FUNCS['self'], CastResolvedEvent)],
    'time-vault':
        [Triggered(TapCardEffect(), T_FUNCS['self'], CastResolvedEvent)],
    'tivadars-crusade':
        [Triggered(DestroyAll(lambda gs, s: gs.card_filter.in_play().by_sub_type('Goblin').result()),
                   None, CastResolvedEvent)],
    'tormods-crypt':
        [Activated('T', GraveyardToExileInItsEntirety(), T_FUNCS['all_players'], extra_costs=[SacSelfCost()])],
    'tranquility':
        [Triggered(DestroyAll(lambda gs, s: gs.card_filter.in_play().by_type('Enchantment').result()),
                   None, CastResolvedEvent)],
    'triskelion':
        [Triggered(AddCountersYourTurnOnly(PLUS_ONE, 3), T_FUNCS['self'], CastResolvedEvent)],
    'tsunami':
        [Triggered(DestroyAll(lambda gs, s: gs.card_filter.in_play().by_slug('island').result()),
                   None, CastResolvedEvent)],
    'twiddle':
        [Triggered(Twiddle(), T_FUNCS['artifacts_creatures_lands_in_play'], CastResolvedEvent)],
    'typhoon':
        [Triggered(Typhoon(), T_FUNCS['opponent'], CastResolvedEvent)],
    'unholy-strength':
        [Triggered(PumpEffect(2, 1), T_FUNCS['creatures_in_play'], CastResolvedEvent)],
    'unstable-mutation':
        [Triggered(PumpEffect(3, 3), T_FUNCS['creatures_in_play'], CastResolvedEvent),
         Triggered(AddCountersOnHostTurn(MINUS_ONE), T_FUNCS['self'], UpkeepEvent)],
    'unsummon':
        [Triggered(BoardToHand(), T_FUNCS['creatures_in_play'], CastResolvedEvent)],
    'venarian-gold':
        [Triggered(RemoveCountersOnHostTurn(SLEEP), T_FUNCS['self'], UpkeepEvent)],
    'voodoo-doll':
        [Triggered(AddCountersYourTurnOnly(PIN), T_FUNCS['self'], UpkeepEvent),
         Triggered(VoodooDollEndStep(), None, EndStepEvent)],
    'warp-artifact':
        [Triggered(DealDamageOnTargetTurn(1), T_FUNCS['artifacts_in_play'], UpkeepEvent)],
    'weakness':
        [Triggered(PumpEffect(-2, -1), T_FUNCS['creatures_in_play'], CastResolvedEvent)],
    'wheel-of-fortune':
        [Triggered(WheelOfFortune(), trigger_event=CastResolvedEvent)],
    'wrath-of-god':
        [Triggered(ExileAllCreatures(), trigger_event=CastResolvedEvent)]
}




def get_activated_abilities(c: GameCard) -> list[ActivatedAbility | None]:
    eff_invocations = INVOCATIONS.get(c.props.slug)
    return [ActivatedAbility(c, inv) for inv in eff_invocations if inv.activation_type == 'activated'] if eff_invocations else []



# # --- NON-CARD-SPECIFIC PRE-CONSTRUCTED ACTIVATED ABILITY SPEC ---
# def untap_at_owners_upkeep(cost_mana: str):
#     return AAS(cost_mana, False, None, lambda gs, s, _: s.untap(gs), allowed_phases=[Phase.UPKEEP],
#                allowed_player_turn=ActivatedAbility.AllowedPlayerTurn.CASTER, text='Untap')
#
# def untap_host_at_owners_upkeep(cost_mana: str):
#     # WARNING: allowed_player_turn = OPPONENT assumes Paralyze has been played on an opp creature !!!
#     return AAS(cost_mana, False, None, lambda gs, s, _: s.attached_to.untap(gs), allowed_phases=[Phase.UPKEEP],
#                allowed_player_turn=ActivatedAbility.AllowedPlayerTurn.OPPONENT, text='Untap')
#
# # --- NON-CARD-SPECIFIC COMMON/COMPLEX EFFECT FUNCS ---
# def add_mana_func(color: str, amt: int = 1):
#     if color not in COLOR_LETTERS_W_COLORLESS:
#         raise ValueError(f"Color must be {COLOR_LETTERS_W_COLORLESS}")
#
#     def _effect(gs, s, t: GameCard):
#         gs.mana_pools[s.orig_owner_id].add_floating(color, amt)
#     return _effect
#
# def add_remove_kwa_temp(add_or_remove: str, kwa: str):
#     if add_or_remove not in {'add', 'remove'}:
#         raise ValueError("add_or_remove parameter must be either 'add' or 'remove'")
#
#     def _effect(gs, src, t: Target):
#         t.modifiers.temps.append(KWATemp(add_or_remove, kwa))
#     return _effect
#
# def deal_damage_func(amt: int = None):
#     def _effect(gs, source, target):
#         gs.apply_damage(source, amt, target)
#     return _effect
#
# def destroy_all_non_land_perms(gs: GameState, s: GameCard, t: Target):
#     for c in gs.card_filter.in_play().by_type(['Artifact', 'Creature', 'Enchantment']).result():
#         gs.send_to_graveyard_from_play(c)
#
# def destroy_func(gs: GameState, _: GameCard, t: Target):
#     gs.send_to_graveyard_from_play(t)
#
# def dual_land_activated_ability_specs(colors: str) -> list[AAS]:
#     return [AAS('', True, T_FUNCS['card_owner'], add_mana_func(color), text=f'Add {{{color}}}') for color in colors]
#
# def prevent_next_damage_func(amt: int = None):
#     def _effect(gs, src, _):
#         gs.damage_preventions.append(PreventNextDamage(src, amt))
#     return _effect
#
# def pump_func(p_delta: int, t_delta: int):
#     def _effect(gs, source, t: GameCard):
#         t.modifiers.temps.append(PTTemp(p_delta, t_delta))
#     return _effect
#
# # --- CARD SPECIFIC COMPLEX FUNCS ---
# def book_of_rass_func(gs: GameState, c: GameCard, _: Target):
#     gs.decrement_life(c.orig_owner_id, 2, c)
#     gs.draw(gs.hands[c.orig_owner_id], gs.decks[c.orig_owner_id].cards, 1)
#
# def brothers_of_fire_func(gs: GameState, source: GameCard, t: Target):
#     """1 damage to target; 1 damage to caster/owner"""
#     gs.apply_damage(source, 1, t)
#     gs.apply_damage(source, 1, source.orig_owner_id)
#
# def electric_eel_func(gs: GameState, source: GameCard, _: Target):
#     source.modifiers.temps.append(PTTemp(2, 0))
#     gs.apply_damage(source, 1, source.orig_owner_id)
#
# def elves_of_deep_shadow_func(gs: GameState, source: GameCard, _: Target):
#     gs.mana_pools[source.orig_owner_id].add_floating('B')
#     gs.apply_damage(source, 1, source.orig_owner_id)
#
# def exchange_life_totals(gs: GameState, s: GameCard, _: Target):
#     your_life = gs.life[s.orig_owner_id]
#     opp_life = gs.life[flip(s.orig_owner_id)]
#     gs.life[s.orig_owner_id], gs.life[flip(s.orig_owner_id)] = opp_life, your_life
#
# def forcefield_func(gs: GameState, s: GameCard, t: Target):
#     gs.damage_preventions.append(PreventNextDamage(s, source_card=t, target_player=s.orig_owner_id, combat_only=True))
#     gs.apply_damage(t, 1, s.orig_owner_id, is_combat=True)
#
# def greed_func(gs: GameState, source: GameCard, _: Target):
#     gs.decrement_life(source.orig_owner_id, 2, source)
#     gs.draw(gs.hands[source.orig_owner_id], gs.decks[source.orig_owner_id].cards, 1)
#
# def hammerheim_func(gs: GameState, source: GameCard, t: Target):
#     for land in ('Island', 'Forest', 'Mountain', 'Swamps', 'Plains'):
#         t.modifiers.temps.append(KWATemp('remove', f'{land}walk'))
#
# def kry_shield_func(gs: GameState, s: GameCard, t: Target):
#     """Prevent all damage that would be dealt this turn by target creature you control.
#     That creature gets +0/+X until end of turn, where X is its mana value"""
#     gs.damage_preventions.append(PreventNextDamage(s, source_card=t))
#     t.modifiers.temps.append(PTTemp(0, t.props.casting_weight))
#
# def jade_monolith_func(gs: GameState, s: GameCard, t: Optional[GameCard] = None):
#     """target = the GameCard being protected"""
#
#     def redirect_damage(prevented: int):
#         gs.apply_damage(t, prevented, t.orig_owner_id)
#
#     gs.damage_preventions.append(PreventNextDamage(s, None, target_card=t, on_prevent=redirect_damage))
#
# def maze_of_ith_func(gs: GameState, s: GameCard, t: Target):
#     the_combat = [com for com in gs.combats if com.attacker == t]
#     if not the_combat:
#         return
#     gs.damage_preventions.append(PreventNextDamage(s, None, target_card=t, combat_only=True))
#     for b in the_combat[0].blockers:
#         gs.damage_preventions.append(PreventNextDamage(s, None, target_card=b, combat_only=True))
#     t.untap(gs)
#
# def orcish_artillery_func(gs: GameState, s: GameCard, t: Target):
#     """{T}: This creature deals 2 damage to any target and 3 damage to you"""
#     gs.apply_damage(s, 2, t)
#     gs.apply_damage(s, 3, s.orig_owner_id)
#
# def psionic_entity_func(gs: "GameState", source: "GameCard", t: Target):
#     # {T}: This creature deals 2 damage to any target and 3 damage to itself
#     gs.apply_damage(source, 2, t)
#     gs.apply_damage(source, 3, source)
#
# def rakalite_func(gs: GameState, s: GameCard, _: Target):
#     prevent_next_damage_func(1)
#     gs.return_to_hand(s)
#
# def rocket_launcher_func(gs: GameState, s: GameCard, t: Target):
#     """{2}: Deal 1 damage to any target. Destroy Rocket Launcher at next end step."""
#     gs.apply_damage(s, 1, t)
#     gs.end_step_funcs.append(lambda gs, s: gs.send_to_graveyard_from_play(s))
#
# def shimian_nightstalker_func(gs: GameState, s: GameCard, t: Target):
#     """{B}, {T}: All damage that would be dealt to you this turn by target attacking creature is dealt
#     to this creature instead.  target = the GameCard doing the damage"""
#     def redirect_damage(prevented: int):
#         gs.apply_damage(t, prevented, t.orig_owner_id)
#
#     gs.damage_preventions.append(PreventNextDamage(s, None, target_player=s.orig_owner_id,
#                                                    source_card=t, on_prevent=redirect_damage))
#
# def stone_giant_func(gs: GameState, s: GameCard, t: Target):
#     """{T}: Target creature you control with toughness less than this creature's power gains flying until end of turn.
#     Destroy that creature at the beginning of the next end step."""
#     add_remove_kwa_temp('add', 'Flying')
#     gs.end_step_funcs.append(lambda gs, s: gs.send_to_graveyard_from_play(t))


# MANA_BATTERY_ADD_CHARGE_AAS = AAS('2', True, lambda _, s: s, lambda gs, s, t: s.counters.add_counter(CHARGE))
#
# ACTIVATED_ABILITY: dict[str, list[AAS]] = {
#     'amulet-of-kroog': [AAS('2', True, T_FUNCS['all_creatures_and_players'], prevent_next_damage_func(1))],
#     'argivian-blacksmith': [AAS('', True, T_FUNCS['artifact_creatures_in_play'], prevent_next_damage_func(2))],
#     'badlands': dual_land_activated_ability_specs('BR'),
#     'bayou': dual_land_activated_ability_specs('BG'),
#     'blessing': [AAS('W', False, None, pump_func(1, 1))],
#     # 'birds-of-paradise': [AAS('', True, T_FUNCS['card_owner'],
#     #                           add_mana_func(c), text=f'Add 1 {c}') for c in COLOR_LETTERS],
#     'black-mana-battery': [MANA_BATTERY_ADD_CHARGE_AAS],  # add discharge logic
#     'blue-mana-battery': [MANA_BATTERY_ADD_CHARGE_AAS],  # add discharge logic
#     'book-of-rass': [AAS('2', False, T_FUNCS['card_owner'], lambda gs, s, t: book_of_rass_func(gs, s, t))],
#     'brainwash': [AAS('3', False, None, add_remove_kwa_temp('add', 'Attack'))],  # WARNING: validate that target_Filter=None is correct
#     'brass-man': [untap_at_owners_upkeep('1')],
#     'brothers-of-fire':
#         [AAS('', True, T_FUNCS['all_creatures_and_players'], lambda gs, s, t: brothers_of_fire_func(gs, s, t))],
#     'carrion-ants': [AAS('1', False, None, pump_func(1, 1))],
#     'celestial-prism': [AAS('2', True, T_FUNCS['card_owner'],
#                             add_mana_func(c), text=f'Add 1 {c}') for c in COLOR_LETTERS],
#     'circle-of-protection-artifacts':
#         [AAS('1', False, T_FUNCS['artifacts_in_play'],  # would this include instants/sorceries?
#              lambda gs, src, t: gs.damage_preventions.append(PreventNextDamage(src, source_card=t, target_player=src.orig_owner_id)))],
#     'circle-of-protection-black':
#         [AAS('1', False, T_FUNCS['black_in_play'],  # would this include instants/sorceries?
#              lambda gs, src, t: gs.damage_preventions.append(PreventNextDamage(src, source_card=t, target_player=src.orig_owner_id)))],
#     'circle-of-protection-blue':
#         [AAS('1', False, T_FUNCS['blue_in_play'],  # would this include instants/sorceries?
#              lambda gs, src, t: gs.damage_preventions.append(PreventNextDamage(src, source_card=t, target_player=src.orig_owner_id)))],
#     'circle-of-protection-green':
#         [AAS('1', False, T_FUNCS['green_in_play'],  # would this include instants/sorceries?
#              lambda gs, src, t: gs.damage_preventions.append(PreventNextDamage(src, source_card=t, target_player=src.orig_owner_id)))],
#     'circle-of-protection-red':
#         [AAS('1', False, T_FUNCS['red_in_play'],  # would this include instants/sorceries?
#              lambda gs, src, t: gs.damage_preventions.append(PreventNextDamage(src, source_card=t, target_player=src.orig_owner_id)))],
#     'circle-of-protection-white':
#         [AAS('1', False, T_FUNCS['white_in_play'],  # would this include instants/sorceries?
#              lambda gs, src, t: gs.damage_preventions.append(PreventNextDamage(src, source_card=t, target_player=src.orig_owner_id)))],
#     'coal-golem':
#         [AAS('3', False, None, add_mana_func('R', 3), extra_costs=[SacSelfCost()])],
#     'colossus-of-sardia': [untap_at_owners_upkeep('9')],
#     'conservator':
#         [AAS('3', True, None, lambda gs, src, _: gs.damage_preventions.append(
#                         PreventNextDamage(src, remaining=2, target_player=src.orig_owner_id)))],
#     'dragon-engine': [AAS('2', False, None, pump_func(1, 0))],
#     'dwarven-demolition-team': [AAS('', True, T_FUNCS['walls_in_play'], destroy_func)],
#     'electric-eel': [AAS('RR', False, None, lambda gs, s, t: electric_eel_func(gs, s, t))],
#     'elves-of-deep-shadow': [AAS('', True, None, lambda gs, s, t: elves_of_deep_shadow_func(gs, s, t))],
#     'emerald-dragonfly': [AAS('GG', False, None, add_remove_kwa_temp('add', 'First Strike'))],
#     'exorcist': [AAS('1W', True, T_FUNCS['black_creatures_in_play'], destroy_func)],
#     'farmstead':
#         [AAS('WW', True, lambda gs, _: gs.player_turn_idx, lambda gs, _, t: gs.increment_life(gs.player_turn_idx, 1))],
#     'fire-drake': [AAS('R', False, None, pump_func(1, 0), max_activations_per_turn=1)],
#     'fire-sprites': [AAS('G', True, lambda _, s: s.orig_owner_id, add_mana_func('R'))],
#     'firebreathing': [AAS('R', False, None, pump_func(1, 0))],
#     'flood':
#         [AAS('UU', False, lambda gs, source: CardFilter(gs).in_play().creatures().untapped().has('Flying', False).result(),
#              lambda gs, source, t: t.tap(gs))],
#     'flying-carpet':
#         [AAS('2', True, T_FUNCS['creatures_in_play'], add_remove_kwa_temp('add', 'Flying'))],
#     'forcefield':
#         # Next time an unblocked creature of your choice would deal combat damage to you this turn, reduce damage to 1
#         [AAS('1', False, T_FUNCS['unblocked_attackers'], forcefield_func)],
#     'fountain-of-youth':
#         [AAS('2', True, lambda _, s: s.orig_owner_id, lambda gs, s, _: gs.increment_life(s.orig_owner_id, 1, s))],
#     'frozen-shade': [AAS('B', False, None, pump_func(1, 1))],
#     'gaeas-touch': [AAS('', False, lambda gs, s: s.orig_owner_id, add_mana_func('G', 2),
#                         extra_costs=[ExileSelfCost()])],  # gaeas-touch has one more Activated Ability left to code
#     'ghosts-of-the-damned':
#         [AAS('', True, T_FUNCS['creatures_in_play'], pump_func(-1, 0))],
#     'goblin-balloon-brigade':  # is lambda gs, source: source the best way?
#         [AAS('R', False, lambda gs, source: source, add_remove_kwa_temp('add', 'Flying'))],
#     'goblin-digging-team': [AAS('', True, T_FUNCS['walls_in_play'], destroy_func,
#                                 extra_costs=[SacSelfCost()])],
#     'granite-gargoyle': [AAS('R', False, lambda gs, source: source, pump_func(0, 1))],
#     'grapeshot-catapult': [AAS('', True, T_FUNCS['fliers_in_play'], deal_damage_func(4))],
#     'greater-realm-of-preservation':
#         [AAS('1W', False, T_FUNCS['black_and_red_in_play'],  # would this include instants/sorceries?
#              lambda gs, src, t: gs.damage_preventions.append(
#                             PreventNextDamage(src, source_card=t, target_player=src.orig_owner_id)))],
#     'greed': [AAS('B', False, T_FUNCS['card_owner'], lambda gs, s, t: greed_func(gs, s, t))],
#     'green-mana-battery': [MANA_BATTERY_ADD_CHARGE_AAS],  # add discharge logic
#     'hammerheim':
#         # {T}: Add {R}. {T}: Target creature loses all landwalk abilities until end of turn.
#         [AAS('', True, lambda _, s: s.orig_owner_id, add_mana_func('R')),
#          AAS('', True, T_FUNCS['creatures_in_play'], lambda gs, s, t: hammerheim_func(gs, s, t))],
#     'holy-armor': [AAS('W', False, None, pump_func(0, 1))],
#     'horn-of-deafening':
#         [AAS('2', True, T_FUNCS['creatures_in_play'],
#              lambda gs, s, t: gs.damage_preventions.append(PreventNextDamage(s, source_card=t,
#                                                                                         combat_only=True)))],
#     'hyperion-blacksmith':
#         # {T}: You may tap or untap target artifact an opponent controls
#         [AAS('', True, lambda gs, s: CardFilter(gs).on_player_board(flip(s.orig_owner_id)).artifacts().result(),
#              lambda gs, source, t: t.untap(gs) if t.is_tapped else t.tap(gs))],
#     'icy-manipulator':
#     # {1}, {T}: Tap target artifact, creature, or land
#         [AAS('1', True, lambda gs, source: CardFilter(gs).in_play().by_type(['Artifact', 'Creature', 'Land']).tapped(False).result(),
#              lambda gs, source, t: t.tap(gs))],
#     'instill-energy':
#         # {0}: Untap enchanted creature. Activate only during your turn and only once each turn
#         [AAS('', False, None, lambda gs, source, t: t.untap(gs),
#              allowed_player_turn=ActivatedAbility.AllowedPlayerTurn.CASTER, max_activations_per_turn=1)],
#     'island-fish-jasconius': [untap_at_owners_upkeep('UUU')],
#     'jade-monolith': [AAS('1', False, T_FUNCS['all_creatures_and_players'], jade_monolith_func)],
#     'jandors-saddlebags': [AAS('3', True, T_FUNCS['tapped_creatures'], lambda gs, source, t: t.untap(gs))],
#     'jayemdae-tome':
#         [AAS('4', True, T_FUNCS['card_owner'],
#              lambda gs, s, t: gs.draw(gs.hands[s.orig_owner_id], gs.decks[s.orig_owner_id].cards, 1))],
#     'killer-bees': [AAS('G', False, lambda gs, source: source, pump_func(1, 1))],
#     'king-suleiman':
#         [AAS('', True, lambda gs, s: gs.card_filter.in_play().by_sub_type(['Djinn', 'Efreet']).result(),
#              destroy_func)],
#     'kry-shield': [AAS('2', True, T_FUNCS['your_creatures_in_play'], kry_shield_func)],
#     'ley-druid':
#         [AAS('', True, T_FUNCS['tapped_lands'], lambda gs, source, t: t.untap(gs))],
#     'llanowar-elves': [AAS('', True, T_FUNCS['card_owner'], add_mana_func('G'))],
#     'mana-vault': [untap_at_owners_upkeep('4'), AAS('', True, T_FUNCS['card_owner'], add_mana_func('C', 3))],
#     'maze-of-ith': [AAS('', True, lambda gs, s: gs.card_filter.attackers().result(), maze_of_ith_func)],
#     'merfolk-assassin':
#         [AAS('', True, lambda gs, source: gs.card_filter.in_play().has('Islandwalk').result(), destroy_func)],
#     'miracle-worker':
#         [AAS('', True, T_FUNCS['auras_on_owners_creatures'], destroy_func)],  # should i send an aura to the graveyard w/o using host.remove_aura()?
#     'mirror-universe': [AAS('', True, None, exchange_life_totals, allowed_phases=[Phase.UPKEEP],
#                             allowed_player_turn=ActivatedAbility.AllowedPlayerTurn.CASTER, extra_costs=[SacSelfCost()])],
#     'mox-emerald': [AAS('', True, T_FUNCS['card_owner'], add_mana_func('G'))],
#     'mox-jet': [AAS('', True, T_FUNCS['card_owner'], add_mana_func('B'))],
#     'mox-pearl': [AAS('', True, T_FUNCS['card_owner'], add_mana_func('W'))],
#     'mox-ruby': [AAS('', True, T_FUNCS['card_owner'], add_mana_func('R'))],
#     'mox-sapphire': [AAS('', True, T_FUNCS['card_owner'], add_mana_func('U'))],
#     'nettling-imp': [AAS('', True, T_FUNCS['opp_creatures_who_could_have_but_didnt_attack'],
#                          lambda gs, s, t: gs.end_step_funcs.append(nettling_imp_on_end_step),
#                          allowed_player_turn=ActivatedAbility.AllowedPlayerTurn.OPPONENT,
#                          allowed_phases=[phase for phase in Phase if phase < Phase.DECLARE_ATTACKERS])],
#     'nevinyrrals-disk': [AAS('1', True, None, lambda gs, s, t: destroy_all_non_land_perms(gs, s, t))],
#     'northern-paladin': [AAS('WW', True, T_FUNCS['creatures_and_enchantments_in_play'], destroy_func)],
#     'oasis': [AAS('', True, T_FUNCS['creatures_in_play'], prevent_next_damage_func(1))],
#     'orcish-artillery': [AAS('', True, T_FUNCS['all_creatures_and_players'], orcish_artillery_func)],
#     'paralyze': [untap_host_at_owners_upkeep('4')],
#     'pendelhaven':
#         [AAS('', True, lambda gs, s: s.orig_owner_id, add_mana_func('G')),
#          AAS('', True, T_FUNCS['one_one_creatures_in_play'], pump_func(1, 2))],
#     'pirate-ship': [AAS('', True, T_FUNCS['all_creatures_and_players'], deal_damage_func(1))],
#     'pixie-queen':
#         [AAS('GGG', True, T_FUNCS['creatures_in_play'], add_remove_kwa_temp('add', 'Flying'))],
#     'plateau': dual_land_activated_ability_specs('RW'),
#     'pradesh-gypsies': [AAS('1G', True, T_FUNCS['creatures_in_play'], pump_func(-2, 0))],
#     'prodigal-sorcerer': [AAS('', True, T_FUNCS['all_creatures_and_players'], deal_damage_func(1))],
#     'psionic-entity':
#         [AAS('', True, T_FUNCS['all_creatures_and_players'], lambda gs, s, t: psionic_entity_func(gs, s, t))],
#     'radjan-spirit':
#         [AAS('', True, T_FUNCS['creatures_in_play'], add_remove_kwa_temp('remove', 'Flying'))],
#     'rakalite': [AAS('2', False, T_FUNCS['all_creatures_and_players'], rakalite_func)],
#     'red-mana-battery': [MANA_BATTERY_ADD_CHARGE_AAS],  # add discharge logic
#     'relic-barrier': [AAS('', True, T_FUNCS['untapped_artifacts_in_play'], lambda gs, s, t: t.tap(gs))],
#     'rod-of-ruin': [AAS('3', True, T_FUNCS['all_creatures_and_players'], deal_damage_func(1))],
#     'rocket-launcher':
#         [AAS('2', False, T_FUNCS['all_creatures_and_players'], lambda gs, s, t: rocket_launcher_func(gs, s, t))],
#     'royal-assassin': [AAS('', True, T_FUNCS['tapped_creatures'], destroy_func)],
#     'samite-healer': [AAS('', True, T_FUNCS['all_creatures_and_players'], prevent_next_damage_func(1))],
#     'savannah': dual_land_activated_ability_specs('GW'),
#
#     'savaen-elves': [AAS('GG', True, T_FUNCS['auras_on_lands'], destroy_func)],
#     'scarecrow': [AAS('6', True, None,
#                       lambda gs, s, t: gs.global_effects.append((s, scarecrow_func)))],
#     'scarwood-hag': [AAS('GGGG', True, T_FUNCS['creatures_in_play_wo_forestwalk'],
#                          add_remove_kwa_temp('add', 'Forestwalk')),
#                      AAS('GGGG', True, T_FUNCS['creatures_in_play_w_forestwalk'],
#                          add_remove_kwa_temp('remove', 'Forestwalk'))],
#     'scavenger-folk': [AAS('G', True, T_FUNCS['artifacts_in_play'], destroy_func, extra_costs=[SacSelfCost()])],
#     'scrubland': dual_land_activated_ability_specs('BW'),
#     'shimian-night-stalker': [AAS('B', True, T_FUNCS['attackers'], shimian_nightstalker_func)],
#     'shivan-dragon': [AAS('R', False, None, pump_func(1, 0))],
#     'sisters-of-the-flame': [AAS('', True, lambda gs, s: s.orig_owner_id, add_mana_func('R'))],
#     'sol-ring': [AAS('', True, lambda gs, s: s.orig_owner_id, add_mana_func('C', 2))],
#     'sorceress-queen': [AAS('', True, lambda gs, s: [c for c in T_FUNCS['creatures_in_play'] if c != s],
#                             lambda gs, s, t: t.modifiers.temps.append(PTTemp(-t.power, t.toughness - 2)))],
#     'spinal-villain': [AAS('', True, T_FUNCS['blue_creatures_in_play'], destroy_func)],
#     'staff-of-zegon': [AAS('3', True, T_FUNCS['creatures_in_play'], pump_func(-2, 0))],
#     'stone-giant': [AAS('', True, T_FUNCS['stone_giant'], stone_giant_func)],
#     'strip-mine': [AAS('', True, lambda gs, s: s.orig_owner_id, add_mana_func('C')),
#                    AAS('', True, T_FUNCS['lands_in_play'], destroy_func, extra_costs=[SacSelfCost()])],
#     'taiga': dual_land_activated_ability_specs('RG'),
#     'tropical-island': dual_land_activated_ability_specs('GU'),
#     'tundra': dual_land_activated_ability_specs('WU'),
#     'underground-sea': dual_land_activated_ability_specs('BU'),
#     'volcanic-island': dual_land_activated_ability_specs('RU'),
#     'wall-of-water': [AAS('U', False, None, pump_func(1, 0))],
#     'white-mana-battery': [MANA_BATTERY_ADD_CHARGE_AAS],  # add discharge logic
# }
