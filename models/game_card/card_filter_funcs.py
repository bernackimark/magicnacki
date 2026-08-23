from __future__ import annotations
from typing import Callable, TYPE_CHECKING

if TYPE_CHECKING:
    from game_state import GameState
    from game_card import GameCard
    from models.actions.base import Action

from models.constants import Target, ALL_PLAYER_INDICES, BASIC_LANDS, KW, Zone
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
    'no_lands': lambda gs, s: len(T_FUNCS['lands'](gs, s)) == 0,
    'opp_has_island': lambda gs, s: gs.card_filter.on_player_board(flip(s.owner_id)).islands().result(),
    'opp_has_non_token_white_perm': lambda gs, s: gs.card_filter.on_player_board(flip(s.owner_id)).non_token().white().permanents().result(),
    'you_have_a_dwarf': lambda gs, s: len(T_FUNCS['your_dwarves'](gs, s)) > 0,
    'you_have_a_forest': lambda gs, s: gs.card_filter.on_player_board(s.owner_id).forests().result(),
    'you_have_a_swamp': lambda gs, s: gs.card_filter.on_player_board(s.owner_id).forests().result(),
    'you_have_no_lands': lambda gs, s: len(T_FUNCS['your_lands'](gs, s)) == 0
}

"""
Maps string keys to lambda functions that simplifies slug-effect map;
Always follows "lambda GameState, source: " and returns a list;
Ex: T_FUNCS['black_creatures'] in 'bad-moon' -> lambda gs, s: gs.card_filter.in_play().creatures().black().result()
Since 90% of lookups seek cards on battlefield, keys that don't specify will only return those on battlfield.
Ex: 'artifacts' will only return artifact creatures currently on the battlefield.
Ex: 'artifacts_in_graveyards' explicitly indicates that it's looking somewhere besides the battlefield."""
T_FUNCS: [str, Callable[[GameState, GameCard], list[Target | GameCard | Action | int | None]]] = {
    # --- COMMON TARGET FUNCS ---
    'active_volcano_targets': lambda gs, s: gs.card_filter.in_play().blue().permanents().result() +
                                 gs.card_filter.in_play().islands().result(),
    'all_creatures_and_players': lambda gs, s: gs.card_filter.in_play().creatures().result() + [0, 1],
    'all_lands_in_game': lambda gs, s: gs.card_filter.lands().result(),
    'all_players': lambda gs, s: [0, 1],
    'another_orc_or_goblin':
        lambda gs, s: [c for c in gs.card_filter.in_play().by_sub_type(['Orc', 'Golbin']).result() if c is not s],
    'artifact_creatures': lambda gs, s: gs.card_filter.in_play().artifacts().creatures().result(),
    'artifact_spells': lambda gs, s: [s for s in gs.action_stack.spells if s.card.is_artifact],
    'artifacts_and_enchantments': lambda gs, s: gs.card_filter.in_play().by_type(['Artifact', 'Enchantment']).result(),
    'artifacts_creatures_enchantments': lambda gs, s: gs.card_filter.in_play().by_type(['Artifact', 'Creature', 'Enchantment']).result(),
    'artifacts_creatures_lands': lambda gs, s: gs.card_filter.in_play().by_type(['Artifact', 'Creature', 'Land']).result(),
    'artifacts': lambda gs, s: gs.card_filter.in_play().artifacts().result(),
    'artifacts_in_graveyards': lambda gs, s: gs.card_filter.in_graveyards().artifacts().result(),
    'artifacts_in_your_graveyard': lambda gs, s: gs.card_filter.in_player_graveyard(s.owner_id).artifacts().result(),
    'assembly_workers': lambda gs, s: gs.card_filter.in_play().by_sub_type('Assembly-Worker').result(),
    'attackers': lambda gs, s: gs.card_filter.attackers().result(),
    'auras_on_creatures': lambda gs, s: [a for c in gs.card_filter.in_play().creatures().result() for a in c.auras],
    'auras_on_lands': lambda gs, s: [a for c in gs.card_filter.in_play().lands().result() for a in c.auras],
    'auras_on_creatures_or_lands': lambda gs, s: [a for c in gs.card_filter.in_play().creatures().result() for a in c.auras] + \
        [a for c in gs.card_filter.in_play().lands().result() for a in c.auras],
    'auras_on_owners_creatures': lambda gs, s: [a for c in gs.card_filter.on_player_board(s.owner_id).creatures().result()
                                                for a in c.auras],
    'black': lambda gs, s: gs.card_filter.in_play().black().result(),
    'black_and_red': lambda gs, s: gs.card_filter.in_play().black().result() + gs.card_filter.in_play().red().result(),
    'black_creatures': lambda gs, s: gs.card_filter.in_play().creatures().black().result(),
    'black_permanents': lambda gs, s: gs.card_filter.in_play().permanents().black().result(),
    'black_spells': lambda gs, s: [s for s in gs.action_stack.spells if s.card.is_black],
    'blockers': lambda gs, s: gs.card_filter.blockers().result(),
    'blocking_walls': lambda gs, s: gs.card_filter.blockers().walls().result(),
    'blue': lambda gs, s: gs.card_filter.in_play().blue().result(),
    'blue_creatures': lambda gs, s: gs.card_filter.in_play().creatures().blue().result(),
    'blue_permanents': lambda gs, s: gs.card_filter.in_play().permanents().blue().result(),
    'blue_spells': lambda gs, s: [s for s in gs.action_stack.spells if s.card.is_blue],
    'cards': lambda gs, s: gs.card_filter.in_play().result(),
    'cards_in_your_graveyard': lambda gs, s: gs.card_filter.in_player_graveyard(s.owner_id).result(),
    'cards_in_your_hand': lambda gs, s: gs.card_filter.in_player_hand(s.owner_id).result(),
    'city_in_a_bottle': lambda gs, s: [c for c in
                                       gs.card_filter.in_play().non_token().permanents().by_set_code('arn').result()
                                       if c.props.slug != 'city-in-a-bottle'],
    'combatants': lambda gs, s: gs.card_filter.combatants().result(),
    'combating_against': lambda gs, s: gs.card_filter.combating_against(s).result(),
    'creature_spells': lambda gs, s: [s for s in gs.action_stack.spells if s.card.is_creature],
    'creatures_in_all_graveyards': lambda gs, s: gs.card_filter.in_graveyards().creatures().result(),
    'creatures': lambda gs, s: gs.card_filter.in_play().creatures().result(),
    'creatures_w_forestwalk': lambda gs, s: gs.card_filter.in_play().has(KW.FORESTWALK).result(),
    'creatures_wo_forestwalk': lambda gs, s: gs.card_filter.in_play().has(KW.FORESTWALK, False).result(),
    'creatures_in_your_graveyard': lambda gs, s: gs.card_filter.in_player_graveyard(s.owner_id).creatures().result(),
    'creatures_and_enchantments': lambda gs, s: gs.card_filter.in_play().by_type(['Creature', 'Enchantment']).result(),
    'creatures_and_lands': lambda gs, s: gs.card_filter.in_play().creatures().result() +
                                         gs.card_filter.in_play().lands().result(),
    'creatures_and_players': lambda gs, s: gs.card_filter.in_play().creatures().result() + ALL_PLAYER_INDICES,
    'creatures_power_two_or_less': lambda gs, s: [c for c in gs.card_filter.in_play().creatures().result()
                                                  if c.power <= 2],
    'creatures_power_three_or_more': lambda gs, s: [c for c in gs.card_filter.in_play().creatures().result()
                                                    if c.power >= 3],
    'creatures_with_first_strike': lambda gs, s: [c for c in gs.card_filter.in_play().creatures().result
                                                          if KW.FIRST_STRIKE in c.keyword_abilities],
    'creatures_with_swampwalk': lambda gs, s: [c for c in gs.card_filter.in_play().creatures().result
                                                       if KW.SWAMPWALK in c.keyword_abilities],
    'djinns_and_efreets': lambda gs, s: gs.card_filter.in_play().by_sub_type(['Djinn', 'Efreet']).result(),
    'elephants': lambda gs, s: gs.card_filter.in_play().by_sub_type('Elephant').result(),
    'enchanted_cards': lambda gs, s: gs.card_filter.is_enchanted().result(),
    'enchanted_creatures': lambda gs, s: gs.card_filter.is_enchanted().creatures().result(),
    'enchants': lambda gs, s: gs.card_filter.in_play.enchantments().result(),
    'enchants_in_your_graveyard': lambda gs, s: gs.card_filter.in_player_graveyard(s.owner_id).enchantments().result(),
    'flash_flood': lambda gs, s: gs.card_filter.in_play().red().permanents().result() +
                                 gs.card_filter.in_play().mountains().result(),
    'fliers': lambda gs, _: gs.card_filter.in_play().creatures().has(KW.FLYING).result(),
    'forests': lambda gs, _: gs.card_filter.in_play().forests().result(),
    'forests_in_your_hand': lambda gs, s: gs.card_filter.in_player_hand(s.owner_id).forests().result(),
    'forestwalkers': lambda gs, s: gs.card_filter.in_play().has(KW.FORESTWALK).result(),
    'goblin_permanents_in_your_hand': lambda gs, s: gs.card_filter.in_player_hand(s.owner_id).by_sub_type('Goblin').permanents().result(),
    'goblins': lambda gs, s: gs.card_filter.in_play().by_sub_type('Goblin').result(),
    'golgothian_sylex': lambda gs, s: [c for c in
                                       gs.card_filter.in_play().non_token().permanents().by_set_code('AQ').result()
                                       if c.props.slug != 'golgothian-sylex'],
    'green': lambda gs, s: gs.card_filter.in_play().green().result(),
    'green_and_white_creatures': lambda gs, s: [gs.card_filter.in_play().green().creatures().result()] +
                                               [gs.card_filter.in_play().white().creatures().result()],
    'green_creatures': lambda gs, s: gs.card_filter.in_play().creatures().green().result(),
    'green_spells': lambda gs, s: [s for s in gs.action_stack.spells if s.card.is_green],
    'host': lambda gs, s: s.host,
    'host_owner': lambda gs, s: s.host.owner_id,
    'in_turn_player': lambda gs, _: gs.player_turn_idx,
    'in_turn_player_tapped_blue_creatures': lambda gs, s: gs.card_filter.on_player_board(gs.player_turn_idx).tapped().blue().creatures().result(),
    'instant_spells': lambda gs, s: [s for s in gs.action_stack.spells if s.card.is_instant],
    'islands': lambda gs, s: gs.card_filter.in_play().islands().result(),
    'islandwalkers': lambda gs, s: gs.card_filter.in_play().has(KW.ISLANDWALK).result(),
    'lands': lambda gs, s: gs.card_filter.in_play().lands().result(),
    'legendary_creatures': lambda gs, s: gs.card_filter.in_play().legendary().creatures().result(),
    'non_artifact_creatures': lambda gs, s: gs.card_filter.in_play().non_artifact_creatures().result(),
    'non_artifact_non_black_creatures': lambda gs, s: gs.card_filter.non_artifact_creatures().non_black().result(),
    'non_artifact_non_white_creatures': lambda gs, s: gs.card_filter.non_artifact_creatures().non_white().result(),
    'non_basic_lands': lambda gs, s: [c for c in gs.card_filter.in_play().lands.result()
                                      if c.props.slug not in BASIC_LANDS],
    'non_creature_artifacts': lambda gs, s: gs.card_filter.in_play().non_creature_artifacts().result(),
    'non_fliers': lambda gs, _: gs.card_filter.in_play().creatures().has(KW.FLYING, False).result(),
    'non_token_creatures': lambda gs, s: gs.card_filter.in_play().non_token().creatures().result(),
    'non_token_permanents': lambda gs, s: gs.card_filter.in_play().non_token().permanents().result(),
    'non_wall_creatures': lambda gs, s: gs.card_filter.in_play().non_wall_creatures().result(),
    'non_wall_creatures_wo_summoning_sickness': lambda gs, s: [c for c in gs.card_filter.in_play().non_wall_creatures().result()
                                                               if not c.has_summoning_sickness],
    'non_wall_non_fliers': lambda gs, s: gs.card_filter.in_play().non_wall_creatures().has(KW.FLYING, False).result(),
    'non_white_creatures': lambda gs, s: gs.card_filter.in_play().non_white().creatures().result(),
    'one_one_creatures': lambda gs, s: [c for c in gs.card_filter.in_play().creatures().result()
                                        if c.power == 1 and c.toughness == 1],
    'opp': lambda gs, s: flip(s.owner_id),
    'opp_artifacts': lambda gs, s: gs.card_filter.on_player_board(flip(s.owner_id)).artifacts().result(),
    'opp_attackers': lambda gs, s: gs.card_filter.on_player_board(flip(s.owner_id)).attackers().result(),
    'opp_creatures': lambda gs, s: gs.card_filter.on_player_board(flip(s.owner_id)).creatures().result(),
    'opp_creatures_power_not_greater_than_source':
        lambda gs, s: [c for c in gs.card_filter.on_player_board(flip(s.owner_id)).creatures().result()
                       if c.power <= s.power],
    'opp_creatures_who_could_have_but_didnt_attack':
        lambda gs, s: [c for c in gs.card_filter.on_player_board(flip(s.owner_id)).creatures().result()
                       if c not in gs.card_filter.attackers().result()
                       and not c.has_summoning_sickness and 'Defender' not in c.keyword_abilities],
    'opp_legendary_creatures': lambda gs, s: gs.card_filter.on_player_board(flip(s.owner_id)).legendary().creatures().result(),
    'opp_non_token_perms':
        lambda gs, s: [c for c in gs.card_filter.on_player_board(flip(s.owner_id)).permanents.result()
                       if not c.is_token],
    'opp_non_wall_creatures': lambda gs, s: gs.card_filter.on_player_board(flip(s.owner_id)).non_wall_creatures().result(),
    'opp_tapped_artifacts': lambda gs, s: gs.card_filter.on_player_board(flip(s.owner_id)).tapped().artifacts().result(),
    'opp_untapped_artifacts': lambda gs, s: gs.card_filter.on_player_board(flip(s.owner_id)).untapped().artifacts().result(),
    'other_creatures': lambda gs, s: [c for c in T_FUNCS['creatures'](gs, s) if c is not s],
    'other_merfolk': lambda gs, s: [c for c in gs.card_filter.in_play().creatures().by_sub_type('Merfolk').result()
                                    if c is not s],
    'other_zombies': lambda gs, s: [c for c in gs.card_filter.in_play().creatures().by_sub_type('Zombie').result()
                                    if c is not s],
    'owner': lambda gs, s: s.owner_id,
    'permanents': lambda gs, s: gs.card_filter.in_play().permanents().result(),
    'perms_you_own_and_control': lambda gs, s: [p for p in gs.card_filter.in_play().permanents().result()
                                                if id(p) in {id(y) for y in gs.card_filter.on_player_board(s.owner_id).result()} &
                                                {id(z) for z in gs.card_filter.on_player_board(s.owner_id).result()}],
    'plague_rats': lambda gs, s: gs.card_filter.in_play().by_slug('plague-rats').result(),
    'plains': lambda gs, s: gs.card_filter.in_play().plains().result(),
    'red': lambda gs, s: gs.card_filter.in_play().red().result(),
    'red_permanents': lambda gs, s: gs.card_filter.in_play().permanents().red().result(),
    'red_spells': lambda gs, s: [s for s in gs.action_stack.spells if s.card.is_red],
    'self': lambda gs, s: s,
    'spells': lambda gs, s: gs.action_stack.spells,
    'spells_aura_or_instant_targeting_your_perm':
        (lambda gs, s: [spell for spell in gs.stack if (('Instant' in spell.types or 'Aura' in spell.types)
                                                        and any(isinstance(t, GameCard) and t.owner_id == s.owner_id
                                                        and t.zone == Zone.BATTLEFIELD for t in spell.targets))]),
    'spells_instants': lambda gs, s: [spell for spell in gs.action_stack.spells if 'Instant' in spell.types],
    'stone_giant': lambda gs, s: [c for c in gs.card_filter.on_player_board(s.owner_id).creatures().result()
                                  if c.toughness < s.power],
    'tapped_creatures': lambda gs, s: gs.card_filter.in_play().creatures().tapped().result(),
    'tapped_or_blocking_creatures': lambda gs, s: list(set(gs.card_filter.blockers().result() +
                                                           gs.card_filter.tapped().creatures().result())),
    'tapped_lands': lambda gs, s: gs.card_filter.in_play().lands().tapped().result(),
    'unblocked_attackers': lambda gs, s: gs.card_filter.unblocked_attackers().result(),
    'unenchanted_perms': lambda gs, s: gs.card_filter.is_enchanted(False).permanents().in_play().result(),
    'untapped_artifacts': lambda gs, s: gs.card_filter.in_play().artifacts().untapped().result(),
    'untapped_artifacts_creatures_lands': lambda gs, s: gs.card_filter.in_play().by_type(['Artifact', 'Creature', 'Land']).untapped().result(),
    'untapped_creatures': lambda gs, s: gs.card_filter.in_play().creatures().untapped().result(),
    'untapped_creatures_without_flying':
        lambda gs, s: gs.card_filter.in_play().creatures().untapped().has(KW.FLYING, False).result(),
    'walls': lambda gs, s: gs.card_filter.in_play().walls().result(),
    'white_creatures': lambda gs, s: gs.card_filter.in_play().white().creatures().result(),
    'white': lambda gs, s: gs.card_filter.in_play().white().result(),
    'your_artifacts': lambda gs, s: gs.card_filter.on_player_board(s.owner_id).artifacts().result(),
    'your_attackers': lambda gs, s: gs.card_filter.on_player_board(s.owner_id).attackers().result(),
    'your_kobolds_of_kher_keep': lambda gs, s: gs.card_filter.on_player_board(s.owner_id).by_slug('kobolds-of-kher-keep').result(),
    'your_creatures': lambda gs, s: gs.card_filter.on_player_board(s.owner_id).creatures().result(),
    'your-dwarves': lambda gs, s: gs.card_filter.on_player_board(s.owner_id).by_sub_type('Dwarf').result(),
    'your_green_creatures': lambda gs, s: gs.card_filter.on_player_board(s.owner_id).creatures().green().result(),
    'your_forests': lambda gs, s: gs.card_filter.on_player_board(s.owner_id).forests().result(),
    'your_lands': lambda gs, s: gs.card_filter.on_player_board(s.owner_id).lands().result(),
    'your_non_creature_artifacts': lambda gs, s: gs.card_filter.on_player_board(s.owner_id).non_creature_artifacts().result(),
    'your_non_wall_creatures': lambda gs, s: gs.card_filter.on_player_board(s.owner_id).non_wall_creatures().result(),
    'your_other_creatures':
        lambda gs, s: [c for c in gs.card_filter.on_player_board(s.owner_id).creatures().result() if c is not s],
    'your_other_orcs':
        lambda gs, s: [c for c in gs.card_filter.on_player_board(s.owner_id).by_sub_type('Orc').result()
                       if c is not s],
    'your_other_kobolds':
        lambda gs, s: [c for c in gs.card_filter.on_player_board(s.owner_id).by_sub_type('Kobold').result()
                       if c is not s],
    'your_permanents': lambda gs, s: gs.card_filter.on_player_board(s.owner_id).permanents().result(),
    'your_swamps': lambda gs, s: gs.card_filter.on_player_board(s.owner_id).swamps().result(),
    'your_tapped_blue_creatures': lambda gs, s: gs.card_filter.on_player_board(s.owner_id).tapped().blue().creatures().result(),
    'your_tapped_lands': lambda gs, s: gs.card_filter.on_player_board(s.owner_id).lands().tapped().result(),
    'your_untapped_creatures':
        lambda gs, s: gs.card_filter.on_player_board(s.owner_id).creatures().untapped().result(),
    'your_untapped_non_attacking_creatures':
        lambda gs, s: [c for c in gs.card_filter.on_player_board(s.owner_id).creatures().untapped().result() if c not in
                       gs.card_filter.attackers().result().copy()],
    'your_untapped_white_creatures':
        lambda gs, s: gs.card_filter.on_player_board(s.owner_id).creatures().untapped().white().result(),
    'your_walls': lambda gs, s: gs.card_filter.on_player_board(s.owner_id).in_play().walls().result(),
}
