from __future__ import annotations
from typing import Callable, TYPE_CHECKING

if TYPE_CHECKING:
    from game_state import GameState
    from game_card import GameCard

from models.constants import ALL_PLAYER_INDICES, BASIC_LANDS, KW, Zone
from models.utils import flip

A_FUNCS: [str, Callable[[GameState, GameCard], tuple[int | None]]] = {
    'all_players': lambda gs, s: (0, 1),
    'host_owner': lambda gs, s: (s.host.owner_id, ),
    'opponent': lambda gs, s: (flip(s.owner_id), ),
}

C_FUNCS: [str, Callable[[GameState, GameCard], bool]] = {
    'host_is_basic_mountain': lambda gs, s: s.host.props.slug == 'mountain',
    'self_is_not_attacking': lambda gs, s: s not in gs.card_filter.attackers().result(),
    'self_is_untapped': lambda gs, s: not s.is_tapped,
    'no_lands': lambda gs, s: len(CF.lands()(gs, s)) == 0,
    'opp_has_island': lambda gs, s: gs.card_filter.on_player_board(flip(s.owner_id)).islands().result(),
    'opp_has_non_token_white_perm': lambda gs, s: gs.card_filter.on_player_board(flip(s.owner_id)).non_token().white().permanents().result(),
    'you_have_a_dwarf': lambda gs, s: len(CF.your_dwarves()(gs, s)) > 0,
    'you_have_a_forest': lambda gs, s: gs.card_filter.on_player_board(s.owner_id).forests().result(),
    'you_have_a_swamp': lambda gs, s: gs.card_filter.on_player_board(s.owner_id).forests().result(),
    'you_have_no_lands': lambda gs, s: len(CF.your_lands()(gs, s)) == 0
}

