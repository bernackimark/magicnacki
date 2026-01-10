from card_filter import CardFilter
from utils import flip


def all_player_indices(gs):
    return list(range(gs.player_cnt))


CAST_TARGETS = {
    'animate-wall': lambda gs: CardFilter(gs).in_play().walls().result(),
    'ancestral-recall': lambda gs: all_player_indices(gs),
    'artifact-ward': lambda gs: CardFilter(gs).in_play().creatures().result(),
    'blood-lust': lambda gs: CardFilter(gs).in_play().creatures().result(),
    'boomerang': lambda gs: CardFilter(gs).in_play().permanents().result(),
    'braingeyser': lambda gs: all_player_indices(gs),
    'brainwash': lambda gs: CardFilter(gs).in_play().creatures().result(),
    'burrowing': lambda gs: CardFilter(gs).in_play().creatures().result(),
    'curse-artifact': lambda gs: CardFilter(gs).in_play().artifacts().result(),
    'cursed-land': lambda gs: CardFilter(gs).in_play().lands.result(),
    'crumble': lambda gs: CardFilter(gs).in_play().artifacts().result(),
    'demonic-torment': lambda gs: CardFilter(gs).in_play().creatures().result(),
    'desert-twister': lambda gs: CardFilter(gs).in_play().permanents().result(),
    'disenchant': lambda gs: CardFilter(gs).in_play().by_type(['Artifact', 'Enchantment']).result(),
    'divine-offering': lambda gs: CardFilter(gs).in_play().artifacts().result(),
    'drain-power': lambda gs: all_player_indices(gs),
    'earthbind': lambda gs: CardFilter(gs).in_play().creatures().result(),
    'energy-tap': lambda gs: CardFilter(gs).on_player_board(gs.player_turn_idx).creatures().untapped().result(),
    'erosion': lambda gs: CardFilter(gs).in_play().lands().result(),
    'eternal-warrior': lambda gs: CardFilter(gs).in_play().creatures().result(),
    'eye-for-an-eye': lambda gs: CardFilter(gs).in_play().result(),
    'farmstead': lambda gs: CardFilter(gs).on_player_board(gs.player_turn_idx).lands.result(),
    'feedback': lambda gs: CardFilter(gs).in_play().by_type('Enchantment').result(),
    'feint': lambda gs: CardFilter(gs).attackers().result(),
    'firebreathing': lambda gs: CardFilter(gs).in_play().creatures().result(),
    'fishliver-oil': lambda gs: CardFilter(gs).in_play().creatures().result(),
    'flashfires': lambda gs: CardFilter(gs).in_play().by_slug('plains').result(),
    'gaseous-form': lambda gs: CardFilter(gs).in_play().creatures().result(),
    'giant-growth': lambda gs: CardFilter(gs).in_play().creatures().result(),
    'giant-strength': lambda gs: CardFilter(gs).in_play().creatures().result(),
    'great-defender': lambda gs: CardFilter(gs).in_play().creatures().result(),
    'ice-storm': lambda gs: CardFilter(gs).in_play().lands().result(),
    'immolation': lambda gs: CardFilter(gs).in_play().creatures().result(),
    'indestructible-aura': lambda gs: CardFilter(gs).in_play().creatures().result(),
    'instill-energy': lambda gs: CardFilter(gs).in_play().creatures().result(),
    'jovial-evil': lambda gs: flip(gs.action_on_idx),  # test this
    'jump': lambda gs: CardFilter(gs).in_play().creatures().result(),
    'lightning-bolt': lambda gs: CardFilter(gs).in_play().creatures().result() + all_player_indices(gs),
    'mana-short': lambda gs: all_player_indices(gs),
    'martyrs-cry': lambda gs: CardFilter(gs).in_play().creatures().white().result(),
    'psychic-venom': lambda gs: CardFilter(gs).in_play().lands().result(),
    'shatter': lambda gs: CardFilter(gs).in_play().artifacts().result(),
    'sinkhole': lambda gs: CardFilter(gs).in_play().lands().result(),
    'spirit-link': lambda gs: CardFilter(gs).in_play().creatures().result(),
    'stone_rain': lambda gs: CardFilter(gs).in_play().lands().result(),
    'storm-seeker': lambda gs: all_player_indices(gs),
    'subdue': lambda gs: CardFilter(gs).in_play().creatures().result(),
    'twiddle': lambda gs: CardFilter(gs).in_play().by_type(['Artifact', 'Creature', 'Land']).result(),
    'unsummon': lambda gs: CardFilter(gs).in_play().creatures().result()
}
