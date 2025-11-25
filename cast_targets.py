from card_filter import CardFilter


def all_player_indices(gs):
    return list(range(gs.player_cnt))


CAST_TARGETS = {
    'animate-wall': lambda gs: CardFilter(gs).in_play().walls().result(),
    'braingeyser': lambda gs: all_player_indices(gs),
    'brainwash': lambda gs: CardFilter(gs).in_play().creatures().result(),
    'disenchant': lambda gs: CardFilter(gs).in_play().by_type(['Artifact', 'Enchantment']).result(),
    'drain-power': lambda gs: all_player_indices(gs),
    'energy-tap': lambda gs: CardFilter(gs).on_player_board(gs.player_turn_idx).creatures().tapped(False).result(),
    'farmstead': lambda gs: CardFilter(gs).on_player_board(gs.player_turn_idx).lands.result(),
    'feedback': lambda gs: CardFilter(gs).in_play().by_type('Enchantment').result(),
    'jump': lambda gs: CardFilter(gs).in_play().creatures().result(),
    'mana-short': lambda gs: all_player_indices(gs),
    'psychic-venom': lambda gs: CardFilter(gs).in_play().lands().result(),
    'twiddle': lambda gs: CardFilter(gs).in_play().by_type(['Artifact', 'Creature', 'Land']).result(),
    'unsummon': lambda gs: CardFilter(gs).in_play().creatures().result()
}