class CF:
    """A collection of methods that return lambdas, allowing IDE recommended completion in slug-effspec map;
    Always returns "lambda GameState, source: []" (with a couple exceptions like .self() which should be addressed);
    Ex: CF.black_creatures() (as in 'bad-moon') -> lambda gs, s: gs.card_filter.in_play().creatures().black().result()
    Since 90% of lookups seek cards on battlefield, keys that don't specify will only return those on battlfield.
    Ex: CF.artifacts() will only return artifact creatures currently on the battlefield.
    Ex: CF.artifacts_in_graveyards() explicitly indicates that it's looking somewhere besides the battlefield."""

    @staticmethod
    def all_creatures_and_players():
        return lambda gs, s: gs.card_filter.in_play().creatures().result() + [0, 1]

    @staticmethod
    def all_lands_in_game():
        return lambda gs, s: gs.card_filter.lands().result()

    @staticmethod
    def all_players():
        return lambda gs, s: [0, 1]

    @staticmethod
    def another_orc_or_goblin():
        return lambda gs, s: [c for c in gs.card_filter.in_play().by_sub_type(['Orc', 'Golbin']).result() if c is not s]

    @staticmethod
    def artifact_creatures():
        return lambda gs, s: gs.card_filter.in_play().artifacts().creatures().result()

    @staticmethod
    def artifact_spells():
        return lambda gs, s: [s for s in gs.action_stack.spells if s.card.is_artifact]

    @staticmethod
    def artifacts_and_enchantments():
        return lambda gs, s: gs.card_filter.in_play().by_type(['Artifact', 'Enchantment']).result()

    @staticmethod
    def artifacts_creatures_enchantments():
        return lambda gs, s: gs.card_filter.in_play().by_type(['Artifact', 'Creature', 'Enchantment']).result()

    @staticmethod
    def artifacts_creatures_lands():
        return lambda gs, s: gs.card_filter.in_play().by_type(['Artifact', 'Creature', 'Land']).result()

    @staticmethod
    def artifacts():
        return lambda gs, s: gs.card_filter.in_play().artifacts().result()

    @staticmethod
    def artifacts_in_graveyards():
        return lambda gs, s: gs.card_filter.in_graveyards().artifacts().result()

    @staticmethod
    def artifacts_in_your_graveyard():
        return lambda gs, s: gs.card_filter.in_player_graveyard(s.owner_id).artifacts().result()

    @staticmethod
    def assembly_workers():
        return lambda gs, s: gs.card_filter.in_play().by_sub_type('Assembly-Worker').result()

    @staticmethod
    def attackers():
        return lambda gs, s: gs.card_filter.attackers().result()

    @staticmethod
    def auras_on_creatures():
        return lambda gs, s: [a for c in gs.card_filter.in_play().creatures().result() for a in c.auras]

    @staticmethod
    def auras_on_lands():
        return lambda gs, s: [a for c in gs.card_filter.in_play().lands().result() for a in c.auras]

    @staticmethod
    def auras_on_creatures_or_lands():
        return lambda gs, s: [a for c in gs.card_filter.in_play().creatures().result() for a in c.auras] + \
                             [a for c in gs.card_filter.in_play().lands().result() for a in c.auras]

    @staticmethod
    def auras_on_owners_creatures():
        return lambda gs, s: [a for c in gs.card_filter.on_player_board(s.owner_id).creatures().result()
                              for a in c.auras]

    @staticmethod
    def basic_lands_in_your_library():
        return lambda gs, s: [c for c in gs.card_filter.in_play_library(s.owner_id).result() if c.props.is_basic_land]

    @staticmethod
    def black():
        return lambda gs, s: gs.card_filter.in_play().black().result()

    @staticmethod
    def black_and_red():
        return lambda gs, s: gs.card_filter.in_play().black().result() + gs.card_filter.in_play().red().result()

    @staticmethod
    def black_creatures():
        return lambda gs, s: gs.card_filter.in_play().creatures().black().result()

    @staticmethod
    def black_permanents():
        return lambda gs, s: gs.card_filter.in_play().permanents().black().result()

    @staticmethod
    def black_spells():
        return lambda gs, s: [s for s in gs.action_stack.spells if s.card.is_black]

    @staticmethod
    def blockers():
        return lambda gs, s: gs.card_filter.blockers().result()

    @staticmethod
    def blocking_walls():
        return lambda gs, s: gs.card_filter.blockers().walls().result()

    @staticmethod
    def blue():
        return lambda gs, s: gs.card_filter.in_play().blue().result()

    @staticmethod
    def blue_creatures():
        return lambda gs, s: gs.card_filter.in_play().creatures().blue().result()

    @staticmethod
    def blue_permanents():
        return lambda gs, s: gs.card_filter.in_play().permanents().blue().result()

    @staticmethod
    def blue_spells():
        return lambda gs, s: [s for s in gs.action_stack.spells if s.card.is_blue]

    @staticmethod
    def cards():
        return lambda gs, s: gs.card_filter.in_play().result()

    @staticmethod
    def cards_in_your_graveyard():
        return lambda gs, s: gs.card_filter.in_player_graveyard(s.owner_id).result()

    @staticmethod
    def cards_in_your_hand():
        return lambda gs, s: gs.card_filter.in_player_hand(s.owner_id).result()

    @staticmethod
    def city_in_a_bottle():
        return lambda gs, s: [c for c in
                              gs.card_filter.in_play().non_token().permanents().by_set_code('arn').result()
                              if c.props.slug != 'city-in-a-bottle']

    @staticmethod
    def combatants():
        return lambda gs, s: gs.card_filter.combatants().result()

    @staticmethod
    def combating_against():
        return lambda gs, s: gs.card_filter.combating_against(s).result()

    @staticmethod
    def creature_spells():
        return lambda gs, s: [s for s in gs.action_stack.spells if s.card.is_creature]

    @staticmethod
    def creatures_in_all_graveyards():
        return lambda gs, s: gs.card_filter.in_graveyards().creatures().result()

    @staticmethod
    def creatures():
        return lambda gs, s: gs.card_filter.in_play().creatures().result()

    @staticmethod
    def creatures_w_forestwalk():
        return lambda gs, s: gs.card_filter.in_play().has(KW.FORESTWALK).result()

    @staticmethod
    def creatures_wo_forestwalk():
        return lambda gs, s: gs.card_filter.in_play().has(KW.FORESTWALK, False).result()

    @staticmethod
    def creatures_in_your_graveyard():
        return lambda gs, s: gs.card_filter.in_player_graveyard(s.owner_id).creatures().result()

    @staticmethod
    def creatures_and_enchantments():
        return lambda gs, s: gs.card_filter.in_play().by_type(['Creature', 'Enchantment']).result()

    @staticmethod
    def creatures_and_lands():
        return lambda gs, s: gs.card_filter.in_play().creatures().result() + gs.card_filter.in_play().lands.result()

    @staticmethod
    def creatures_and_players():
        return lambda gs, s: gs.card_filter.in_play().creatures().result() + ALL_PLAYER_INDICES

    @staticmethod
    def creatures_power_two_or_less():
        return lambda gs, s: [c for c in gs.card_filter.in_play().creatures().result() if c.power <= 2]

    @staticmethod
    def creatures_power_three_or_more():
        return lambda gs, s: [c for c in gs.card_filter.in_play().creatures().result() if c.power >= 3]

    @staticmethod
    def creatures_with_first_strike():
        return lambda gs, s: [c for c in gs.card_filter.in_play().creatures().result
                              if KW.FIRST_STRIKE in c.keyword_abilities]

    @staticmethod
    def creatures_with_swampwalk():
        return lambda gs, s: [c for c in gs.card_filter.in_play().creatures().result
                              if KW.SWAMPWALK in c.keyword_abilities]

    @staticmethod
    def djinns_and_efreets():
        return lambda gs, s: gs.card_filter.in_play().by_sub_type(['Djinn', 'Efreet']).result()

    @staticmethod
    def elephants():
        return lambda gs, s: gs.card_filter.in_play().by_sub_type('Elephant').result()

    @staticmethod
    def enchanted_cards():
        return lambda gs, s: gs.card_filter.is_enchanted().result()

    @staticmethod
    def enchanted_creatures():
        return lambda gs, s: gs.card_filter.is_enchanted().creatures().result()

    @staticmethod
    def enchants():
        return lambda gs, s: gs.card_filter.in_play.enchantments().result()

    @staticmethod
    def enchants_in_your_graveyard():
        return lambda gs, s: gs.card_filter.in_player_graveyard(s.owner_id).enchantments().result()

    @staticmethod
    def flash_flood():
        return lambda gs, s: (gs.card_filter.in_play().red().permanents().result() +
                              gs.card_filter.in_play().mountains().result())

    @staticmethod
    def fliers():
        return lambda gs, _: gs.card_filter.in_play().creatures().has(KW.FLYING).result()

    @staticmethod
    def forests():
        return lambda gs, _: gs.card_filter.in_play().forests().result()

    @staticmethod
    def forests_in_your_hand():
        return lambda gs, s: gs.card_filter.in_player_hand(s.owner_id).forests().result()

    @staticmethod
    def forestwalkers():
        return lambda gs, s: gs.card_filter.in_play().has(KW.FORESTWALK).result()

    @staticmethod
    def goblin_permanents_in_your_hand():
        return lambda gs, s: gs.card_filter.in_player_hand(s.owner_id).by_sub_type('Goblin').permanents().result()

    @staticmethod
    def goblins():
        return lambda gs, s: gs.card_filter.in_play().by_sub_type('Goblin').result()

    @staticmethod
    def golgothian_sylex():
        return lambda gs, s: [c for c in gs.card_filter.in_play().non_token().permanents().by_set_code('AQ').result()
                              if c.props.slug != 'golgothian-sylex']

    @staticmethod
    def green():
        return lambda gs, s: gs.card_filter.in_play().green().result()

    @staticmethod
    def green_and_white_creatures():
        return lambda gs, s: (gs.card_filter.in_play().green().creatures().result() +
                              gs.card_filter.in_play().white().creatures().result())

    @staticmethod
    def green_creatures():
        return lambda gs, s: gs.card_filter.in_play().creatures().green().result()

    @staticmethod
    def green_spells():
        return lambda gs, s: [s for s in gs.action_stack.spells if s.card.is_green]

    @staticmethod
    def host():
        return lambda gs, s: s.host

    @staticmethod
    def host_owner():
        return lambda gs, s: s.host.owner_id

    @staticmethod
    def in_turn_player():
        return lambda gs, _: gs.player_turn_idx

    @staticmethod
    def in_turn_player_tapped_blue_creatures():
        return lambda gs, s: gs.card_filter.on_player_board(gs.player_turn_idx).tapped().blue().creatures().result()

    @staticmethod
    def instant_spells():
        return lambda gs, s: [s for s in gs.action_stack.spells if s.card.is_instant]

    @staticmethod
    def islands():
        return lambda gs, s: gs.card_filter.in_play().islands().result()

    @staticmethod
    def islandwalkers():
        return lambda gs, s: gs.card_filter.in_play().has(KW.ISLANDWALK).result()

    @staticmethod
    def lands():
        return lambda gs, s: gs.card_filter.in_play().lands().result()

    @staticmethod
    def legendary_creatures():
        return lambda gs, s: gs.card_filter.in_play().legendary().creatures().result()

    @staticmethod
    def mountains():
        return lambda gs, s: gs.card_filter.in_play().mountains().result()

    @staticmethod
    def non_artifact_creatures():
        return lambda gs, s: gs.card_filter.in_play().non_artifact_creatures().result()

    @staticmethod
    def non_artifact_non_black_creatures():
        return lambda gs, s: gs.card_filter.non_artifact_creatures().non_black().result()

    @staticmethod
    def non_artifact_non_white_creatures():
        return lambda gs, s: gs.card_filter.non_artifact_creatures().non_white().result()

    @staticmethod
    def non_basic_lands():
        return lambda gs, s: [c for c in gs.card_filter.in_play().lands.result()
                              if c.props.slug not in BASIC_LANDS]

    @staticmethod
    def non_creature_artifacts():
        return lambda gs, s: gs.card_filter.in_play().non_creature_artifacts().result()

    @staticmethod
    def non_fliers():
        return lambda gs, _: gs.card_filter.in_play().creatures().has(KW.FLYING, False).result()

    @staticmethod
    def non_token_creatures():
        return lambda gs, s: gs.card_filter.in_play().non_token().creatures().result()

    @staticmethod
    def non_token_permanents():
        return lambda gs, s: gs.card_filter.in_play().non_token().permanents().result()

    @staticmethod
    def non_wall_creatures():
        return lambda gs, s: gs.card_filter.in_play().non_wall_creatures().result()

    @staticmethod
    def non_wall_creatures_wo_summoning_sickness():
        return lambda gs, s: [c for c in gs.card_filter.in_play().non_wall_creatures().result()
                              if not c.has_summoning_sickness]

    @staticmethod
    def non_wall_non_fliers():
        return lambda gs, s: gs.card_filter.in_play().non_wall_creatures().has(KW.FLYING, False).result()

    @staticmethod
    def non_white_creatures():
        return lambda gs, s: gs.card_filter.in_play().non_white().creatures().result()

    @staticmethod
    def one_one_creatures():
        return lambda gs, s: [c for c in gs.card_filter.in_play().creatures().result()
                              if c.power == 1 and c.toughness == 1]

    @staticmethod
    def opp():
        return lambda gs, s: flip(s.owner_id)

    @staticmethod
    def opp_artifacts():
        return lambda gs, s: gs.card_filter.on_player_board(flip(s.owner_id)).artifacts().result()

    @staticmethod
    def opp_attackers():
        return lambda gs, s: gs.card_filter.on_player_board(flip(s.owner_id)).attackers().result()

    @staticmethod
    def opp_creatures():
        return lambda gs, s: gs.card_filter.on_player_board(flip(s.owner_id)).creatures().result()

    @staticmethod
    def opp_creatures_power_not_greater_than_source():
        return lambda gs, s: [c for c in gs.card_filter.on_player_board(flip(s.owner_id)).creatures().result()
                              if c.power <= s.power]

    @staticmethod
    def opp_creatures_who_could_have_but_didnt_attack():
        return lambda gs, s: [c for c in gs.card_filter.on_player_board(flip(s.owner_id)).creatures().result()
                              if c not in gs.card_filter.attackers().result()
                              and not c.has_summoning_sickness and 'Defender' not in c.keyword_abilities]

    @staticmethod
    def opp_legendary_creatures():
        return lambda gs, s: gs.card_filter.on_player_board(flip(s.owner_id)).legendary().creatures().result()

    @staticmethod
    def opp_non_token_perms():
        return lambda gs, s: [c for c in gs.card_filter.on_player_board(flip(s.owner_id)).permanents.result()
                              if not c.is_token]

    @staticmethod
    def opp_non_wall_creatures():
        return lambda gs, s: gs.card_filter.on_player_board(flip(s.owner_id)).non_wall_creatures().result()

    @staticmethod
    def opp_tapped_artifacts():
        return lambda gs, s: gs.card_filter.on_player_board(flip(s.owner_id)).tapped().artifacts().result()

    @staticmethod
    def opp_untapped_artifacts():
        return lambda gs, s: gs.card_filter.on_player_board(flip(s.owner_id)).untapped().artifacts().result()

    @staticmethod
    def other_creatures():
        return lambda gs, s: [c for c in CF.creatures()(gs, s) if c is not s]

    @staticmethod
    def other_merfolk():
        return lambda gs, s: [c for c in gs.card_filter.in_play().creatures().by_sub_type('Merfolk').result()
                              if c is not s]

    @staticmethod
    def other_zombies():
        return lambda gs, s: [c for c in gs.card_filter.in_play().creatures().by_sub_type('Zombie').result()
                              if c is not s]

    @staticmethod
    def owner():
        return lambda gs, s: s.owner_id

    @staticmethod
    def permanents():
        return lambda gs, s: gs.card_filter.in_play().permanents().result()

    @staticmethod
    def perms_you_own_and_control():
        return lambda gs, s: [p for p in gs.card_filter.in_play().permanents().result()
                              if id(p) in {id(y) for y in gs.card_filter.on_player_board(s.owner_id).result()} &
                              {id(z) for z in gs.card_filter.on_player_board(s.owner_id).result()}]

    @staticmethod
    def plague_rats():
        return lambda gs, s: gs.card_filter.in_play().by_slug('plague-rats').result()

    @staticmethod
    def plains():
        return lambda gs, s: gs.card_filter.in_play().plains().result()

    @staticmethod
    def red():
        return lambda gs, s: gs.card_filter.in_play().red().result()

    @staticmethod
    def red_permanents():
        return lambda gs, s: gs.card_filter.in_play().permanents().red().result()

    @staticmethod
    def red_spells():
        return lambda gs, s: [s for s in gs.action_stack.spells if s.card.is_red]

    @staticmethod
    def self():
        return lambda gs, s: s

    @staticmethod
    def spells():
        return lambda gs, s: gs.action_stack.spells

    @staticmethod
    def spells_aura_or_instant_targeting_your_perm():
        return lambda gs, s: [spell for spell in gs.stack
                              if (('Instant' in spell.types or 'Aura' in spell.types)
                                  and any(isinstance(t, GameCard) and t.owner_id == s.owner_id
                                          and t.zone == Zone.BATTLEFIELD for t in spell.targets))]

    @staticmethod
    def spells_instants():
        return lambda gs, s: [spell for spell in gs.action_stack.spells if 'Instant' in spell.types]

    @staticmethod
    def stone_giant():
        return lambda gs, s: [c for c in gs.card_filter.on_player_board(s.owner_id).creatures().result()
                              if c.toughness < s.power]

    @staticmethod
    def tapped_creatures():
        return lambda gs, s: gs.card_filter.in_play().creatures().tapped().result()

    @staticmethod
    def tapped_or_blocking_creatures():
        return lambda gs, s: list(set(gs.card_filter.blockers().result() +
                                      gs.card_filter.tapped().creatures().result()))

    @staticmethod
    def tapped_lands():
        return lambda gs, s: gs.card_filter.in_play().lands().tapped().result()

    @staticmethod
    def unblocked_attackers():
        return lambda gs, s: gs.card_filter.unblocked_attackers().result()

    @staticmethod
    def unenchanted_perms():
        return lambda gs, s: gs.card_filter.is_enchanted(False).permanents().in_play().result()

    @staticmethod
    def untapped_artifacts():
        return lambda gs, s: gs.card_filter.in_play().artifacts().untapped().result()

    @staticmethod
    def untapped_artifacts_creatures_lands():
        return lambda gs, s: gs.card_filter.in_play().by_type(['Artifact', 'Creature', 'Land']).untapped().result()

    @staticmethod
    def untapped_creatures():
        return lambda gs, s: gs.card_filter.in_play().creatures().untapped().result()

    @staticmethod
    def untapped_creatures_without_flying():
        return lambda gs, s: gs.card_filter.in_play().creatures().untapped().has(KW.FLYING, False).result()

    @staticmethod
    def walls():
        return lambda gs, s: gs.card_filter.in_play().walls().result()

    @staticmethod
    def white_creatures():
        return lambda gs, s: gs.card_filter.in_play().white().creatures().result()

    @staticmethod
    def white():
        return lambda gs, s: gs.card_filter.in_play().white().result()

    @staticmethod
    def your_artifacts():
        return lambda gs, s: gs.card_filter.on_player_board(s.owner_id).artifacts().result()

    @staticmethod
    def your_attackers():
        return lambda gs, s: gs.card_filter.on_player_board(s.owner_id).attackers().result()

    @staticmethod
    def your_kobolds_of_kher_keep():
        return lambda gs, s: gs.card_filter.on_player_board(s.owner_id).by_slug('kobolds-of-kher-keep').result()

    @staticmethod
    def your_creatures():
        return lambda gs, s: gs.card_filter.on_player_board(s.owner_id).creatures().result()

    @staticmethod
    def your_dwarves():
        return lambda gs, s: gs.card_filter.on_player_board(s.owner_id).by_sub_type('Dwarf').result()

    @staticmethod
    def your_green_creatures():
        return lambda gs, s: gs.card_filter.on_player_board(s.owner_id).creatures().green().result()

    @staticmethod
    def your_forests():
        return lambda gs, s: gs.card_filter.on_player_board(s.owner_id).forests().result()

    @staticmethod
    def your_lands():
        return lambda gs, s: gs.card_filter.on_player_board(s.owner_id).lands().result()

    @staticmethod
    def your_non_creature_artifacts():
        return lambda gs, s: gs.card_filter.on_player_board(s.owner_id).non_creature_artifacts().result()

    @staticmethod
    def your_non_wall_creatures():
        return lambda gs, s: gs.card_filter.on_player_board(s.owner_id).non_wall_creatures().result()

    @staticmethod
    def your_other_creatures():
        return lambda gs, s: [c for c in gs.card_filter.on_player_board(s.owner_id).creatures().result() if c is not s]

    @staticmethod
    def your_other_goblins():
        return lambda gs, s: [c for c in gs.card_filter.on_player_board(s.owner_id).by_sub_type('Goblin').result()
                              if c is not s]

    @staticmethod
    def your_other_orcs():
        return lambda gs, s: [c for c in gs.card_filter.on_player_board(s.owner_id).by_sub_type('Orc').result()
                              if c is not s]

    @staticmethod
    def your_other_kobolds():
        return lambda gs, s: [c for c in gs.card_filter.on_player_board(s.owner_id).by_sub_type('Kobold').result()
                              if c is not s]

    @staticmethod
    def your_permanents():
        return lambda gs, s: gs.card_filter.on_player_board(s.owner_id).permanents().result()

    @staticmethod
    def your_swamps():
        return lambda gs, s: gs.card_filter.on_player_board(s.owner_id).swamps().result()

    @staticmethod
    def your_tapped_blue_creatures():
        return lambda gs, s: gs.card_filter.on_player_board(s.owner_id).tapped().blue().creatures().result()

    @staticmethod
    def your_tapped_lands():
        return lambda gs, s: gs.card_filter.on_player_board(s.owner_id).lands().tapped().result()

    @staticmethod
    def your_untapped_creatures():
        return lambda gs, s: gs.card_filter.on_player_board(s.owner_id).creatures().untapped().result()

    @staticmethod
    def your_untapped_non_attacking_creatures():
        return lambda gs, s: [c for c in gs.card_filter.on_player_board(s.owner_id).creatures().untapped().result()
                              if c not in gs.card_filter.attackers().result().copy()]

    @staticmethod
    def your_untapped_white_creatures():
        return lambda gs, s: gs.card_filter.on_player_board(s.owner_id).creatures().untapped().white().result()

    @staticmethod
    def your_walls():
        return lambda gs, s: gs.card_filter.on_player_board(s.owner_id).in_play().walls().result()
